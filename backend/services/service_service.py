"""
Service service — business logic for IT service CRUD operations.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from backend.database.models import Service

logger = logging.getLogger(__name__)

_VALID_STATUSES = {"active", "inactive", "maintenance", "deprecated"}


def _normalize_status(value: str) -> str:
    lower = value.strip().lower()
    return lower if lower in _VALID_STATUSES else "active"


def check_duplicate_service(db: Session, service_name: str) -> Optional[dict]:
    """Check if an active service with the same name already exists."""
    if not service_name or not service_name.strip():
        return None
    existing = db.query(Service).filter(
        Service.service_name.ilike(service_name.strip()),
        Service.status.in_(["active", "maintenance"]),
    ).first()
    return existing.to_dict() if existing else None


def list_services(
    db: Session,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> list[dict]:
    """Retrieve services with optional filters."""
    query = db.query(Service)

    if status:
        norm_status = status.strip().lower()
        query = query.filter(Service.status == norm_status)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            Service.service_name.ilike(pattern) | Service.description.ilike(pattern)
        )

    query = query.order_by(Service.created_at.desc())
    return [s.to_dict() for s in query.all()]


def get_service(db: Session, service_id: int) -> Optional[dict]:
    svc = db.query(Service).filter(Service.id == service_id).first()
    return svc.to_dict() if svc else None


def create_service(db: Session, data: dict, allow_duplicate: bool = False) -> dict:
    name = data.get("service_name", "Unnamed Service")

    if not allow_duplicate:
        dup = check_duplicate_service(db, name)
        if dup:
            logger.info("Found existing duplicate service #%d '%s'", dup["id"], dup["service_name"])
            dup["is_duplicate"] = True
            return dup

    svc = Service(
        service_name=name,
        description=data.get("description"),
        status=_normalize_status(data.get("status", "active")),
        owner=data.get("owner"),
    )
    db.add(svc)
    db.commit()
    db.refresh(svc)
    logger.info("Created service #%d: %s", svc.id, svc.service_name)
    res = svc.to_dict()
    res["is_duplicate"] = False
    return res


def update_service(db: Session, service_id: int, data: dict) -> Optional[dict]:
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        return None

    for field in ("service_name", "description", "owner"):
        if field in data and data[field] is not None:
            setattr(svc, field, data[field])
    if "status" in data and data["status"] is not None:
        svc.status = _normalize_status(data["status"])

    db.commit()
    db.refresh(svc)
    logger.info("Updated service #%d", svc.id)
    return svc.to_dict()


def delete_service(db: Session, service_id: int) -> bool:
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        return False
    db.delete(svc)
    db.commit()
    logger.info("Deleted service #%d", service_id)
    return True
