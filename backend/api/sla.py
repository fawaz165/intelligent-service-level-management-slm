"""
SLA REST endpoints — query Service Level Agreement targets, monitoring metrics, and risk predictions.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import SLA, Service, Ticket, Incident
from backend.services import sla_service, telemetry_service

router = APIRouter(prefix="/api/sla", tags=["sla"])


class PredictRequest(BaseModel):
    entity_type: str  # "ticket" or "incident"
    id: str  # numeric ticket ID or incident code e.g. "1" or "INC-20260902-001"


# ── SLA Risk & Metrics Endpoints (MUST precede /{sla_id}) ─────────────────

@router.get("/metrics")
def get_sla_metrics(db: Session = Depends(get_db)):
    """Return aggregate SLA dashboard metrics."""
    return sla_service.get_sla_dashboard_metrics(db)


@router.get("/telemetry")
def get_telemetry(db: Session = Depends(get_db)):
    """Return real host and labeled simulated IT infrastructure telemetry."""
    return telemetry_service.get_telemetry_metrics(db)


@router.get("/risks")
def get_sla_risks(
    risk_level: Optional[str] = Query(None, description="Filter by risk level: Critical, High, Medium, Low"),
    entity: Optional[str] = Query(None, description="Filter by entity: ticket, incident"),
    service: Optional[str] = Query(None, description="Filter by service name"),
    breached_only: bool = Query(False, description="Show only breached records"),
    include_resolved: bool = Query(False, description="Include resolved/closed records"),
    db: Session = Depends(get_db),
):
    """Return evaluated SLA risks for monitored active tickets and incidents."""
    return sla_service.get_all_sla_risks(
        db,
        risk_filter=risk_level,
        entity_filter=entity,
        service_filter=service,
        breached_only=breached_only,
        include_resolved=include_resolved,
    )


@router.post("/predict")
async def predict_risk(
    req: PredictRequest,
    db: Session = Depends(get_db),
):
    """
    Generate on-demand DeepSeek-R1 1.5B qualitative root cause prediction and remediation recommendations.
    Distinguishes rule-based calculations from model predictions.
    """
    entity_type = req.entity_type.lower().strip()
    target_id = req.id.strip()

    item = None
    if entity_type in ("incident", "incidents"):
        # Look up by incident_id or numeric id
        item = db.query(Incident).filter(Incident.incident_id == target_id).first()
        if not item and target_id.isdigit():
            item = db.query(Incident).filter(Incident.id == int(target_id)).first()
        entity_type = "incident"
    else:
        clean_id = target_id.lstrip("#")
        if clean_id.isdigit():
            item = db.query(Ticket).filter(Ticket.id == int(clean_id)).first()
        entity_type = "ticket"

    if not item:
        raise HTTPException(status_code=404, detail=f"{entity_type.capitalize()} '{target_id}' not found")

    # Evaluate deterministic rule-based baseline
    evaluated = sla_service.evaluate_single_item(item, entity_type, db)

    # Enrich with DeepSeek-R1 1.5B qualitative analysis
    enriched = await sla_service.enrich_with_ai_prediction(evaluated)
    return enriched


# ── SLA Target Records (Existing) ────────────────────────────────────────

@router.get("")
def list_sla(
    priority: Optional[str] = None,
    service_id: Optional[int] = None,
    service_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List SLA targets configured in the database."""
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
    """Get a specific SLA record by ID."""
    sla = db.query(SLA).filter(SLA.id == sla_id).first()
    if not sla:
        raise HTTPException(status_code=404, detail=f"SLA record #{sla_id} not found")
    return sla.to_dict()
