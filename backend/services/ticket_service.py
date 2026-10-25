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


def check_duplicate_ticket(db: Session, title: str, category: Optional[str] = None) -> Optional[dict]:
    """Check if an active (open or in_progress) ticket with the same title already exists."""
    if not title or not title.strip():
        return None
    query = db.query(Ticket).filter(
        Ticket.title.ilike(title.strip()),
        Ticket.status.in_(["open", "in_progress"]),
    )
    if category:
        norm_cat = _VALID_CATEGORIES.get(category.strip().lower(), category.strip())
        query = query.filter(Ticket.category == norm_cat)
    existing = query.first()
    return existing.to_dict() if existing else None


def list_tickets(
    db: Session,
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    assigned_to: Optional[object] = None,
    service_id: Optional[object] = None,
) -> list[dict]:
    """Retrieve tickets with optional filters — parameterized queries throughout."""
    from backend.database.models import User, Service

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
    if assigned_to is not None and str(assigned_to).strip():
        val = str(assigned_to).strip()
        if val.isdigit():
            query = query.filter(Ticket.assigned_to == int(val))
        else:
            query = query.join(User, Ticket.assigned_to == User.id, isouter=True).filter(
                or_(User.name.ilike(f"%{val}%"), User.username.ilike(f"%{val}%"))
            )
    if service_id is not None and str(service_id).strip():
        val = str(service_id).strip()
        if val.isdigit():
            query = query.filter(Ticket.service_id == int(val))
        else:
            query = query.join(Service, Ticket.service_id == Service.id, isouter=True).filter(
                Service.service_name.ilike(f"%{val}%")
            )
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


def create_ticket(db: Session, data: dict, allow_duplicate: bool = False) -> dict:
    """Create a new ticket from validated parameters, checking for duplicates."""
    title = data.get("title", "Untitled Ticket")
    category = _normalize_category(data.get("category", "Application"))

    if not allow_duplicate:
        dup = check_duplicate_ticket(db, title, category)
        if dup:
            logger.info("Found existing active duplicate ticket #%d '%s'", dup["id"], dup["title"])
            dup["is_duplicate"] = True
            return dup

    ticket = Ticket(
        title=title,
        description=data.get("description"),
        category=category,
        priority=_normalize_priority(data.get("priority", "medium")),
        status=_normalize_status(data.get("status", "open")),
        assigned_to=data.get("assigned_to"),
        service_id=data.get("service_id"),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    logger.info("Created ticket #%d: %s", ticket.id, ticket.title)
    res = ticket.to_dict()
    res["is_duplicate"] = False
    return res


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
        "assigned_to": lambda v: int(v) if (v is not None and str(v).strip() != "" and str(v).strip().lower() != "unassigned") else None,
        "service_id": lambda v: int(v) if (v is not None and str(v).strip() != "") else None,
    }

    for field, normalizer in field_map.items():
        if field in data:
            val = data[field]
            if field in ("assigned_to", "service_id"):
                setattr(ticket, field, normalizer(val))
            elif val is not None:
                setattr(ticket, field, normalizer(val))

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
