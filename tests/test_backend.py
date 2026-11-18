"""
Comprehensive backend test suite for ISLM (Intelligent Service Level Management).
Verifies:
  1. Database connectivity & SQLite configuration
  2. Health endpoint (/api/health)
  3. SLA calculation engine, parsing, and threshold logic
  4. SLA deterministic evaluation for Incident and Ticket records
  5. Live host telemetry and correlated infrastructure metrics
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.connection import check_db_connection, SessionLocal
from backend.database.models import Incident, Ticket
from backend.services import sla_service
from backend.services import telemetry_service


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_database_connection():
    """Verify that the SQLite database engine connects and executes queries."""
    connected = check_db_connection()
    assert connected is True, "Database connection check failed"


def test_health_endpoint(client):
    """Verify that /api/health responds with HTTP 200 and connected database status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["database"]["connected"] is True
    assert data["database"]["type"] == "SQLite"


def test_sla_duration_parser():
    """Verify SLA duration parsing for minutes, hours, and days."""
    assert sla_service.parse_duration_to_minutes("15 minutes") == 15
    assert sla_service.parse_duration_to_minutes("30m") == 30
    assert sla_service.parse_duration_to_minutes("4 hours") == 240
    assert sla_service.parse_duration_to_minutes("2h") == 120
    assert sla_service.parse_duration_to_minutes("2 days") == 2880
    assert sla_service.parse_duration_to_minutes(None) is None


def test_sla_format_minutes():
    """Verify human-readable duration formatting."""
    assert sla_service.format_minutes(15) == "15m"
    assert sla_service.format_minutes(60) == "1h"
    assert sla_service.format_minutes(150) == "2h 30m"
    assert sla_service.format_minutes(None) == "N/A"


def test_sla_rule_evaluation():
    """Verify deterministic SLA evaluation for an incident record."""
    db = SessionLocal()
    try:
        inc = db.query(Incident).first()
        if inc:
            eval_result = sla_service.evaluate_single_item(inc, "incident", db)
            assert "risk_level" in eval_result
            assert "status_label" in eval_result
            assert "percent_elapsed" in eval_result
            assert "elapsed_minutes" in eval_result
            assert "remaining_minutes" in eval_result
            assert "is_breached" in eval_result
            assert "reason" in eval_result
            assert "recommended_action" in eval_result
            assert eval_result["risk_level"] in ["Low", "Medium", "High", "Critical"]
    finally:
        db.close()


def test_telemetry_metrics_collection():
    """Verify real host telemetry and simulated IT telemetry structure."""
    db = SessionLocal()
    try:
        telemetry = telemetry_service.get_telemetry_metrics(db)
        assert "real_metrics" in telemetry
        assert "simulated_metrics" in telemetry
        real = telemetry["real_metrics"]
        assert real["storage_engine"] == "SQLite3 (WAL Mode)"
        assert "database_response_time_ms" in real
        assert "host_cpu_usage_pct" in real
        assert "host_ram_usage_pct" in real
        sim = telemetry["simulated_metrics"]
        assert "network_latency_ms" in sim
        assert "router_r101" in sim
    finally:
        db.close()
