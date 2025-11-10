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

router = APIRouter()  # mount under /dashboard in main.py


# 1) OVERVIEW
@router.get("/overview", response_model=OverviewOut, dependencies=[Depends(require_permission("dashboard", "Read"))])
async def get_overview():
    try:
        data = await svc.get_overview()
        return OverviewOut(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load overview: {e}")


# 2) SALES SERIES
@router.get("/sales", response_model=SalesSeriesOut, dependencies=[Depends(require_permission("dashboard", "Read"))])
async def get_sales(days: int = Query(30, ge=1, le=365)):
    try:
        series = await svc.sales_series(days)
        return SalesSeriesOut(days=days, series=series)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load sales series: {e}")


# 3) USER GROWTH SERIES
@router.get("/user-growth", response_model=UserGrowthOut, dependencies=[Depends(require_permission("dashboard", "Read"))])
async def get_user_growth(days: int = Query(30, ge=1, le=365)):
    try:
        series = await svc.user_growth(days)
        return UserGrowthOut(days=days, series=series)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load user growth series: {e}")


# 4) TOP PRODUCTS
@router.get("/top-products", response_model=TopProductsOut, dependencies=[Depends(require_permission("dashboard", "Read"))])
async def get_top_products(limit: int = Query(10, ge=1, le=100)):
    try:
        items = await svc.top_products(limit)
        return TopProductsOut(limit=limit, items=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load top products: {e}")


# 5) LOW STOCK
@router.get("/low-stock", response_model=LowStockOut, dependencies=[Depends(require_permission("dashboard", "Read"))])
async def get_low_stock(threshold: int = Query(10, ge=0, le=10_000)):
    try:
        items = await svc.low_stock(threshold)
        return LowStockOut(threshold=threshold, items=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load low-stock items: {e}")


# 6) SYSTEM HEALTH
@router.get("/system-health", response_model=SystemHealthOut, dependencies=[Depends(require_permission("dashboard", "Read"))])
async def get_system_health():
    try:
        data = await svc.system_health()
        return SystemHealthOut(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load system health: {e}")