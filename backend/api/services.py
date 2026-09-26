"""
Service REST endpoints — direct CRUD access.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.schemas import ServiceCreate, ServiceUpdate
from backend.services import service_service

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("")
def list_services(
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return service_service.list_services(db, status=status, search=search)


@router.get("/{service_id}")
def get_service(service_id: int, db: Session = Depends(get_db)):
    s = service_service.get_service(db, service_id)
    if not s:
        raise HTTPException(status_code=404, detail=f"Service #{service_id} not found")
    return s


@router.post("", status_code=201)
def create_service(data: ServiceCreate, db: Session = Depends(get_db)):
    return service_service.create_service(db, data.model_dump())


@router.put("/{service_id}")
def update_service(service_id: int, data: ServiceUpdate, db: Session = Depends(get_db)):
    result = service_service.update_service(db, service_id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail=f"Service #{service_id} not found")
    return result


@router.delete("/{service_id}")
def delete_service(service_id: int, db: Session = Depends(get_db)):
    if not service_service.delete_service(db, service_id):
        raise HTTPException(status_code=404, detail=f"Service #{service_id} not found")
    return {"message": f"Service #{service_id} deleted"}
