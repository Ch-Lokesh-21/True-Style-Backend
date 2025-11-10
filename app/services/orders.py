"""
Service layer for Orders.
- Encapsulates all business logic: stock checks, payments, OTP handling, ownership checks,
  and transactional writes. Routes stay thin and declarative.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
import re
import secrets

from bson import ObjectId
from pymongo import ReturnDocument
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.api.deps import get_current_user  # only for typing/context, not used directly
from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.utils.crypto import encrypt_card_no
from app.schemas.object_id import PyObjectId
from app.schemas.orders import OrdersCreate, OrdersUpdate, OrdersOut
from app.crud import orders as orders_crud


# ----------------- helpers -----------------

def _to_oid(v: Any, field: str) -> ObjectId:
    try:
        return ObjectId(str(v))
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid {field}")

async def _get_payment_type_doc(payment_type_id: PyObjectId) -> dict:
    pt = await db["payment_types"].find_one({"_id": ObjectId(str(payment_type_id))})
    if not pt:
        raise HTTPException(status_code=400, detail="Unknown payment type")
    return pt

async def _get_payment_status_id_by_label(label: str) -> ObjectId:
    doc = await db["payment_status"].find_one({"status": label})
    if not doc:
        raise HTTPException(status_code=500, detail=f"Payment status '{label}' not found")
    return doc["_id"]

async def _get_address_for_user(address_id: PyObjectId, user_id: PyObjectId) -> dict:
    addr = await db["user_address"].find_one(
        {"_id": ObjectId(str(address_id)), "user_id": ObjectId(str(user_id))}
    )
    if not addr:
        raise HTTPException(status_code=404, detail="Address not found")
    return addr  # embed full snapshot or whitelist if needed

async def _get_cart_and_items_for_user(user_id: ObjectId) -> Tuple[dict, list]:
    cart = await db["carts"].find_one({"user_id": user_id})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    items = await db["cart_items"].find({"cart_id": cart["_id"]}).to_list(length=None)
    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    return cart, items

_UPI_RE = re.compile(r"^[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}$")

def _gen_otp(n: int = 6) -> str:
    """Return a cryptographically-strong zero-padded numeric OTP of length n."""
    return str(secrets.randbelow(10**n)).zfill(n)

async def _get_status_doc_by_id(status_id: PyObjectId) -> dict:
    doc = await db["order_status"].find_one({"_id": ObjectId(str(status_id))})
    if not doc:
        raise HTTPException(status_code=400, detail="Unknown order status")
    return doc

def _require_card_details(card_name: Optional[str], card_no: Optional[str]) -> tuple[str, str]:
    if not card_name or not card_name.strip():
        raise HTTPException(status_code=400, detail="card_name is required for CARD payments")
    if not card_no or not card_no.strip():
        raise HTTPException(status_code=400, detail="card_no is required for CARD payments")
    num = card_no.replace(" ", "")
    if not (12 <= len(num) <= 19) or not num.isdigit():
        raise HTTPException(status_code=400, detail="Invalid card_no (must be 12–19 digits)")
    return card_name.strip(), num

def _require_upi_details(upi_id: Optional[str]) -> str:
    if not upi_id or not upi_id.strip():
        raise HTTPException(status_code=400, detail="upi_id is required for UPI payments")
    val = upi_id.strip()
    if not _UPI_RE.fullmatch(val):
        raise HTTPException(status_code=400, detail="Invalid UPI format (expected something@bank)")
    return val


# ----------------- services -----------------

async def place_order_service(
    user_id: PyObjectId,
    address_id: PyObjectId,
    payment_type_id: PyObjectId,
    card_name: Optional[str],
    card_no: Optional[str],
    upi_id: Optional[str],
    current_user: Dict[str, Any],
) -> OrdersOut:
    """
    Create an order for the current user with full transactional flow:
    - Validate ownership, payment type/details.
    - Embed address snapshot.
    - Decrement product stock atomically; mark out_of_stock when it hits zero.
    - Create order, move cart_items → order_items, create payment (+ details).
    - Clear cart_items.
    """
    # owner check: user can only place own order
    if str(current_user.get("user_id", "")) != str(user_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    user_oid = _to_oid(user_id, "user_id")
    addr_doc = await _get_address_for_user(address_id, user_id)
    order_address = {
        "mobile_no": addr_doc["mobile_no"],
        "postal_code": addr_doc["postal_code"],
        "country": addr_doc["country"],
        "state": addr_doc["state"],
        "city": addr_doc["city"],
        "address": addr_doc["address"],
    }

    pay_type_doc = await _get_payment_type_doc(payment_type_id)
    ptype = str(pay_type_doc.get("type", "")).strip().lower()
    if ptype not in {"cod", "card", "upi"}:
        raise HTTPException(status_code=400, detail="Unsupported payment type")

    is_cod  = ptype == "cod"
    is_card = ptype == "card"
    is_upi  = ptype == "upi"

    payment_status_id = await _get_payment_status_id_by_label("pending" if is_cod else "success")

    # Gather cart + items (outside txn); writes happen inside txn
    cart, items = await _get_cart_and_items_for_user(user_oid)

    # Initial order status must be 'placed'
    order_status_doc = await db["order_status"].find_one({"status": "placed"})
    if not order_status_doc:
        raise HTTPException(status_code=500, detail="Order status 'placed' not found")

    # Validate payment details
    card_name_v, card_no_v, upi_id_v = None, None, None
    if is_card:
        card_name_v, card_no_v = _require_card_details(card_name, card_no)
    elif is_upi:
        upi_id_v = _require_upi_details(upi_id)

    session = await db.client.start_session()
    try:
        async with session.start_transaction():
            order_total = 0.0
            now = datetime.now(timezone.utc)

            # A) Check & decrement stock; compute totals
            for it in items:
                pid: ObjectId = it["product_id"]
                qty: int = int(it.get("quantity", 1))

                prod_after = await db["products"].find_one_and_update(
                    {"_id": pid, "quantity": {"$gte": qty}},
                    {"$inc": {"quantity": -qty}, "$currentDate": {"updatedAt": True}},
                    session=session,
                    return_document=ReturnDocument.AFTER,
                    projection={"price": 1, "total_price": 1, "quantity": 1, "out_of_stock": 1},
                )
                if not prod_after:
                    raise HTTPException(status_code=400, detail="Insufficient stock for a product in your cart")

                if int(prod_after.get("quantity", 0)) == 0 and not bool(prod_after.get("out_of_stock", False)):
                    await db["products"].update_one(
                        {"_id": pid, "out_of_stock": {"$ne": True}},
                        {"$set": {"out_of_stock": True}, "$currentDate": {"updatedAt": True}},
                        session=session,
                    )

                price = float(prod_after.get("total_price", prod_after.get("price", 0.0)))
                order_total += price * qty

            order_total = round(order_total, 2)

            # B) Create order
            order_payload = OrdersCreate(
                user_id=user_id,
                address=order_address,
                status_id=order_status_doc["_id"],
                total=order_total,
                delivery_otp=None,
            )
            order_doc = stamp_create(order_payload.model_dump(mode="python"))
            order_res = await db["orders"].insert_one(order_doc, session=session)
            order_id = order_res.inserted_id

            # C) Move cart_items → order_items
            oi_bulk = [
                {
                    "order_id": order_id,
                    "product_id": it["product_id"],
                    "quantity": it.get("quantity", 1),
                    "size": it.get("size"),
                    "user_id": user_oid,
                    "createdAt": now,
                    "updatedAt": now,
                }
                for it in items
            ]
            if oi_bulk:
                await db["order_items"].insert_many(oi_bulk, session=session)

            # D) Create payment
            payment_doc = stamp_create({
                "user_id": user_oid,
                "order_id": order_id,
                "payment_types_id": ObjectId(str(payment_type_id)),
                "payment_status_id": payment_status_id,
                "invoice_no": f"INV-{order_id}",
                "delivery_fee": 0.0,
                "amount": order_total,
            })
            pay_res = await db["payments"].insert_one(payment_doc, session=session)
            payment_id = pay_res.inserted_id

            # D1) Persist payment details (card/upi)
            if is_card:
                card_row = stamp_create({
                    "payment_id": payment_id,
                    "name": card_name_v,
                    "card_no": encrypt_card_no(card_no_v),
                })
                await db["card_details"].insert_one(card_row, session=session)

            if is_upi:
                upi_row = stamp_create({
                    "payment_id": payment_id,
                    "upi_id": upi_id_v,
                })
                await db["upi_details"].insert_one(upi_row, session=session)

            # E) Clear cart items
            await db["cart_items"].delete_many({"cart_id": cart["_id"]}, session=session)

        # Return saved order (outside txn)
        saved = await db["orders"].find_one({"_id": order_id})
        return OrdersOut.model_validate(saved)

    except HTTPException:
        raise
    except Exception as e:
        try:
            await session.abort_transaction()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to place order: {e}")
    finally:
        try:
            await session.end_session()
        except Exception:
            pass


async def list_my_orders_service(skip: int, limit: int, current_user: Dict[str, Any]) -> List[OrdersOut]:
    """
    List the current user's orders with pagination.
    """
    try:
        user_oid = ObjectId(str(current_user["user_id"]))
        return await orders_crud.list_all(skip=skip, limit=limit, query={"user_id": user_oid})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list orders: {e}")


async def get_my_order_service(order_id: PyObjectId, current_user: Dict[str, Any]) -> OrdersOut:
    """
    Get one order with ownership enforcement.
    """
    try:
        order = await orders_crud.get_one(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if str(order.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="Forbidden")
        return order
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get order: {e}")


async def admin_get_order_service(order_id: PyObjectId) -> OrdersOut:
    """
    Admin: get any order by id.
    """
    try:
        order = await orders_crud.get_one(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get order: {e}")


async def update_my_order_status_service(
    order_id: PyObjectId,
    payload: OrdersUpdate,
    current_user: Dict[str, Any],
) -> OrdersOut:
    """
    User updates their own order status.

    Requires:
        payload.status_id not None
    """
    try:
        if payload.status_id is None:
            raise HTTPException(status_code=400, detail="status_id is required")
        order = await orders_crud.get_one(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if str(order.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="Forbidden")

        updated = await orders_crud.update_one(order_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Order not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update order: {e}")


async def admin_update_order_status_service(order_id: PyObjectId, payload: OrdersUpdate) -> OrdersOut:
    """
    Admin: update order status_id.
      - If new status is 'out for delivery' → generate OTP and store it.
      - If new status is 'delivered' → clear OTP.
    """
    try:
        if payload.status_id is None:
            raise HTTPException(status_code=400, detail="status_id is required")

        sdoc = await _get_status_doc_by_id(payload.status_id)
        sname = str(sdoc.get("status", "")).strip().lower()

        updates: Dict[str, Any] = {"status_id": sdoc["_id"]}

        if sname in {"out for delivery", "out_for_delivery", "out-for-delivery"}:
            updates["delivery_otp"] = _gen_otp(6)
        elif sname in {"delivered"}:
            updates["delivery_otp"] = None

        updated_doc = await db["orders"].find_one_and_update(
            {"_id": ObjectId(str(order_id))},
            {"$set": stamp_update(updates)},
            return_document=True,
        )
        if not updated_doc:
            raise HTTPException(status_code=404, detail="Order not found")

        return OrdersOut.model_validate(updated_doc)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update order: {e}")


async def admin_delete_order_service(order_id: PyObjectId):
    """
    Admin: transactionally delete one order and related documents.

    Returns:
        JSONResponse({ "status": "deleted", "stats": {...} })
    """
    try:
        result = await orders_crud.delete_one_cascade(order_id)
        if result is None or result.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Order not found")
        if result.get("status") != "deleted":
            raise HTTPException(status_code=500, detail="Failed to delete order")
        return JSONResponse(status_code=200, content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete order: {e}")