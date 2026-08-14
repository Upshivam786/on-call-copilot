---
title: Kubernetes Pod CrashLoopBackOff
type: runbook
team: platform
service: kubernetes
severity: high
---

# Runbook: Kubernetes Pod CrashLoopBackOff

## Alert Definition
- **Alert Name**: `PodCrashLoopBackOff`
- **Threshold**: Pod in CrashLoopBackOff state for > 5 min
- **Severity**: High

## Symptoms
- Pod status: `CrashLoopBackOff`
- Restart count increasing
- Service degraded or unavailable

## Initial Assessment (3 min)
1. Check pod status: `kubectl get pods -n <namespace>`
2. View pod details: `kubectl describe pod <pod-name> -n <namespace>`
3. Check logs: `kubectl logs <pod-name> -n <namespace> --previous`

## Common Causes

### 1. Application Startup Failure (Most Common)
**Symptoms:**
- Container exits immediately with error code 1
- Logs show config error or missing dependency

**Resolution:**
```bash
# Check logs for specific error
kubectl logs <pod> --previous | tail -50

# Common fixes:
# - Missing env var: kubectl set env deployment/<name> MISSING_VAR=value
# - Wrong image tag: kubectl set image deployment/<name> <name>=<image>:<correct-tag>
# - ConfigMap missing: kubectl apply -f configmap.yaml
```

### 2. Resource Exhaustion (OOMKilled)
**Symptoms:**
- Container status: `OOMKilled` (exit code 137)
- Memory usage near limit

**Resolution:**
```bash
# Check if OOMKilled
kubectl describe pod <pod> | grep -i "OOMKilled\|Last State"

# Increase memory limit
kubectl set resources deployment/<name> --limits=memory=512Mi
```

### 3. Liveness Probe Failure
**Symptoms:**
- Pod restarts but app is actually healthy
- Probe timeout errors in events

**Resolution:**
```bash
# Check probe config
kubectl get deployment <name> -o jsonpath='{.spec.template.spec.containers[0].livenessProbe}'

# Increase initialDelaySeconds or failureThreshold
kubectl patch deployment <name> --type merge -p '{"spec":{"template":{"spec":{"containers":[{"name":"<name>","livenessProbe":{"initialDelaySeconds":60}}]}}}}'
```

### 4. Dependency Not Ready
**Symptoms:**
- Pod can't connect to database/cache at startup
- Connection refused errors

**Resolution:**
- Add init container to wait for dependencies
- Use `depends_on` in Helm charts
- Implement retry logic in app startup

## Escalation
- **After 15 min**: Page Service owning team
- **If customer-facing**: Declare incident

## Post-Incident
1. Add startup probe to prevent false CrashLoopBackOff
2. Improve health check logic
3. Document root cause

## References
- [K8s Debugging Pods Guide](https://wiki.internal/k8s/debug)
- [Probes Best Practices](https://wiki.internal/k8s/probes)