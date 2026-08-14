---
title: INC-2026-0142 Payments API Outage
type: postmortem
incident_id: INC-2026-0142
date: 2026-03-15
severity: critical
services: [payments-api, payments-db]
---

# Postmortem: INC-2026-0142 — Payments API Outage

**Date**: 2026-03-15 14:23 UTC
**Duration**: 47 minutes
**Severity**: Critical (SEV-1)
**Impact**: 100% payment failures, ~$2.3M lost transactions

## Summary
A database connection pool exhaustion caused complete outage of the payments-api service. A deployment earlier that day increased per-request database connections without PgBouncer scaling, exhausting PostgreSQL's max_connections.

## Timeline
| Time (UTC) | Event |
|------------|-------|
| 14:23 | Alert `HighErrorRate_payments-api` fires (5xx > 5%) |
| 14:25 | On-call paged, starts investigation |
| 14:31 | Root cause identified: connection pool exhausted |
| 14:35 | Attempted app scale-up (made worse — more connections) |
| 14:42 | Rolled back deployment from 14:10 |
| 14:55 | Service recovered, error rate < 0.1% |
| 15:10 | All-clear, incident closed |

## Root Cause
The 14:10 deployment changed connection handling logic, increasing average connections per request from 1 to 4. Combined with an autoscaling event that tripled pod count, total connections exceeded PostgreSQL max_connections (200). No PgBouncer was deployed in production.

## Impact
- 47 minutes of complete payment failure
- ~$2.3M in lost/abandoned transactions
- 12,000+ failed customer attempts
- SLA breach: 99.95% → 99.2% for the day

## Resolution
1. Rolled back to pre-14:10 deployment
2. Temporarily increased max_connections to 500
3. Deployed PgBouncer as connection proxy
4. Added connection pool monitoring

## Action Items
- [x] Deploy PgBouncer to all database frontends (DONE 2026-03-17)
- [x] Add connection pool alerting (DONE 2026-03-18)
- [ ] Implement connection leak detection (IN PROGRESS)
- [ ] Add load test for connection scaling (DUE 2026-04-01)
- [ ] Review all services for direct DB connections (DUE 2026-04-15)

## Lessons Learned
**What went well:**
- Fast detection via alerting
- Clear runbook for connection issues

**What went wrong:**
- Scale-up made it worse (no understanding of root cause)
- PgBouncer not in production despite known risk

**Where we got lucky:**
- Rollback was clean, no data corruption
- Off-peak hours (14:00 UTC = low US traffic)

## References
- [Payments Architecture](https://wiki.internal/payments/arch)
- [PgBouncer Deployment](https://wiki.internal/db/pgbouncer-deploy)
- Related runbook: Database Connection Pool Exhaustion
