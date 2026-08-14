---
title: Payments API High Error Rate
type: runbook
team: payments
service: payments-api
severity: high
---

# Runbook: Payments API High Error Rate

## Alert Definition
- **Alert Name**: `HighErrorRate_payments-api`
- **Threshold**: 5xx error rate > 2% over 5 minutes
- **Severity**: High

## Symptoms
- Increased 5xx responses from `/api/v1/charge` endpoint
- Elevated p99 latency (>2s)
- Customer complaints about failed payments

## Initial Assessment (5 min)
1. Check Grafana dashboard: **Payments → Error Rates**
2. Verify if error rate spike is global or isolated to one region
3. Check recent deployments: `kubectl rollout history deployment/payments-api -n payments`

## Common Causes

### 1. Database Connection Exhaustion (Most Common)
**Symptoms:**
- Connection pool timeout errors in logs
- `connection refused` or `too many connections`

**Resolution:**
```bash
# Check current connections
kubectl exec -it payments-db-0 -- psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check max_connections
kubectl exec -it payments-db-0 -- psql -c "SHOW max_connections;"

# If exhausted, scale connection pool
kubectl scale deployment payments-api --replicas=3
```

### 2. Third-Party Payment Gateway Timeout
**Symptoms:**
- Errors correlate with `stripe_api_timeout` metrics
- Upstream gateway returning 503

**Resolution:**
- Check Stripe status page
- Enable circuit breaker: `kubectl set env deployment/payments-api CIRCUIT_BREAKER=enabled`
- Switch to backup gateway if available

### 3. Recent Bad Deployment
**Symptoms:**
- Error spike within 10 min of deploy
- Stack traces pointing to new code path

**Resolution:**
```bash
# Rollback to previous version
kubectl rollout undo deployment/payments-api -n payments

# Verify recovery
kubectl rollout status deployment/payments-api -n payments
```

## Escalation
- **After 15 min without resolution**: Page Payments on-call lead
- **After 30 min**: Engage Platform team
- **Customer impact > 1%**: Declare incident, notify Comms

## Post-Incident
1. Create postmortem within 24 hours
2. Add runbook improvements
3. File tickets for preventive measures

## References
- [Payment Gateway SLA](https://wiki.internal/payments/sla)
- [Database Tuning Guide](https://wiki.internal/db/tuning)
- Similar incident: INC-2026-0142 (2026-03-15)
