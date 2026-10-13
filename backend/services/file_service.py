"""
File service — business logic for file management.

Physical files are stored under STORAGE_PATH. Metadata is in the DB.
Safe path construction prevents directory traversal attacks.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.models import File

logger = logging.getLogger(__name__)


def _safe_path(filename: str) -> Path:
    """Construct a safe path inside the storage directory — no traversal allowed."""
    storage = settings.storage_dir()
    safe_name = Path(filename).name  # strips any directory components
    return storage / safe_name


def list_files(
    db: Session,
    file_type: Optional[str] = None,
    search: Optional[str] = None,
    uploaded_by: Optional[int] = None,
    uploader_name: Optional[str] = None,
) -> list[dict]:
    """List file metadata with optional type, name, and uploader filters."""
    from backend.database.models import User

    query = db.query(File)

    if file_type:
        ft = file_type.strip().lower()
        if not ft.startswith("."):
            ft = f".{ft}"
        query = query.filter(File.file_type == ft)
    if search:
        query = query.filter(File.file_name.ilike(f"%{search}%"))
    if uploaded_by:
        query = query.filter(File.uploaded_by == int(uploaded_by))
    if uploader_name:
        u_str = uploader_name.strip()
        query = query.join(User, File.uploaded_by == User.id, isouter=True).filter(
            User.name.ilike(f"%{u_str}%") | User.username.ilike(f"%{u_str}%")
        )

    query = query.order_by(File.created_at.desc())
    return [f.to_dict() for f in query.all()]


def get_file(db: Session, file_id: int) -> Optional[dict]:
    f = db.query(File).filter(File.id == file_id).first()
    return f.to_dict() if f else None


def save_file(
    db: Session,
    file_name: str,
    file_content: bytes,
    uploaded_by: Optional[int] = None,
) -> dict:
    """
    Save a file to disk and record metadata in the database.

    Validates: file type whitelist, file size limit, safe path.
    """
    ext = Path(file_name).suffix.lower()

    # Validate file type
    if ext not in settings.ALLOWED_FILE_TYPES:
        raise ValueError(f"File type '{ext}' is not allowed. Allowed: {', '.join(settings.ALLOWED_FILE_TYPES)}")

    # Validate file size
    if len(file_content) > settings.MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File exceeds maximum size of {settings.MAX_FILE_SIZE_MB} MB.")

    # Write to storage
    dest = _safe_path(file_name)

    # Handle name collision by appending a counter
    if dest.exists():
        stem = dest.stem
        counter = 1
        while dest.exists():
            dest = dest.parent / f"{stem}_{counter}{ext}"
            counter += 1

    dest.write_bytes(file_content)

    # Record metadata
    record = File(
        file_name=dest.name,
        file_path=str(dest),
        file_type=ext,
        file_size=len(file_content),
        uploaded_by=uploaded_by,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info("Saved file #%d: %s (%d bytes)", record.id, record.file_name, record.file_size)
    return record.to_dict()


def delete_file(db: Session, file_id: int) -> bool:
    """Delete file from disk and database."""
    record = db.query(File).filter(File.id == file_id).first()
    if not record:
        return False

    # Remove physical file
    try:
        p = Path(record.file_path)
        if p.exists():
            p.unlink()
    except OSError as e:
        logger.warning("Could not delete physical file %s: %s", record.file_path, e)

    db.delete(record)
    db.commit()
    logger.info("Deleted file #%d: %s", file_id, record.file_name)
    return True


def delete_file_by_name(db: Session, file_name: str) -> bool:
    """Delete a file by its name (case-insensitive match)."""
    record = db.query(File).filter(File.file_name.ilike(file_name)).first()
    if not record:
        return False
    return delete_file(db, record.id)
