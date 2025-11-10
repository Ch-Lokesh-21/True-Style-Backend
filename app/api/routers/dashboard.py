"""
Dashboard Routes

Provides analytics and metrics for the admin dashboard:
- Overview statistics
- Sales timeline
- User growth timeline
- Best-selling products
- Low-stock alerts
- System health stats
"""

from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.deps import require_permission
from app.schemas.dashboard import (
    OverviewOut,
    SalesSeriesOut,
    UserGrowthOut,
    TopProductsOut,
    LowStockOut,
    SystemHealthOut,
)
from app.services import dashboard as svc

router = APIRouter()  # mounted under /dashboard in main.py


@router.get(
    "/overview",
    response_model=OverviewOut,
    dependencies=[Depends(require_permission("dashboard", "Read"))],
)
async def get_overview():
    """
    Get high-level dashboard summary including:
      - total orders
      - completed orders
      - total revenue
      - user count
      - product count

    Returns:
        OverviewOut: Aggregated numeric KPIs for UI display.
    """
    try:
        data = await svc.get_overview()
        return OverviewOut(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load overview: {e}")


@router.get(
    "/sales",
    response_model=SalesSeriesOut,
    dependencies=[Depends(require_permission("dashboard", "Read"))],
)
async def get_sales(days: int = Query(30, ge=1, le=365)):
    """
    Time-series graph: total sales revenue per day.

    Args:
        days (int): Number of recent days to include (max 365).

    Returns:
        SalesSeriesOut: (days, list of {date, total_sales} points)
    """
    try:
        series = await svc.sales_series(days)
        return SalesSeriesOut(days=days, series=series)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load sales series: {e}")


@router.get(
    "/user-growth",
    response_model=UserGrowthOut,
    dependencies=[Depends(require_permission("dashboard", "Read"))],
)
async def get_user_growth(days: int = Query(30, ge=1, le=365)):
    """
    Time-series graph: number of new users registered per day.

    Args:
        days (int): Number of recent days to include.

    Returns:
        UserGrowthOut: (days, list of {date, count} points)
    """
    try:
        series = await svc.user_growth(days)
        return UserGrowthOut(days=days, series=series)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load user growth series: {e}")


@router.get(
    "/top-products",
    response_model=TopProductsOut,
    dependencies=[Depends(require_permission("dashboard", "Read"))],
)
async def get_top_products(limit: int = Query(10, ge=1, le=100)):
    """
    Get highest-selling products for leaderboard charts.

    Args:
        limit (int): Maximum number of products to return.

    Returns:
        TopProductsOut: Ranked list of products with total sold qty.
    """
    try:
        items = await svc.top_products(limit)
        return TopProductsOut(limit=limit, items=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load top products: {e}")


@router.get(
    "/low-stock",
    response_model=LowStockOut,
    dependencies=[Depends(require_permission("dashboard", "Read"))],
)
async def get_low_stock(threshold: int = Query(10, ge=0, le=10_000)):
    """
    List items that are at or below a given stock threshold.

    Args:
        threshold (int): Minimum stock level to trigger alert.

    Returns:
        LowStockOut: Items with remaining_qty <= threshold
    """
    try:
        items = await svc.low_stock(threshold)
        return LowStockOut(threshold=threshold, items=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load low-stock items: {e}")


@router.get(
    "/system-health",
    response_model=SystemHealthOut,
    dependencies=[Depends(require_permission("dashboard", "Read"))],
)
async def get_system_health():
    """
    Show real-time system diagnostics including:
      - DB health
      - API latency
      - Orders log trends
      - Error counts

    Returns:
        SystemHealthOut: Aggregated key operational metrics.
    """
    try:
        data = await svc.system_health()
        return SystemHealthOut(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load system health: {e}")