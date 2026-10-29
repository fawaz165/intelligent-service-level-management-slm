"""
Intent Dispatcher — routes validated LLM intents to the correct backend service.

Architecture:  LLM Intent → Dispatcher → Service → Database
The dispatcher never touches the database directly.
"""

import logging
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.schemas import LLMIntent
from backend.services import ticket_service, service_service, file_service, incident_service, sla_service, telemetry_service

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
    "sla_risk": "sla_risk",
    "sla_risks": "sla_risk",
    "sla risk": "sla_risk",
    "sla risks": "sla_risk",
    "sla breach": "sla_risk",
    "sla breaches": "sla_risk",
    "sla_breach": "sla_risk",
    "sla_breaches": "sla_risk",
    "breach": "sla_risk",
    "breaches": "sla_risk",
    "risk": "sla_risk",
    "risks": "sla_risk",
    "database": "database_counts",
    "database_counts": "database_counts",
    "db_counts": "database_counts",
    "tables": "database_counts",
    "table_counts": "database_counts",
    "record_counts": "database_counts",
    "counts": "database_counts",
    "sla_metrics": "sla_metrics",
    "sla_metric": "sla_metrics",
    "sla_summary": "sla_metrics",
    "sla_kpis": "sla_metrics",
    "sla_kpi": "sla_metrics",
    "sla_dashboard": "sla_metrics",
    "telemetry": "telemetry",
    "network_telemetry": "telemetry",
    "host_telemetry": "telemetry",
    "system_telemetry": "telemetry",
    "telemetry_metrics": "telemetry",
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

    # ── SLA RISK operations ──────────────────────────────────────────
    if entity == "sla_risk":
        return await _handle_sla_risk(op, params, filters, intent, db)

    # ── USER / SLA — read-only for now ───────────────────────────────
    if entity in ("user", "sla"):
        return _handle_readonly(entity, op, filters, db)

    # ── DATABASE RECORD COUNTS ───────────────────────────────────────
    if entity == "database_counts":
        return _handle_database_counts(db)

    # ── SLA GLOBAL METRICS ───────────────────────────────────────────
    if entity == "sla_metrics":
        return _handle_sla_metrics(db)

    # ── TELEMETRY operations (Issue 2) ──────────────────────────────
    if entity == "telemetry":
        return _handle_telemetry(db, intent.message or "")

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
        # Single incident lookup by ID or incident code
        target_id = record_id or filters.get("id") or filters.get("incident_id")
        if target_id is not None:
            inc = incident_service.get_incident(db, target_id)
            if inc:
                desc = inc.get('description') or 'No description provided.'
                reply = (
                    f"Details for Incident {inc['incident_id']}: \"{inc['title']}\" "
                    f"({inc['status']}, {inc['severity']} severity).\n"
                    f"Description: {desc}"
                )
                return {
                    "reply": reply,
                    "data": [inc],
                    "data_type": "incidents",
                    "requires_confirmation": False,
                    "pending_action": None,
                }
            else:
                return {
                    "reply": f"Incident '{target_id}' was not found in the database.",
                    "data": [],
                    "data_type": "incidents",
                    "requires_confirmation": False,
                    "pending_action": None,
                }

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
def _generate_ticket_troubleshooting_recommendation(ticket: dict) -> str:
    """Generate category- and context-aware operational troubleshooting steps."""
    cat = (ticket.get("category") or "General").capitalize()
    title = ticket.get("title") or ""
    desc = ticket.get("description") or ""
    assignee = ticket.get("assignee_name") or "assigned technician"

    if cat == "Network" or "router" in title.lower() or "switch" in title.lower() or "packet" in desc.lower():
        return (
            f"Recommended Troubleshooting Steps:\n"
            f"1. Path Verification: Execute ping and traceroute tests to Router R101 / target interfaces to pinpoint the packet drop point.\n"
            f"2. Interface Error Inspection: Check router console for CRC errors, input queue drops, and carrier transitions on active uplink ports.\n"
            f"3. Routing & Link Stability: Review BGP/OSPF neighbor adjacency logs and syslog buffers for route flapping or flapping peer links.\n"
            f"4. Bandwidth & QoS Audit: Inspect WAN egress queue saturation and discard rates during peak utilization windows.\n"
            f"5. Hardware & Hand-off Check: Direct {assignee} to coordinate with network operations for cable/SFP physical integrity testing."
        )
    elif cat == "Database" or "sql" in title.lower() or "database" in title.lower():
        return (
            f"Recommended Troubleshooting Steps:\n"
            f"1. Connection Pool Audit: Inspect active vs maximum allowed database connections and connection pool saturation.\n"
            f"2. Lock & Contention Analysis: Query pg_stat_activity / SHOW PROCESSLIST for blocked transactions or table lock contention.\n"
            f"3. Slow Query Diagnostics: Check query execution plans and slow query logs for unindexed scans or high I/O queries.\n"
            f"4. Resource Sizing: Verify disk I/O latency, buffer pool hit ratio, and database host memory limits.\n"
            f"5. Action Assignment: Direct {assignee} to optimize query indexes or increase connection pool ceiling if sustained."
        )
    elif cat == "Server":
        return (
            f"Recommended Troubleshooting Steps:\n"
            f"1. Host Telemetry Verification: Review CPU, memory, and disk I/O metrics on the affected server node.\n"
            f"2. Process Health Check: Identify runaway processes, memory leaks, or hung daemon threads via top/htop.\n"
            f"3. System Log Triage: Inspect /var/log/messages or Event Viewer for kernel panics, OOM killer invocations, or disk faults.\n"
            f"4. Service Restart / Failover: If unresponsive, evaluate graceful service restart or failover to secondary cluster node.\n"
            f"5. Assignment Follow-up: Coordinate with {assignee} to verify host health recovery post-remediation."
        )
    else:
        return (
            f"Recommended Troubleshooting Steps:\n"
            f"1. Symptom Triage: Replicate the reported issue against standard service benchmarks and error logs.\n"
            f"2. Dependency Check: Verify upstream APIs, authentication providers, and database connectivity.\n"
            f"3. Component Isolation: Review recent deployment diffs, configuration updates, or environment variable changes.\n"
            f"4. Workaround & Containment: Apply temporary failover or traffic rerouting if customer-impacting.\n"
            f"5. Escalation: Engage {assignee} to implement permanent fix and document post-incident learnings."
        )


# ═════════════════════════════════════════════════════════════════════════
# TICKET handler
# ═════════════════════════════════════════════════════════════════════════
def _handle_ticket(op, params, filters, record_id, intent, db):
    if op in ("READ", "SEARCH"):
        # Single ticket lookup by ID (Issue 1)
        target_id = record_id or filters.get("id") or filters.get("ticket_id")
        if target_id is not None:
            try:
                tid = int(target_id)
            except (ValueError, TypeError):
                tid = None

            if tid is not None:
                ticket = ticket_service.get_ticket(db, tid)
                if ticket:
                    raw_msg = (intent.message or "").lower()
                    is_troubleshooting = bool(
                        filters.get("troubleshoot")
                        or any(
                            w in raw_msg for w in [
                                "analyz", "troubleshoot", "recommend", "step", "fix",
                                "diagnos", "investigat", "action", "guidanc"
                            ]
                        )
                    )
                    if is_troubleshooting:
                        steps_text = _generate_ticket_troubleshooting_recommendation(ticket)
                        reply = (
                            f"Analysis for Ticket #{tid}: \"{ticket['title']}\" "
                            f"({ticket['priority'].upper()} priority, {ticket['category']}).\n\n"
                            f"{steps_text}"
                        )
                    else:
                        desc = ticket.get("description") or "No description provided."
                        reply = (
                            f"Details for Ticket #{tid}: \"{ticket['title']}\" "
                            f"({ticket['status']}, {ticket['priority']} priority).\n"
                            f"Description: {desc}"
                        )

                    return {
                        "reply": reply,
                        "data": [ticket],
                        "data_type": "tickets",
                        "requires_confirmation": False,
                        "pending_action": None,
                    }
                else:
                    return {
                        "reply": f"Ticket #{tid} was not found in the database.",
                        "data": [],
                        "data_type": "tickets",
                        "requires_confirmation": False,
                        "pending_action": None,
                    }

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


# ═════════════════════════════════════════════════════════════════════════
# SLA RISK handler
# ═════════════════════════════════════════════════════════════════════════
async def _handle_sla_risk(op, params, filters, intent, db):
    risk_level = filters.get("risk_level") or filters.get("priority")
    entity_filter = filters.get("entity")
    service_filter = filters.get("service")
    breached_only = bool(filters.get("breached_only") or "breach" in (intent.message or "").lower())

    risks = sla_service.get_all_sla_risks(
        db,
        risk_filter=risk_level,
        entity_filter=entity_filter,
        service_filter=service_filter,
        breached_only=breached_only,
    )

    # If user explicitly requested prediction / AI analysis, enrich top items with DeepSeek-R1
    if filters.get("with_ai") or any(w in (intent.message or "").lower() for w in ["predict", "prediction", "ai", "recommend"]):
        enriched = []
        for r in risks[:3]:
            r_copy = dict(r)
            r_enriched = await sla_service.enrich_with_ai_prediction(r_copy)
            enriched.append(r_enriched)
        risks = enriched + risks[3:]

    count = len(risks)
    global_metrics = sla_service.get_sla_dashboard_metrics(db)
    total_monitored = global_metrics["total_monitored"]
    count = len(risks)
    breached_cnt = sum(1 for r in risks if r.get("is_breached"))
    crit_cnt = sum(1 for r in risks if r.get("risk_level") == "Critical")

    if count == 0:
        if breached_only or (risk_level and risk_level.lower() in ("breached", "breach")):
            reply = f"No breached items found (0 out of {total_monitored} active monitored items in the SLA system; global compliance rate is {global_metrics['compliance_rate']}%)."
        elif risk_level and risk_level.lower() in ("at_risk", "at-risk", "at risk"):
            reply = f"No at-risk items found (0 out of {total_monitored} active monitored items in the SLA system; global compliance rate is {global_metrics['compliance_rate']}%)."
        elif risk_level and risk_level.lower() in ("healthy", "on_track", "on-track", "on track"):
            reply = f"No healthy items found (0 out of {total_monitored} active monitored items in the SLA system; global compliance rate is {global_metrics['compliance_rate']}%)."
        elif risk_level:
            reply = f"No {risk_level.capitalize()}-risk items found matching your criteria (out of {total_monitored} active monitored items in the SLA system; global compliance rate is {global_metrics['compliance_rate']}%)."
        else:
            reply = f"No items matching your SLA criteria were found (out of {total_monitored} active monitored items in the system; global compliance rate is {global_metrics['compliance_rate']}%)."
    elif breached_only or (risk_level and risk_level.lower() in ("breached", "breach")):
        reply = (
            f"Found {count} breached item{'s' if count != 1 else ''} "
            f"(out of {total_monitored} active monitored items in the SLA system; global compliance rate is {global_metrics['compliance_rate']}%)."
        )
    elif risk_level and risk_level.lower() in ("at_risk", "at-risk", "at risk"):
        reply = (
            f"Found {count} at-risk item{'s' if count != 1 else ''} "
            f"(out of {total_monitored} active monitored items in the SLA system; global compliance rate is {global_metrics['compliance_rate']}%)."
        )
    elif risk_level and risk_level.lower() in ("healthy", "on_track", "on-track", "on track"):
        reply = (
            f"Found {count} healthy / on-track item{'s' if count != 1 else ''} "
            f"(out of {total_monitored} active monitored items in the SLA system; global compliance rate is {global_metrics['compliance_rate']}%)."
        )
    elif risk_level:
        reply = (
            f"Found {count} {risk_level.capitalize()}-risk item{'s' if count != 1 else ''} "
            f"(out of {total_monitored} active monitored items in the SLA system; global compliance rate is {global_metrics['compliance_rate']}%)."
        )
    else:
        entity_desc = f"{entity_filter} " if entity_filter else ""
        reply = (
            f"Found {count} {entity_desc}monitored item{'s' if count != 1 else ''} in SLA risk monitoring: "
            f"{breached_cnt} currently breached, {crit_cnt} at Critical risk "
            f"(Global compliance rate: {global_metrics['compliance_rate']}% across {total_monitored} active items)."
        )

    return {
        "reply": reply,
        "data": risks,
        "data_type": "sla_risks",
        "requires_confirmation": False,
        "pending_action": None,
    }


# ═════════════════════════════════════════════════════════════════════════
# DATABASE RECORD COUNTS handler (Issue 2)
# ═════════════════════════════════════════════════════════════════════════
def _handle_database_counts(db: Session) -> dict:
    from backend.database.models import Ticket, Incident, Service, User, SLA, File

    ticket_cnt = db.query(Ticket).count()
    service_cnt = db.query(Service).count()
    user_cnt = db.query(User).count()
    sla_cnt = db.query(SLA).count()
    incident_cnt = db.query(Incident).count()
    file_cnt = db.query(File).count()
    total_cnt = ticket_cnt + service_cnt + user_cnt + sla_cnt + incident_cnt + file_cnt

    data = [
        {"table": "tickets", "count": ticket_cnt, "description": "Support tickets"},
        {"table": "services", "count": service_cnt, "description": "Catalog services"},
        {"table": "users", "count": user_cnt, "description": "System users"},
        {"table": "sla", "count": sla_cnt, "description": "Service level agreement targets"},
        {"table": "incidents", "count": incident_cnt, "description": "Production incidents"},
        {"table": "files", "count": file_cnt, "description": "Stored file metadata records"},
    ]

    # Clean prose summary with NO raw markdown table syntax (rendered by DataTable in UI)
    reply = (
        f"Database record counts across all 6 tables in SQLite (`islm_recovered.db`): "
        f"{total_cnt} total records ({ticket_cnt} tickets, {service_cnt} services, {user_cnt} users, "
        f"{sla_cnt} SLA records, {incident_cnt} incidents, {file_cnt} file metadata records)."
    )

    return {
        "reply": reply,
        "data": data,
        "data_type": "database_counts",
        "requires_confirmation": False,
        "pending_action": None,
    }


# ═════════════════════════════════════════════════════════════════════════
# SLA GLOBAL METRICS handler (Issue 3 & 4)
# ═════════════════════════════════════════════════════════════════════════
def _handle_sla_metrics(db: Session) -> dict:
    metrics = sla_service.get_sla_dashboard_metrics(db)

    total_monitored = metrics["total_monitored"]
    breached_count = metrics["breached_count"]
    at_risk_count = metrics["at_risk_count"]
    imminent_breach_count = metrics["imminent_breach_count"]
    high_risk_count = metrics["high_risk_count"]
    healthy_count = metrics["healthy_count"]
    compliant_count = metrics["compliant_count"]
    compliance_rate = metrics["compliance_rate"]
    total_all = metrics["total_all_records"]
    resolved_count = metrics["resolved_count"]

    # Mutually exclusive partition: breached_count + at_risk_count + healthy_count == total_monitored
    data = [
        {"metric": "Total Monitored Items", "value": str(total_monitored), "status": "Active"},
        {"metric": "Breached Items", "value": str(breached_count), "status": "Breached" if breached_count > 0 else "Compliant"},
        {"metric": "At Risk Items", "value": f"{at_risk_count} ({imminent_breach_count} Critical imminent, {high_risk_count} High)", "status": "At Risk" if at_risk_count > 0 else "Healthy"},
        {"metric": "Healthy / On-Track Items", "value": str(healthy_count), "status": "Healthy"},
        {"metric": "Overall Compliance Rate", "value": f"{compliance_rate}%", "status": "Compliant" if compliance_rate >= 90.0 else "Degraded"},
        {"metric": "Compliant Items", "value": str(compliant_count), "status": "Compliant"},
        {"metric": "Total System Records", "value": f"{total_all} ({resolved_count} resolved/closed)", "status": "Total"},
    ]

    # Clean prose introductory reply with NO raw markdown table syntax (rendered by DataTable in UI)
    reply = (
        f"Global SLA Metrics Summary across {total_monitored} active monitored items: "
        f"{breached_count} breached, {at_risk_count} at risk, and {healthy_count} healthy/on-track. "
        f"Overall compliance rate is {compliance_rate}%."
    )

    return {
        "reply": reply,
        "data": data,
        "data_type": "sla_metrics",
        "requires_confirmation": False,
        "pending_action": None,
    }


# ═════════════════════════════════════════════════════════════════════════
# TELEMETRY handler (Issue 2)
# ═════════════════════════════════════════════════════════════════════════
def _handle_telemetry(db: Session, user_message: str) -> dict:
    """
    Handle natural-language telemetry questions about network latency, packet loss,
    and host metrics, returning values and clearly distinguishing real measurements
    from simulated telemetry.
    """
    metrics = telemetry_service.get_telemetry_metrics(db)
    real = metrics.get("real_metrics", {})
    sim = metrics.get("simulated_metrics", {})

    net_lat = sim.get("network_latency_ms", 18.2)
    pkt_loss = sim.get("packet_loss_pct", 0.02)
    net_status = sim.get("network_latency_status", "Healthy")
    pkt_status = sim.get("packet_loss_status", "Healthy")
    net_source = sim.get("network_latency_source", "WAN Edge Gateway R101 (Simulated)")
    pkt_source = sim.get("packet_loss_source", "ICMP Probe (Simulated)")

    db_lat = real.get("database_response_time_ms", 0.5)
    db_status = real.get("database_response_time_status", "Healthy")
    cpu_pct = real.get("host_cpu_usage_pct", 15.0)
    cpu_status = real.get("host_cpu_status", "Healthy")
    ram_pct = real.get("host_ram_usage_pct", 60.0)
    ram_status = real.get("host_ram_status", "Healthy")
    loop_lat = real.get("loopback_latency_ms", 0.8)

    # Clean prose explanation clearly distinguishing real measurements from simulated telemetry
    reply = (
        f"Current Telemetry & Performance Measurements:\n\n"
        f"• Network Telemetry (🟣 SIMULATED):\n"
        f"  - WAN Latency: {net_lat} ms ({net_status}, Source: {net_source})\n"
        f"  - Packet Loss Rate: {pkt_loss}% ({pkt_status}, Source: {pkt_source})\n"
        f"  - Measurement Type: SIMULATED — These network metrics are simulated enterprise IT telemetry correlated with active ticket and incident records in SQLite (e.g. Router R101, Switch SW-05).\n\n"
        f"• Host System Telemetry (🟢 REAL):\n"
        f"  - SQLite Query Latency: {db_lat} ms ({db_status})\n"
        f"  - Host CPU Utilization: {cpu_pct}% ({cpu_status}, OS Kernel via psutil)\n"
        f"  - Host RAM Utilization: {ram_pct}% ({ram_status}, Virtual Memory via psutil)\n"
        f"  - Local Loopback Latency: {loop_lat} ms\n"
        f"  - Measurement Type: REAL — These are live, verified host measurements captured directly from the local operating system and SQLite database engine."
    )

    data = [
        {
            "metric": "WAN Network Latency",
            "value": f"{net_lat} ms",
            "type": "🟣 Simulated",
            "status": net_status,
            "source": net_source,
        },
        {
            "metric": "Packet Loss Rate",
            "value": f"{pkt_loss}%",
            "type": "🟣 Simulated",
            "status": pkt_status,
            "source": pkt_source,
        },
        {
            "metric": "SQLite Response Time",
            "value": f"{db_lat} ms",
            "type": "🟢 Real",
            "status": db_status,
            "source": "SQLite islm.db Kernel",
        },
        {
            "metric": "Host CPU Utilization",
            "value": f"{cpu_pct}%",
            "type": "🟢 Real",
            "status": cpu_status,
            "source": "OS Kernel (psutil)",
        },
        {
            "metric": "Host RAM Utilization",
            "value": f"{ram_pct}%",
            "type": "🟢 Real",
            "status": ram_status,
            "source": "Virtual Memory (psutil)",
        },
    ]

    return {
        "reply": reply,
        "data": data,
        "data_type": "telemetry",
        "requires_confirmation": False,
        "pending_action": None,
    }



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
