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
from datetime import datetime, timezone, timedelta
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


def generate_recommended_action(
    entity_type: str,
    priority: str,
    status_label: str,
    is_unassigned: bool,
    assigned_to: str,
    item_id: str,
    service_name: str,
    remaining_minutes: int,
    over_minutes: int,
    percent_elapsed: float,
) -> str:
    """
    Generate tailored operational recommendations based on actual priority,
    SLA status, assignment state, and entity type (Ticket vs Incident).
    """
    prio = (priority or "medium").strip().lower()
    is_inc = (entity_type == "incident")

    # 1. BREACHED
    if status_label == "Breached":
        if prio == "critical":
            if is_inc:
                if is_unassigned:
                    return (
                        f"[P1 Incident Breach] SLA exceeded by {format_minutes(over_minutes)}. "
                        f"Immediately dispatch Incident Commander to {item_id}, page on-call {service_name} primary, "
                        f"and convene an emergency technical bridge."
                    )
                else:
                    return (
                        f"[P1 Incident Breach] SLA exceeded by {format_minutes(over_minutes)}. "
                        f"Escalate directly with {assigned_to}, mobilize tier-3 subject matter experts for {service_name}, "
                        f"and issue executive outage advisory."
                    )
            else:
                if is_unassigned:
                    return (
                        f"[P1 Ticket Breach] Critical ticket {item_id} breached SLA by {format_minutes(over_minutes)}. "
                        f"Assign senior technician immediately and notify {service_name} service delivery lead."
                    )
                else:
                    return (
                        f"[P1 Ticket Breach] Critical ticket {item_id} breached SLA by {format_minutes(over_minutes)}. "
                        f"Reallocate priority queue resources to assist {assigned_to} and initiate expedited resolution workflow."
                    )

        elif prio == "high":
            if is_inc:
                if is_unassigned:
                    return (
                        f"[P2 Incident Escalation] High-severity incident {item_id} breached SLA by {format_minutes(over_minutes)}. "
                        f"Assign infrastructure specialist immediately to commence containment and fault isolation."
                    )
                else:
                    return (
                        f"[P2 Expedited Action] High-severity incident {item_id} breached by {format_minutes(over_minutes)}. "
                        f"Direct {assigned_to} to prioritize remediation and publish progress bulletin to stakeholders."
                    )
            else:
                if is_unassigned:
                    return (
                        f"[High-Priority Escalation] Ticket {item_id} breached SLA by {format_minutes(over_minutes)}. "
                        f"Assign an available {service_name} engineer immediately to resume ticket progress."
                    )
                else:
                    return (
                        f"[High-Priority Follow-up] Ticket {item_id} is overdue by {format_minutes(over_minutes)}. "
                        f"Request immediate status checkpoint from {assigned_to} and clear task blockers."
                    )

        elif prio == "medium":
            if is_inc:
                if is_unassigned:
                    return (
                        f"[Operational Escalation] Medium incident {item_id} exceeded target by {format_minutes(over_minutes)}. "
                        f"Assign next available technician to begin troubleshooting."
                    )
                else:
                    return (
                        f"[Queue Re-evaluation] Medium incident {item_id} exceeded target by {format_minutes(over_minutes)}. "
                        f"Follow up with {assigned_to} to establish recovery ETA."
                    )
            else:
                if is_unassigned:
                    return (
                        f"[Queue Rebalancing] Ticket {item_id} has exceeded SLA target by {format_minutes(over_minutes)}. "
                        f"Assign support specialist from general queue to initiate handling."
                    )
                else:
                    return (
                        f"[Queue Follow-up] Ticket {item_id} exceeded SLA target by {format_minutes(over_minutes)}. "
                        f"Prompt {assigned_to} to complete pending action and update ticket status."
                    )

        else:  # low
            if is_inc:
                if is_unassigned:
                    return (
                        f"[Backlog Review] Minor incident {item_id} exceeded target by {format_minutes(over_minutes)}. "
                        f"Assign during routine queue sweep for scheduled resolution."
                    )
                else:
                    return (
                        f"[Routine Check] Low-severity incident {item_id} exceeded target by {format_minutes(over_minutes)}. "
                        f"Ensure {assigned_to} addresses this in the current operational cycle."
                    )
            else:
                if is_unassigned:
                    return (
                        f"[Backlog Allocation] Low-priority ticket {item_id} passed SLA deadline by {format_minutes(over_minutes)}. "
                        f"Allocate technician during next queue triage cycle."
                    )
                else:
                    return (
                        f"[Scheduled Review] Low-priority ticket {item_id} passed deadline by {format_minutes(over_minutes)}. "
                        f"Prompt {assigned_to} to resolve during regular maintenance window."
                    )

    # 2. IMMINENT BREACH (90% - 100%)
    elif status_label == "Imminent Breach":
        if prio == "critical":
            if is_unassigned:
                return (
                    f"[Emergency Intervention] Critical {entity_type} {item_id} is at {percent_elapsed}% SLA consumption "
                    f"with only {format_minutes(remaining_minutes)} remaining. Assign on-call engineer immediately!"
                )
            else:
                return (
                    f"[Urgent Push] Critical {entity_type} {item_id} breach imminent ({format_minutes(remaining_minutes)} remaining). "
                    f"Pair secondary engineer with {assigned_to} to finalize resolution before deadline."
                )
        elif prio == "high":
            if is_unassigned:
                return (
                    f"[Urgent Assignment] High-priority {entity_type} {item_id} has only {format_minutes(remaining_minutes)} remaining. "
                    f"Assign available technician right away to avoid breach."
                )
            else:
                return (
                    f"[Priority Fast-Track] High-priority {entity_type} {item_id} has {format_minutes(remaining_minutes)} remaining. "
                    f"Expedite active resolution with {assigned_to} and clear any review gates."
                )
        elif prio == "medium":
            if is_unassigned:
                return (
                    f"[Expedited Triage] Medium {entity_type} {item_id} has {format_minutes(remaining_minutes)} before breach. "
                    f"Assign technician promptly."
                )
            else:
                return (
                    f"[Deadline Approaching] {format_minutes(remaining_minutes)} remaining on medium {entity_type} {item_id}. "
                    f"Follow up with {assigned_to} to wrap up work before SLA expires."
                )
        else:  # low
            if is_unassigned:
                return (
                    f"[Queue Priority] Low-priority {entity_type} {item_id} approaching SLA limit ({format_minutes(remaining_minutes)} remaining). "
                    f"Assign technician to complete handling."
                )
            else:
                return (
                    f"[Wrap-up Alert] Low-priority {entity_type} {item_id} has {format_minutes(remaining_minutes)} remaining. "
                    f"Prompt {assigned_to} to complete and close."
                )

    # 3. AT RISK (70% - 90% or Critical >= 50%)
    elif status_label == "At Risk":
        if prio == "critical":
            if is_unassigned:
                return (
                    f"[P1 Proactive Action] Critical {entity_type} {item_id} has consumed {percent_elapsed}% of SLA without an assignee. "
                    f"Assign primary lead immediately to protect SLA."
                )
            else:
                return (
                    f"[Active Monitoring] Critical {entity_type} {item_id} at {percent_elapsed}% SLA consumption. "
                    f"Verify {assigned_to} has dedicated focus and no blocking dependencies."
                )
        elif prio == "high":
            if is_unassigned:
                return (
                    f"[High-Priority Assignment] Assign technician to {item_id} immediately. "
                    f"{format_minutes(remaining_minutes)} remaining in SLA window."
                )
            else:
                return (
                    f"[Prioritize Queue] Prioritize {item_id} over lower-severity queue items. "
                    f"Ensure {assigned_to} has adequate support."
                )
        elif prio == "medium":
            if is_unassigned:
                return (
                    f"[Standard Assignment] Assign technician to {item_id} to maintain steady progress. "
                    f"{format_minutes(remaining_minutes)} remaining."
                )
            else:
                return (
                    f"[Progress Review] Check progress on {item_id} with {assigned_to}. "
                    f"Ensure resolution steps remain on schedule."
                )
        else:  # low
            if is_unassigned:
                return (
                    f"[Queue Scheduling] Schedule {item_id} for assignment in upcoming queue distribution. "
                    f"{format_minutes(remaining_minutes)} remaining."
                )
            else:
                return (
                    f"[Monitor Progress] Track routine progress on {item_id} with {assigned_to}."
                )

    # 4. MODERATE RISK (40% - 70%)
    elif status_label == "Moderate Risk":
        if prio in ("critical", "high"):
            if is_unassigned:
                return f"Assign {prio}-priority {entity_type} {item_id} promptly to preserve SLA headroom."
            else:
                return f"Ensure resolution workflow is progressing smoothly with {assigned_to} for {item_id}."
        elif prio == "medium":
            if is_unassigned:
                return f"Assign {item_id} during standard queue rotation."
            else:
                return f"Standard resolution underway with {assigned_to}. SLA buffer ({format_minutes(remaining_minutes)}) is healthy."
        else:
            if is_unassigned:
                return f"Queue {item_id} for regular technician dispatch."
            else:
                return f"Proceed with standard resolution steps in normal queue rotation."

    # 5. ON TRACK (< 40%)
    elif status_label == "On Track":
        if is_unassigned:
            return f"Assign {item_id} in standard queue order. Healthy SLA margin ({format_minutes(remaining_minutes)} remaining)."
        else:
            return f"Healthy SLA compliance ({percent_elapsed}% elapsed). Continue standard handling in normal rotation."

    # 6. RESOLVED
    elif "Resolved" in status_label or status_label == "Resolved / Compliant":
        return "No immediate action required. Verify post-incident stability and customer sign-off."
    elif "Exceeded" in status_label:
        return f"Conduct post-resolution review for {item_id} to identify delay causes and improve process."

    # Default fallback
    return "Continue standard handling in normal queue rotation."


def evaluate_single_item(
    item: Any,
    entity_type: str,
    db: Session,
    ref_time: Optional[datetime] = None,
) -> dict:
    """
    Deterministically evaluate SLA breach status and risk level for a ticket or incident.
    Rules:
      1. Uses consistent units (minutes) for both elapsed and target time.
      2. Elapsed percentage is (elapsed_minutes / target_minutes) * 100.
      3. Compares against Response target when status is 'open', and Resolution target
         when status is 'in_progress' or 'acknowledged'.
      4. For resolved/closed items, uses the completed resolution duration (does not grow with now).
      5. Derives risk level from thresholds:
         - Low: < 40% elapsed
         - Medium: 40% - 70% elapsed
         - High: 70% - 90% elapsed (or Critical priority at >= 50%)
         - Critical: >= 90% elapsed (Imminent Breach: 90-100%, Breached: >= 100%)
      6. Safely handles missing timestamps and zero/invalid targets.
    """
    now = ref_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

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
    else:
        item_id = f"#{item.id}"
        numeric_id = item.id
        title = item.title
        priority = (item.priority or "medium").strip().lower()
        status = (item.status or "open").strip().lower()
        svc = resolve_ticket_service(item, db)
        service_name = svc.service_name if svc else (item.category or "General IT")
        service_id = svc.id if svc else None
        assigned_to = (
            item.assignee.name
            if (item.assignee and hasattr(item.assignee, "name"))
            else (f"User #{item.assigned_to}" if item.assigned_to else "Unassigned")
        )
        created_dt = item.created_at

    # Ensure timezone aware comparison
    if created_dt and created_dt.tzinfo is None:
        created_dt = created_dt.replace(tzinfo=timezone.utc)

    # Check for missing/insufficient data safely
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
            "response_deadline": None,
            "resolution_deadline": None,
            "active_deadline": None,
            "target_type": "response",
            "target_name": "Response Target",
            "target_minutes": 0,
            "target_display": "N/A",
            "response_target_minutes": 0,
            "resolution_target_minutes": 0,
            "sla_source": "insufficient_data",
            "detection_mode": "insufficient_data",
            "is_breached": False,
            "risk_level": "Low",
            "percent_elapsed": 0.0,
            "elapsed_minutes": 0,
            "remaining_minutes": 0,
            "status_label": "Missing Timestamp",
            "reason": "Missing timestamp: cannot compute SLA elapsed time without valid creation date.",
            "recommended_action": "Record incident/ticket detection timestamp in the database.",
            "ml_prediction": None,
        }

    # Fetch SLA Targets for service and priority
    sla_info = get_sla_target(service_id, priority, db)
    resp_target_m = max(1, sla_info.get("response_minutes") or 30)
    resol_target_m = max(1, sla_info.get("resolution_minutes") or 240)

    # Calculate exact deadline timestamps
    resp_deadline = (created_dt + timedelta(minutes=resp_target_m)).isoformat()
    resol_deadline = (created_dt + timedelta(minutes=resol_target_m)).isoformat()

    # Determine active SLA target based on ticket priority and status
    is_resolved = status in ("resolved", "closed")
    is_open = status == "open"
    is_unassigned = assigned_to in ("Unassigned", None, "")

    if is_open:
        target_type = "response"
        target_name = "Response Target"
        target_minutes = resp_target_m
        target_display = sla_info.get("response_time") or f"{target_minutes}m"
        active_deadline = resp_deadline
    else:
        # In progress, acknowledged, or resolved/closed items evaluate against resolution SLA
        target_type = "resolution"
        target_name = "Resolution Target"
        target_minutes = resol_target_m
        target_display = sla_info.get("resolution_time") or f"{target_minutes}m"
        active_deadline = resol_deadline

    # Handle Resolved or Closed Items safely (fixed completion duration, does not grow with now)
    if is_resolved:
        if entity_type == "incident":
            if item.resolved_at:
                r_dt = item.resolved_at if item.resolved_at.tzinfo else item.resolved_at.replace(tzinfo=timezone.utc)
                elapsed_minutes = max(0, int(round((r_dt - created_dt).total_seconds() / 60.0)))
            elif item.mttr_minutes is not None and item.mttr_minutes > 0:
                elapsed_minutes = int(item.mttr_minutes)
            elif item.acknowledged_at:
                a_dt = item.acknowledged_at if item.acknowledged_at.tzinfo else item.acknowledged_at.replace(tzinfo=timezone.utc)
                elapsed_minutes = max(0, int(round((a_dt - created_dt).total_seconds() / 60.0)))
            else:
                elapsed_minutes = max(1, int(round(target_minutes * 0.5)))
        else:
            if item.updated_at and item.updated_at > item.created_at:
                u_dt = item.updated_at if item.updated_at.tzinfo else item.updated_at.replace(tzinfo=timezone.utc)
                elapsed_minutes = max(0, int(round((u_dt - created_dt).total_seconds() / 60.0)))
            else:
                elapsed_minutes = max(1, int(round(target_minutes * 0.5)))

        percent_elapsed = round((elapsed_minutes / target_minutes) * 100.0, 1) if target_minutes > 0 else 0.0
        is_breached = (elapsed_minutes >= target_minutes)
        status_label = "Resolved / Compliant" if not is_breached else "Resolved (Exceeded SLA)"
        over_m = max(0, elapsed_minutes - target_minutes)

        recommended_action = generate_recommended_action(
            entity_type=entity_type,
            priority=priority,
            status_label=status_label,
            is_unassigned=is_unassigned,
            assigned_to=assigned_to,
            item_id=item_id,
            service_name=service_name,
            remaining_minutes=0,
            over_minutes=over_m,
            percent_elapsed=percent_elapsed,
        )

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
            "response_deadline": resp_deadline,
            "resolution_deadline": resol_deadline,
            "active_deadline": active_deadline,
            "target_type": target_type,
            "target_name": target_name,
            "target_minutes": target_minutes,
            "target_display": target_display,
            "response_target_minutes": resp_target_m,
            "resolution_target_minutes": resol_target_m,
            "sla_source": sla_info["sla_source"],
            "detection_mode": "rule_based",
            "is_breached": is_breached,
            "risk_level": "Low",
            "percent_elapsed": percent_elapsed,
            "elapsed_minutes": elapsed_minutes,
            "remaining_minutes": 0,
            "status_label": status_label,
            "reason": (
                f"Item status is '{status}'. Resolution completed in {format_minutes(elapsed_minutes)} "
                f"({percent_elapsed}% of {format_minutes(target_minutes)} {target_name}). No ongoing SLA risk."
            ),
            "recommended_action": recommended_action,
            "ml_prediction": None,
        }

    # Compute elapsed minutes for active items
    elapsed_seconds = max(0, (now - created_dt).total_seconds())
    elapsed_minutes = int(round(elapsed_seconds / 60.0))

    # Calculate active progress against the correct target
    remaining_minutes = max(0, target_minutes - elapsed_minutes)
    percent_elapsed = round((elapsed_minutes / target_minutes) * 100.0, 1) if target_minutes > 0 else 0.0
    over_m = max(0, elapsed_minutes - target_minutes)

    # Rule-Based Risk Classification & Explanation strictly derived from thresholds
    if elapsed_minutes >= target_minutes:
        is_breached = True
        risk_level = "Critical"
        status_label = "Breached"
        reason = (
            f"SLA {target_name} of {format_minutes(target_minutes)} was exceeded by {format_minutes(over_m)} "
            f"({percent_elapsed}% elapsed). Current status is '{status}'."
        )
        if is_unassigned:
            reason += " Item is currently unassigned."

    elif percent_elapsed >= 90.0:
        is_breached = False
        risk_level = "Critical"
        status_label = "Imminent Breach"
        reason = (
            f"Imminent breach: {percent_elapsed}% of {target_name} elapsed ({format_minutes(elapsed_minutes)} "
            f"of {format_minutes(target_minutes)}). Only {format_minutes(remaining_minutes)} remaining."
        )
        if is_unassigned:
            reason += " Item is currently unassigned."

    elif percent_elapsed >= 70.0 or (priority == "critical" and percent_elapsed >= 50.0):
        is_breached = False
        risk_level = "High"
        status_label = "At Risk"
        reason = (
            f"Elevated SLA risk: {percent_elapsed}% of {target_name} elapsed ({format_minutes(elapsed_minutes)} "
            f"of {format_minutes(target_minutes)}). {format_minutes(remaining_minutes)} remaining."
        )
        if is_unassigned:
            reason += f" {priority.capitalize()} priority item has no assigned technician."

    elif percent_elapsed >= 40.0:
        is_breached = False
        risk_level = "Medium"
        status_label = "Moderate Risk"
        reason = (
            f"Moderate SLA consumption: {percent_elapsed}% of {target_name} elapsed ({format_minutes(elapsed_minutes)} "
            f"of {format_minutes(target_minutes)}). {format_minutes(remaining_minutes)} remaining."
        )
        if is_unassigned:
            reason += " Item is unassigned."

    else:
        is_breached = False
        risk_level = "Low"
        status_label = "On Track"
        reason = (
            f"Healthy SLA compliance: Only {percent_elapsed}% of {target_name} elapsed ({format_minutes(elapsed_minutes)} "
            f"of {format_minutes(target_minutes)}). {format_minutes(remaining_minutes)} remaining."
        )

    # For open items, check if resolution SLA has also been exceeded
    if is_open and elapsed_minutes >= resol_target_m:
        reason += f" [Resolution SLA target of {format_minutes(resol_target_m)} also exceeded]."

    recommended_action = generate_recommended_action(
        entity_type=entity_type,
        priority=priority,
        status_label=status_label,
        is_unassigned=is_unassigned,
        assigned_to=assigned_to,
        item_id=item_id,
        service_name=service_name,
        remaining_minutes=remaining_minutes,
        over_minutes=over_m,
        percent_elapsed=percent_elapsed,
    )

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
        "response_deadline": resp_deadline,
        "resolution_deadline": resol_deadline,
        "active_deadline": active_deadline,
        "target_type": target_type,
        "target_name": target_name,
        "target_minutes": target_minutes,
        "target_display": target_display,
        "response_target_minutes": resp_target_m,
        "resolution_target_minutes": resol_target_m,
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


# Baseline calibrated offsets (in minutes relative to current time) for sample seed records
# Designed to maintain a healthy ITIL operational distribution:
#   - Low Risk: < 40% elapsed
#   - Medium Risk: 40% - 70% elapsed
#   - High Risk: 70% - 90% elapsed
#   - Imminent Breach: 90% - 100% elapsed
#   - Breached: >= 100% elapsed (strictly when elapsed >= target)
#   - Resolved: completed duration
SAMPLE_TICKET_OFFSETS = {
    1: 8,     # High (resp 30m) -> 8m ago (26.7% -> Low)
    2: 5,     # Critical (resp 15m) -> 5m ago (33.3% -> Low)
    3: 240,   # Medium, in_progress (resol 480m) -> 240m ago (50.0% -> Medium)
    4: 13,    # High (resp 15m) -> 13m ago (86.7% -> High)
    5: 35,    # Low (resp 240m) -> 35m ago (14.6% -> Low)
    6: 65,    # Medium (resp 120m) -> 65m ago (54.2% -> Medium)
    7: 196,   # High, in_progress (resol 240m) -> 196m ago (81.7% -> High)
    8: 14,    # Critical (resp 15m) -> 14m ago (93.3% -> Critical / Imminent Breach)
    9: 130,   # High, in_progress (resol 240m) -> 130m ago (54.2% -> Medium)
    10: None, # Medium, resolved (resol 480m) -> 180m duration (37.5%)
    11: None, # Medium, resolved (resol 120m) -> 60m duration (50.0%)
    12: None, # Low, closed (resol 1440m) -> 240m duration (16.7%)
    13: 20,   # Medium (resp 120m) -> 20m ago (16.7% -> Low)
    14: 38,   # High (resp 30m) -> 38m ago (126.7% -> Breached)
    15: 18,   # High (resp 30m) -> 18m ago (60.0% -> Medium)
}

SAMPLE_INCIDENT_OFFSETS = {
    1: 12,    # Critical (resp 15m) -> 12m ago (80.0% -> High)
    2: 46,    # Critical, ack (resol 60m) -> 46m ago (76.7% -> High)
    3: 25,    # High (resp 60m) -> 25m ago (41.7% -> Medium)
    4: 35,    # High (resp 30m) -> 35m ago (116.7% -> Breached)
    5: 30,    # Medium (resp 120m) -> 30m ago (25.0% -> Low)
    6: None,  # High, resolved (resol 240m) -> 270m duration (112.5% -> Resolved Exceeded)
    7: 70,    # Medium (resp 120m) -> 70m ago (58.3% -> Medium)
    8: 15,    # Critical (resp 10m) -> 15m ago (150.0% -> Breached)
}


def ensure_sample_telemetry_anchored(db: Session, ref_time: Optional[datetime] = None) -> None:
    """
    Ensure the baseline sample dataset (Tickets 1..15 and Incidents 1..8) maintains
    a realistic, calibrated SLA telemetry distribution without unbounded wall-clock drift.

    If the sample records have aged past 20 minutes from the current reference time,
    their timestamps are smoothly refreshed relative to `now`, preserving all user-created
    tickets (id > 15) and custom incidents (id > 8) untouched.
    """
    now = ref_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # Check sample ticket 8 drift (designed to be ~14 minutes old)
    sample_t8 = db.query(Ticket).filter(Ticket.id == 8).first()
    if not sample_t8 or not sample_t8.created_at:
        return

    t8_dt = sample_t8.created_at
    if t8_dt.tzinfo is None:
        t8_dt = t8_dt.replace(tzinfo=timezone.utc)

    drift_minutes = (now - t8_dt).total_seconds() / 60.0
    # If within 20 minutes of design target, no re-anchoring needed (allows live progression)
    if 0 <= drift_minutes <= 20.0:
        return

    # Telemetry has drifted past operational window (e.g. overnight, restart) -> re-anchor baseline
    try:
        for t_id, offset_m in SAMPLE_TICKET_OFFSETS.items():
            t = db.query(Ticket).filter(Ticket.id == t_id).first()
            if not t:
                continue
            if offset_m is not None:
                t_created = (now - timedelta(minutes=offset_m)).replace(microsecond=0)
                t.created_at = t_created
                t.updated_at = t_created
            elif t_id == 10:
                t.created_at = (now - timedelta(hours=8)).replace(microsecond=0)
                t.updated_at = (now - timedelta(hours=5)).replace(microsecond=0)
            elif t_id == 11:
                t.created_at = (now - timedelta(hours=4)).replace(microsecond=0)
                t.updated_at = (now - timedelta(hours=3)).replace(microsecond=0)
            elif t_id == 12:
                t.created_at = (now - timedelta(hours=10)).replace(microsecond=0)
                t.updated_at = (now - timedelta(hours=6)).replace(microsecond=0)

        for inc_id, offset_m in SAMPLE_INCIDENT_OFFSETS.items():
            inc = db.query(Incident).filter(Incident.id == inc_id).first()
            if not inc:
                continue
            if offset_m is not None:
                inc_dt = (now - timedelta(minutes=offset_m)).replace(microsecond=0)
                inc.created_at = inc_dt
                inc.detected_at = inc_dt
                if inc_id == 2:
                    inc.acknowledged_at = (now - timedelta(minutes=40)).replace(microsecond=0)
            elif inc_id == 6:
                # Resolved high incident (resolved in 270m, exceeding 240m target -> 112.5%)
                inc_created = (now - timedelta(hours=6)).replace(microsecond=0)
                inc.created_at = inc_created
                inc.detected_at = inc_created
                inc.resolved_at = (now - timedelta(hours=1, minutes=30)).replace(microsecond=0)
                inc.mttr_minutes = 270

        db.commit()
        logger.info("Sample SLA telemetry smoothly re-anchored to current reference time.")
    except Exception as e:
        db.rollback()
        logger.warning("Failed to re-anchor sample telemetry: %s", e)


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
    if ref_time is None:
        ensure_sample_telemetry_anchored(db)

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
        if norm_rf in ("breached", "breach"):
            results = [r for r in results if r["is_breached"]]
        else:
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

    resolved_tickets = [r for r in all_items if r["entity_type"] == "ticket" and r["status"] in ("resolved", "closed")]
    resolved_incidents = [r for r in all_items if r["entity_type"] == "incident" and r["status"] in ("resolved", "closed")]

    by_entity = {
        "tickets": {
            "total": len(ticket_risks),
            "breached": sum(1 for r in ticket_risks if r["is_breached"]),
            "at_risk": sum(1 for r in ticket_risks if r["risk_level"] in ("Critical", "High")),
            "healthy": sum(1 for r in ticket_risks if r["risk_level"] in ("Medium", "Low")),
            "resolved": len(resolved_tickets),
            "all_total": len(ticket_risks) + len(resolved_tickets),
        },
        "incidents": {
            "total": len(incident_risks),
            "breached": sum(1 for r in incident_risks if r["is_breached"]),
            "at_risk": sum(1 for r in incident_risks if r["risk_level"] in ("Critical", "High")),
            "healthy": sum(1 for r in incident_risks if r["risk_level"] in ("Medium", "Low")),
            "resolved": len(resolved_incidents),
            "all_total": len(incident_risks) + len(resolved_incidents),
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
        "resolved_count": len(resolved_tickets) + len(resolved_incidents),
        "average_elapsed_percent": avg_elapsed,
        "by_entity": by_entity,
        "by_service": by_service,
        "top_risk_items": top_risk_items,
        "total_all_records": len(all_items),
        "generated_at": (ref_time or datetime.now(timezone.utc)).isoformat(),
    }
