"""Read-only repeated evaluation of ISLM SLA synthesis through its Ollama service."""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import statistics
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from backend.config import settings
from backend.database.connection import SessionLocal
from backend.database.models import Incident, Ticket
from backend.services import sla_service

CASES = [
    ("INC-20260902-001", "incident", "DBMS-SRE-RUNBOOK-204", ["cpu", "query", "lock", "index"]),
    ("INC-20260902-007", "incident", "NET-SRE-RUNBOOK-101", ["packet", "ping", "wan", "interface"]),
    ("INC-20260902-006", "incident", "APP-SRE-RUNBOOK-405", ["memory", "worker", "heap", "post-incident"]),
    ("INC-20260902-002", "incident", "APP-SRE-RUNBOOK-405", ["gateway", "502", "proxy", "upstream"]),
    ("INC-20260902-003", "incident", "DBMS-SRE-RUNBOOK-204", ["replication", "lag", "binlog", "checkpoint"]),
    ("INC-20260902-004", "incident", "SYS-SRE-RUNBOOK-501", ["disk", "storage", "inodes", "capacity"]),
    ("INC-20260902-005", "incident", "SEC-SRE-RUNBOOK-302", ["tls", "certificate", "chain", "renew"]),
    (1, "ticket", "NET-SRE-RUNBOOK-101", ["router", "connectivity", "interface", "ping"]),
    (2, "ticket", "DBMS-SRE-RUNBOOK-204", ["backup", "catalog", "snapshot", "dump"]),
    (8, "ticket", "NET-SRE-RUNBOOK-101", ["switch", "fan", "thermal", "chassis"]),
    ("INC-20260902-008", "incident", "APP-SRE-RUNBOOK-405", ["load balancer", "health check", "worker", "post-incident"]),
    (4, "ticket", "SEC-SRE-RUNBOOK-302", ["ssl", "certificate", "tls", "renew"]),
]

FIELDS = ["incident_summary", "possible_root_causes", "sla_risk_explanation",
          "recommended_troubleshooting_steps", "supporting_evidence", "uncertainties_or_missing_info"]


class Monitor:
    def __init__(self):
        self.samples = []
        self.stop_event = threading.Event()

    def start(self):
        self.samples = []
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.sample, daemon=True)
        self.thread.start()

    def sample(self):
        psutil.cpu_percent(None)
        while not self.stop_event.is_set():
            self.samples.append((psutil.cpu_percent(None), psutil.virtual_memory().used / 1048576))
            self.stop_event.wait(.2)

    def finish(self, before_mb):
        self.stop_event.set()
        self.thread.join()
        cpus = [x[0] for x in self.samples]
        memories = [x[1] for x in self.samples]
        return {"cpu_avg_pct": mean(cpus), "cpu_peak_pct": max(cpus, default=None),
                "ram_avg_used_mb": mean(memories), "ram_peak_used_mb": max(memories, default=None),
                "ram_delta_peak_mb": round(max(0, max(memories, default=before_mb) - before_mb), 1)}


def mean(values):
    return round(statistics.mean(values), 3) if values else None


def score(card, pred, expected_id, keywords):
    texts = [str(pred.get(k) or "") for k in FIELDS]
    completeness = sum(len(s.strip()) > 15 for s in texts)
    actions = str(pred.get("recommended_troubleshooting_steps") or "").lower()
    context = pred.get("domain_runbook_context") or {}
    hits = sum(k in actions for k in keywords)
    runbook_match = context.get("runbook_id") == expected_id
    metrics = pred.get("authoritative_metrics") or {}
    expected = {k: card.get(k) for k in ("target_minutes", "elapsed_minutes", "percent_elapsed", "remaining_minutes", "is_breached")}
    found = {k: metrics.get(k) for k in expected}
    sla_match = expected == found
    risk = str(pred.get("sla_risk_explanation") or "").lower()
    contradiction = ((card.get("is_breached") and any(x in risk for x in ("sla was met", "within sla"))) or
                     (card.get("status") in ("resolved", "closed") and any(x in risk for x in ("breach imminent", "immediate intervention required"))))
    return completeness, expected, found, sla_match and not contradiction, runbook_match, hits, len(keywords)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repetitions", type=int, default=2, help="Repeat each selected case; default 2")
    ap.add_argument("--case-limit", type=int, default=12, help="Number of fixed read-only cases, default 12")
    args = ap.parse_args()
    cases = CASES[:args.case_limit]
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    out = ROOT / "evaluation" / "runs"
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / f"raw_{stamp}.csv"
    report_path = out / f"report_{stamp}.md"
    db = SessionLocal()
    rows = []
    monitor = Monitor()
    run_start = datetime.now(timezone.utc).isoformat()
    try:
        for case_index, (ident, entity, runbook_id, keywords) in enumerate(cases, 1):
            for rep in range(1, args.repetitions + 1):
                item = (db.query(Incident).filter(Incident.incident_id == ident).first() if entity == "incident"
                        else db.query(Ticket).filter(Ticket.id == ident).first())
                if item is None:
                    rows.append({"case_id": f"C{case_index:02}", "repeat": rep, "entity_id": ident, "status": "missing_fixture"})
                    continue
                ref_time = datetime.now(timezone.utc)
                card = sla_service.evaluate_single_item(item, entity, db, ref_time=ref_time)
                base = psutil.virtual_memory().used / 1048576
                monitor.start()
                start = time.perf_counter()
                enriched = await sla_service.enrich_with_ai_prediction(card, db=db)
                latency = round(time.perf_counter() - start, 3)
                resource = monitor.finish(base)
                pred = enriched.get("ml_prediction") or {}
                completeness, expected, found, sla_ok, rb_match, hits, total = score(card, pred, runbook_id, keywords)
                rows.append({
                    "run_started_utc": run_start, "case_id": f"C{case_index:02}", "repeat": rep,
                    "entity_type": entity, "entity_id": str(ident), "runbook_expected": runbook_id,
                    "runbook_actual": (pred.get("domain_runbook_context") or {}).get("runbook_id", ""),
                    "status": "fallback" if pred.get("status") == "unavailable" else "success",
                    "latency_sec": latency, **resource, "sections_present": completeness,
                    "completeness_pct": round(completeness / 6 * 100, 1),
                    "sla_authoritative_match": sla_ok, "sla_expected_json": json.dumps(expected, sort_keys=True),
                    "sla_reported_json": json.dumps(found, sort_keys=True), "runbook_id_match": rb_match,
                    "runbook_keyword_hits": hits, "runbook_keyword_total": total,
                    "runbook_keyword_coverage_pct": round(hits / total * 100, 1),
                    "action_text_relevance_proxy": round((hits / total + int(rb_match)) / 2 * 100, 1),
                    "error": pred.get("error", ""), "response_json": json.dumps(pred, ensure_ascii=False),
                })
                print(f"{case_index}/{len(cases)} repeat {rep}/{args.repetitions}: {latency}s {rows[-1]['status']}", flush=True)
    finally:
        db.close()
    keys = sorted({k for row in rows for k in row})
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    ok = [r for r in rows if r.get("status") == "success" and r.get("latency_sec") is not None]
    lat = [r["latency_sec"] for r in ok]
    successful = len(ok)
    metrics = {
        "runs": len(rows), "successful_inferences": successful, "fallbacks": sum(r.get("status") == "fallback" for r in rows),
        "latency_mean_sec": mean(lat), "latency_min_sec": min(lat) if lat else None,
        "latency_max_sec": max(lat) if lat else None,
        "completeness_mean_pct": mean([r["completeness_pct"] for r in ok]) if ok else None,
        "sla_match_pct": mean([100 if r["sla_authoritative_match"] else 0 for r in ok]) if ok else None,
        "runbook_proxy_mean_pct": mean([r["action_text_relevance_proxy"] for r in ok]) if ok else None,
        "cpu_avg_pct": mean([r["cpu_avg_pct"] for r in ok if r["cpu_avg_pct"] is not None]) if ok else None,
        "cpu_peak_max_pct": max((r["cpu_peak_pct"] for r in ok if r["cpu_peak_pct"] is not None), default=None),
        "ram_delta_peak_max_mb": max((r["ram_delta_peak_mb"] for r in ok if r["ram_delta_peak_mb"] is not None), default=None),
    }
    report = f"""# ISLM DeepSeek-R1:1.5B Experimental Evaluation\n\n- Run started (UTC): {run_start}\n- Model configured: `{settings.OLLAMA_MODEL}`\n- Ollama URL: `{settings.OLLAMA_URL}`\n- Database: `{settings.DATABASE_URL}`\n- Cases: {len(cases)} fixed existing ticket/incident records; repetitions per case: {args.repetitions}\n- Raw CSV: `{csv_path.relative_to(ROOT).as_posix()}`\n\n## Methodology\n\nThe runner loads existing Ticket and Incident rows through SQLAlchemy, computes each SLA card using the project's `evaluate_single_item`, then calls the existing `enrich_with_ai_prediction` function. It does not issue writes or seed data. Latency is wall-clock around that enrichment call (including prompt preparation, Ollama transport, generation, parsing and fallback). CPU is whole-host utilization sampled every 200 ms and RAM is whole-host used memory; RAM delta is peak minus pre-call used memory. Raw parsed predictions and the compared SLA values are retained per observation in the CSV.\n\nCompleteness is the number of six non-empty response sections over six. SLA checks compare the reported authoritative metric object to the SQLite-derived card and flag selected textual contradictions. This checks the app's returned response; because the application itself injects authoritative fields, it does not independently establish that free-form model prose is factually correct. Runbook relevance is an automatic proxy combining expected runbook ID match and hit rate for predeclared case keywords in recommendation text; it is not human grading.\n\n## Results\n\n```json\n{json.dumps(metrics, indent=2)}\n```\n\n## Interpretation and limitations\n\nOnly successful model responses contribute to inference latency and response-quality averages. Fallbacks are counted separately and their error text and deterministic response are recorded. If there are fewer than ten successful calls, the requested latency/quality benchmark is incomplete. Host CPU/RAM includes other processes and may miss brief peaks between samples; it is not Ollama-process-only attribution. Fixtures are a small, fixed sample from the existing database, and time-sensitive SLA values are recomputed at each repeat. Automated keyword relevance can reward incidental word matches and requires human review for stronger claims. No production records were changed.\n"""
    report_path.write_text(report, encoding="utf-8")
    print(f"CSV: {csv_path}\nReport: {report_path}\nSummary: {json.dumps(metrics)}")


if __name__ == "__main__":
    asyncio.run(main())
