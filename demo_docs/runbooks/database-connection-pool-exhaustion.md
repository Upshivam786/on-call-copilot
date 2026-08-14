---
title: Database Connection Pool Exhaustion
type: runbook
team: platform
service: postgresql
severity: critical
---

# Runbook: Database Connection Pool Exhaustion

## Alert Definition
- **Alert Name**: `PostgreSQLConnectionPoolExhausted`
- **Threshold**: Active connections > 90% of max_connections
- **Severity**: Critical

## Symptoms
- Application logs show "connection refused" or "too many connections"
- Query latency spikes
- Multiple services affected simultaneously

## Initial Assessment (2 min)
1. Check current connections: `SELECT count(*) FROM pg_stat_activity;`
2. Check max_connections: `SHOW max_connections;`
3. Identify top consumers: `SELECT application_name, count(*) FROM pg_stat_activity GROUP BY 1 ORDER BY 2 DESC;`

## Common Causes

### 1. Missing Connection Pooling (Most Common)
Applications connecting directly without PgBouncer.

**Resolution:**
```bash
# Deploy PgBouncer if not present
kubectl apply -f pgbouncer-deployment.yaml

# Update app connection strings to use PgBouncer
kubectl set env deployment/payments-api DB_HOST=pgbouncer
```

### 2. Connection Leak in Application
**Symptoms:**
- Connection count grows steadily over time
- `idle in transaction` queries accumulating

**Resolution:**
```bash
# Find leaked connections
SELECT pid, application_name, state, query_start
FROM pg_stat_activity
WHERE state = 'idle in transaction'
AND query_start < now() - interval '5 minutes';

# Terminate leaked connections
SELECT pg_terminate_backend(pid) FROM ...;
```

### 3. Sudden Traffic Spike
**Resolution:**
- Temporarily increase `max_connections` (requires restart)
- Scale PgBouncer pool: `kubectl scale deployment pgbouncer --replicas=5`
- Enable connection timeout: `statement_timeout = '30s'`

## Escalation
- **Immediate**: Page Database on-call
- **If multiple services affected**: Declare SEV-1 incident

## Post-Incident
1. Audit all services for proper connection pooling
2. Add connection monitoring dashboards
3. Set up automated connection leak detection

## References
- [PgBouncer Configuration Guide](https://wiki.internal/db/pgbouncer)
- [Connection Pooling Best Practices](https://wiki.internal/db/pooling)
- Similar incident: INC-2026-0087 (2026-02-20)