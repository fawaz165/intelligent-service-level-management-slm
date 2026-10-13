"""
Ticket service — business logic for ticket CRUD operations.

All database access uses parameterized queries through SQLAlchemy ORM.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.database.models import Ticket, TICKET_CATEGORIES, TICKET_PRIORITIES, TICKET_STATUSES

logger = logging.getLogger(__name__)

# Allowed values for validation
_VALID_CATEGORIES = {c.lower(): c for c in TICKET_CATEGORIES}
_VALID_PRIORITIES = set(TICKET_PRIORITIES)
_VALID_STATUSES = set(TICKET_STATUSES)


def _normalize_category(value: str) -> str:
    """Normalize category to title case, validating against allowed list."""
    lower = value.strip().lower()
    if lower in _VALID_CATEGORIES:
        return _VALID_CATEGORIES[lower]
    return "Application"  # default for creation


def _normalize_priority(value: str) -> str:
    lower = value.strip().lower()
    return lower if lower in _VALID_PRIORITIES else "medium"


def _normalize_status(value: str) -> str:
    lower = value.strip().lower().replace(" ", "_")
    return lower if lower in _VALID_STATUSES else "open"


def list_tickets(
    db: Session,
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    assigned_to: Optional[int] = None,
    service_id: Optional[int] = None,
) -> list[dict]:
    """Retrieve tickets with optional filters — parameterized queries throughout."""
    query = db.query(Ticket)

    if status:
        norm_status = status.strip().lower().replace(" ", "_").replace("-", "_")
        query = query.filter(Ticket.status == norm_status)
    if category:
        norm_cat = _VALID_CATEGORIES.get(category.strip().lower(), category.strip())
        query = query.filter(Ticket.category == norm_cat)
    if priority:
        norm_prio = priority.strip().lower()
        query = query.filter(Ticket.priority == norm_prio)
    if assigned_to:
        query = query.filter(Ticket.assigned_to == int(assigned_to))
    if service_id:
        query = query.filter(Ticket.service_id == int(service_id))
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Ticket.title.ilike(pattern),
                Ticket.description.ilike(pattern),
            )
        )

    query = query.order_by(Ticket.created_at.desc())
    return [t.to_dict() for t in query.all()]


def get_ticket(db: Session, ticket_id: int) -> Optional[dict]:
    """Get a single ticket by ID."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    return ticket.to_dict() if ticket else None


def create_ticket(db: Session, data: dict) -> dict:
    """Create a new ticket from validated parameters."""
    ticket = Ticket(
        title=data.get("title", "Untitled Ticket"),
        description=data.get("description"),
        category=_normalize_category(data.get("category", "Application")),
        priority=_normalize_priority(data.get("priority", "medium")),
        status=_normalize_status(data.get("status", "open")),
        assigned_to=data.get("assigned_to"),
        service_id=data.get("service_id"),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    logger.info("Created ticket #%d: %s", ticket.id, ticket.title)
    return ticket.to_dict()


def update_ticket(db: Session, ticket_id: int, data: dict) -> Optional[dict]:
    """Update specific fields of a ticket."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        return None

    field_map = {
        "title": lambda v: v,
        "description": lambda v: v,
        "category": _normalize_category,
        "priority": _normalize_priority,
        "status": _normalize_status,
        "assigned_to": lambda v: int(v) if v is not None else None,
        "service_id": lambda v: int(v) if v is not None else None,
    }

    for field, normalizer in field_map.items():
        if field in data and data[field] is not None:
            setattr(ticket, field, normalizer(data[field]))

    db.commit()
    db.refresh(ticket)
    logger.info("Updated ticket #%d", ticket.id)
    return ticket.to_dict()


def delete_ticket(db: Session, ticket_id: int) -> bool:
    """Delete a ticket by ID. Returns True if found and deleted."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        return False
    db.delete(ticket)
    db.commit()
    logger.info("Deleted ticket #%d", ticket_id)
    return True
