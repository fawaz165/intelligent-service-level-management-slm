"""
LLM Service — communicates with Ollama / DeepSeek-R1:1.5B.

Responsibilities:
  1. Load the system prompt
  2. Try deterministic keyword-based parsing FIRST (fast + reliable)
  3. Fall back to Ollama LLM for ambiguous queries
  4. Parse and validate the structured JSON intent
  5. Strip <think> reasoning blocks from the model output
  6. Provide health-check for Ollama connectivity
"""

import json
import re
import logging
from pathlib import Path
from typing import Optional, AsyncGenerator

import httpx

from backend.config import settings
from backend.database.schemas import LLMIntent

logger = logging.getLogger(__name__)

# ── Reusable HTTP client (avoids TCP reconnection overhead per request) ──
_http_client = httpx.AsyncClient(timeout=120.0)

# ── Load system prompt ───────────────────────────────────────────────────
_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.txt"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

# ── JSON schema for structured output (Ollama format parameter) ──────────
_INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "enum": [
                "CREATE", "READ", "UPDATE", "DELETE", "SEARCH",
                "FILE_LIST", "FILE_SEARCH", "FILE_DELETE",
                "GENERAL", "UNKNOWN",
            ],
        },
        "entity": {
            "type": "string",
            "enum": [
                "ticket", "incident", "service", "user", "sla", "file",
            ],
        },
        "parameters": {
            "type": "object",
            "additionalProperties": True,
        },
        "filters": {
            "type": "object",
            "additionalProperties": True,
        },
        "record_id": {"type": "integer"},
        "requires_confirmation": {"type": "boolean"},
        "message": {"type": "string"},
    },
    "required": ["operation", "entity", "message"],
}

# ── Ollama inference options for speed ───────────────────────────────────
_OLLAMA_OPTIONS = {
    "num_ctx": 2048,        # smaller context window = faster
    "num_predict": 512,     # cap max generated tokens
    "temperature": 0.3,     # more deterministic = less wandering
}


# ═════════════════════════════════════════════════════════════════════════
# DETERMINISTIC PRE-LLM INTENT PARSER
# Handles common patterns without calling the LLM — fast and reliable.
# ═════════════════════════════════════════════════════════════════════════

# Ticket categories the system recognizes
_CATEGORY_MAP = {
    "network": "Network",
    "networking": "Network",
    "database": "Database",
    "db": "Database",
    "server": "Server",
    "servers": "Server",
    "application": "Application",
    "app": "Application",
    "software": "Application",
    "security": "Security",
    "hardware": "Hardware",
}

_PRIORITIES = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "critical": "critical",
    "urgent": "critical",
    "p1": "critical",
    "p2": "high",
    "p3": "medium",
    "p4": "low",
}

_STATUSES = {
    "open": "open",
    "in_progress": "in_progress",
    "in progress": "in_progress",
    "in-progress": "in_progress",
    "acknowledged": "acknowledged",
    "pending": "in_progress",
    "resolved": "resolved",
    "closed": "closed",
}

# Words that signal "show me data" (READ intent)
_READ_KEYWORDS = {"show", "list", "get", "view", "display", "fetch", "see", "find", "search", "all", "records", "count", "total", "how"}

# Words that signal tickets vs incidents
_TICKET_SYNONYMS = {"ticket", "tickets", "issue", "issues", "case", "cases", "request", "requests"}
_INCIDENT_SYNONYMS = {"incident", "incidents"}

# Words that signal an entity
_ENTITY_KEYWORDS = {
    "incident": "incident", "incidents": "incident",
    "ticket": "ticket", "tickets": "ticket",
    "issue": "ticket", "issues": "ticket",
    "case": "ticket", "cases": "ticket",
    "request": "ticket", "requests": "ticket",
    "service": "service", "services": "service",
    "user": "user", "users": "user",
    "sla": "sla", "slas": "sla",
    "file": "file", "files": "file",
}


def _try_deterministic_parse(user_message: str) -> Optional[LLMIntent]:
    """
    Attempt to deterministically parse user intent from keyword patterns.

    Returns an LLMIntent if a confident match is found, None otherwise.
    This runs BEFORE the LLM and handles the most common query patterns.
    """
    msg_lower = user_message.lower().strip()
    words = set(re.findall(r'[a-z_]+', msg_lower))

    # ── Detect intent type ───────────────────────────────────────────
    is_read = bool(words & _READ_KEYWORDS) or any(p in msg_lower for p in ["how many", "what are", "count of", "number of"])
    is_create = any(kw in msg_lower for kw in ["create", "add", "new", "make", "open a", "raise"])
    is_delete = any(kw in msg_lower for kw in ["delete", "remove", "drop"])
    is_update = any(kw in msg_lower for kw in ["update", "change", "modify", "edit", "set", "assign", "close", "resolve"])

    # ── Detect entity (strictly differentiate incident vs ticket vs sla_risk) ──
    entity = None
    is_sla_risk = (
        bool(words & {"risk", "risks", "breach", "breaches", "breaching"})
        or any(p in msg_lower for p in ["at risk", "at-risk", "sla monitoring", "sla prediction", "predict breach", "predict sla", "sla status"])
    )
    if is_sla_risk:
        entity = "sla_risk"
        is_read = True
    elif words & _INCIDENT_SYNONYMS:
        entity = "incident"
    elif words & {"ticket", "tickets"}:
        entity = "ticket"
    elif "sla" in msg_lower:
        entity = "sla"
    else:
        for kw, ent in _ENTITY_KEYWORDS.items():
            if kw in words:
                entity = ent
                break

    # ── Extract category / service ───────────────────────────────────
    detected_category = None
    for cat_kw, cat_val in _CATEGORY_MAP.items():
        if cat_kw in words:
            detected_category = cat_val
            break

    # Also detect explicit category patterns like:
    # "for an invalid category", "category: XYZ", "tickets for [category]"
    cat_match = re.search(r'(?:for|in|under|with)\s+(?:an?\s+)?([a-zA-Z0-9_-]+)\s+categor(?:y|ies)', msg_lower)
    if not cat_match:
        cat_match = re.search(r'categor(?:y|ies)\s*[:=]?\s*([a-zA-Z0-9_-]+)', msg_lower)
    if not cat_match:
        cat_match = re.search(r'tickets?\s+(?:for|in|under)\s+(?:an?\s+)?([a-zA-Z0-9_-]+)', msg_lower)

    if cat_match:
        cand = cat_match.group(1).lower()
        if cand in _CATEGORY_MAP:
            detected_category = _CATEGORY_MAP[cand]
        elif cand not in ("all", "open", "closed", "resolved", "new", "high", "low", "medium", "critical"):
            detected_category = cat_match.group(1).capitalize()
        if not entity:
            entity = "ticket"

    # Check for "invalid category" phrase specifically
    if "invalid" in words and ("category" in words or "categories" in words):
        detected_category = "Invalid"
        if not entity:
            entity = "ticket"
        is_read = True

    # If we detect a category name but no explicit entity keyword,
    # infer entity=ticket (e.g., "show open network tickets" → ticket)
    if detected_category and not entity:
        entity = "ticket"

    # ── Extract priority / severity ──────────────────────────────────
    detected_priority = None
    for prio_kw, prio_val in _PRIORITIES.items():
        if prio_kw in words:
            detected_priority = prio_val
            break
    if not detected_priority:
        prio_match = re.search(r'(?:with|where|having|for)?\s*(?:priority|severity)(?:\s+(?:is|equals|of)|[:=])?\s+([a-zA-Z0-9_-]+)', msg_lower)
        if prio_match:
            cand_prio = prio_match.group(1).lower()
            if cand_prio in _PRIORITIES:
                detected_priority = _PRIORITIES[cand_prio]
            elif cand_prio not in ("all", "open", "closed", "ticket", "tickets", "incident", "incidents"):
                detected_priority = cand_prio

    # ── Extract status ───────────────────────────────────────────────
    detected_status = None
    for status_kw, status_val in _STATUSES.items():
        if status_kw in msg_lower:
            detected_status = status_val
            break
    if not detected_status:
        stat_match = re.search(r'(?:with|in|where|having|for)?\s*status(?:\s+(?:is|equals|of)|[:=])?\s+([a-zA-Z0-9_-]+)', msg_lower)
        if stat_match:
            cand_stat = stat_match.group(1).lower()
            if cand_stat in _STATUSES:
                detected_status = _STATUSES[cand_stat]
            elif cand_stat not in ("all", "ticket", "tickets", "incident", "incidents", "service", "services"):
                detected_status = cand_stat

    # ── Extract record ID (e.g., "ticket #5", "incident #2") ─────────
    record_id = None
    id_match = re.search(r'#?\b(\d+)\b', msg_lower)
    if id_match and (is_delete or is_update):
        record_id = int(id_match.group(1))

    # ── BUILD THE INTENT ─────────────────────────────────────────────

    # READ operations (most common)
    if is_read and entity:
        filters = {}
        if detected_status:
            filters["status"] = detected_status

        if entity == "incident":
            if detected_category:
                filters["service"] = detected_category
            elif "network" in words:
                filters["service"] = "Network"
            elif "database" in words:
                filters["service"] = "Database"
            elif "api" in words or "gateway" in words:
                filters["service"] = "API-Gateway"
            elif "cache" in words:
                filters["service"] = "Cache-Layer"
            elif "security" in words:
                filters["service"] = "Security-Gateway"

            if detected_priority:
                filters["severity"] = detected_priority

        elif entity == "ticket":
            if detected_category:
                filters["category"] = detected_category
            if detected_priority:
                filters["priority"] = detected_priority

        elif entity == "sla":
            if detected_priority:
                filters["priority"] = detected_priority
            for svc_kw in ["database", "api-gateway", "cache", "network", "email", "security", "backup", "monitoring"]:
                if svc_kw in msg_lower:
                    filters["service"] = svc_kw
                    break

        elif entity == "sla_risk":
            if words & _TICKET_SYNONYMS:
                filters["entity"] = "ticket"
            elif words & _INCIDENT_SYNONYMS:
                filters["entity"] = "incident"
            if "breach" in words or "breaches" in words or "breached" in words:
                filters["breached_only"] = True
            if detected_priority:
                filters["risk_level"] = detected_priority
            if detected_category:
                filters["service"] = detected_category
            if any(w in words for w in ["predict", "prediction", "ai"]):
                filters["with_ai"] = True

        elif entity == "file":
            uploader_match = re.search(r'uploaded\s+by\s+([a-zA-Z0-9_-]+)', msg_lower)
            if uploader_match:
                filters["uploader"] = uploader_match.group(1).capitalize()

        # Build descriptive message
        parts = []
        if detected_status:
            parts.append(detected_status)
        if detected_priority:
            prio_label = "severity" if entity == "incident" else "priority"
            parts.append(f"{detected_priority}-{prio_label}")
        if entity == "incident" and filters.get("service"):
            parts.append(filters["service"])
        elif entity == "ticket" and detected_category:
            parts.append(detected_category)
        desc = " ".join(parts)

        entity_display = {
            "ticket": "tickets",
            "incident": "incidents",
            "service": "services",
            "user": "users",
            "sla": "SLA records",
            "sla_risk": "SLA risk evaluations",
            "file": "files",
        }.get(entity, entity)
        msg = f"Retrieving {desc + ' ' if desc else ''}{entity_display}."

        return LLMIntent(
            operation="READ",
            entity=entity,
            filters=filters if filters else None,
            message=msg,
        )

    # ── Extract explicit title for CREATE ────────────────────────────
    extracted_title = None
    title_match = re.search(r'(?:called|named|titled|with title)\s+["\']?([^"\']+)["\']?', user_message, re.IGNORECASE)
    if title_match:
        extracted_title = title_match.group(1).strip()
    else:
        quote_match = re.search(r'["\']([^"\']{3,})["\']', user_message)
        if quote_match:
            extracted_title = quote_match.group(1).strip()

    # CREATE operations
    if is_create and entity == "incident":
        params = {}
        if extracted_title:
            params["title"] = extracted_title
        if detected_category:
            params["affected_service"] = detected_category
        if detected_priority:
            params["severity"] = detected_priority
        return LLMIntent(
            operation="CREATE",
            entity="incident",
            parameters=params if params else None,
            message=f"Creating a {detected_priority or 'new'} {detected_category or ''} incident.".replace("  ", " "),
        )

    if is_create and entity == "ticket":
        params = {}
        if extracted_title:
            params["title"] = extracted_title
        if detected_category:
            params["category"] = detected_category
        if detected_priority:
            params["priority"] = detected_priority

        return LLMIntent(
            operation="CREATE",
            entity="ticket",
            parameters=params if params else None,
            message=f"Creating a {detected_priority or 'new'} {detected_category or ''} ticket.".replace("  ", " "),
        )

    if is_create and entity == "service":
        if extracted_title:
            return LLMIntent(
                operation="CREATE",
                entity="service",
                parameters={"service_name": extracted_title},
                message=f"Creating service '{extracted_title}'.",
            )
        return None

    # DELETE operations
    if is_delete and entity and record_id:
        return LLMIntent(
            operation="DELETE",
            entity=entity,
            record_id=record_id,
            requires_confirmation=True,
            message=f"Deleting {entity} #{record_id}.",
        )

    # UPDATE operations
    if is_update and entity and record_id:
        params = {}
        if detected_status:
            params["status"] = detected_status
        if detected_priority:
            params["priority"] = detected_priority
        return LLMIntent(
            operation="UPDATE",
            entity=entity,
            record_id=record_id,
            parameters=params if params else None,
            message=f"Updating {entity} #{record_id}.",
        )

    # Simple entity query (e.g. "incidents", "SLA records")
    if entity and not is_create and not is_delete and not is_update:
        is_simple_query = len(words) <= 5 or entity in ("sla", "user", "incident")
        if is_simple_query and entity in ("sla", "user", "file", "service", "incident"):
            entity_display = {
                "sla": "SLA records",
                "user": "users",
                "file": "files",
                "service": "services",
                "incident": "incidents",
            }.get(entity, entity)
            return LLMIntent(
                operation="READ",
                entity=entity,
                message=f"Retrieving {entity_display}.",
            )

    return None


# ═════════════════════════════════════════════════════════════════════════
# TEXT PROCESSING HELPERS
# ═════════════════════════════════════════════════════════════════════════

def _strip_think_blocks(text: str) -> str:
    """Remove <think>...</think> reasoning blocks from DeepSeek-R1 output."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _extract_json(text: str) -> Optional[dict]:
    """Try to parse JSON from text, handling markdown fences and extra whitespace."""
    text = _strip_think_blocks(text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _post_validate_llm_intent(intent: LLMIntent, user_message: str) -> LLMIntent:
    """
    Post-process an LLM-generated intent to catch common misclassifications.
    """
    msg_lower = user_message.lower().strip()
    words = set(re.findall(r'[a-z_]+', msg_lower))

    is_read = bool(words & _READ_KEYWORDS)

    # Fix #1: LLM said CREATE/UPDATE but user clearly asked to READ/SHOW
    if intent.operation in ("CREATE", "UPDATE") and is_read and not any(
        kw in msg_lower for kw in ["create", "add", "new", "make", "update", "change"]
    ):
        logger.warning(
            "Post-validate override: LLM said %s but user asked to read. Overriding to READ.",
            intent.operation,
        )
        deterministic = _try_deterministic_parse(user_message)
        if deterministic:
            return deterministic
        intent.operation = "READ"
        return intent

    # Fix #2: LLM returned GENERAL/UNKNOWN but we can detect the entity
    if intent.operation in ("GENERAL", "UNKNOWN"):
        deterministic = _try_deterministic_parse(user_message)
        if deterministic:
            return deterministic

    # Fix #3: Incident vs Ticket strict differentiation
    if "incident" in words or "incidents" in words:
        if intent.entity != "incident":
            intent.entity = "incident"
    elif "ticket" in words or "tickets" in words:
        if intent.entity != "ticket":
            intent.entity = "ticket"

    return intent


# ═════════════════════════════════════════════════════════════════════════
# MAIN INTENT EXTRACTION
# ═════════════════════════════════════════════════════════════════════════

async def get_intent(user_message: str) -> LLMIntent:
    """
    Extract structured intent from a user message.

    Pipeline:
      1. Try deterministic keyword parsing (instant, reliable)
      2. Fall back to LLM if no confident keyword match
      3. Post-validate LLM output to catch misclassifications
    """
    # Step 1: Try deterministic parse first (fast path)
    deterministic = _try_deterministic_parse(user_message)
    if deterministic:
        logger.info("Deterministic parse succeeded: op=%s entity=%s", deterministic.operation, deterministic.entity)
        return deterministic

    # Step 2: Fall back to LLM
    logger.info("Deterministic parse failed, falling back to LLM for: %s", user_message[:100])

    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "format": _INTENT_SCHEMA,
        "options": _OLLAMA_OPTIONS,
        "keep_alive": "10m",
    }

    try:
        resp = await _http_client.post(
            f"{settings.OLLAMA_URL}/api/chat",
            json=payload,
        )
        resp.raise_for_status()

        data = resp.json()
        raw_content = data.get("message", {}).get("content", "")
        logger.info("Raw LLM response: %s", raw_content[:500])

        parsed = _extract_json(raw_content)
        if parsed is None:
            logger.warning("LLM returned unparseable output, using GENERAL fallback")
            return LLMIntent(
                operation="GENERAL",
                entity="",
                message="I couldn't understand that. Try asking me to show tickets, create a service, or list files.",
            )

        # Validate through Pydantic
        intent = LLMIntent(**parsed)

        # Safety: force confirmation on destructive ops even if model forgot
        if intent.operation in ("DELETE", "FILE_DELETE"):
            intent.requires_confirmation = True

        # Step 3: Post-validate to catch LLM misclassifications
        return _post_validate_llm_intent(intent, user_message)

    except httpx.ConnectError:
        logger.error("Cannot connect to Ollama at %s", settings.OLLAMA_URL)
        return LLMIntent(
            operation="GENERAL",
            entity="",
            message="⚠️ Cannot connect to Ollama. Please make sure Ollama is running on your machine.",
        )
    except httpx.HTTPStatusError as e:
        logger.error("Ollama HTTP error: %s", e)
        return LLMIntent(
            operation="GENERAL",
            entity="",
            message=f"⚠️ Ollama returned an error (HTTP {e.response.status_code}). Make sure the model '{settings.OLLAMA_MODEL}' is installed.",
        )
    except Exception as e:
        logger.error("LLM service error: %s", e, exc_info=True)
        return LLMIntent(
            operation="GENERAL",
            entity="",
            message="⚠️ An error occurred while processing your request. Please try again.",
        )


async def generate_response(user_message: str, context: str) -> str:
    """
    Ask the model to generate a natural-language response given context.
    Used to explain operation results back to the user.
    """
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a helpful IT service management assistant. "
                    "Given the operation result below, provide a brief, friendly summary to the user. "
                    "Keep it concise — 1-3 sentences maximum. Do not use markdown code blocks."
                ),
            },
            {
                "role": "user",
                "content": f"User asked: {user_message}\n\nResult:\n{context}",
            },
        ],
        "stream": False,
        "options": {
            "num_ctx": 2048,
            "num_predict": 256,
            "temperature": 0.3,
        },
        "keep_alive": "10m",
    }

    try:
        resp = await _http_client.post(
            f"{settings.OLLAMA_URL}/api/chat",
            json=payload,
        )
        resp.raise_for_status()

        data = resp.json()
        raw = data.get("message", {}).get("content", "")
        return strip_think_blocks(raw) or "Operation completed."

    except Exception as e:
        logger.warning("Response generation failed: %s", e)
        return "Operation completed successfully."


def strip_think_blocks(text: str) -> str:
    """Remove <think>...</think> reasoning blocks produced by DeepSeek-R1."""
    if not text:
        return ""
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.DOTALL)
    cleaned = re.sub(r"<think>[\s\S]*$", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()


_strip_think_blocks = strip_think_blocks
clean_think_tags = strip_think_blocks


async def call_llm(prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 256) -> str:
    """
    Directly invoke Ollama / DeepSeek-R1:1.5B with a prompt and return stripped text.
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "num_ctx": 2048,
            "num_predict": max_tokens,
            "temperature": 0.3,
        },
        "keep_alive": "10m",
    }
    resp = await _http_client.post(
        f"{settings.OLLAMA_URL}/api/chat",
        json=payload,
    )
    resp.raise_for_status()
    raw = resp.json().get("message", {}).get("content", "")
    return strip_think_blocks(raw)


async def check_ollama() -> dict:
    """Check Ollama connectivity and model availability."""
    result = {"connected": False, "model": settings.OLLAMA_MODEL, "model_available": False}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check Ollama is running
            resp = await client.get(f"{settings.OLLAMA_URL}/api/tags")
            resp.raise_for_status()
            result["connected"] = True

            # Check model is available
            models = resp.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            result["model_available"] = any(
                settings.OLLAMA_MODEL in name for name in model_names
            )
    except Exception:
        pass
    return result
