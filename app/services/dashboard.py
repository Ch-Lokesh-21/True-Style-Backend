"""
Dashboard Analytics Service

Provides aggregated insights for the admin dashboard such as:
- System overview counts
- Sales series
- User growth trends
- Top-selling products
- Low-stock products
- System backup/restore health
"""

from __future__ import annotations
import datetime as dt
from datetime import datetime, timezone
from typing import List, Dict, Any

from bson import ObjectId
from app.core.database import db

TZ = "Asia/Kolkata"


def _date_floor_utc(days_back: int) -> datetime:
    """
    Compute a UTC datetime representing midnight (00:00:00 UTC) N days ago.

    Args:
        days_back (int): Number of days in the past to compute from.

    Returns:
        datetime: Midnight UTC timestamp N days before today.
    """
    now = datetime.now(timezone.utc)
    start = now - dt.timedelta(days=days_back)
    return datetime(start.year, start.month, start.day)


async def get_overview() -> Dict[str, Any]:
    """
    Compute high-level system metrics for the admin dashboard.

    Metrics include:
      - Total users
      - Total products
      - Total orders
      - Total returns
      - Total exchanges
      - Total revenue (from successful payments)

    Returns:
        Dict[str, Any]: Aggregated counts and revenue value.
    """
    users = await db["users"].count_documents({})
    products = await db["products"].count_documents({})
    orders = await db["orders"].count_documents({})
    returns = await db["returns"].count_documents({})
    exchanges = await db["exchanges"].count_documents({})

    # Find payment_status IDs marked as "success"
    paid_status_ids = []
    async for s in db["payment_status"].find({"status": {"$in": ["success"]}}, {"_id": 1}):
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


async def sales_series(days: int) -> List[Dict[str, Any]]:
    """
    Aggregate daily sales revenue over the specified number of days.

    Args:
        days (int): Number of days to include (e.g., last 30 days).

    Returns:
        List[Dict[str, Any]]: A list of daily {date, value} pairs where
        `value` is total payment amount on that date.
    """
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


async def user_growth(days: int) -> List[Dict[str, Any]]:
    """
    Aggregate count of new user registrations per day.

    Args:
        days (int): Days in the past to compute.

    Returns:
        List[Dict]: List of {date, value} where `value` is number of users joined that day.
    """
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


async def top_products(limit: int) -> List[Dict[str, Any]]:
    """
    Find the top-selling products by quantity and revenue.

    Args:
        limit (int): Maximum number of products to return.

    Returns:
        List[Dict[str, Any]]: List of products with aggregated sale details:
            - product_id
            - name
            - total_quantity sold
            - total_orders count
            - total_revenue computed
    """
    pipeline = [
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
            "total_revenue": {"$multiply": ["$total_quantity", "$unit_price"]},
        }},
        {"$sort": {"total_quantity": -1, "total_revenue": -1}},
        {"$limit": limit},
    ]
    rows = await db["order_item"].aggregate(pipeline).to_list(None)
    for r in rows:
        r["total_revenue"] = float(r.get("total_revenue", 0.0))
        r["total_quantity"] = int(r.get("total_quantity", 0))
        r["total_orders"] = int(r.get("total_orders", 0))
    return rows


async def low_stock(threshold: int) -> List[Dict[str, Any]]:
    """
    Return list of products whose quantity is below or equal to a threshold.

    Args:
        threshold (int): Minimum stock threshold.

    Returns:
        List[Dict[str, Any]]: product_id, name, and current quantity.
    """
    cursor = db["products"].find({"quantity": {"$lte": threshold}}, {"_id": 1, "name": 1, "quantity": 1}).sort("quantity", 1)
    items: List[Dict[str, Any]] = []
    async for d in cursor:
        items.append({
            "product_id": str(d["_id"]),
            "name": d.get("name", ""),
            "quantity": int(d.get("quantity", 0)),
        })
    return items


async def system_health() -> Dict[str, Any]:
    """
    Summarize system backups and restore health.

    Returned information:
      - Last backup record (status, timestamps, size)
      - Failed backups in last 7 days
      - Failed restores in last 7 days

    Returns:
        Dict[str, Any]: System health summary.
    """
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