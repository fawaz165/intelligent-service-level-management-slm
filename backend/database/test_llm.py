"""Quick test: hit Ollama directly and show what the LLM returns."""
import httpx, json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.config import settings
from pathlib import Path

prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.txt"
system_prompt = prompt_path.read_text(encoding="utf-8")

schema = {
    "type": "object",
    "properties": {
        "operation": {"type": "string", "enum": ["CREATE","READ","UPDATE","DELETE","SEARCH","FILE_LIST","FILE_SEARCH","FILE_DELETE","GENERAL","UNKNOWN"]},
        "entity": {"type": "string"},
        "parameters": {"type": "object", "additionalProperties": True},
        "filters": {"type": "object", "additionalProperties": True},
        "record_id": {"type": "integer"},
        "requires_confirmation": {"type": "boolean"},
        "message": {"type": "string"},
    },
    "required": ["operation", "entity", "message"],
}

test_queries = [
    "show all open tickets",
    "create a high-priority database ticket",
    "list uploaded files",
    "Show SLA records",
    "show users",
]

for q in test_queries:
    print(f"\n{'='*60}")
    print(f"QUERY: {q}")
    print(f"{'='*60}")
    
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": q},
        ],
        "stream": False,
        "format": schema,
        "options": {"num_ctx": 2048, "num_predict": 512, "temperature": 0.3},
        "keep_alive": "10m",
    }
    
    resp = httpx.post(f"{settings.OLLAMA_URL}/api/chat", json=payload, timeout=120.0)
    data = resp.json()
    raw = data.get("message", {}).get("content", "")
    print(f"RAW OUTPUT: {raw[:500]}")
    
    try:
        parsed = json.loads(raw)
        print(f"OPERATION: {parsed.get('operation')}")
        print(f"ENTITY: {parsed.get('entity')}")
        print(f"MESSAGE: {parsed.get('message')}")
        print(f"FILTERS: {parsed.get('filters')}")
    except:
        print("FAILED TO PARSE JSON")
