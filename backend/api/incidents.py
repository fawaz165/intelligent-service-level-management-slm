"""
Incident REST endpoints — direct CRUD access (bypasses LLM).
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.schemas import IncidentCreate, IncidentUpdate
from backend.services import incident_service

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("")
def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    service: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return incident_service.list_incidents(db, status=status, severity=severity, service=service, search=search)


@router.get("/{incident_id}")
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    inc = incident_service.get_incident(db, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return inc


@router.post("", status_code=201)
def create_incident(data: IncidentCreate, allow_duplicate: bool = False, db: Session = Depends(get_db)):
    if not allow_duplicate:
        dup = incident_service.check_duplicate_incident(db, data.title)
        if dup:
            raise HTTPException(
                status_code=409,
                detail=f"Active incident '{dup['incident_id']}' with title '{dup['title']}' already exists.",
            )
    return incident_service.create_incident(db, data.model_dump(), allow_duplicate=True)


@router.put("/{incident_id}")
def update_incident(incident_id: str, data: IncidentUpdate, db: Session = Depends(get_db)):
    result = incident_service.update_incident(db, incident_id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return result


@router.delete("/{incident_id}")
def delete_incident(incident_id: str, db: Session = Depends(get_db)):
    if not incident_service.delete_incident(db, incident_id):
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return {"message": f"Incident {incident_id} deleted"}
