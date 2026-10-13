"""
Intent Dispatcher — routes validated LLM intents to the correct backend service.

Architecture:  LLM Intent → Dispatcher → Service → Database
The dispatcher never touches the database directly.
"""

import logging
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.schemas import LLMIntent
from backend.services import ticket_service, service_service, file_service, incident_service

logger = logging.getLogger(__name__)

# Validation constants
VALID_TICKET_CATEGORIES = ("Database", "Network", "Server", "Application", "Security", "Hardware")
VALID_TICKET_STATUSES = ("open", "in_progress", "resolved", "closed")
VALID_TICKET_PRIORITIES = ("low", "medium", "high", "critical")

VALID_INCIDENT_STATUSES = ("open", "acknowledged", "resolved", "closed")
VALID_INCIDENT_SEVERITIES = ("critical", "high", "medium", "low")

VALID_SERVICE_STATUSES = ("active", "inactive", "maintenance", "deprecated")
VALID_SLA_PRIORITIES = ("critical", "high", "medium", "low")

# Category names mapped to ticket category titles
_CATEGORY_MAP = {
    "database": "Database",
    "db": "Database",
    "network": "Network",
    "networking": "Network",
    "server": "Server",
    "servers": "Server",
    "application": "Application",
    "app": "Application",
    "software": "Application",
    "security": "Security",
    "hardware": "Hardware",
}

# Entities we know how to handle
_ENTITY_HANDLERS = {
    "incident": "incident",
    "incidents": "incident",
    "ticket": "ticket",
    "tickets": "ticket",
    "service": "service",
    "services": "service",
    "file": "file",
    "files": "file",
    "user": "user",
    "users": "user",
    "sla": "sla",
    "slas": "sla",
    "sla record": "sla",
    "sla records": "sla",
    "sla_records": "sla",
    **{cat: "ticket" for cat in _CATEGORY_MAP},
}


def _resolve_entity(raw: str) -> str:
    """Normalize the entity name."""
    return _ENTITY_HANDLERS.get(raw.strip().lower(), raw.strip().lower())


async def dispatch(intent: LLMIntent, db: Session) -> dict:
    """
    Execute the operation described by the LLM intent.

    Returns:
        {
            "reply": str,          # message to show the user
            "data": list | None,   # structured data (table rows)
            "data_type": str | None,
            "requires_confirmation": bool,
            "pending_action": dict | None,
        }
    """
    op = intent.operation.upper()
    raw_entity = intent.entity.strip().lower() if intent.entity else ""
    entity = _resolve_entity(raw_entity)
    params = intent.parameters or {}
    filters = intent.filters or {}
    record_id = intent.record_id

    # Fallback: If entity was specified as a category (e.g., "database"), auto-populate category parameter/filter
    if raw_entity in _CATEGORY_MAP:
        cat_val = _CATEGORY_MAP[raw_entity]
        if op == "CREATE" and "category" not in params:
            params["category"] = cat_val
        elif op in ("READ", "SEARCH") and "category" not in filters:
            filters["category"] = cat_val

    logger.info("Dispatching: op=%s entity=%s id=%s params=%s filters=%s", op, entity, record_id, params, filters)

    # ── GENERAL / UNKNOWN — no DB operation needed ───────────────────
    if op in ("GENERAL", "UNKNOWN"):
        return {
            "reply": intent.message or "I'm here to help with IT service management. Try asking me to show tickets, create a service, or manage files.",
            "data": None,
            "data_type": None,
            "requires_confirmation": False,
            "pending_action": None,
        }

    # ── INCIDENT operations ──────────────────────────────────────────
    if entity == "incident":
        return _handle_incident(op, params, filters, record_id, intent, db)

    # ── TICKET operations ────────────────────────────────────────────
    if entity == "ticket":
        return _handle_ticket(op, params, filters, record_id, intent, db)

    # ── SERVICE operations ───────────────────────────────────────────
    if entity == "service":
        return _handle_service(op, params, filters, record_id, intent, db)

    # ── FILE operations ──────────────────────────────────────────────
    if entity == "file":
        return _handle_file(op, params, filters, record_id, intent, db)

    # ── USER / SLA — read-only for now ───────────────────────────────
    if entity in ("user", "sla"):
        return _handle_readonly(entity, op, filters, db)

    return {
        "reply": f"I don't know how to work with '{entity}' yet. I can manage tickets, services, and files.",
        "data": None,
        "data_type": None,
        "requires_confirmation": False,
        "pending_action": None,
    }


# ═════════════════════════════════════════════════════════════════════════
# INCIDENT handler
# ═════════════════════════════════════════════════════════════════════════
def _handle_incident(op, params, filters, record_id, intent, db):
    if op in ("READ", "SEARCH"):
        # Validate status if provided
        status_filter = filters.get("status")
        if status_filter:
            norm_status = status_filter.strip().lower().replace(" ", "_").replace("-", "_")
            if norm_status not in VALID_INCIDENT_STATUSES:
                valid_list = ", ".join(VALID_INCIDENT_STATUSES)
                return {
                    "reply": f"'{status_filter}' is not a valid incident status. Valid statuses are: {valid_list}.",
                    "data": [],
                    "data_type": "incidents",
                    "requires_confirmation": False,
                    "pending_action": None,
                }
            filters["status"] = norm_status

        # Validate severity if provided
        sev_filter = filters.get("severity") or filters.get("priority")
        if sev_filter:
            norm_sev = sev_filter.strip().lower()
            if norm_sev not in VALID_INCIDENT_SEVERITIES:
                valid_list = ", ".join(VALID_INCIDENT_SEVERITIES)
                return {
                    "reply": f"'{sev_filter}' is not a valid incident severity. Valid severities are: {valid_list}.",
                    "data": [],
                    "data_type": "incidents",
                    "requires_confirmation": False,
                    "pending_action": None,
                }
            filters["severity"] = norm_sev

        results = incident_service.list_incidents(
            db,
            status=filters.get("status"),
            severity=filters.get("severity"),
            service=filters.get("service") or filters.get("category") or filters.get("affected_service"),
            search=filters.get("search") or filters.get("keyword") or filters.get("query"),
        )
        count = len(results)
        filter_parts = []
        if filters.get("status"):
            filter_parts.append(filters["status"])
        if filters.get("severity"):
            filter_parts.append(f"{filters['severity']}-severity")
        if filters.get("service") or filters.get("category"):
            filter_parts.append(filters.get("service") or filters.get("category"))
        filter_desc = " ".join(filter_parts) + " " if filter_parts else ""

        if count > 0:
            reply = f"Found {count} {filter_desc}incident{'s' if count != 1 else ''}."
        else:
            reply = f"No {filter_desc}incidents found matching your criteria." if filter_desc else "No incidents currently exist in the database."

        return {
            "reply": reply,
            "data": results,
            "data_type": "incidents",
            "requires_confirmation": False,
            "pending_action": None,
        }

    if op == "CREATE":
        if not params.get("title") and not params.get("description"):
            return {
                "reply": "To create an incident, please provide a title or issue description, affected service, and severity (critical, high, medium, low).",
                "data": None,
                "data_type": None,
                "requires_confirmation": False,
                "pending_action": None,
            }

        # Check for duplicate incident
        if params.get("title"):
            dup = incident_service.check_duplicate_incident(db, params["title"])
            if dup:
                return {
                    "reply": f"⚠️ An active incident with this title already exists: Incident {dup['incident_id']} — \"{dup['title']}\" ({dup['status']}, {dup['severity']} severity). Creation was skipped to prevent duplicate records.",
                    "data": [dup],
                    "data_type": "incidents",
                    "requires_confirmation": False,
                    "pending_action": None,
                }

        result = incident_service.create_incident(db, params)
        return {
            "reply": f"✅ Incident {result['incident_id']} created: \"{result['title']}\" ({result['severity']} severity, {result['affected_service'] or 'General'}).",
            "data": [result],
            "data_type": "incidents",
            "requires_confirmation": False,
            "pending_action": None,
        }

    if op == "UPDATE":
        if not record_id:
            return {
                "reply": "Which incident should I update? Please provide the incident ID.",
                "data": None, "data_type": None,
                "requires_confirmation": False, "pending_action": None,
            }
        result = incident_service.update_incident(db, record_id, params)
        if result is None:
            return {
                "reply": f"❌ Incident #{record_id} not found.",
                "data": None, "data_type": None,
                "requires_confirmation": False, "pending_action": None,
            }
        return {
            "reply": f"✅ Incident {result['incident_id']} updated successfully.",
            "data": [result],
            "data_type": "incidents",
            "requires_confirmation": False,
            "pending_action": None,
        }

    if op == "DELETE":
        if not record_id:
            return {
                "reply": "Which incident should I delete? Please provide the incident ID.",
                "data": None, "data_type": None,
                "requires_confirmation": False, "pending_action": None,
            }
        inc = incident_service.get_incident(db, record_id)
        if inc is None:
            return {
                "reply": f"❌ Incident #{record_id} not found.",
                "data": None, "data_type": None,
                "requires_confirmation": False, "pending_action": None,
            }
        return {
            "reply": f"⚠️ You are about to delete incident {inc['incident_id']}: \"{inc['title']}\". This action cannot be undone.",
            "data": [inc],
            "data_type": "incidents",
            "requires_confirmation": True,
            "pending_action": {"operation": "DELETE", "entity": "incident", "record_id": record_id},
        }

    return {"reply": intent.message or "I'm not sure what to do with that incident request.", "data": None, "data_type": None, "requires_confirmation": False, "pending_action": None}


# ═════════════════════════════════════════════════════════════════════════
# TICKET handler
# ═════════════════════════════════════════════════════════════════════════
def _handle_ticket(op, params, filters, record_id, intent, db):
    if op in ("READ", "SEARCH"):
        # Validate category if provided
        cat_filter = filters.get("category")
        if cat_filter:
            norm_cat = _CATEGORY_MAP.get(cat_filter.lower()) or (cat_filter if cat_filter in VALID_TICKET_CATEGORIES else None)
            if not norm_cat:
                valid_list = ", ".join(VALID_TICKET_CATEGORIES)
                return {
                    "reply": f"'{cat_filter}' is not a valid category. Valid categories are: {valid_list}.",
                    "data": [],
                    "data_type": "tickets",
                    "requires_confirmation": False,
                    "pending_action": None,
                }
            filters["category"] = norm_cat

        # Validate status if provided
        status_filter = filters.get("status")
        if status_filter:
            norm_status = status_filter.strip().lower().replace(" ", "_").replace("-", "_")
            if norm_status not in VALID_TICKET_STATUSES:
                valid_list = ", ".join(VALID_TICKET_STATUSES)
                return {
                    "reply": f"'{status_filter}' is not a valid ticket status. Valid statuses are: {valid_list}.",
                    "data": [],
                    "data_type": "tickets",
                    "requires_confirmation": False,
                    "pending_action": None,
                }
            filters["status"] = norm_status

        # Validate priority if provided
        prio_filter = filters.get("priority")
        if prio_filter:
            norm_prio = prio_filter.strip().lower()
            if norm_prio not in VALID_TICKET_PRIORITIES:
                valid_list = ", ".join(VALID_TICKET_PRIORITIES)
                return {
                    "reply": f"'{prio_filter}' is not a valid ticket priority. Valid priorities are: {valid_list}.",
                    "data": [],
                    "data_type": "tickets",
                    "requires_confirmation": False,
                    "pending_action": None,
                }
            filters["priority"] = norm_prio

        results = ticket_service.list_tickets(
            db,
            status=filters.get("status"),
            category=filters.get("category"),
            priority=filters.get("priority"),
            search=filters.get("search") or filters.get("keyword") or filters.get("query"),
            assigned_to=filters.get("assigned_to"),
            service_id=filters.get("service_id"),
        )
        count = len(results)
        # Build a human-readable filter description
        filter_parts = []
        if filters.get("status"):
            filter_parts.append(filters["status"])
        if filters.get("category"):
            filter_parts.append(filters["category"])
        if filters.get("priority"):
            filter_parts.append(f"{filters['priority']}-priority")
        filter_desc = " ".join(filter_parts) + " " if filter_parts else ""

        if count > 0:
            reply = f"Found {count} {filter_desc}ticket{'s' if count != 1 else ''}."
        else:
            reply = f"No {filter_desc}tickets found matching your criteria." if filter_desc else "No tickets currently exist in the database."

        return {
            "reply": reply,
            "data": results,
            "data_type": "tickets",
            "requires_confirmation": False,
            "pending_action": None,
        }

    if op == "CREATE":
        msg_lower = (intent.message or "").lower()

        # Handle missing information: check if user provided any specifics
        if not params.get("title") and not params.get("category") and not params.get("description") and not any(kw in msg_lower for kw in ["database", "network", "server", "application", "security", "hardware", "critical", "high", "medium", "low"]):
            valid_list = ", ".join(VALID_TICKET_CATEGORIES)
            return {
                "reply": f"To create a ticket, please provide details such as the title or issue description, category ({valid_list}), and priority (low, medium, high, critical).",
                "data": None,
                "data_type": None,
                "requires_confirmation": False,
                "pending_action": None,
            }

        # Infer priority if missing
        if "priority" not in params:
            for prio in ("critical", "high", "medium", "low"):
                if prio in msg_lower:
                    params["priority"] = prio
                    break

        # Infer category if missing
        if "category" not in params:
            for cat_key, cat_val in _CATEGORY_MAP.items():
                if cat_key in msg_lower:
                    params["category"] = cat_val
                    break

        # Validate category if specified
        cat = params.get("category")
        if cat:
            norm_cat = _CATEGORY_MAP.get(cat.lower()) or (cat if cat in VALID_TICKET_CATEGORIES else None)
            if not norm_cat:
                valid_list = ", ".join(VALID_TICKET_CATEGORIES)
                return {
                    "reply": f"'{cat}' is not a valid category for a ticket. Valid categories are: {valid_list}.",
                    "data": None,
                    "data_type": None,
                    "requires_confirmation": False,
                    "pending_action": None,
                }
            params["category"] = norm_cat

        # Infer title if missing
        if not params.get("title"):
            cat = params.get("category", "")
            prio = params.get("priority", "")
            if cat or prio:
                title_parts = [p.capitalize() for p in [prio, cat, "Ticket"] if p]
                params["title"] = " ".join(title_parts)
            else:
                params["title"] = intent.message or "New Ticket"

        # Check for duplicate active ticket
        if params.get("title"):
            dup = ticket_service.check_duplicate_ticket(db, params["title"], params.get("category"))
            if dup:
                return {
                    "reply": f"⚠️ An active ticket with this title already exists: Ticket #{dup['id']} — \"{dup['title']}\" ({dup['status']}, {dup['priority']} priority, {dup['category']}). Creation was skipped to prevent duplicate records.",
                    "data": [dup],
                    "data_type": "tickets",
                    "requires_confirmation": False,
                    "pending_action": None,
                }

        result = ticket_service.create_ticket(db, params)
        return {
            "reply": f"✅ Ticket #{result['id']} created: \"{result['title']}\" ({result['priority']} priority, {result['category']}).",
            "data": [result],
            "data_type": "tickets",
            "requires_confirmation": False,
            "pending_action": None,
        }

    if op == "UPDATE":
        if not record_id:
            return {
                "reply": "Which ticket should I update? Please provide the ticket ID.",
                "data": None, "data_type": None,
                "requires_confirmation": False, "pending_action": None,
            }
        result = ticket_service.update_ticket(db, record_id, params)
        if result is None:
            return {
                "reply": f"❌ Ticket #{record_id} not found.",
                "data": None, "data_type": None,
                "requires_confirmation": False, "pending_action": None,
            }
        return {
            "reply": f"✅ Ticket #{record_id} updated successfully.",
            "data": [result],
            "data_type": "tickets",
            "requires_confirmation": False,
            "pending_action": None,
        }

    if op == "DELETE":
        if not record_id:
            return {
                "reply": "Which ticket should I delete? Please provide the ticket ID.",
                "data": None, "data_type": None,
                "requires_confirmation": False, "pending_action": None,
            }
        # Return confirmation request — actual deletion happens on confirm
        ticket = ticket_service.get_ticket(db, record_id)
        if ticket is None:
            return {
                "reply": f"❌ Ticket #{record_id} not found.",
                "data": None, "data_type": None,
                "requires_confirmation": False, "pending_action": None,
            }
        return {
            "reply": f"⚠️ You are about to delete ticket #{record_id}: \"{ticket['title']}\". This action cannot be undone.",
            "data": [ticket],
            "data_type": "tickets",
            "requires_confirmation": True,
            "pending_action": {"operation": "DELETE", "entity": "ticket", "record_id": record_id},
        }

    return {"reply": intent.message or "I'm not sure what to do with that ticket request.", "data": None, "data_type": None, "requires_confirmation": False, "pending_action": None}


# ═════════════════════════════════════════════════════════════════════════
# SERVICE handler
# ═════════════════════════════════════════════════════════════════════════
def _handle_service(op, params, filters, record_id, intent, db):
    if op in ("READ", "SEARCH"):
        status_filter = filters.get("status")
        if status_filter:
            norm_status = status_filter.strip().lower()
            if norm_status not in VALID_SERVICE_STATUSES:
                valid_list = ", ".join(VALID_SERVICE_STATUSES)
                return {
                    "reply": f"'{status_filter}' is not a valid service status. Valid statuses are: {valid_list}.",
                    "data": [],
                    "data_type": "services",
                    "requires_confirmation": False,
                    "pending_action": None,
                }
            filters["status"] = norm_status

        results = service_service.list_services(
            db,
            status=filters.get("status"),
            search=filters.get("search") or filters.get("keyword"),
        )
        count = len(results)
        if count > 0:
            status_desc = f"{filters.get('status')} " if filters.get("status") else ""
            reply = f"Found {count} {status_desc}service{'s' if count != 1 else ''}."
        else:
            reply = "No services found matching your criteria." if filters else "No services currently exist in the database."

        return {
            "reply": reply,
            "data": results,
            "data_type": "services",
            "requires_confirmation": False,
            "pending_action": None,
        }

    if op == "CREATE":
        if not params.get("service_name"):
            return {
                "reply": "I need a name to create a service. What should it be called?",
                "data": None, "data_type": None,
                "requires_confirmation": False, "pending_action": None,
            }

        # Check for duplicate service
        dup = service_service.check_duplicate_service(db, params["service_name"])
        if dup:
            return {
                "reply": f"⚠️ An active service with this name already exists: Service #{dup['id']} — \"{dup['service_name']}\" ({dup['status']}). Creation was skipped to prevent duplicate records.",
                "data": [dup],
                "data_type": "services",
                "requires_confirmation": False,
                "pending_action": None,
            }

        result = service_service.create_service(db, params)
        return {
            "reply": f"✅ Service #{result['id']} created: \"{result['service_name']}\".",
            "data": [result],
            "data_type": "services",
            "requires_confirmation": False,
            "pending_action": None,
        }

    if op == "UPDATE":
        if not record_id:
            return {"reply": "Which service should I update? Please provide the service ID.", "data": None, "data_type": None, "requires_confirmation": False, "pending_action": None}
        result = service_service.update_service(db, record_id, params)
        if result is None:
            return {"reply": f"❌ Service #{record_id} not found.", "data": None, "data_type": None, "requires_confirmation": False, "pending_action": None}
        return {
            "reply": f"✅ Service #{record_id} updated successfully.",
            "data": [result],
            "data_type": "services",
            "requires_confirmation": False,
            "pending_action": None,
        }

    if op == "DELETE":
        if not record_id:
            return {"reply": "Which service should I delete? Please provide the service ID.", "data": None, "data_type": None, "requires_confirmation": False, "pending_action": None}
        svc = service_service.get_service(db, record_id)
        if svc is None:
            return {"reply": f"❌ Service #{record_id} not found.", "data": None, "data_type": None, "requires_confirmation": False, "pending_action": None}
        return {
            "reply": f"⚠️ You are about to delete service #{record_id}: \"{svc['service_name']}\". This action cannot be undone.",
            "data": [svc],
            "data_type": "services",
            "requires_confirmation": True,
            "pending_action": {"operation": "DELETE", "entity": "service", "record_id": record_id},
        }

    return {"reply": intent.message or "I'm not sure what to do with that service request.", "data": None, "data_type": None, "requires_confirmation": False, "pending_action": None}


# ═════════════════════════════════════════════════════════════════════════
# FILE handler
# ═════════════════════════════════════════════════════════════════════════
def _handle_file(op, params, filters, record_id, intent, db):
    if op in ("FILE_LIST", "READ", "SEARCH", "FILE_SEARCH"):
        ft = filters.get("file_type") or filters.get("type") or params.get("file_type")
        if ft:
            norm_ft = ft.strip().lower()
            if not norm_ft.startswith("."):
                norm_ft = f".{norm_ft}"
            if norm_ft not in settings.ALLOWED_FILE_TYPES:
                allowed_str = ", ".join(sorted(settings.ALLOWED_FILE_TYPES))
                return {
                    "reply": f"'{ft}' is not a supported file type. Supported types are: {allowed_str}.",
                    "data": [],
                    "data_type": "files",
                    "requires_confirmation": False,
                    "pending_action": None,
                }
            ft = norm_ft

        uploader = filters.get("uploader") or filters.get("uploaded_by") or filters.get("user")
        results = file_service.list_files(
            db,
            file_type=ft,
            search=filters.get("search") or filters.get("file_name") or filters.get("keyword"),
            uploader_name=uploader,
        )
        count = len(results)
        if count > 0:
            reply = f"Found {count} file{'s' if count != 1 else ''}."
        else:
            reply = "No files found matching your criteria." if (ft or uploader or filters.get("search")) else "No files currently exist in the database."

        return {
            "reply": reply,
            "data": results,
            "data_type": "files",
            "requires_confirmation": False,
            "pending_action": None,
        }

    if op in ("FILE_DELETE", "DELETE"):
        # Try by ID first, then by name
        target_id = record_id
        target_name = params.get("file_name") or filters.get("file_name")

        if target_id:
            f = file_service.get_file(db, target_id)
            if f is None:
                return {"reply": f"❌ File #{target_id} not found.", "data": None, "data_type": None, "requires_confirmation": False, "pending_action": None}
            return {
                "reply": f"⚠️ You are about to delete file \"{f['file_name']}\". This action cannot be undone.",
                "data": [f],
                "data_type": "files",
                "requires_confirmation": True,
                "pending_action": {"operation": "FILE_DELETE", "entity": "file", "record_id": target_id},
            }
        elif target_name:
            # Look up by name
            files = file_service.list_files(db, search=target_name)
            if not files:
                return {"reply": f"❌ No file found matching \"{target_name}\".", "data": None, "data_type": None, "requires_confirmation": False, "pending_action": None}
            f = files[0]
            return {
                "reply": f"⚠️ You are about to delete file \"{f['file_name']}\". This action cannot be undone.",
                "data": [f],
                "data_type": "files",
                "requires_confirmation": True,
                "pending_action": {"operation": "FILE_DELETE", "entity": "file", "record_id": f["id"]},
            }
        else:
            return {"reply": "Which file should I delete? Please provide the file name or ID.", "data": None, "data_type": None, "requires_confirmation": False, "pending_action": None}

    return {"reply": intent.message or "I can list, search, or delete files.", "data": None, "data_type": None, "requires_confirmation": False, "pending_action": None}


# ═════════════════════════════════════════════════════════════════════════
# READ-ONLY entities (user, sla)
# ═════════════════════════════════════════════════════════════════════════
def _handle_readonly(entity, op, filters, db):
    from backend.database.models import User, SLA, Service

    if op not in ("READ", "SEARCH"):
        return {"reply": f"Currently, {entity} records are read-only.", "data": None, "data_type": None, "requires_confirmation": False, "pending_action": None}

    if entity == "user":
        query = db.query(User).order_by(User.name)
        results = [u.to_dict() for u in query.all()]
        count = len(results)
        reply = f"Found {count} user{'s' if count != 1 else ''}." if count > 0 else "No user records exist in the database."
        return {"reply": reply, "data": results, "data_type": "users", "requires_confirmation": False, "pending_action": None}

    if entity == "sla":
        # Validate priority if provided
        prio = filters.get("priority")
        if prio:
            norm_prio = prio.strip().lower()
            if norm_prio not in VALID_SLA_PRIORITIES:
                valid_list = ", ".join(VALID_SLA_PRIORITIES)
                return {
                    "reply": f"'{prio}' is not a valid SLA priority. Valid priorities are: {valid_list}.",
                    "data": [],
                    "data_type": "sla",
                    "requires_confirmation": False,
                    "pending_action": None,
                }
            filters["priority"] = norm_prio

        query = db.query(SLA).join(Service, SLA.service_id == Service.id, isouter=True)
        if filters.get("priority"):
            query = query.filter(SLA.priority.ilike(filters["priority"]))
        if filters.get("service_id"):
            try:
                query = query.filter(SLA.service_id == int(filters["service_id"]))
            except (ValueError, TypeError):
                pass
        if filters.get("service") or filters.get("service_name"):
            s_name = filters.get("service") or filters.get("service_name")
            query = query.filter(Service.service_name.ilike(f"%{s_name}%"))
        query = query.order_by(SLA.service_id, SLA.priority)
        results = [s.to_dict() for s in query.all()]
        count = len(results)
        filter_parts = []
        if filters.get("priority"):
            filter_parts.append(f"{filters['priority']}-priority")
        if filters.get("service_name") or filters.get("service"):
            filter_parts.append(filters.get("service_name") or filters.get("service"))
        filter_desc = " ".join(filter_parts) + " " if filter_parts else ""

        if count > 0:
            reply = f"Found {count} {filter_desc}SLA record{'s' if count != 1 else ''}."
        else:
            reply = f"No {filter_desc}SLA records found matching your criteria." if filter_desc else "No SLA records currently exist in the database."

        return {
            "reply": reply,
            "data": results,
            "data_type": "sla",
            "requires_confirmation": False,
            "pending_action": None,
        }

    return {"reply": "I'm not sure how to handle that.", "data": None, "data_type": None, "requires_confirmation": False, "pending_action": None}


async def execute_confirmed_action(action: dict, db: Session) -> dict:
    """Execute a previously confirmed destructive action."""
    op = action.get("operation", "").upper()
    entity = action.get("entity", "")
    record_id = action.get("record_id")

    if op == "DELETE" and entity == "incident":
        success = incident_service.delete_incident(db, record_id)
        return {
            "reply": f"✅ Incident #{record_id} has been deleted." if success else f"❌ Incident #{record_id} not found.",
            "data": None, "data_type": None,
            "requires_confirmation": False, "pending_action": None,
        }

    if op == "DELETE" and entity == "ticket":
        success = ticket_service.delete_ticket(db, record_id)
        return {
            "reply": f"✅ Ticket #{record_id} has been deleted." if success else f"❌ Ticket #{record_id} not found.",
            "data": None, "data_type": None,
            "requires_confirmation": False, "pending_action": None,
        }

    if op == "DELETE" and entity == "service":
        success = service_service.delete_service(db, record_id)
        return {
            "reply": f"✅ Service #{record_id} has been deleted." if success else f"❌ Service #{record_id} not found.",
            "data": None, "data_type": None,
            "requires_confirmation": False, "pending_action": None,
        }

    if op == "FILE_DELETE" and entity == "file":
        success = file_service.delete_file(db, record_id)
        return {
            "reply": f"✅ File #{record_id} has been deleted." if success else f"❌ File #{record_id} not found.",
            "data": None, "data_type": None,
            "requires_confirmation": False, "pending_action": None,
        }

    return {"reply": "Unknown confirmed action.", "data": None, "data_type": None, "requires_confirmation": False, "pending_action": None}
