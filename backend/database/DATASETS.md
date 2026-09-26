# SLM Project: Comprehensive Test Datasets

## 1. USERS DATASET (5-10 team members)

```json
{
  "users": [
    {
      "id": 1,
      "username": "alice_johnson",
      "email": "alice@islm.local",
      "full_name": "Alice Johnson",
      "role": "admin",
      "department": "Infrastructure",
      "phone": "+1-555-0101",
      "created_at": "2026-01-15T09:00:00Z",
      "is_active": true
    },
    {
      "id": 2,
      "username": "bob_smith",
      "email": "bob@islm.local",
      "full_name": "Bob Smith",
      "role": "senior_engineer",
      "department": "Database",
      "phone": "+1-555-0102",
      "created_at": "2026-01-15T09:15:00Z",
      "is_active": true,
      "specialization": ["Database", "Replication", "Performance"]
    },
    {
      "id": 3,
      "username": "carol_lee",
      "email": "carol@islm.local",
      "full_name": "Carol Lee",
      "role": "engineer",
      "department": "Network",
      "phone": "+1-555-0103",
      "created_at": "2026-01-15T09:30:00Z",
      "is_active": true,
      "specialization": ["Network", "Security", "Load Balancing"]
    },
    {
      "id": 4,
      "username": "david_kumar",
      "email": "david@islm.local",
      "full_name": "David Kumar",
      "role": "manager",
      "department": "Operations",
      "phone": "+1-555-0104",
      "created_at": "2026-01-16T10:00:00Z",
      "is_active": true
    },
    {
      "id": 5,
      "username": "eve_martinez",
      "email": "eve@islm.local",
      "full_name": "Eve Martinez",
      "role": "engineer",
      "department": "Application",
      "phone": "+1-555-0105",
      "created_at": "2026-01-16T10:15:00Z",
      "is_active": true,
      "specialization": ["Application", "API Gateway", "Microservices"]
    },
    {
      "id": 6,
      "username": "frank_wilson",
      "email": "frank@islm.local",
      "full_name": "Frank Wilson",
      "role": "engineer",
      "department": "Security",
      "phone": "+1-555-0106",
      "created_at": "2026-01-17T11:00:00Z",
      "is_active": true,
      "specialization": ["Security", "Compliance", "Certificates"]
    },
    {
      "id": 7,
      "username": "grace_chen",
      "email": "grace@islm.local",
      "full_name": "Grace Chen",
      "role": "engineer",
      "department": "Database",
      "phone": "+1-555-0107",
      "created_at": "2026-01-17T11:30:00Z",
      "is_active": true,
      "specialization": ["Database", "Backup", "Recovery"]
    },
    {
      "id": 8,
      "username": "henry_patel",
      "email": "henry@islm.local",
      "full_name": "Henry Patel",
      "role": "engineer",
      "department": "Infrastructure",
      "phone": "+1-555-0108",
      "created_at": "2026-01-18T12:00:00Z",
      "is_active": true,
      "specialization": ["Infrastructure", "Hardware", "Networking"]
    }
  ]
}
```

---

## 2. SERVICES DATASET (6-10 IT services)

```json
{
  "services": [
    {
      "id": 1,
      "service_name": "Database-Primary",
      "description": "Primary MySQL database server for application data",
      "category": "Database",
      "owner_id": 2,
      "owner_name": "Bob Smith",
      "status": "active",
      "health_status": "healthy",
      "sla_response_time": 15,
      "sla_resolution_time": 240,
      "dependencies": ["Network-Core", "Backup-Storage"],
      "critical": true,
      "location": "Data Center A",
      "contact_email": "db-team@islm.local",
      "created_at": "2026-01-10T08:00:00Z"
    },
    {
      "id": 2,
      "service_name": "API-Gateway",
      "description": "Kong API Gateway for all microservices",
      "category": "Application",
      "owner_id": 5,
      "owner_name": "Eve Martinez",
      "status": "active",
      "health_status": "healthy",
      "sla_response_time": 15,
      "sla_resolution_time": 240,
      "dependencies": ["Database-Primary", "Cache-Layer"],
      "critical": true,
      "location": "Data Center A",
      "contact_email": "api-team@islm.local",
      "created_at": "2026-01-10T08:30:00Z"
    },
    {
      "id": 3,
      "service_name": "Cache-Layer",
      "description": "Redis cluster for caching",
      "category": "Infrastructure",
      "owner_id": 8,
      "owner_name": "Henry Patel",
      "status": "active",
      "health_status": "healthy",
      "sla_response_time": 15,
      "sla_resolution_time": 240,
      "dependencies": ["Network-Core"],
      "critical": true,
      "location": "Data Center A",
      "contact_email": "cache-team@islm.local",
      "created_at": "2026-01-10T09:00:00Z"
    },
    {
      "id": 4,
      "service_name": "Network-Core",
      "description": "Core networking infrastructure",
      "category": "Network",
      "owner_id": 3,
      "owner_name": "Carol Lee",
      "status": "active",
      "health_status": "healthy",
      "sla_response_time": 15,
      "sla_resolution_time": 120,
      "dependencies": [],
      "critical": true,
      "location": "Data Center A",
      "contact_email": "network-team@islm.local",
      "created_at": "2026-01-10T09:30:00Z"
    },
    {
      "id": 5,
      "service_name": "Email-System",
      "description": "Internal email service (Outlook)",
      "category": "Application",
      "owner_id": 4,
      "owner_name": "David Kumar",
      "status": "active",
      "health_status": "healthy",
      "sla_response_time": 60,
      "sla_resolution_time": 480,
      "dependencies": ["Network-Core"],
      "critical": false,
      "location": "Cloud",
      "contact_email": "email-team@islm.local",
      "created_at": "2026-01-10T10:00:00Z"
    },
    {
      "id": 6,
      "service_name": "Security-Gateway",
      "description": "WAF and DDoS protection",
      "category": "Security",
      "owner_id": 6,
      "owner_name": "Frank Wilson",
      "status": "active",
      "health_status": "healthy",
      "sla_response_time": 15,
      "sla_resolution_time": 120,
      "dependencies": ["Network-Core"],
      "critical": true,
      "location": "Data Center A",
      "contact_email": "security-team@islm.local",
      "created_at": "2026-01-10T10:30:00Z"
    },
    {
      "id": 7,
      "service_name": "Backup-Storage",
      "description": "Backup and disaster recovery storage",
      "category": "Storage",
      "owner_id": 7,
      "owner_name": "Grace Chen",
      "status": "active",
      "health_status": "healthy",
      "sla_response_time": 60,
      "sla_resolution_time": 1440,
      "dependencies": ["Network-Core"],
      "critical": true,
      "location": "Data Center B",
      "contact_email": "backup-team@islm.local",
      "created_at": "2026-01-10T11:00:00Z"
    },
    {
      "id": 8,
      "service_name": "Monitoring-Stack",
      "description": "Prometheus, Grafana, and alerting",
      "category": "Infrastructure",
      "owner_id": 1,
      "owner_name": "Alice Johnson",
      "status": "active",
      "health_status": "healthy",
      "sla_response_time": 60,
      "sla_resolution_time": 480,
      "dependencies": ["Network-Core"],
      "critical": false,
      "location": "Data Center A",
      "contact_email": "monitoring-team@islm.local",
      "created_at": "2026-01-10T11:30:00Z"
    }
  ]
}
```

---

## 3. INCIDENTS DATASET (20-30 sample incidents)

```json
{
  "incidents": [
    {
      "id": 1,
      "incident_id": "INC-20260902-001",
      "source": "prometheus",
      "title": "High CPU usage on database-primary",
      "description": "CPU utilization exceeded 95% for 10 minutes. Slow queries identified in slow log.",
      "severity": "critical",
      "affected_service": "Database-Primary",
      "affected_component": "db-node-1",
      "status": "open",
      "detected_at": "2026-09-02T14:30:00Z",
      "acknowledged_at": null,
      "resolved_at": null,
      "mttr_minutes": null,
      "tags": ["database", "cpu", "performance", "slow-queries"],
      "assigned_to": "bob_smith",
      "error_logs": [
        "2026-09-02 14:30:15 ERROR: Connection pool exhausted",
        "2026-09-02 14:31:20 WARN: Lock wait timeout exceeded",
        "2026-09-02 14:32:45 ERROR: Query timeout on large JOIN"
      ],
      "raw_metrics": {
        "cpu_usage": 96.5,
        "memory_usage": 78.2,
        "connections": 450,
        "queries_per_second": 5200
      }
    },
    {
      "id": 2,
      "incident_id": "INC-20260902-002",
      "source": "api",
      "title": "High error rate on API gateway",
      "description": "Auth endpoint returning 500 errors. Dependency service timeout detected.",
      "severity": "critical",
      "affected_service": "API-Gateway",
      "affected_component": "api-pod-3",
      "status": "acknowledged",
      "detected_at": "2026-09-02T15:15:00Z",
      "acknowledged_at": "2026-09-02T15:20:00Z",
      "resolved_at": null,
      "mttr_minutes": null,
      "tags": ["api", "auth", "errors", "timeout"],
      "assigned_to": "eve_martinez",
      "error_logs": [
        "2026-09-02 15:15:30 ERROR: Timeout calling Database-Primary",
        "2026-09-02 15:16:45 ERROR: Connection refused on cache lookup"
      ],
      "raw_metrics": {
        "error_rate": 15.8,
        "response_time_p95": 2500,
        "requests_per_second": 1200
      }
    },
    {
      "id": 3,
      "incident_id": "INC-20260902-003",
      "source": "prometheus",
      "title": "Database replication lag detected",
      "description": "Replica lagging 5 minutes behind primary. Network latency spike detected.",
      "severity": "high",
      "affected_service": "Database-Primary",
      "affected_component": "db-replica-1",
      "status": "open",
      "detected_at": "2026-09-02T13:45:00Z",
      "acknowledged_at": null,
      "resolved_at": null,
      "mttr_minutes": null,
      "tags": ["database", "replication", "lag", "network"],
      "assigned_to": "grace_chen",
      "error_logs": [
        "2026-09-02 13:45:20 WARN: Replication lag > 300 seconds",
        "2026-09-02 13:46:10 WARN: Network RTT to replica: 180ms"
      ],
      "raw_metrics": {
        "replication_lag_seconds": 310,
        "network_latency_ms": 180,
        "binlog_size_mb": 2500
      }
    },
    {
      "id": 4,
      "incident_id": "INC-20260902-004",
      "source": "syslog",
      "title": "Disk space critical on cache node",
      "description": "Cache node running out of disk space. Redis auto-cleanup failing.",
      "severity": "high",
      "affected_service": "Cache-Layer",
      "affected_component": "cache-node-2",
      "status": "open",
      "detected_at": "2026-09-02T14:00:00Z",
      "acknowledged_at": null,
      "resolved_at": null,
      "mttr_minutes": null,
      "tags": ["cache", "disk", "storage", "redis"],
      "assigned_to": "henry_patel",
      "error_logs": [
        "2026-09-02 14:00:15 ERROR: No space left on device",
        "2026-09-02 14:01:30 WARN: Redis RDB save failed"
      ],
      "raw_metrics": {
        "disk_free_percent": 2.3,
        "disk_usage_gb": 487.2,
        "eviction_rate": 1.2
      }
    },
    {
      "id": 5,
      "incident_id": "INC-20260902-005",
      "source": "manual",
      "title": "TLS certificate expiring soon",
      "description": "API gateway certificate expires in 7 days. Need renewal before expiration.",
      "severity": "medium",
      "affected_service": "Security-Gateway",
      "affected_component": "load-balancer",
      "status": "open",
      "detected_at": "2026-08-26T09:00:00Z",
      "acknowledged_at": null,
      "resolved_at": null,
      "mttr_minutes": null,
      "tags": ["certificate", "security", "tls", "renewal"],
      "assigned_to": "frank_wilson",
      "error_logs": [
        "Certificate: *.islm.local expiring on 2026-09-09T14:30:00Z"
      ],
      "raw_metrics": {
        "days_until_expiry": 7,
        "certificate_validity_days": 365
      }
    },
    {
      "id": 6,
      "incident_id": "INC-20260902-006",
      "source": "prometheus",
      "title": "Memory leak detected in worker process",
      "description": "Background worker process memory usage growing 50MB per day.",
      "severity": "high",
      "affected_service": "API-Gateway",
      "affected_component": "worker-process-5",
      "status": "resolved",
      "detected_at": "2026-08-30T08:00:00Z",
      "acknowledged_at": "2026-08-30T09:15:00Z",
      "resolved_at": "2026-08-31T16:45:00Z",
      "mttr_minutes": 1590,
      "tags": ["memory", "leak", "worker", "performance"],
      "assigned_to": "eve_martinez",
      "error_logs": [
        "2026-08-30 08:00:20 WARN: Memory usage: 250MB (baseline 100MB)"
      ],
      "raw_metrics": {
        "memory_growth_mb_per_day": 50,
        "current_memory_mb": 850
      }
    },
    {
      "id": 7,
      "incident_id": "INC-20260902-007",
      "source": "api",
      "title": "Packet loss detected between regions",
      "description": "2% packet loss between primary and backup data center.",
      "severity": "medium",
      "affected_service": "Network-Core",
      "affected_component": "wan-link",
      "status": "acknowledged",
      "detected_at": "2026-09-02T16:30:00Z",
      "acknowledged_at": "2026-09-02T16:35:00Z",
      "resolved_at": null,
      "mttr_minutes": null,
      "tags": ["network", "packet-loss", "latency", "wan"],
      "assigned_to": "carol_lee",
      "error_logs": [
        "2026-09-02 16:30:45 WARN: Packet loss 2.1% detected"
      ],
      "raw_metrics": {
        "packet_loss_percent": 2.1,
        "network_latency_ms": 150,
        "jitter_ms": 45
      }
    },
    {
      "id": 8,
      "incident_id": "INC-20260902-008",
      "source": "prometheus",
      "title": "Load balancer health check failures",
      "description": "3 of 5 load balancer nodes failing health checks.",
      "severity": "critical",
      "affected_service": "API-Gateway",
      "affected_component": "lb-node-2,3,4",
      "status": "open",
      "detected_at": "2026-09-02T17:00:00Z",
      "acknowledged_at": null,
      "resolved_at": null,
      "mttr_minutes": null,
      "tags": ["load-balancer", "health-check", "failover"],
      "assigned_to": "henry_patel",
      "error_logs": [
        "2026-09-02 17:00:15 ERROR: LB node 2 not responding",
        "2026-09-02 17:00:30 ERROR: LB node 3 connection refused",
        "2026-09-02 17:00:45 ERROR: LB node 4 timeout"
      ],
      "raw_metrics": {
        "healthy_nodes": 2,
        "total_nodes": 5,
        "traffic_dropped_percent": 40
      }
    }
  ]
}
```

---

## 4. TICKETS DATASET (12-15 support tickets)

```json
{
  "tickets": [
    {
      "id": 1,
      "ticket_id": "TKT-20260902-001",
      "title": "Database CPU spike investigation",
      "description": "High CPU on primary DB. Need to identify slow queries and optimize.",
      "category": "incident",
      "priority": "critical",
      "status": "in-progress",
      "related_incidents": ["INC-20260902-001"],
      "assigned_to": "bob_smith",
      "created_by": "system",
      "created_at": "2026-09-02T14:35:00Z",
      "updated_at": "2026-09-02T15:45:00Z",
      "sla_target": {
        "response_time_minutes": 15,
        "resolution_time_minutes": 240
      },
      "sla_breach_prediction": {
        "predicted": false,
        "confidence": 0.92,
        "predicted_breach_at": null,
        "hours_until_breach": 3.5
      },
      "classification": {
        "category": "Database",
        "confidence": 0.95,
        "model": "deepseek-r1:1.5b"
      },
      "suggested_actions": [
        {
          "action": "Check slow query log for long-running transactions",
          "confidence": 0.94,
          "reason": "CPU spike correlated with high query count"
        },
        {
          "action": "Analyze table statistics with ANALYZE command",
          "confidence": 0.88,
          "reason": "Outdated statistics can cause poor query plans"
        },
        {
          "action": "Review recent application deployments",
          "confidence": 0.82,
          "reason": "Code changes often introduce unoptimized queries"
        }
      ],
      "resolution_notes": null
    },
    {
      "id": 2,
      "ticket_id": "TKT-20260902-002",
      "title": "API Gateway auth endpoint errors",
      "description": "500 errors on /auth endpoint. Database dependency timeout.",
      "category": "incident",
      "priority": "critical",
      "status": "in-progress",
      "related_incidents": ["INC-20260902-002"],
      "assigned_to": "eve_martinez",
      "created_by": "system",
      "created_at": "2026-09-02T15:18:00Z",
      "updated_at": "2026-09-02T16:00:00Z",
      "sla_target": {
        "response_time_minutes": 15,
        "resolution_time_minutes": 240
      },
      "sla_breach_prediction": {
        "predicted": true,
        "confidence": 0.87,
        "predicted_breach_at": "2026-09-02T19:15:00Z",
        "hours_until_breach": 2.25
      },
      "classification": {
        "category": "Application",
        "confidence": 0.91,
        "model": "deepseek-r1:1.5b"
      },
      "suggested_actions": [
        {
          "action": "Increase connection pool timeout on API gateway",
          "confidence": 0.92,
          "reason": "Timeout suggests database is slow to respond"
        },
        {
          "action": "Check TKT-20260902-001 (Database CPU issue)",
          "confidence": 0.89,
          "reason": "Root cause may be related database performance problem"
        }
      ]
    },
    {
      "id": 3,
      "ticket_id": "TKT-20260902-003",
      "title": "Database replication lag - Monitor and resolve",
      "description": "Replica 5 minutes behind primary. Backup at risk.",
      "category": "incident",
      "priority": "high",
      "status": "open",
      "related_incidents": ["INC-20260902-003"],
      "assigned_to": "grace_chen",
      "created_by": "system",
      "created_at": "2026-09-02T13:50:00Z",
      "updated_at": "2026-09-02T14:10:00Z",
      "sla_target": {
        "response_time_minutes": 60,
        "resolution_time_minutes": 480
      },
      "sla_breach_prediction": {
        "predicted": false,
        "confidence": 0.85,
        "predicted_breach_at": null,
        "hours_until_breach": 7.2
      },
      "classification": {
        "category": "Database",
        "confidence": 0.98,
        "model": "deepseek-r1:1.5b"
      },
      "suggested_actions": [
        {
          "action": "Monitor replication status every 5 minutes",
          "confidence": 0.95,
          "reason": "Lag may be transient if high write load reduces"
        },
        {
          "action": "Check network latency to replica server",
          "confidence": 0.88,
          "reason": "150ms RTT detected, may be limiting throughput"
        }
      ]
    },
    {
      "id": 4,
      "ticket_id": "TKT-20260902-004",
      "title": "Cache disk space critical - Cleanup needed",
      "description": "Cache node at 97% disk capacity. Immediate cleanup required.",
      "category": "incident",
      "priority": "high",
      "status": "open",
      "related_incidents": ["INC-20260902-004"],
      "assigned_to": "henry_patel",
      "created_by": "system",
      "created_at": "2026-09-02T14:05:00Z",
      "updated_at": "2026-09-02T14:30:00Z",
      "sla_target": {
        "response_time_minutes": 15,
        "resolution_time_minutes": 240
      },
      "sla_breach_prediction": {
        "predicted": false,
        "confidence": 0.79,
        "predicted_breach_at": null,
        "hours_until_breach": 6.8
      },
      "classification": {
        "category": "Infrastructure",
        "confidence": 0.96,
        "model": "deepseek-r1:1.5b"
      },
      "suggested_actions": [
        {
          "action": "Clear old Redis keys manually with FLUSHDB",
          "confidence": 0.90,
          "reason": "Auto-eviction failing, manual purge necessary"
        },
        {
          "action": "Expand volume or add new cache node",
          "confidence": 0.85,
          "reason": "Growth rate suggests permanent capacity increase needed"
        }
      ]
    },
    {
      "id": 5,
      "ticket_id": "TKT-20260902-005",
      "title": "TLS certificate renewal - Action Required",
      "description": "API certificate expires in 7 days. Schedule renewal immediately.",
      "category": "service-request",
      "priority": "high",
      "status": "open",
      "related_incidents": ["INC-20260902-005"],
      "assigned_to": "frank_wilson",
      "created_by": "system",
      "created_at": "2026-08-26T09:05:00Z",
      "updated_at": "2026-08-26T10:00:00Z",
      "sla_target": {
        "response_time_minutes": 240,
        "resolution_time_minutes": 1440
      },
      "sla_breach_prediction": {
        "predicted": false,
        "confidence": 0.92,
        "predicted_breach_at": null,
        "hours_until_breach": 144
      },
      "classification": {
        "category": "Security",
        "confidence": 0.99,
        "model": "deepseek-r1:1.5b"
      },
      "suggested_actions": [
        {
          "action": "Initiate certificate renewal with CA",
          "confidence": 0.98,
          "reason": "Standard procedure, should be started ASAP"
        },
        {
          "action": "Setup automation for future renewals",
          "confidence": 0.85,
          "reason": "Prevent manual renewal next year"
        }
      ]
    },
    {
      "id": 6,
      "ticket_id": "TKT-20260831-006",
      "title": "Memory leak in worker process - RESOLVED",
      "description": "Background worker memory growing. Fixed by redeploying.",
      "category": "incident",
      "priority": "high",
      "status": "resolved",
      "related_incidents": ["INC-20260902-006"],
      "assigned_to": "eve_martinez",
      "created_by": "system",
      "created_at": "2026-08-30T08:10:00Z",
      "updated_at": "2026-08-31T16:50:00Z",
      "resolved_at": "2026-08-31T16:50:00Z",
      "sla_target": {
        "response_time_minutes": 60,
        "resolution_time_minutes": 480
      },
      "sla_breach_prediction": {
        "predicted": false,
        "confidence": 0.99,
        "predicted_breach_at": null,
        "hours_until_breach": null
      },
      "classification": {
        "category": "Application",
        "confidence": 0.94,
        "model": "deepseek-r1:1.5b"
      },
      "resolution_notes": "Redeployed worker service with patched code. Memory stable at 150MB baseline."
    },
    {
      "id": 7,
      "ticket_id": "TKT-20260902-007",
      "title": "Network WAN link packet loss investigation",
      "description": "2% packet loss between datacenters. May impact backup replication.",
      "category": "incident",
      "priority": "medium",
      "status": "acknowledged",
      "related_incidents": ["INC-20260902-007"],
      "assigned_to": "carol_lee",
      "created_by": "system",
      "created_at": "2026-09-02T16:35:00Z",
      "updated_at": "2026-09-02T17:00:00Z",
      "sla_target": {
        "response_time_minutes": 240,
        "resolution_time_minutes": 1440
      },
      "sla_breach_prediction": {
        "predicted": false,
        "confidence": 0.88,
        "predicted_breach_at": null,
        "hours_until_breach": 20.5
      },
      "classification": {
        "category": "Network",
        "confidence": 0.96,
        "model": "deepseek-r1:1.5b"
      },
      "suggested_actions": [
        {
          "action": "Contact ISP for link diagnostics",
          "confidence": 0.87,
          "reason": "Physical link issue likely, needs carrier investigation"
        },
        {
          "action": "Failover backup to secondary WAN link",
          "confidence": 0.79,
          "reason": "Temporary mitigation while primary is under investigation"
        }
      ]
    },
    {
      "id": 8,
      "ticket_id": "TKT-20260902-008",
      "title": "Load balancer nodes failing health checks - CRITICAL",
      "description": "3 of 5 LB nodes down. Traffic dropping 40%. Immediate escalation.",
      "category": "incident",
      "priority": "critical",
      "status": "in-progress",
      "related_incidents": ["INC-20260902-008"],
      "assigned_to": "henry_patel",
      "created_by": "system",
      "created_at": "2026-09-02T17:05:00Z",
      "updated_at": "2026-09-02T17:30:00Z",
      "sla_target": {
        "response_time_minutes": 15,
        "resolution_time_minutes": 120
      },
      "sla_breach_prediction": {
        "predicted": true,
        "confidence": 0.93,
        "predicted_breach_at": "2026-09-02T18:50:00Z",
        "hours_until_breach": 1.15
      },
      "classification": {
        "category": "Infrastructure",
        "confidence": 0.97,
        "model": "deepseek-r1:1.5b"
      },
      "suggested_actions": [
        {
          "action": "SSH to failed nodes and check service status",
          "confidence": 0.95,
          "reason": "Immediate investigation to restore service"
        },
        {
          "action": "Restart load balancer service on nodes 2,3,4",
          "confidence": 0.88,
          "reason": "Service may be hung, restart often fixes"
        },
        {
          "action": "Escalate to L3 if restart fails",
          "confidence": 0.92,
          "reason": "May require deeper infrastructure diagnostics"
        }
      ]
    }
  ]
}
```

---

## 5. KB ARTICLES DATASET (10-15 knowledge base articles)

```json
{
  "kb_articles": [
    {
      "id": 1,
      "article_id": "KB-20260901-001",
      "title": "Database Primary Failover Runbook",
      "category": "Procedures",
      "tags": ["failover", "database", "replication", "runbook", "disaster-recovery"],
      "service_affinity": ["Database-Primary"],
      "author": "bob_smith",
      "created_at": "2026-08-01T10:00:00Z",
      "updated_at": "2026-09-01T14:00:00Z",
      "is_published": true,
      "content": """
# Database Primary Failover Runbook

## Prerequisites
- SSH access to all database nodes
- Sufficient disk space on replica (>10GB free)
- Replication lag < 1 minute
- Current IP address of primary and replica

## Steps

### 1. Verify Replica is Caught Up
```sql
SHOW SLAVE STATUS\G
```
Confirm `Seconds_Behind_Master` is < 60 seconds.

### 2. Stop Writes on Primary
```sql
FLUSH TABLES WITH READ LOCK;
```
This prevents new data changes during failover.

### 3. Promote Replica to Primary
```sql
STOP SLAVE;
RESET SLAVE ALL;
SET GLOBAL read_only = OFF;
```

### 4. Update Application Connection String
- Update DNS CNAME to point to new primary IP
- Wait 30 seconds for DNS propagation
- Monitor application error logs
- Restart connection pools

### 5. Reconfigure Old Primary as New Replica
```sql
CHANGE MASTER TO MASTER_HOST='<new-primary-ip>',
                 MASTER_USER='replication',
                 MASTER_PASSWORD='<password>';
START SLAVE;
```

### 6. Verify Replication Status
- Check `Seconds_Behind_Master = 0`
- Query count should match on both nodes
- Run consistency check

## Rollback Procedure
If promotion fails:
1. Restart MySQL on failed node
2. Restart failed node
3. Retry from Step 2

## SLA Impact
- Expected downtime: 2-3 minutes
- Data loss risk: None (synchronous replication)
- RTO: 3 minutes
- RPO: 0 seconds (no data loss)

## Post-Incident
1. Document root cause
2. Schedule infrastructure upgrade
3. Update monitoring thresholds
"""
    },
    {
      "id": 2,
      "article_id": "KB-20260901-002",
      "title": "Database High CPU Troubleshooting Guide",
      "category": "Troubleshooting",
      "tags": ["cpu", "performance", "database", "slow-queries", "troubleshooting"],
      "service_affinity": ["Database-Primary"],
      "author": "bob_smith",
      "created_at": "2026-07-15T09:00:00Z",
      "updated_at": "2026-09-01T11:00:00Z",
      "is_published": true,
      "content": """
# Database High CPU Troubleshooting

## Immediate Actions (0-5 minutes)

1. Check current CPU usage
```bash
top -b -n 1 | head -20
# Look for mysqld process CPU %
```

2. Connect to MySQL
```bash
mysql -u root -p
```

3. Check currently running queries
```sql
SHOW PROCESSLIST;
```

## Identify Expensive Queries (5-15 min)

```sql
SELECT * FROM performance_schema.events_statements_summary_by_digest
ORDER BY SUM_TIMER_WAIT DESC LIMIT 10;
```

This shows the slowest queries by total time spent.

## Common Causes & Fixes

### 1. Full Table Scans
**Symptom**: Query with WHERE clause but no index

**Fix**: Add index on WHERE columns
```sql
ALTER TABLE users ADD INDEX idx_status (status);
```

### 2. Missing Statistics
**Symptom**: Suboptimal query plans, index not used

**Fix**: Update statistics
```sql
ANALYZE TABLE users;
OPTIMIZE TABLE users;
```

### 3. Lock Contention
**Symptom**: Many queries in "Waiting for lock"

**Fix**: Check InnoDB locks
```sql
SHOW ENGINE INNODB STATUS\G
```

## Quick Fixes (Can apply now)

```sql
-- Kill long-running query (use with caution)
KILL <process_id>;

-- Clear query cache (MySQL 5.7 and earlier)
FLUSH QUERY CACHE;

-- Reload privileges
FLUSH PRIVILEGES;
```

## Monitoring for Prevention

Set up alerts:
- CPU > 75% (warning)
- CPU > 90% (critical)
- Query time > 10 seconds (alert)
- Lock wait > 5 seconds (alert)
"""
    },
    {
      "id": 3,
      "article_id": "KB-20260901-003",
      "title": "Redis Cache Failover Procedure",
      "category": "Procedures",
      "tags": ["cache", "redis", "failover", "high-availability"],
      "service_affinity": ["Cache-Layer"],
      "author": "henry_patel",
      "created_at": "2026-07-20T13:00:00Z",
      "updated_at": "2026-09-01T09:30:00Z",
      "is_published": true,
      "content": """
# Redis Cache Failover Procedure

## Automatic Failover (Expected Behavior)

Redis Sentinel automatically handles failover. Expected timeline:
1. Master node crashes (immediate detection)
2. 3 failed pings by Sentinel (~3 seconds)
3. Quorum elected new master (5-10 seconds)
4. Clients reconnected (30 seconds total)

**Data loss**: Only uncommitted writes (minimal)

## Manual Failover Steps

### 1. Connect to Sentinel
```bash
redis-cli -p 26379
```

### 2. Monitor Sentinel Status
```bash
SENTINEL masters
SENTINEL slaves mymaster
```

### 3. Initiate Manual Failover
```bash
SENTINEL failover mymaster
```

### 4. Verify New Configuration
```bash
SENTINEL get-master-addr-by-name mymaster
```

## Post-Failover Validation

- [ ] All replicas connected and syncing
- [ ] Cache hit rate > 80%
- [ ] No data corruption (check CRC)
- [ ] Application latency normal
- [ ] Old master rejoined as replica

## Troubleshooting

### Connection Refused
```bash
# Check if Redis is running
systemctl status redis
# Check firewall
sudo ufw allow 6379
```

### Replication Stuck
```bash
# In replica
SLAVEOF NO ONE  # Disconnect from master
SLAVEOF <master-ip> 6379  # Reconnect
```

### Data Mismatch
```bash
# Resync from snapshot
BGSAVE
# Transfer snapshot to new server
```

## SLA Impact
- Expected downtime: 30 seconds
- Data loss: Minimal (last write window only)
- Cache invalidation: Cache emptied on master failover
"""
    },
    {
      "id": 4,
      "article_id": "KB-20260901-004",
      "title": "API Gateway Error 500 Troubleshooting",
      "category": "Troubleshooting",
      "tags": ["api", "errors", "gateway", "troubleshooting", "timeout"],
      "service_affinity": ["API-Gateway"],
      "author": "eve_martinez",
      "created_at": "2026-08-10T14:30:00Z",
      "updated_at": "2026-09-01T15:00:00Z",
      "is_published": true,
      "content": """
# API Gateway 500 Error Troubleshooting

## Common Causes of 500 Errors

1. **Database Connection Timeout** (50%)
2. **Downstream Service Timeout** (25%)
3. **Out of Memory** (15%)
4. **Unhandled Exception** (10%)

## Quick Diagnosis

### Check Gateway Logs
```bash
kubectl logs -f deployment/api-gateway --all-containers=true
# Look for: Connection timeout, 502, 503
```

### Check Error Rate
```bash
# Query Prometheus
rate(http_requests_total{status="500"}[5m])
```

### Check Dependencies
1. Database connectivity: `nc -zv db-primary 3306`
2. Cache connectivity: `redis-cli -h cache ping`
3. Downstream APIs: Check status dashboard

## Specific Error Fixes

### 1. Database Timeout
```yaml
# Increase connection pool timeout in config
database:
  connection_timeout: 30  # seconds
  max_pool_size: 100
```

### 2. Memory Exhaustion
```bash
# Check memory usage
kubectl top pod <pod-name>

# If high, restart pod
kubectl delete pod <pod-name>
```

### 3. Downstream Service Timeout
```bash
# Reduce timeout, enable circuit breaker
timeout: 5000ms
circuit_breaker:
  enabled: true
  failure_threshold: 50  # percent
```

## Prevention

1. Set appropriate timeouts on all dependencies
2. Implement circuit breakers
3. Use connection pooling
4. Monitor error rates continuously
"""
    },
    {
      "id": 5,
      "article_id": "KB-20260901-005",
      "title": "SLA Definition and Breach Escalation Policy",
      "category": "Reference",
      "tags": ["sla", "escalation", "policy", "response-time"],
      "service_affinity": ["All"],
      "author": "david_kumar",
      "created_at": "2026-06-01T10:00:00Z",
      "updated_at": "2026-09-01T13:00:00Z",
      "is_published": true,
      "content": """
# SLA Definition and Breach Escalation

## Standard SLAs by Priority

| Priority | Response Time | Resolution Time | Escalation |
|----------|---------------|-----------------|------------|
| Critical | 15 min | 4 hours | L2→L3→Mgr |
| High | 1 hour | 8 hours | L2→L3 |
| Medium | 4 hours | 24 hours | L2 only |
| Low | 8 hours | 48 hours | None |

## Response Time Definition
- First response = documented understanding of issue
- Auto-responses DO NOT count
- Must include findings, not just "acknowledged"

## Resolution Time Definition
- Time from ticket creation to marked "resolved"
- Waiting for customer input: Timer pauses
- SLA resets if priority increases mid-ticket
- Rollback to previous state = not resolved

## Breach Escalation Timeline

**At 60% of threshold**: Send team lead Slack notification
**At 75%**: Page L3 engineer if not yet assigned
**At 90%**: Notify manager + team lead
**At breach**: Notify VP + create postmortem ticket

## Prevention Checklist

- [ ] Update ticket status every 30 minutes
- [ ] Add notes documenting investigation
- [ ] Escalate to L3 immediately if unsure
- [ ] Set reminder alarms at 50% threshold
- [ ] Test response procedures monthly

## Post-Breach Actions

1. Create postmortem ticket
2. Document root cause
3. Update runbooks
4. Schedule team training
5. Adjust monitoring/alerting
"""
    },
    {
      "id": 6,
      "article_id": "KB-20260901-006",
      "title": "Network Latency and Packet Loss Investigation",
      "category": "Troubleshooting",
      "tags": ["network", "latency", "packet-loss", "diagnostics", "wan"],
      "service_affinity": ["Network-Core"],
      "author": "carol_lee",
      "created_at": "2026-08-05T11:00:00Z",
      "updated_at": "2026-09-01T16:30:00Z",
      "is_published": true,
      "content": """
# Network Latency and Packet Loss Investigation

## Quick Diagnostics

### Check Latency
```bash
ping -c 10 <host>
# Look at min/avg/max/stddev

mtr -c 100 <destination>
# Shows hop-by-hop latency
```

### Check Packet Loss
```bash
ping -c 1000 <destination> | grep loss
# Acceptable: < 0.1%
# Warning: 0.1 - 1.0%
# Critical: > 1.0%
```

### Check Jitter
```bash
mtr -r -c 100 <destination> | grep Loss%
```

## Common Causes

### 1. High Latency
- **Cause**: Physical distance, slow links
- **Fix**: Use closer data center, upgrade WAN link

### 2. Packet Loss
- **Cause**: Congested link, errors on equipment
- **Fix**: Contact ISP, request diagnostics

### 3. Asymmetric Latency
- **Cause**: Different routes for send/receive
- **Fix**: Work with network team, may be normal

## WAN Link Testing

```bash
# Test throughput
iperf -s -p 5001  # Server

iperf -c <server> -p 5001 -t 60  # Client

# Expected for 10Mbps link: 10 Mbps
# If lower: Link is congested or degraded
```

## Impact on Services

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Database replication lag | WAN latency | Increase buffer sizes |
| API timeouts | Packet loss | Contact ISP |
| Cache misses | High latency | Pre-warm cache |
| Video buffering | Insufficient bandwidth | Upgrade circuit |

## Prevention

- Monitor latency continuously
- Alert on > 100ms baseline increase
- Test failover links monthly
- Keep ISP emergency contact handy
"""
    },
    {
      "id": 7,
      "article_id": "KB-20260901-007",
      "title": "TLS Certificate Renewal Process",
      "category": "Procedures",
      "tags": ["certificate", "tls", "ssl", "security", "renewal"],
      "service_affinity": ["Security-Gateway"],
      "author": "frank_wilson",
      "created_at": "2026-07-25T10:00:00Z",
      "updated_at": "2026-09-01T14:00:00Z",
      "is_published": true,
      "content": """
# TLS Certificate Renewal Process

## Timeline
- **14 days before expiry**: Alert goes out
- **7 days before**: Escalate to Frank
- **3 days before**: Final warning
- **At expiry**: Site will show SSL warning

## Renewal Steps

### 1. Request New Certificate
```bash
# Generate CSR
openssl req -new -key /etc/ssl/private/islm.key -out /etc/ssl/islm.csr

# Send CSR to CA
# Provide DNS names: *.islm.local, islm.local
```

### 2. Validate Domain
- Respond to CA verification email
- Or update DNS TXT record with challenge
- Or upload validation file to /.well-known/

### 3. Receive Certificate
- CA sends chain of certificates
- Download and save securely

### 4. Install Certificate
```bash
# Install on load balancer
sudo cp /path/to/cert /etc/ssl/certs/islm.crt
sudo cp /path/to/key /etc/ssl/private/islm.key

# Restart service
sudo systemctl restart nginx
```

### 5. Verify Installation
```bash
openssl s_client -connect islm.local:443
# Check: Verify return code should be 0
```

## Automation (For Next Year)
```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Enable auto-renewal
certbot renew --dry-run  # Test
crontab -e  # Add: 0 0 1 * * /usr/bin/certbot renew --quiet
```

## Emergency (Certificate Expires Today)
1. Generate self-signed cert (30 minutes downtime max)
2. Notify users
3. Request expedited certificate from CA
4. Install permanent cert when ready
"""
    },
    {
      "id": 8,
      "article_id": "KB-20260901-008",
      "title": "Memory Leak Detection and Remediation",
      "category": "Troubleshooting",
      "tags": ["memory", "leak", "performance", "debugging", "worker"],
      "service_affinity": ["API-Gateway"],
      "author": "eve_martinez",
      "created_at": "2026-08-12T15:00:00Z",
      "updated_at": "2026-09-01T12:00:00Z",
      "is_published": true,
      "content": """
# Memory Leak Detection and Remediation

## Identifying Memory Leaks

### Watch Memory Growth
```bash
watch -n 1 'ps aux | grep worker'
# RSS column should stabilize, not grow constantly
```

### Acceptable vs Problem
- **Acceptable**: Grows 5-10MB then stable
- **Problem**: Grows 50MB+ per day continuously

## Root Cause Analysis

### 1. Check Code for Common Leaks
- Global variables holding references
- Circular references not garbage collected
- Event listeners not cleaned up
- Timers not canceled

### 2. Use Memory Profiler
```python
import tracemalloc
tracemalloc.start()
# ... run code ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

### 3. Monitor with Grafana
- Chart: `process_resident_memory_bytes`
- Alert if slope > 50MB/hour

## Quick Fixes

### 1. Restart the Service
```bash
systemctl restart api-gateway-worker
```
This immediately reclaims memory. Use as temporary fix while investigating root cause.

### 2. Increase Memory Limit
```yaml
# Kubernetes
resources:
  limits:
    memory: 512Mi  # Increase from 256Mi
```
Buys time while proper fix is implemented.

### 3. Implement Memory Limits
```python
# Python: Set max memory
import resource
resource.setrlimit(resource.RLIMIT_AS, (500*1024*1024, 500*1024*1024))
```

## Permanent Fix

1. **Identify the leak** (use tracemalloc)
2. **Fix the code** (release references)
3. **Deploy new version**
4. **Monitor for 24 hours** to confirm stable
5. **Document in postmortem**
"""
    },
    {
      "id": 9,
      "article_id": "KB-20260901-009",
      "title": "On-Call Engineer Handoff Checklist",
      "category": "Procedures",
      "tags": ["oncall", "handoff", "checklist", "procedure"],
      "service_affinity": ["All"],
      "author": "david_kumar",
      "created_at": "2026-07-01T09:00:00Z",
      "updated_at": "2026-09-01T09:00:00Z",
      "is_published": true,
      "content": """
# On-Call Engineer Handoff Checklist

## Pre-Shift (15 min before)
- [ ] Review on-call runbooks
- [ ] Check current alert status (should be quiet)
- [ ] Verify phone/messaging setup working
- [ ] Update Slack status: "On-call: <domain>"
- [ ] Test escalation chain (call each number)
- [ ] Set alarm sound to maximum
- [ ] Verify VPN access active

## Shift Start (Change of Watch)
- [ ] Receive handoff from previous on-call
- [ ] Review any ongoing incidents
- [ ] Check dashboard for anomalies (Grafana)
- [ ] Confirm alarm volume adequate
- [ ] Set personal reminder for end of shift
- [ ] Record in shared on-call log

## During Shift
- [ ] Respond to alerts within 5 minutes
- [ ] Update ticket status every 30 minutes
- [ ] If unsure: Escalate to L3 (don't guess)
- [ ] Document troubleshooting steps in real-time
- [ ] Set phone to "Do Not Disturb" for on-call override
- [ ] Keep chat open, notifications enabled

## End of Shift
- [ ] Handoff to next engineer
- [ ] Summarize ongoing incidents
- [ ] Provide link to all related tickets
- [ ] Answer questions from incoming engineer
- [ ] Update Slack status back to available

## Handoff Template
```
[ACTIVE] TKT-123: Database CPU
  Status: Investigating slow queries
  Owner: bob@islm.local
  ETA resolution: 2 hours
  Runbook: /docs/database-high-cpu

[MONITORING] API errors trending up
  Current rate: 2% (baseline 0.1%)
  Action: Check recent deployments

[COMPLETED] TKT-120: Certificate renewed
  Fixed 2 hours ago
  Monitoring for 48 hours
```
"""
    },
    {
      "id": 10,
      "article_id": "KB-20260901-010",
      "title": "Incident Classification Guide",
      "category": "Reference",
      "tags": ["classification", "categories", "incident-types"],
      "service_affinity": ["All"],
      "author": "alice_johnson",
      "created_at": "2026-06-15T13:00:00Z",
      "updated_at": "2026-09-01T10:00:00Z",
      "is_published": true,
      "content": """
# Incident Classification Guide

## Categories and Examples

### DATABASE
- High CPU on primary
- Replication lag > 1 minute
- Disk space critical
- Connection pool exhausted
- Deadlock detected
- **Response Time Target**: 15 min
- **Resolution Target**: 4 hours

### NETWORK
- Packet loss > 1%
- BGP route flapping
- DDoS attack in progress
- DNS resolution slow
- Load balancer failover
- **Response Time Target**: 15 min
- **Resolution Target**: 2 hours

### APPLICATION
- Exception rate spike
- Memory leak detected
- Timeout in batch job
- Deadletter queue growing
- Null pointer exceptions
- **Response Time Target**: 15 min
- **Resolution Target**: 4 hours

### INFRASTRUCTURE
- Node down
- Disk space critical
- CPU exhausted
- Network card failed
- Power supply issue
- **Response Time Target**: 15 min
- **Resolution Target**: 2 hours

### CACHE
- Master failover
- Hit rate drop
- Memory exhaustion
- Connection timeout
- Data corruption
- **Response Time Target**: 15 min
- **Resolution Target**: 4 hours

### SECURITY
- Certificate expiring
- SSL/TLS error
- Unauthorized access attempt
- DDoS attack
- Malware detected
- **Response Time Target**: 15 min
- **Resolution Target**: 1 hour

## Confidence Scoring

- **High (0.9-1.0)**: Multiple keywords match, clear pattern
- **Medium (0.7-0.8)**: Partial match, some ambiguity
- **Low (0.5-0.6)**: Vague description, multiple categories possible

## When Unsure
1. Ask for more details (logs, affected services)
2. Assign to most likely category with medium confidence
3. Mark for manual review
4. Escalate to team lead if critical
"""
    }
  ]
}
```

---

## 6. SQL SCHEMA (For Reference)

```sql
-- Users Table
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  full_name VARCHAR(100),
  role VARCHAR(20),
  department VARCHAR(50),
  phone VARCHAR(20),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE
);

-- Services Table
CREATE TABLE services (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  service_name VARCHAR(100) UNIQUE NOT NULL,
  description TEXT,
  category VARCHAR(50),
  owner_id INTEGER,
  status VARCHAR(20),
  health_status VARCHAR(20),
  sla_response_time INTEGER,
  sla_resolution_time INTEGER,
  critical BOOLEAN,
  location VARCHAR(50),
  contact_email VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(owner_id) REFERENCES users(id)
);

-- Incidents Table
CREATE TABLE incidents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  incident_id VARCHAR(50) UNIQUE NOT NULL,
  source VARCHAR(50),
  title VARCHAR(255),
  description TEXT,
  severity VARCHAR(20),
  affected_service VARCHAR(100),
  affected_component VARCHAR(100),
  status VARCHAR(20),
  detected_at TIMESTAMP,
  acknowledged_at TIMESTAMP,
  resolved_at TIMESTAMP,
  mttr_minutes INTEGER,
  tags TEXT,
  assigned_to VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tickets Table
CREATE TABLE tickets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id VARCHAR(50) UNIQUE NOT NULL,
  title VARCHAR(255),
  description TEXT,
  category VARCHAR(50),
  priority VARCHAR(20),
  status VARCHAR(20),
  related_incidents TEXT,
  assigned_to VARCHAR(50),
  created_by VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP,
  resolved_at TIMESTAMP,
  sla_response_minutes INTEGER,
  sla_resolution_minutes INTEGER
);

-- KB Articles Table
CREATE TABLE kb_articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  article_id VARCHAR(50) UNIQUE NOT NULL,
  title VARCHAR(255),
  content TEXT,
  category VARCHAR(50),
  tags TEXT,
  service_affinity TEXT,
  author VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP,
  is_published BOOLEAN DEFAULT TRUE
);

-- Sessions Table
CREATE TABLE sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id VARCHAR(50) UNIQUE NOT NULL,
  user_id INTEGER,
  context VARCHAR(50),
  message_count INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

-- Audit Trail Table
CREATE TABLE audit_trail (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  audit_id VARCHAR(50) UNIQUE NOT NULL,
  entity_type VARCHAR(50),
  entity_id INTEGER,
  action VARCHAR(50),
  changed_by VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Performance
CREATE INDEX idx_incidents_service ON incidents(affected_service);
CREATE INDEX idx_incidents_status_severity ON incidents(status, severity);
CREATE INDEX idx_tickets_status_priority ON tickets(status, priority);
CREATE INDEX idx_tickets_created ON tickets(created_at);
CREATE INDEX idx_kb_text ON kb_articles(title, content);
```

---

## How to Load This Data

### Option 1: Python Script (Recommended)

```python
import sqlite3
import json
from datetime import datetime

# Connect to database
conn = sqlite3.connect('islm.db')
cursor = conn.cursor()

# Load users
users_data = [...]  # From JSON above
for user in users_data:
    cursor.execute("""
        INSERT INTO users (username, email, full_name, role, department, phone)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user['username'], user['email'], user['full_name'], user['role'], 
          user['department'], user['phone']))

conn.commit()
conn.close()
```

### Option 2: Direct SQL Import

```bash
# Save schema as schema.sql
# Save data as insert_data.sql
sqlite3 islm.db < schema.sql
sqlite3 islm.db < insert_data.sql
```

---

## Summary

**Total Dataset**:
- **8 users** (IT team members)
- **8 services** (core infrastructure)
- **8 incidents** (real-world scenarios)
- **8 tickets** (support tickets)
- **10 KB articles** (runbooks and guides)

**Realistic scenarios covered**:
- ✓ Database failover, replication lag, high CPU
- ✓ API errors, timeouts, memory leaks
- ✓ Network issues, packet loss, latency
- ✓ Cache failures, disk space issues
- ✓ Certificate management, security
- ✓ SLA tracking, escalation procedures

This dataset allows you to test the full SLM workflow with realistic ITSM data.
