from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, NonNegativeInt, NonNegativeFloat


# ---------- Reusable small models ----------

class TimePoint(BaseModel):
    date: str = Field(..., description="ISO date (YYYY-MM-DD) in Asia/Kolkata")
    value: NonNegativeFloat = 0.0


# ---------- Overview ----------

class OverviewOut(BaseModel):
    users: NonNegativeInt = 0
    products: NonNegativeInt = 0
    orders: NonNegativeInt = 0
    returns: NonNegativeInt = 0
    exchanges: NonNegativeInt = 0
    revenue: NonNegativeFloat = 0.0


# ---------- Sales (time series) ----------

class SalesSeriesOut(BaseModel):
    days: NonNegativeInt
    series: List[TimePoint]


# ---------- User growth (time series) ----------

class UserGrowthOut(BaseModel):
    days: NonNegativeInt
    series: List[TimePoint]


# ---------- Top products (by qty sold) ----------

class TopProductOut(BaseModel):
    product_id: str
    name: str
    total_quantity: NonNegativeInt
    total_orders: NonNegativeInt
    total_revenue: NonNegativeFloat


class TopProductsOut(BaseModel):
    limit: NonNegativeInt
    items: List[TopProductOut]


# ---------- Low stock ----------

class LowStockItemOut(BaseModel):
    product_id: str
    name: str
    quantity: NonNegativeInt


class LowStockOut(BaseModel):
    threshold: NonNegativeInt
    items: List[LowStockItemOut]


# ---------- System health (backups / restores) ----------

class LastBackupInfo(BaseModel):
    status: str
    scope: Optional[str] = None
    frequency: Optional[str] = None
    size: Optional[float] = None
    scheduled_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    path: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class SystemHealthOut(BaseModel):
    last_backup: Optional[LastBackupInfo] = None
    failed_backups_7d: NonNegativeInt = 0
    failed_restores_7d: NonNegativeInt = 0