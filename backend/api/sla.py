"""
SLA REST endpoints — query Service Level Agreement targets.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import SLA, Service

router = APIRouter(prefix="/api/sla", tags=["sla"])


@router.get("")
def list_sla(
    priority: Optional[str] = None,
    service_id: Optional[int] = None,
    service_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(SLA).join(Service, SLA.service_id == Service.id, isouter=True)
    if priority:
        query = query.filter(SLA.priority.ilike(priority.strip()))
    if service_id:
        query = query.filter(SLA.service_id == int(service_id))
    if service_name:
        query = query.filter(Service.service_name.ilike(f"%{service_name.strip()}%"))
    query = query.order_by(SLA.service_id, SLA.priority)
    return [s.to_dict() for s in query.all()]


@router.get("/{sla_id}")
def get_sla(sla_id: int, db: Session = Depends(get_db)):
    sla = db.query(SLA).filter(SLA.id == sla_id).first()
    if not sla:
        raise HTTPException(status_code=404, detail=f"SLA record #{sla_id} not found")
    return sla.to_dict()
