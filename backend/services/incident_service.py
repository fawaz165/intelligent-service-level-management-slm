"""
Incident service — business logic for incident CRUD operations.

All database access uses parameterized queries through SQLAlchemy ORM.
Operates on the actual SQLite `incidents` table and schema.
"""

import logging
from typing import Optional, Union
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.database.models import Incident, INCIDENT_SEVERITIES, INCIDENT_STATUSES

logger = logging.getLogger(__name__)

_VALID_SEVERITIES = set(INCIDENT_SEVERITIES)
_VALID_STATUSES = set(INCIDENT_STATUSES)


def list_incidents(
    db: Session,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    service: Optional[str] = None,
    search: Optional[str] = None,
) -> list[dict]:
    """Retrieve incidents with optional filters — parameterized queries throughout."""
    query = db.query(Incident)

    if status:
        norm_status = status.strip().lower().replace(" ", "_").replace("-", "_")
        query = query.filter(Incident.status == norm_status)

    if severity:
        norm_sev = severity.strip().lower()
        query = query.filter(Incident.severity == norm_sev)

    if service:
        srv_pattern = f"%{service.strip()}%"
        query = query.filter(Incident.affected_service.ilike(srv_pattern))

    if search:
        s_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Incident.title.ilike(s_pattern),
                Incident.description.ilike(s_pattern),
                Incident.incident_id.ilike(s_pattern),
                Incident.affected_service.ilike(s_pattern),
                Incident.tags.ilike(s_pattern),
            )
        )

    query = query.order_by(Incident.id.asc())
    return [inc.to_dict() for inc in query.all()]


def get_incident(db: Session, incident_id: Union[int, str]) -> Optional[dict]:
    """Get a single incident by integer ID or incident_id string (e.g. 'INC-20260902-001')."""
    if isinstance(incident_id, int) or (isinstance(incident_id, str) and incident_id.isdigit()):
        inc = db.query(Incident).filter(Incident.id == int(incident_id)).first()
    else:
        inc = db.query(Incident).filter(Incident.incident_id.ilike(str(incident_id))).first()
    return inc.to_dict() if inc else None


def check_duplicate_incident(db: Session, title: str) -> Optional[dict]:
    """Check if an active (open or acknowledged) incident with the same title already exists."""
    if not title or not title.strip():
        return None
    query = db.query(Incident).filter(
        Incident.title.ilike(title.strip()),
        Incident.status.in_(["open", "acknowledged"]),
    )
    existing = query.first()
    return existing.to_dict() if existing else None


def create_incident(db: Session, data: dict, allow_duplicate: bool = False) -> dict:
    """Create a new incident from validated parameters, checking for duplicates."""
    title = data.get("title", "New Incident")

    if not allow_duplicate:
        dup = check_duplicate_incident(db, title)
        if dup:
            logger.info("Found existing active duplicate incident #%d (%s)", dup["id"], dup["incident_id"])
            dup["is_duplicate"] = True
            return dup

    inc_id = data.get("incident_id")
    if not inc_id:
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        count = db.query(Incident).count() + 1
        inc_id = f"INC-{now_str}-{count:03d}"

    severity = (data.get("severity") or "medium").strip().lower()
    if severity not in _VALID_SEVERITIES:
        severity = "medium"

    status = (data.get("status") or "open").strip().lower()
    if status not in _VALID_STATUSES:
        status = "open"

    incident = Incident(
        incident_id=inc_id,
        source=data.get("source", "manual"),
        title=title,
        description=data.get("description"),
        severity=severity,
        affected_service=data.get("affected_service") or data.get("service"),
        affected_component=data.get("affected_component"),
        status=status,
        assigned_to=data.get("assigned_to"),
        tags=data.get("tags") if isinstance(data.get("tags"), str) else (", ".join(data.get("tags")) if data.get("tags") else None),
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    logger.info("Created incident #%d (%s): %s", incident.id, incident.incident_id, incident.title)
    res = incident.to_dict()
    res["is_duplicate"] = False
    return res


def update_incident(db: Session, incident_id: Union[int, str], data: dict) -> Optional[dict]:
    """Update specific fields of an incident."""
    if isinstance(incident_id, int) or (isinstance(incident_id, str) and incident_id.isdigit()):
        inc = db.query(Incident).filter(Incident.id == int(incident_id)).first()
    else:
        inc = db.query(Incident).filter(Incident.incident_id.ilike(str(incident_id))).first()

    if not inc:
        return None

    for field in ("title", "description", "severity", "affected_service", "affected_component", "status", "assigned_to", "tags"):
        if field in data:
            val = data[field]
            if field == "assigned_to":
                clean_val = str(val).strip() if val is not None else ""
                setattr(inc, field, clean_val if clean_val and clean_val.lower() != "unassigned" else None)
            elif val is not None:
                if field == "severity":
                    val = val.strip().lower()
                elif field == "status":
                    val = val.strip().lower().replace(" ", "_").replace("-", "_")
                setattr(inc, field, val)

    db.commit()
    db.refresh(inc)
    logger.info("Updated incident #%d (%s)", inc.id, inc.incident_id)
    return inc.to_dict()


def delete_incident(db: Session, incident_id: Union[int, str]) -> bool:
    """Delete an incident by ID or incident_id."""
    if isinstance(incident_id, int) or (isinstance(incident_id, str) and incident_id.isdigit()):
        inc = db.query(Incident).filter(Incident.id == int(incident_id)).first()
    else:
        inc = db.query(Incident).filter(Incident.incident_id.ilike(str(incident_id))).first()

    if not inc:
        return False
    db.delete(inc)
    db.commit()
    logger.info("Deleted incident #%d (%s)", inc.id, inc.incident_id)
    return True
