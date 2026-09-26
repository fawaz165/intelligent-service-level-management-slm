"""
LLM Service — communicates with Ollama / DeepSeek-R1:1.5B.

Responsibilities:
  1. Load the system prompt
  2. Send user messages to Ollama with structured-output constraints
  3. Parse and validate the structured JSON intent
  4. Strip <think> reasoning blocks from the model output
  5. Provide health-check for Ollama connectivity
  6. Stream tokens from Ollama for real-time responses
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
                "ticket", "service", "user", "sla", "file",
                "tickets", "services", "users", "files", "slas", "sla records", "sla_records",
                "Ticket", "Service", "User", "SLA", "File",
                "Tickets", "Services", "Users", "SLAs", "Files",
                "database", "network", "server", "application", "security", "hardware",
                "Database", "Network", "Server", "Application", "Security", "Hardware",
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


def _strip_think_blocks(text: str) -> str:
    """Remove <think>...</think> reasoning blocks from DeepSeek-R1 output."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _extract_json(text: str) -> Optional[dict]:
    """Try to parse JSON from text, handling markdown fences and extra whitespace."""
    text = _strip_think_blocks(text)

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code fences
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding any JSON object in the text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _apply_intent_heuristics(intent: Optional[LLMIntent], user_message: str) -> LLMIntent:
    """Fallback heuristics to recover intent when LLM yields GENERAL/UNKNOWN or fails JSON parsing."""
    if intent and intent.operation not in ("GENERAL", "UNKNOWN") and intent.entity:
        return intent

    msg_lower = user_message.lower().strip()
    is_query = any(kw in msg_lower for kw in ["show", "list", "get", "view", "display", "fetch", "see", "all", "records"])

    if is_query or "sla" in msg_lower:
        if "sla" in msg_lower:
            return LLMIntent(operation="READ", entity="sla", message="Retrieving SLA records.")
        elif "user" in msg_lower:
            return LLMIntent(operation="READ", entity="user", message="Retrieving user list.")
        elif "ticket" in msg_lower:
            return LLMIntent(operation="READ", entity="ticket", message="Retrieving tickets.")
        elif "service" in msg_lower:
            return LLMIntent(operation="READ", entity="service", message="Retrieving services.")
        elif "file" in msg_lower:
            return LLMIntent(operation="READ", entity="file", message="Retrieving files.")

    if intent:
        return intent

    return LLMIntent(
        operation="GENERAL",
        entity="",
        message="I'm here to help with IT service management. What would you like to do?",
    )


async def get_intent(user_message: str) -> LLMIntent:
    """
    Send user_message to DeepSeek-R1:1.5B via Ollama and return a validated LLMIntent.

    Falls back to a GENERAL intent if the model response cannot be parsed.
    """
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "format": _INTENT_SCHEMA,
        "options": _OLLAMA_OPTIONS,
        "keep_alive": "10m",    # keep model loaded in memory
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
            return _apply_intent_heuristics(None, user_message)

        # Validate through Pydantic
        intent = LLMIntent(**parsed)

        # Safety: force confirmation on destructive ops even if model forgot
        if intent.operation in ("DELETE", "FILE_DELETE"):
            intent.requires_confirmation = True

        return _apply_intent_heuristics(intent, user_message)

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


async def get_intent_streaming(user_message: str) -> AsyncGenerator[str, None]:
    """
    Stream tokens from Ollama as they are generated.

    Yields individual content tokens (with <think> blocks filtered out).
    The final yield is the complete parsed intent as a JSON string prefixed with
    the sentinel '___INTENT___:'.
    """
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "stream": True,
        "format": _INTENT_SCHEMA,
        "options": _OLLAMA_OPTIONS,
        "keep_alive": "10m",
    }

    full_content = ""
    in_think_block = False

    try:
        async with _http_client.stream(
            "POST",
            f"{settings.OLLAMA_URL}/api/chat",
            json=payload,
        ) as resp:
            resp.raise_for_status()

            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue

                token = chunk.get("message", {}).get("content", "")
                if not token:
                    if chunk.get("done"):
                        break
                    continue

                full_content += token

                # Filter out <think> blocks in real-time
                if "<think>" in token:
                    in_think_block = True
                    continue
                if "</think>" in token:
                    in_think_block = False
                    continue
                if in_think_block:
                    continue

                # Yield visible token to the client
                yield token

                if chunk.get("done"):
                    break

    except httpx.ConnectError:
        yield "⚠️ Cannot connect to Ollama. Please make sure Ollama is running."
        full_content = ""
    except Exception as e:
        logger.error("Streaming error: %s", e, exc_info=True)
        yield "⚠️ An error occurred while processing your request."
        full_content = ""

    # Parse the accumulated content into an intent
    if full_content:
        parsed = _extract_json(full_content)
        if parsed:
            try:
                intent = LLMIntent(**parsed)
                if intent.operation in ("DELETE", "FILE_DELETE"):
                    intent.requires_confirmation = True
                yield f"___INTENT___:{intent.model_dump_json()}"
            except Exception:
                yield f'___INTENT___:{{"operation":"GENERAL","entity":"","message":"{_strip_think_blocks(full_content)[:200]}"}}'
        else:
            clean = _strip_think_blocks(full_content)
            yield f'___INTENT___:{{"operation":"GENERAL","entity":"","message":"{clean[:200]}"}}'
    else:
        yield '___INTENT___:{"operation":"GENERAL","entity":"","message":"⚠️ Could not get a response. Please try again."}'


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
        return _strip_think_blocks(raw) or "Operation completed."

    except Exception as e:
        logger.warning("Response generation failed: %s", e)
        return "Operation completed successfully."


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
