"""
SLA Monitoring & Risk Prediction Service.

Responsibilities:
  1. Parse SLA response/resolution targets into minutes.
  2. Map tickets and incidents to their corresponding services and SLA rules.
  3. Perform strictly deterministic rule-based risk evaluation (elapsed time,
     SLA thresholds, breach status, and risk classification: Critical, High, Medium, Low).
  4. Provide clear explanatory reasons and actionable remediation recommendations.
  5. Distinguish rule-based mathematical calculations from optional DeepSeek-R1 1.5B
     ML / LLM qualitative root-cause synthesis and actions.
  6. Compute dashboard summary metrics (total monitored, breached, at-risk, compliance rate,
     breakdown by service and risk level).
"""

import re
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from backend.database.models import Ticket, Incident, Service, SLA, User
from backend.services import llm_service

logger = logging.getLogger(__name__)

# Standard ITIL fallback SLA targets when a service lacks an explicit SLA row
DEFAULT_BASELINE_SLA = {
    "critical": {"response_minutes": 15, "resolution_minutes": 120, "response_time": "15 minutes", "resolution_time": "2 hours"},
    "high": {"response_minutes": 30, "resolution_minutes": 240, "response_time": "30 minutes", "resolution_time": "4 hours"},
    "medium": {"response_minutes": 120, "resolution_minutes": 480, "response_time": "2 hours", "resolution_time": "8 hours"},
    "low": {"response_minutes": 240, "resolution_minutes": 1440, "response_time": "4 hours", "resolution_time": "24 hours"},
}

# Mapping keywords in category or incident affected_service to Service IDs
_SERVICE_KEYWORD_MAP = {
    "network": 1,
    "r101": 1,
    "sw-05": 1,
    "firewall": 1,
    "switch": 1,
    "router": 1,
    "vpn": 1,
    "database": 2,
    "sql": 2,
    "mysql": 2,
    "postgres": 2,
    "replication": 2,
    "backup": 2,
    "email": 3,
    "collaboration": 3,
    "web": 4,
    "api": 4,
    "gateway": 4,
    "application": 4,
    "app": 4,
    "cache": 4,
    "security": 5,
    "ssl": 5,
    "tls": 5,
    "certificate": 5,
    "antivirus": 5,
    "hardware": 6,
    "printer": 6,
    "laptop": 6,
}


def parse_duration_to_minutes(dur_str: Optional[str]) -> Optional[int]:
    """Parse strings like '15 minutes', '1 hour', '4 hours', '24 hours' into integer minutes."""
    if not dur_str:
        return None
    s = dur_str.strip().lower()
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(minute|min|m|hour|hr|h|day|d)s?$", s)
    if not m:
        return None
    val, unit = float(m.group(1)), m.group(2)
    if unit in ("minute", "min", "m"):
        return int(round(val))
    if unit in ("hour", "hr", "h"):
        return int(round(val * 60))
    if unit in ("day", "d"):
        return int(round(val * 1440))
    return None


def format_minutes(mins: Optional[int]) -> str:
    """Format minutes into human-readable string like '45m', '2h 15m', or '24h'."""
    if mins is None:
        return "N/A"
    if mins < 60:
        return f"{mins}m"
    hours = mins // 60
    rem = mins % 60
    return f"{hours}h {rem}m" if rem else f"{hours}h"


def resolve_ticket_service(ticket: Ticket, db: Session) -> Optional[Service]:
    """Resolve the Service associated with a Ticket."""
    if ticket.service_id:
        svc = db.query(Service).filter(Service.id == ticket.service_id).first()
        if svc:
            return svc

    # Infer from category or title
    search_text = f"{ticket.category or ''} {ticket.title or ''}".lower()
    for kw, svc_id in _SERVICE_KEYWORD_MAP.items():
        if kw in search_text:
            return db.query(Service).filter(Service.id == svc_id).first()

    return None


def resolve_incident_service(incident: Incident, db: Session) -> Optional[Service]:
    """Resolve the Service associated with an Incident."""
    search_text = f"{incident.affected_service or ''} {incident.title or ''}".lower()
    for kw, svc_id in _SERVICE_KEYWORD_MAP.items():
        if kw in search_text:
            return db.query(Service).filter(Service.id == svc_id).first()

    return None


def get_sla_target(service_id: Optional[int], priority: Optional[str], db: Session) -> dict:
    """
    Lookup SLA target for a given service and priority.
    Returns dictionary with resolution/response minutes and source.
    """
    norm_prio = (priority or "medium").strip().lower()
    if norm_prio not in DEFAULT_BASELINE_SLA:
        norm_prio = "medium"

    if service_id:
        sla_rec = db.query(SLA).filter(
            SLA.service_id == service_id,
            SLA.priority.ilike(norm_prio)
        ).first()

        if sla_rec:
            resp_m = parse_duration_to_minutes(sla_rec.response_time)
            resol_m = parse_duration_to_minutes(sla_rec.resolution_time)
            if resol_m is not None:
                return {
                    "response_minutes": resp_m or DEFAULT_BASELINE_SLA[norm_prio]["response_minutes"],
                    "resolution_minutes": resol_m,
                    "response_time": sla_rec.response_time,
                    "resolution_time": sla_rec.resolution_time,
                    "sla_source": "service_sla",
                    "sla_id": sla_rec.id,
                }

    # Baseline ITIL fallback
    base = DEFAULT_BASELINE_SLA[norm_prio]
    return {
        "response_minutes": base["response_minutes"],
        "resolution_minutes": base["resolution_minutes"],
        "response_time": base["response_time"],
        "resolution_time": base["resolution_time"],
        "sla_source": "baseline_itil",
        "sla_id": None,
    }


def evaluate_single_item(
    item: Any,
    entity_type: str,
    db: Session,
    ref_time: Optional[datetime] = None,
) -> dict:
    """
    Deterministically evaluate SLA breach status and risk level for a ticket or incident.
    """
    now = ref_time or datetime.now(timezone.utc)

    # Normalize fields across Ticket and Incident models
    if entity_type == "incident":
        item_id = item.incident_id
        numeric_id = item.id
        title = item.title
        priority = (item.severity or "medium").strip().lower()
        status = (item.status or "open").strip().lower()
        svc = resolve_incident_service(item, db)
        service_name = svc.service_name if svc else (item.affected_service or "General Infrastructure")
        service_id = svc.id if svc else None
        assigned_to = item.assigned_to or "Unassigned"
        created_dt = item.detected_at or item.created_at
        is_incident = True
    else:
        item_id = f"#{item.id}"
        numeric_id = item.id
        title = item.title
        priority = (item.priority or "medium").strip().lower()
        status = (item.status or "open").strip().lower()
        svc = resolve_ticket_service(item, db)
        service_name = svc.service_name if svc else (item.category or "General IT")
        service_id = svc.id if svc else None
        assigned_to = item.assignee.name if (item.assignee and hasattr(item.assignee, "name")) else (f"User #{item.assigned_to}" if item.assigned_to else "Unassigned")
        created_dt = item.created_at
        is_incident = False

    # Ensure timezone aware comparison
    if created_dt and created_dt.tzinfo is None:
        created_dt = created_dt.replace(tzinfo=timezone.utc)

    # Check for missing/insufficient data
    if not created_dt:
        return {
            "id": numeric_id,
            "entity_id": item_id,
            "entity_type": entity_type,
            "title": title,
            "priority": priority,
            "status": status,
            "service_name": service_name,
            "service_id": service_id,
            "assigned_to": assigned_to,
            "created_at": None,
            "response_target": "N/A",
            "resolution_target": "N/A",
            "sla_source": "insufficient_data",
            "detection_mode": "insufficient_data",
            "is_breached": False,
            "risk_level": "Low",
            "percent_elapsed": 0.0,
            "elapsed_minutes": 0,
            "remaining_minutes": 0,
            "status_label": "Insufficient Data",
            "reason": "Missing timestamp: cannot compute SLA elapsed time without valid creation date.",
            "recommended_action": "Record incident/ticket detection timestamp in the database.",
            "ml_prediction": None,
        }

    # Fetch SLA Target
    sla_info = get_sla_target(service_id, priority, db)
    resol_target_m = sla_info["resolution_minutes"]
    resp_target_m = sla_info["response_minutes"]

    # Compute elapsed minutes
    elapsed_seconds = (now - created_dt).total_seconds()
    elapsed_minutes = max(0, int(round(elapsed_seconds / 60.0)))

    # Handle Resolved or Closed Items
    if status in ("resolved", "closed"):
        return {
            "id": numeric_id,
            "entity_id": item_id,
            "entity_type": entity_type,
            "title": title,
            "priority": priority,
            "status": status,
            "service_name": service_name,
            "service_id": service_id,
            "assigned_to": assigned_to,
            "created_at": created_dt.isoformat(),
            "response_target": sla_info["response_time"],
            "resolution_target": sla_info["resolution_time"],
            "sla_source": sla_info["sla_source"],
            "detection_mode": "rule_based",
            "is_breached": False,
            "risk_level": "Low",
            "percent_elapsed": 0.0,
            "elapsed_minutes": elapsed_minutes,
            "remaining_minutes": 0,
            "status_label": "Resolved / Compliant",
            "reason": f"Item status is '{status}'. Resolution complete; no ongoing SLA risk.",
            "recommended_action": "No immediate action required. Verify post-incident stability.",
            "ml_prediction": None,
        }

    # Calculate active progress against resolution SLA
    remaining_minutes = max(0, resol_target_m - elapsed_minutes)
    percent_elapsed = round((elapsed_minutes / resol_target_m) * 100.0, 1) if resol_target_m > 0 else 0.0

    # Rule-Based Risk Classification & Explanation
    is_unassigned = assigned_to in ("Unassigned", None, "")

    if elapsed_minutes >= resol_target_m:
        is_breached = True
        risk_level = "Critical"
        status_label = "Breached"
        over_m = elapsed_minutes - resol_target_m
        reason = (
            f"SLA limit of {format_minutes(resol_target_m)} was exceeded by {format_minutes(over_m)} "
            f"({percent_elapsed}% elapsed). Current status is '{status}'."
        )
        if is_unassigned:
            reason += " Item is currently unassigned."
            recommended_action = (
                f"[Critical Escalation] Assign on-call engineer immediately to {item_id}, "
                f"notify {service_name} service owner, and dispatch incident commander."
            )
        else:
            recommended_action = (
                f"[Critical Escalation] Escalate {item_id} with assignee ({assigned_to}), "
                f"reallocate priority queue resources, and issue stakeholder breach notification."
            )

    elif percent_elapsed >= 90.0:
        is_breached = False
        risk_level = "Critical"
        status_label = "Imminent Breach"
        reason = (
            f"Imminent breach: {percent_elapsed}% of SLA elapsed ({format_minutes(elapsed_minutes)} "
            f"of {format_minutes(resol_target_m)}). Only {format_minutes(remaining_minutes)} remaining."
        )
        recommended_action = (
            f"[Urgent Intervention] Expedite active work on {item_id}. "
            f"Assign secondary engineer to assist {assigned_to} before breach threshold."
        )

    elif percent_elapsed >= 70.0 or (priority == "critical" and percent_elapsed >= 50.0):
        is_breached = False
        risk_level = "High"
        status_label = "At Risk"
        reason = (
            f"Elevated SLA risk: {percent_elapsed}% elapsed ({format_minutes(elapsed_minutes)} "
            f"of {format_minutes(resol_target_m)}). {format_minutes(remaining_minutes)} remaining."
        )
        if is_unassigned:
            reason += " High priority item has no assigned technician."
            recommended_action = f"[High Priority] Assign an available technician to {item_id} immediately to prevent escalation."
        else:
            recommended_action = (
                f"Prioritize resolution of {item_id} over lower-severity queue items. "
                f"Verify no external dependencies are blocking {assigned_to}."
            )

    elif percent_elapsed >= 40.0:
        is_breached = False
        risk_level = "Medium"
        status_label = "Moderate Risk"
        reason = (
            f"Moderate SLA consumption: {percent_elapsed}% elapsed ({format_minutes(elapsed_minutes)} "
            f"of {format_minutes(resol_target_m)}). {format_minutes(remaining_minutes)} remaining."
        )
        recommended_action = (
            f"Review progress of {item_id}. Ensure resolution workflow is underway "
            f"according to standard operating procedures."
        )

    else:
        is_breached = False
        risk_level = "Low"
        status_label = "On Track"
        reason = (
            f"Healthy SLA compliance: Only {percent_elapsed}% elapsed ({format_minutes(elapsed_minutes)} "
            f"of {format_minutes(resol_target_m)}). {format_minutes(remaining_minutes)} remaining."
        )
        recommended_action = f"Continue standard handling in normal queue rotation."

    # Check response SLA for unacknowledged incidents or open tickets
    if status == "open" and elapsed_minutes > resp_target_m:
        reason += f" [Response SLA target of {format_minutes(resp_target_m)} also exceeded]."

    return {
        "id": numeric_id,
        "entity_id": item_id,
        "entity_type": entity_type,
        "title": title,
        "priority": priority,
        "status": status,
        "service_name": service_name,
        "service_id": service_id,
        "assigned_to": assigned_to,
        "created_at": created_dt.isoformat(),
        "response_target": sla_info["response_time"],
        "resolution_target": sla_info["resolution_time"],
        "sla_source": sla_info["sla_source"],
        "detection_mode": "rule_based",
        "is_breached": is_breached,
        "risk_level": risk_level,
        "percent_elapsed": percent_elapsed,
        "elapsed_minutes": elapsed_minutes,
        "remaining_minutes": remaining_minutes,
        "status_label": status_label,
        "reason": reason,
        "recommended_action": recommended_action,
        "ml_prediction": None,
    }


async def enrich_with_ai_prediction(item_risk: dict) -> dict:
    """
    Enrich an item with DeepSeek-R1 1.5B qualitative root cause prediction and actionable remediation.
    Distinguishes rule-based calculations from model predictions.
    """
    entity = item_risk["entity_type"]
    title = item_risk["title"]
    priority = item_risk["priority"]
    service = item_risk["service_name"]
    elapsed_p = item_risk["percent_elapsed"]
    risk_lvl = item_risk["risk_level"]
    assigned = item_risk["assigned_to"]

    prompt = (
        f"You are an IT Service Management reliability engineer. "
        f"A rule-based SLA monitor has evaluated this {entity}:\n"
        f"Title: {title}\n"
        f"Service: {service}\n"
        f"Priority/Severity: {priority}\n"
        f"Assignee: {assigned}\n"
        f"Calculated SLA Elapsed: {elapsed_p}%\n"
        f"Deterministic Risk Level: {risk_lvl}\n\n"
        f"Do NOT invent false numbers or breach percentages. "
        f"Based on the technical nature of this issue, provide a brief qualitative root-cause risk assessment "
        f"and 2 concise, highly specific technical remediation steps.\n"
        f"Respond in 3 short lines."
    )

    try:
        raw_response = await llm_service.call_llm(prompt)
        cleaned = llm_service.clean_think_tags(raw_response).strip()
        lines = [l.strip() for l in cleaned.split("\n") if l.strip()]

        analysis_summary = lines[0] if lines else f"Potential service disruption in {service}."
        action_summary = " ".join(lines[1:]) if len(lines) > 1 else "Investigate logs, isolate component, and notify on-call engineer."

        item_risk["ml_prediction"] = {
            "model_name": "deepseek-r1:1.5b",
            "prediction_type": "qualitative_synthesis",
            "ai_root_cause_analysis": analysis_summary,
            "ai_recommended_action": action_summary,
            "risk_trajectory": "Escalating" if elapsed_p > 75 else ("Stable" if elapsed_p < 40 else "Monitor"),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }
        item_risk["detection_mode"] = "rule_based + ml_prediction"
        if action_summary:
            item_risk["recommended_action"] = f"[AI Recommendation] {action_summary} | [Rule-Based] {item_risk['recommended_action']}"
    except Exception as e:
        logger.warning("DeepSeek-R1 qualitative synthesis failed: %s", e)
        item_risk["ml_prediction"] = {
            "model_name": "deepseek-r1:1.5b",
            "status": "unavailable",
            "error": str(e),
        }

    return item_risk


def get_all_sla_risks(
    db: Session,
    risk_filter: Optional[str] = None,
    entity_filter: Optional[str] = None,
    service_filter: Optional[str] = None,
    breached_only: bool = False,
    include_resolved: bool = False,
    ref_time: Optional[datetime] = None,
) -> List[dict]:
    """
    Retrieve and evaluate SLA risks for all open/active tickets and incidents.
    """
    results: List[dict] = []

    # 1. Evaluate Tickets
    if not entity_filter or entity_filter.lower() in ("ticket", "tickets"):
        t_query = db.query(Ticket)
        if not include_resolved:
            t_query = t_query.filter(Ticket.status.in_(("open", "in_progress")))
        tickets = t_query.all()
        for t in tickets:
            evaluated = evaluate_single_item(t, "ticket", db, ref_time)
            results.append(evaluated)

    # 2. Evaluate Incidents
    if not entity_filter or entity_filter.lower() in ("incident", "incidents"):
        i_query = db.query(Incident)
        if not include_resolved:
            i_query = i_query.filter(Incident.status.in_(("open", "acknowledged")))
        incidents = i_query.all()
        for inc in incidents:
            evaluated = evaluate_single_item(inc, "incident", db, ref_time)
            results.append(evaluated)

    # Apply Filters
    if risk_filter:
        norm_rf = risk_filter.strip().lower()
        results = [r for r in results if r["risk_level"].lower() == norm_rf]

    if service_filter:
        norm_sf = service_filter.strip().lower()
        results = [r for r in results if norm_sf in (r["service_name"] or "").lower()]

    if breached_only:
        results = [r for r in results if r["is_breached"]]

    # Sort results: Critical first, then High, Medium, Low; secondary sort by percent_elapsed descending
    risk_rank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    results.sort(
        key=lambda x: (risk_rank.get(x["risk_level"], 0), x["percent_elapsed"]),
        reverse=True,
    )

    return results


def get_sla_dashboard_metrics(db: Session, ref_time: Optional[datetime] = None) -> dict:
    """
    Compute aggregate summary metrics across all monitored active items.
    """
    active_risks = get_all_sla_risks(db, include_resolved=False, ref_time=ref_time)
    all_items = get_all_sla_risks(db, include_resolved=True, ref_time=ref_time)

    total_monitored = len(active_risks)
    breached_count = sum(1 for r in active_risks if r["is_breached"])
    critical_count = sum(1 for r in active_risks if r["risk_level"] == "Critical")
    high_count = sum(1 for r in active_risks if r["risk_level"] == "High")
    medium_count = sum(1 for r in active_risks if r["risk_level"] == "Medium")
    low_count = sum(1 for r in active_risks if r["risk_level"] == "Low")

    at_risk_count = critical_count + high_count
    compliant_count = total_monitored - breached_count
    compliance_rate = round((compliant_count / total_monitored) * 100.0, 1) if total_monitored > 0 else 100.0

    avg_elapsed = round(sum(r["percent_elapsed"] for r in active_risks) / total_monitored, 1) if total_monitored > 0 else 0.0

    # Entity Breakdown
    ticket_risks = [r for r in active_risks if r["entity_type"] == "ticket"]
    incident_risks = [r for r in active_risks if r["entity_type"] == "incident"]

    by_entity = {
        "tickets": {
            "total": len(ticket_risks),
            "breached": sum(1 for r in ticket_risks if r["is_breached"]),
            "at_risk": sum(1 for r in ticket_risks if r["risk_level"] in ("Critical", "High")),
            "healthy": sum(1 for r in ticket_risks if r["risk_level"] in ("Medium", "Low")),
        },
        "incidents": {
            "total": len(incident_risks),
            "breached": sum(1 for r in incident_risks if r["is_breached"]),
            "at_risk": sum(1 for r in incident_risks if r["risk_level"] in ("Critical", "High")),
            "healthy": sum(1 for r in incident_risks if r["risk_level"] in ("Medium", "Low")),
        },
    }

    # Breakdown by Service
    services_map: Dict[str, dict] = {}
    for r in active_risks:
        s_name = r["service_name"] or "General"
        if s_name not in services_map:
            services_map[s_name] = {
                "service_name": s_name,
                "total": 0,
                "breached": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
            }
        services_map[s_name]["total"] += 1
        if r["is_breached"]:
            services_map[s_name]["breached"] += 1
        lvl = r["risk_level"].lower()
        if lvl in services_map[s_name]:
            services_map[s_name][lvl] += 1

    by_service = sorted(services_map.values(), key=lambda s: (s["breached"], s["critical"], s["total"]), reverse=True)

    # Top 5 high-risk items
    top_risk_items = active_risks[:8]

    return {
        "total_monitored": total_monitored,
        "breached_count": breached_count,
        "at_risk_count": at_risk_count,
        "compliant_count": compliant_count,
        "compliance_rate": compliance_rate,
        "critical_count": critical_count,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
        "average_elapsed_percent": avg_elapsed,
        "by_entity": by_entity,
        "by_service": by_service,
        "top_risk_items": top_risk_items,
        "total_all_records": len(all_items),
        "generated_at": (ref_time or datetime.now(timezone.utc)).isoformat(),
    }
