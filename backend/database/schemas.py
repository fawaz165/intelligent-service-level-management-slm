"""
Pydantic schemas for request / response validation.
Separate from SQLAlchemy models to enforce clean API boundaries.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Chat ─────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    confirm_action: Optional[str] = None   # "yes" / "no" for pending confirmations


class ChatResponse(BaseModel):
    reply: str
    data: Optional[list[dict]] = None
    data_type: Optional[str] = None        # "tickets", "services", "files", "users", "sla"
    requires_confirmation: bool = False
    pending_action: Optional[dict] = None


# ── LLM Intent (what the model returns) ──────────────────────────────────
class LLMIntent(BaseModel):
    """Structured intent extracted by DeepSeek-R1:1.5B."""
    operation: str = Field(..., description="CREATE | READ | UPDATE | DELETE | SEARCH | FILE_LIST | FILE_SEARCH | FILE_DELETE | GENERAL | UNKNOWN")
    entity: str = Field(default="", description="ticket | incident | service | user | sla | file")
    parameters: Optional[dict] = Field(default=None, description="Fields for CREATE / UPDATE")
    filters: Optional[dict] = Field(default=None, description="Filters for READ / SEARCH")
    record_id: Optional[int] = Field(default=None, description="Record ID for UPDATE / DELETE")
    requires_confirmation: bool = Field(default=False, description="True for destructive operations")
    message: str = Field(default="", description="Natural-language message to user")


# ── Incidents ────────────────────────────────────────────────────────────
class IncidentCreate(BaseModel):
    incident_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    severity: str = Field(default="medium")
    affected_service: Optional[str] = None
    affected_component: Optional[str] = None
    status: str = Field(default="open")
    assigned_to: Optional[str] = None
    tags: Optional[str] = None


class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    affected_service: Optional[str] = None
    affected_component: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    tags: Optional[str] = None


class IncidentOut(BaseModel):
    id: int
    incident_id: str
    source: Optional[str] = None
    title: str
    description: Optional[str] = None
    severity: str
    affected_service: Optional[str] = None
    affected_component: Optional[str] = None
    status: str
    assigned_to: Optional[str] = None
    tags: Optional[str] = None
    mttr_minutes: Optional[int] = None
    detected_at: Optional[str] = None
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: Optional[str] = None


# ── Tickets ──────────────────────────────────────────────────────────────
class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    category: str = Field(default="Application")
    priority: str = Field(default="medium")
    status: str = Field(default="open")
    assigned_to: Optional[int] = None
    service_id: Optional[int] = None


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[int] = None
    service_id: Optional[int] = None


class TicketOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    category: str
    priority: str
    status: str
    assigned_to: Optional[int]
    assignee_name: Optional[str]
    service_id: Optional[int]
    service_name: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


# ── Services ─────────────────────────────────────────────────────────────
class ServiceCreate(BaseModel):
    service_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    status: str = Field(default="active")
    owner: Optional[str] = None


class ServiceUpdate(BaseModel):
    service_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None


class ServiceOut(BaseModel):
    id: int
    service_name: str
    description: Optional[str]
    status: str
    owner: Optional[str]
    created_at: Optional[str]


# ── Files ────────────────────────────────────────────────────────────────
class FileOut(BaseModel):
    id: int
    file_name: str
    file_type: str
    file_size: int
    file_size_display: str
    uploaded_by: Optional[int]
    uploader_name: Optional[str]
    created_at: Optional[str]
