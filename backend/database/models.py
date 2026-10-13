"""
SQLAlchemy ORM models for the ISLM database.

Demonstrates:
  • Primary keys (auto-increment)
  • Foreign keys with ON DELETE behaviour
  • Relationships (one-to-many)
  • Constraints (NOT NULL, UNIQUE, CHECK)
  • Indexes on frequently queried columns
  • Default values and server defaults
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Index, CheckConstraint,
)
from sqlalchemy.orm import relationship
from backend.database.connection import Base


def _utcnow():
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════
# USERS
# ═══════════════════════════════════════════════════════════════════════════
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(String(50), nullable=False, default="technician")
    created_at = Column(DateTime, default=_utcnow)

    # Relationships
    assigned_tickets = relationship("Ticket", back_populates="assignee", lazy="selectin")
    uploaded_files = relationship("File", back_populates="uploader", lazy="selectin")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ═══════════════════════════════════════════════════════════════════════════
# SERVICES
# ═══════════════════════════════════════════════════════════════════════════
class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="active")
    owner = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    # Relationships
    tickets = relationship("Ticket", back_populates="service", lazy="selectin")
    slas = relationship("SLA", back_populates="service", lazy="selectin")

    __table_args__ = (
        CheckConstraint("status IN ('active','inactive','maintenance','deprecated')", name="ck_services_status"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "service_name": self.service_name,
            "description": self.description,
            "status": self.status,
            "owner": self.owner,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ═══════════════════════════════════════════════════════════════════════════
# TICKETS
# ═══════════════════════════════════════════════════════════════════════════
TICKET_CATEGORIES = ("Network", "Database", "Server", "Application", "Security", "Hardware")
TICKET_PRIORITIES = ("low", "medium", "high", "critical")
TICKET_STATUSES = ("open", "in_progress", "resolved", "closed")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, default="Application")
    priority = Column(String(20), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="open")
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationships
    assignee = relationship("User", back_populates="assigned_tickets")
    service = relationship("Service", back_populates="tickets")

    __table_args__ = (
        CheckConstraint(
            f"category IN ({','.join(repr(c) for c in TICKET_CATEGORIES)})",
            name="ck_tickets_category",
        ),
        CheckConstraint(
            f"priority IN ({','.join(repr(p) for p in TICKET_PRIORITIES)})",
            name="ck_tickets_priority",
        ),
        CheckConstraint(
            f"status IN ({','.join(repr(s) for s in TICKET_STATUSES)})",
            name="ck_tickets_status",
        ),
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_category", "category"),
        Index("ix_tickets_priority", "priority"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "priority": self.priority,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "assignee_name": self.assignee.name if self.assignee else None,
            "service_id": self.service_id,
            "service_name": self.service.service_name if self.service else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ═══════════════════════════════════════════════════════════════════════════
# INCIDENTS
# ═══════════════════════════════════════════════════════════════════════════
INCIDENT_SEVERITIES = ("critical", "high", "medium", "low")
INCIDENT_STATUSES = ("open", "acknowledged", "resolved", "closed")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String(50), unique=True, nullable=False)
    source = Column(String(50), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, default="medium")
    affected_service = Column(String(100), nullable=True)
    affected_component = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="open")
    detected_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    mttr_minutes = Column(Integer, nullable=True)
    tags = Column(Text, nullable=True)
    assigned_to = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    __table_args__ = (
        Index("ix_incidents_status", "status"),
        Index("ix_incidents_severity", "severity"),
        Index("ix_incidents_affected_service", "affected_service"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "source": self.source,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "affected_service": self.affected_service,
            "affected_component": self.affected_component,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "tags": self.tags,
            "mttr_minutes": self.mttr_minutes,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ═══════════════════════════════════════════════════════════════════════════
# SLA
# ═══════════════════════════════════════════════════════════════════════════
class SLA(Base):
    __tablename__ = "sla"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    priority = Column(String(20), nullable=False)
    response_time = Column(String(50), nullable=False)   # e.g. "1 hour"
    resolution_time = Column(String(50), nullable=False)  # e.g. "4 hours"
    created_at = Column(DateTime, default=_utcnow)

    # Relationships
    service = relationship("Service", back_populates="slas")

    def to_dict(self):
        return {
            "id": self.id,
            "service_id": self.service_id,
            "service_name": self.service.service_name if self.service else None,
            "priority": self.priority,
            "response_time": self.response_time,
            "resolution_time": self.resolution_time,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ═══════════════════════════════════════════════════════════════════════════
# FILES
# ═══════════════════════════════════════════════════════════════════════════
class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    # Relationships
    uploader = relationship("User", back_populates="uploaded_files")

    def to_dict(self):
        return {
            "id": self.id,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "file_size_display": _human_size(self.file_size),
            "uploaded_by": self.uploaded_by,
            "uploader_name": self.uploader.name if self.uploader else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def _human_size(nbytes: int) -> str:
    """Convert bytes to human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(nbytes) < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"
