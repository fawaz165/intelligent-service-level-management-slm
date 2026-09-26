"""
File management REST endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.services import file_service

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("")
def list_files(
    file_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return file_service.list_files(db, file_type=file_type, search=search)


@router.post("/upload", status_code=201)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
):
    """Upload a file — validates type and size, stores in storage/ directory."""
    content = await file.read()
    try:
        result = file_service.save_file(db, file.filename or "unnamed", content)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    if not file_service.delete_file(db, file_id):
        raise HTTPException(status_code=404, detail=f"File #{file_id} not found")
    return {"message": f"File #{file_id} deleted"}
