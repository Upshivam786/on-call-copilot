---
title: INC-2026-0087 Database Pool Exhaustion Cascade
type: postmortem
incident_id: INC-2026-0087
date: 2026-02-20
severity: high
services: [inventory-service, payments-api, postgresql]
---

# Postmortem: INC-2026-0087 — Database Pool Exhaustion Cascade

**Date**: 2026-02-20 09:15 UTC
**Duration**: 23 minutes
**Severity**: High (SEV-2)
**Impact**: Intermittent failures across 3 services

## Summary
A connection leak in inventory-service gradually consumed all available PostgreSQL connections, causing cascading failures in payments-api and other services sharing the database.

## Timeline
| Time (UTC) | Event |
|------------|-------|
| 09:15 | Alert `PostgreSQLConnectionPoolExhausted` fires |
| 09:18 | On-call paged |
| 09:22 | Identified connection leak in inventory-service |
| 09:28 | Terminated leaked connections, service restarted |
| 09:38 | All services recovered |

## Root Cause
Code path in inventory-service's batch job created transactions but failed to commit/rollback in error cases, leaking connections. Over 6 hours, leaked connections accumulated until pool was exhausted.

## Impact
- 23 minutes of degraded service
- ~$400K estimated lost revenue
- 3 services affected

## Resolution
1. Terminated leaked connections via pg_terminate_backend
2. Restarted inventory-service to clear leaks
3. Deployed fix for transaction handling
4. Added connection leak monitoring

## Action Items
- [x] Fix transaction leak in inventory-service
- [x] Add connection leak detection alert
- [ ] Audit all services for similar patterns (DUE 2026-03-10)
- [ ] Implement automated connection termination for idle-in-transaction (DUE 2026-03-15)

## Lessons Learned
**What went well:**
- Pool exhaustion alert caught it before full outage
- Quick identification of source service

**What went wrong:**
- 6 hour leak window before detection
- No automated leak remediation

**Where we got lucky:**
- Business hours, lower traffic volume

## References
- [Transaction Handling Guide](https://wiki.internal/code/transactions)
- Related runbook: Database Connection Pool Exhaustion
