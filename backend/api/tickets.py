"""
Ticket REST endpoints — direct CRUD access (bypasses LLM).
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.schemas import TicketCreate, TicketUpdate
from backend.services import ticket_service

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.get("")
def list_tickets(
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return ticket_service.list_tickets(db, status=status, category=category, priority=priority, search=search)


@router.get("/{ticket_id}")
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    t = ticket_service.get_ticket(db, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found")
    return t


@router.post("", status_code=201)
def create_ticket(data: TicketCreate, allow_duplicate: bool = False, db: Session = Depends(get_db)):
    if not allow_duplicate:
        dup = ticket_service.check_duplicate_ticket(db, data.title, data.category)
        if dup:
            raise HTTPException(
                status_code=409,
                detail=f"Active ticket #{dup['id']} with title '{dup['title']}' already exists.",
            )
    return ticket_service.create_ticket(db, data.model_dump(), allow_duplicate=True)


@router.put("/{ticket_id}")
def update_ticket(ticket_id: int, data: TicketUpdate, db: Session = Depends(get_db)):
    result = ticket_service.update_ticket(db, ticket_id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found")
    return result


@router.delete("/{ticket_id}")
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    if not ticket_service.delete_ticket(db, ticket_id):
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found")
    return {"message": f"Ticket #{ticket_id} deleted"}
