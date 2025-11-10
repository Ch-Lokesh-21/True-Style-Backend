from __future__ import annotations
import datetime as dt
from datetime import datetime, timezone
from typing import List, Dict, Any

from bson import ObjectId
from app.core.database import db

TZ = "Asia/Kolkata"

# Helpers
def _date_floor_utc(days_back: int) -> datetime:
    now = datetime.now(timezone.utc)
    start = now - dt.timedelta(days=days_back)
    # normalize to midnight UTC; we’ll use $dateTrunc with TZ in pipelines
    return datetime(start.year, start.month, start.day)

# -----------------------------------------
# Overview
# -----------------------------------------
async def get_overview() -> Dict[str, Any]:
    users = await db["users"].count_documents({})
    products = await db["products"].count_documents({})
    orders = await db["orders"].count_documents({})
    returns = await db["returns"].count_documents({})
    exchanges = await db["exchanges"].count_documents({})

    # Revenue = sum(payments.amount where payment_status is a "paid-like" state)
    # If your payment_status has a canonical "paid" string, best to filter via lookup.
    # Here we optimistically sum non-null amounts for all payments with a successful status.
    paid_status_ids = []
    async for s in db["payment_status"].find(
        {"status": {"$in": ["success"]}}, {"_id": 1}
    ):
        paid_status_ids.append(s["_id"])

    match_stage = {"payment_status_id": {"$in": paid_status_ids}} if paid_status_ids else {}
    pipeline = [
        {"$match": match_stage} if match_stage else {"$match": {"amount": {"$ne": None}}},
        {"$group": {"_id": None, "sum": {"$sum": {"$ifNull": ["$amount", 0]}}}},
    ]
    agg = await db["payments"].aggregate(pipeline).to_list(1)
    revenue = float(agg[0]["sum"]) if agg else 0.0

    return {
        "users": users,
        "products": products,
        "orders": orders,
        "returns": returns,
        "exchanges": exchanges,
        "revenue": revenue,
    }

# -----------------------------------------
# Sales by day (sum payments.amount)
# -----------------------------------------
async def sales_series(days: int) -> List[Dict[str, Any]]:
    start_utc = _date_floor_utc(days)
    pipeline = [
        {"$match": {"createdAt": {"$gte": start_utc}}},
        {"$group": {
            "_id": {
                "$dateTrunc": {
                    "date": "$createdAt",
                    "unit": "day",
                    "timezone": TZ
                }
            },
            "value": {"$sum": {"$ifNull": ["$amount", 0]}},
        }},
        {"$sort": {"_id": 1}},
    ]
    rows = await db["payments"].aggregate(pipeline).to_list(None)
    return [{"date": r["_id"].date().isoformat(), "value": float(r["value"])} for r in rows]

# -----------------------------------------
# User growth (new users per day)
# -----------------------------------------
async def user_growth(days: int) -> List[Dict[str, Any]]:
    start_utc = _date_floor_utc(days)
    pipeline = [
        {"$match": {"createdAt": {"$gte": start_utc}}},
        {"$group": {
            "_id": {
                "$dateTrunc": {
                    "date": "$createdAt",
                    "unit": "day",
                    "timezone": TZ
                }
            },
            "value": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    rows = await db["users"].aggregate(pipeline).to_list(None)
    return [{"date": r["_id"].date().isoformat(), "value": float(r["value"])} for r in rows]

# -----------------------------------------
# Top products (by sold quantity/revenue)
# -----------------------------------------
async def top_products(limit: int) -> List[Dict[str, Any]]:
    pipeline = [
        # order_item joins product for name, price computed via payments is indirect.
        # We'll aggregate quantities from order_item and multiply by products.total_price
        {"$lookup": {
            "from": "products",
            "localField": "product_id",
            "foreignField": "_id",
            "as": "prod"
        }},
        {"$unwind": "$prod"},
        {"$group": {
            "_id": "$product_id",
            "name": {"$first": "$prod.name"},
            "total_quantity": {"$sum": {"$ifNull": ["$quantity", 0]}},
            "total_orders": {"$addToSet": "$order_id"},
            "unit_price": {"$first": {"$ifNull": ["$prod.total_price", 0]}},
        }},
        {"$project": {
            "_id": 0,
            "product_id": {"$toString": "$_id"},
            "name": 1,
            "total_quantity": 1,
            "total_orders": {"$size": "$total_orders"},
            "total_revenue": {"$multiply": ["$total_quantity", "$unit_price"]}
        }},
        {"$sort": {"total_quantity": -1, "total_revenue": -1}},
        {"$limit": limit},
    ]
    rows = await db["order_item"].aggregate(pipeline).to_list(None)
    # coerce numerics
    for r in rows:
        r["total_revenue"] = float(r.get("total_revenue", 0.0))
        r["total_quantity"] = int(r.get("total_quantity", 0))
        r["total_orders"] = int(r.get("total_orders", 0))
    return rows

# -----------------------------------------
# Low stock
# -----------------------------------------
async def low_stock(threshold: int) -> List[Dict[str, Any]]:
    cursor = db["products"].find({"quantity": {"$lte": threshold}}, {"_id": 1, "name": 1, "quantity": 1}).sort("quantity", 1)
    items: List[Dict[str, Any]] = []
    async for d in cursor:
        items.append({
            "product_id": str(d["_id"]),
            "name": d.get("name", ""),
            "quantity": int(d.get("quantity", 0)),
        })
    return items

# -----------------------------------------
# System health (backups / restores)
# -----------------------------------------
async def system_health() -> Dict[str, Any]:
    # last backup
    last_backup = await db["backup_logs"].find({}).sort("createdAt", -1).limit(1).to_list(1)
    lb = last_backup[0] if last_backup else None
    last_backup_info = None
    if lb:
        last_backup_info = {
            "status": lb.get("status"),
            "scope": lb.get("scope"),
            "frequency": lb.get("frequency"),
            "size": lb.get("size"),
            "path": lb.get("path"),
            "scheduled_at": lb.get("scheduled_at").isoformat() if lb.get("scheduled_at") else None,
            "started_at": lb.get("started_at").isoformat() if lb.get("started_at") else None,
            "finished_at": lb.get("finished_at").isoformat() if lb.get("finished_at") else None,
            "createdAt": lb.get("createdAt").isoformat() if lb.get("createdAt") else None,
            "updatedAt": lb.get("updatedAt").isoformat() if lb.get("updatedAt") else None,
        }

    since = dt.datetime.now(timezone.utc) - dt.timedelta(days=7)

    failed_backups_7d = await db["backup_logs"].count_documents({
        "createdAt": {"$gte": since},
        "status": "failed"
    })

    failed_restores_7d = await db["restore_logs"].count_documents({
        "createdAt": {"$gte": since},
        "status": "failed"
    })

    return {
        "last_backup": last_backup_info,
        "failed_backups_7d": failed_backups_7d,
        "failed_restores_7d": failed_restores_7d,
    }