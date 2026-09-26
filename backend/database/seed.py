"""
Database seeder — populates the database with sample IT service management data.

Data sourced from DATASETS.md — comprehensive test datasets for the ISLM system.

Run:  python -m backend.database.seed   (from project root)
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.database.connection import init_db, SessionLocal
from backend.database.models import User, Service, Ticket, SLA, File


def seed():
    """Insert sample rows if the database is empty."""
    init_db()
    db = SessionLocal()

    try:
        # Skip if data already exists
        if db.query(User).count() > 0:
            print("Database already seeded — skipping.")
            return

        # ── Users (8 team members) ───────────────────────────────────────
        users = [
            User(name="Alice Johnson",  email="alice@islm.local",  role="admin"),
            User(name="Bob Smith",      email="bob@islm.local",    role="technician"),
            User(name="Carol Lee",      email="carol@islm.local",  role="technician"),
            User(name="David Kumar",    email="david@islm.local",  role="manager"),
            User(name="Eve Martinez",   email="eve@islm.local",    role="technician"),
            User(name="Frank Wilson",   email="frank@islm.local",  role="technician"),
            User(name="Grace Chen",     email="grace@islm.local",  role="technician"),
            User(name="Henry Patel",    email="henry@islm.local",  role="technician"),
        ]
        db.add_all(users)
        db.flush()  # get IDs

        # ── Services (8 core IT services) ────────────────────────────────
        services = [
            Service(service_name="Database-Primary",   description="Primary MySQL database server for application data",   status="active", owner="Bob Smith"),
            Service(service_name="API-Gateway",        description="Kong API Gateway for all microservices",               status="active", owner="Eve Martinez"),
            Service(service_name="Cache-Layer",        description="Redis cluster for caching",                            status="active", owner="Henry Patel"),
            Service(service_name="Network-Core",       description="Core networking infrastructure",                       status="active", owner="Carol Lee"),
            Service(service_name="Email-System",       description="Internal email service (Outlook)",                     status="active", owner="David Kumar"),
            Service(service_name="Security-Gateway",   description="WAF and DDoS protection",                              status="active", owner="Frank Wilson"),
            Service(service_name="Backup-Storage",     description="Backup and disaster recovery storage",                 status="active", owner="Grace Chen"),
            Service(service_name="Monitoring-Stack",   description="Prometheus, Grafana, and alerting",                    status="active", owner="Alice Johnson"),
        ]
        db.add_all(services)
        db.flush()

        # ── Tickets (8 realistic incidents) ──────────────────────────────
        tickets = [
            Ticket(
                title="Database CPU spike investigation",
                description="High CPU on primary DB at 96.5%. Connection pool exhausted, lock wait timeout exceeded. Need to identify slow queries and optimize.",
                category="Database", priority="critical", status="in_progress",
                assigned_to=users[1].id, service_id=services[0].id,
            ),
            Ticket(
                title="API Gateway auth endpoint errors",
                description="Auth endpoint returning 500 errors at 15.8% error rate. Dependency service timeout detected. p95 response time at 2500ms.",
                category="Application", priority="critical", status="in_progress",
                assigned_to=users[4].id, service_id=services[1].id,
            ),
            Ticket(
                title="Database replication lag - Monitor and resolve",
                description="Replica lagging 5 minutes behind primary. Network latency spike detected at 180ms RTT. Backup at risk.",
                category="Database", priority="high", status="open",
                assigned_to=users[6].id, service_id=services[0].id,
            ),
            Ticket(
                title="Cache disk space critical - Cleanup needed",
                description="Cache node at 97.7% disk capacity. Redis RDB save failing. Immediate cleanup required.",
                category="Server", priority="high", status="open",
                assigned_to=users[7].id, service_id=services[2].id,
            ),
            Ticket(
                title="TLS certificate renewal - Action Required",
                description="API gateway certificate *.islm.local expires in 7 days. Schedule renewal immediately.",
                category="Security", priority="high", status="open",
                assigned_to=users[5].id, service_id=services[5].id,
            ),
            Ticket(
                title="Memory leak in worker process - RESOLVED",
                description="Background worker memory growing 50MB/day, peaked at 850MB. Fixed by redeploying with patched code. Stable at 150MB.",
                category="Application", priority="high", status="resolved",
                assigned_to=users[4].id, service_id=services[1].id,
            ),
            Ticket(
                title="Network WAN link packet loss investigation",
                description="2.1% packet loss between datacenters. 150ms latency, 45ms jitter. May impact backup replication.",
                category="Network", priority="medium", status="in_progress",
                assigned_to=users[2].id, service_id=services[3].id,
            ),
            Ticket(
                title="Load balancer nodes failing health checks - CRITICAL",
                description="3 of 5 LB nodes down. Traffic dropping 40%. Nodes 2, 3, 4 not responding. Immediate escalation required.",
                category="Network", priority="critical", status="in_progress",
                assigned_to=users[7].id, service_id=services[1].id,
            ),
        ]
        db.add_all(tickets)
        db.flush()

        # ── SLAs (comprehensive coverage for all services) ───────────────
        slas = [
            # Database-Primary
            SLA(service_id=services[0].id, priority="critical", response_time="15 minutes", resolution_time="4 hours"),
            SLA(service_id=services[0].id, priority="high",     response_time="30 minutes", resolution_time="8 hours"),
            SLA(service_id=services[0].id, priority="medium",   response_time="2 hours",    resolution_time="24 hours"),
            SLA(service_id=services[0].id, priority="low",      response_time="4 hours",    resolution_time="48 hours"),
            # API-Gateway
            SLA(service_id=services[1].id, priority="critical", response_time="15 minutes", resolution_time="4 hours"),
            SLA(service_id=services[1].id, priority="high",     response_time="30 minutes", resolution_time="8 hours"),
            # Cache-Layer
            SLA(service_id=services[2].id, priority="critical", response_time="15 minutes", resolution_time="4 hours"),
            SLA(service_id=services[2].id, priority="high",     response_time="30 minutes", resolution_time="8 hours"),
            # Network-Core
            SLA(service_id=services[3].id, priority="critical", response_time="15 minutes", resolution_time="2 hours"),
            SLA(service_id=services[3].id, priority="high",     response_time="30 minutes", resolution_time="4 hours"),
            SLA(service_id=services[3].id, priority="medium",   response_time="2 hours",    resolution_time="8 hours"),
            SLA(service_id=services[3].id, priority="low",      response_time="4 hours",    resolution_time="24 hours"),
            # Email-System
            SLA(service_id=services[4].id, priority="critical", response_time="1 hour",     resolution_time="8 hours"),
            SLA(service_id=services[4].id, priority="high",     response_time="2 hours",    resolution_time="24 hours"),
            # Security-Gateway
            SLA(service_id=services[5].id, priority="critical", response_time="15 minutes", resolution_time="2 hours"),
            SLA(service_id=services[5].id, priority="high",     response_time="30 minutes", resolution_time="4 hours"),
            # Backup-Storage
            SLA(service_id=services[6].id, priority="critical", response_time="1 hour",     resolution_time="24 hours"),
            SLA(service_id=services[6].id, priority="high",     response_time="2 hours",    resolution_time="48 hours"),
            # Monitoring-Stack
            SLA(service_id=services[7].id, priority="critical", response_time="1 hour",     resolution_time="8 hours"),
            SLA(service_id=services[7].id, priority="high",     response_time="2 hours",    resolution_time="24 hours"),
        ]
        db.add_all(slas)

        db.commit()
        print("Database seeded successfully with sample data.")
        print(f"  • {len(users)} users")
        print(f"  • {len(services)} services")
        print(f"  • {len(tickets)} tickets")
        print(f"  • {len(slas)} SLA records")

    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
