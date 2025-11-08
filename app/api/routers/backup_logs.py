from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from app.api.deps import user_required, admin_required
from app.schemas.backup_logs import BackupLogsCreate, BackupLogsUpdate, BackupLogsOut
from app.crud import backup_logs as crud

router = APIRouter()

@router.post("/", response_model=BackupLogsOut, dependencies=[Depends(admin_required)])
async def create_item(payload: BackupLogsCreate):
    d = await crud.create(payload.model_dump())
    return BackupLogsOut.model_validate(d)

@router.get("/", response_model=List[BackupLogsOut], dependencies=[Depends(user_required)])
async def list_items(skip:int=0, limit:int=50):
    docs = await crud.list_all(skip,limit)
    return [BackupLogsOut.model_validate(x) for x in docs]

@router.get("/{item_id}", response_model=BackupLogsOut, dependencies=[Depends(user_required)])
async def get_item(item_id: str):
    d = await crud.get_one(item_id)
    if not d: raise HTTPException(404, "Not found")
    return BackupLogsOut.model_validate(d)

@router.put("/{item_id}", response_model=BackupLogsOut, dependencies=[Depends(admin_required)])
async def update_item(item_id: str, payload: BackupLogsUpdate):
    data = {k:v for k,v in payload.model_dump().items() if v is not None}
    d = await crud.update_one(item_id, data)
    if not d: raise HTTPException(404, "Not found")
    return BackupLogsOut.model_validate(d)

@router.delete("/{item_id}", dependencies=[Depends(admin_required)])
async def delete_item(item_id: str):
    return {"deleted": await crud.delete_one(item_id)}
