"""
Database reset & reseed — drops all data and reseeds with new datasets.

Run:  python -m backend.database.reseed   (from project root)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.database.connection import init_db, SessionLocal
from backend.database.models import User, Service, Ticket, SLA, File


def reseed():
    """Drop all existing data and reseed with new datasets."""
    init_db()
    db = SessionLocal()

    try:
        # Delete all existing data (order matters for foreign keys)
        deleted_files = db.query(File).delete()
        deleted_slas = db.query(SLA).delete()
        deleted_tickets = db.query(Ticket).delete()
        deleted_services = db.query(Service).delete()
        deleted_users = db.query(User).delete()
        db.commit()

        print(f"Cleared old data: {deleted_users} users, {deleted_services} services, "
              f"{deleted_tickets} tickets, {deleted_slas} SLAs, {deleted_files} files")

    except Exception as e:
        db.rollback()
        print(f"Clear failed: {e}")
        raise
    finally:
        db.close()

    # Now run the normal seed
    from backend.database.seed import seed
    seed()


if __name__ == "__main__":
    reseed()
