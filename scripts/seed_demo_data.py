#!/usr/bin/env python
"""Seed database with demo incidents for evaluation."""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import get_session, init_db
from app.models import Incident, Document


# Demo incidents matching the postmortems
DEMO_INCIDENTS = [
    {
        "alert_name": "HighErrorRate_payments-api",
        "severity": "critical",
        "status": "resolved",
        "started_at": datetime(2026, 3, 15, 14, 23),
        "resolved_at": datetime(2026, 3, 15, 15, 10),
        "root_cause": "Database connection pool exhaustion from deployment increasing connections per request without PgBouncer scaling",
        "resolution_steps": "Rolled back deployment; deployed PgBouncer; increased max_connections temporarily",
        "services": ["payments-api", "payments-db"],
        "tags": ["database", "connection-pool", "payments"],
        "raw_payload": {
            "alertname": "HighErrorRate_payments-api",
            "severity": "critical",
            "value": "5.2%",
            "threshold": "2%",
        },
    },
    {
        "alert_name": "PostgreSQLConnectionPoolExhausted",
        "severity": "high",
        "status": "resolved",
        "started_at": datetime(2026, 2, 20, 9, 15),
        "resolved_at": datetime(2026, 2, 20, 9, 38),
        "root_cause": "Connection leak in inventory-service batch job - transactions not committed/rolled back in error paths",
        "resolution_steps": "Terminated leaked connections; restarted inventory-service; deployed transaction fix",
        "services": ["inventory-service", "payments-api", "postgresql"],
        "tags": ["database", "connection-leak", "cascade"],
        "raw_payload": {
            "alertname": "PostgreSQLConnectionPoolExhausted",
            "severity": "high",
            "active_connections": 198,
            "max_connections": 200,
        },
    },
    {
        "alert_name": "PodCrashLoopBackOff",
        "severity": "high",
        "status": "resolved",
        "started_at": datetime(2026, 4, 10, 3, 45),
        "resolved_at": datetime(2026, 4, 10, 4, 12),
        "root_cause": "Missing environment variable DATABASE_URL after config change in Helm values",
        "resolution_steps": "Restored configmap; added env var validation at startup",
        "services": ["inventory-service"],
        "tags": ["kubernetes", "config", "crashloop"],
        "raw_payload": {
            "alertname": "PodCrashLoopBackOff",
            "namespace": "inventory",
            "pod": "inventory-service-6d4f8b9c-m7q32",
        },
    },
    {
        "alert_name": "HighErrorRate_payments-api",
        "severity": "high",
        "status": "resolved",
        "started_at": datetime(2026, 5, 22, 18, 30),
        "resolved_at": datetime(2026, 5, 22, 18, 52),
        "root_cause": "Stripe gateway timeout during provider outage",
        "resolution_steps": "Enabled circuit breaker; routed to backup gateway; Stripe recovered",
        "services": ["payments-api"],
        "tags": ["payments", "third-party", "gateway"],
        "raw_payload": {
            "alertname": "HighErrorRate_payments-api",
            "severity": "high",
            "upstream_error": "stripe_timeout",
        },
    },
    {
        "alert_name": "OOMKilled_payments-api",
        "severity": "medium",
        "status": "resolved",
        "started_at": datetime(2026, 6, 5, 11, 20),
        "resolved_at": datetime(2026, 6, 5, 11, 35),
        "root_cause": "Memory limit too low for new caching feature",
        "resolution_steps": "Increased memory limit; added memory profiling",
        "services": ["payments-api"],
        "tags": ["kubernetes", "oom", "memory"],
        "raw_payload": {
            "alertname": "OOMKilled_payments-api",
            "namespace": "payments",
            "exit_code": 137,
        },
    },
]


async def seed_incidents():
    """Seed demo incidents."""
    async with get_session() as session:
        # Clear existing demo incidents
        await session.execute(
            text("DELETE FROM incidents WHERE raw_payload ? 'alertname'")
        )

        for inc_data in DEMO_INCIDENTS:
            incident = Incident(**inc_data)
            session.add(incident)

        await session.commit()
        print(f"Seeded {len(DEMO_INCIDENTS)} incidents")


async def main():
    print("Initializing database...")
    await init_db()

    print("Seeding demo incidents...")
    await seed_incidents()

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())