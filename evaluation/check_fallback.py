"""Exercise the application's fallback with a deliberately unreachable Ollama URL."""
import asyncio
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from backend.config import settings
from backend.database.connection import SessionLocal
from backend.database.models import Incident
from backend.services import sla_service


async def main():
    db = SessionLocal()
    try:
        item = db.query(Incident).filter(Incident.incident_id == "INC-20260902-001").first()
        if item is None:
            raise RuntimeError("Required existing incident fixture was not found")
        card = sla_service.evaluate_single_item(item, "incident", db, ref_time=datetime.now(timezone.utc))
        original = settings.OLLAMA_URL
        settings.OLLAMA_URL = "http://127.0.0.1:1"
        start = time.perf_counter()
        try:
            result = await sla_service.enrich_with_ai_prediction(card, db=db)
        finally:
            elapsed = round(time.perf_counter() - start, 3)
            settings.OLLAMA_URL = original
        prediction = result.get("ml_prediction") or {}
        row = {
            "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            "test": "deliberately_unreachable_ollama_port_1",
            "configured_model": settings.OLLAMA_MODEL,
            "latency_sec": elapsed,
            "status": prediction.get("status", "success"),
            "fallback_triggered": prediction.get("status") == "unavailable",
            "fallback_sections_present": sum(len(str(prediction.get(k) or "").strip()) > 15 for k in (
                "incident_summary", "possible_root_causes", "sla_risk_explanation",
                "recommended_troubleshooting_steps", "supporting_evidence", "uncertainties_or_missing_info")),
            "authoritative_metrics": json.dumps(prediction.get("authoritative_metrics", {}), sort_keys=True),
            "fallback_runbook_id": (prediction.get("domain_runbook_context") or {}).get("runbook_id", ""),
            "error": prediction.get("error", ""),
            "response_json": json.dumps(prediction, ensure_ascii=False),
        }
        out = ROOT / "evaluation" / "runs"
        out.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        csv_path = out / f"fallback_{stamp}.csv"
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            writer.writeheader()
            writer.writerow(row)
        print(json.dumps({"csv": str(csv_path), "result": row}, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
