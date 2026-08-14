"""Tool: Query Kubernetes cluster (read-only)."""

from typing import Any, Optional

from app.agent.tools.base import BaseTool


class QueryK8sTool(BaseTool):
    """Query Kubernetes cluster state (pods, logs, events, metrics)."""

    name = "query_k8s"
    description = (
        "Query the Kubernetes cluster for real-time state. Use this to check pod status, "
        "view logs, list events, or get resource usage. This is a read-only tool — "
        "it cannot modify cluster state."
    )
    schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["get_pods", "get_logs", "get_events", "describe_pod", "top_pods"],
                "description": "What to query",
            },
            "namespace": {
                "type": "string",
                "description": "Kubernetes namespace (default: all)",
            },
            "pod_name": {
                "type": "string",
                "description": "Pod name (required for logs, describe)",
            },
            "container": {
                "type": "string",
                "description": "Container name (optional, for multi-container pods)",
            },
            "label_selector": {
                "type": "string",
                "description": "Label selector for filtering pods (e.g., 'app=payments-api')",
            },
            "since_seconds": {
                "type": "integer",
                "description": "How far back to fetch logs (default 3600)",
                "default": 3600,
            },
        },
        "required": ["action"],
    }

    def __init__(self, kubeconfig: str | None = None):
        self.kubeconfig = kubeconfig
        self._client = None

    async def execute(
        self,
        action: str,
        namespace: str | None = None,
        pod_name: str | None = None,
        container: str | None = None,
        label_selector: str | None = None,
        since_seconds: int = 3600,
    ) -> dict[str, Any]:
        """Execute Kubernetes query."""
        # This is a mock implementation for demo purposes
        # In production, integrate with kubernetes.client.CoreV1Api

        if action == "get_pods":
            return self._mock_get_pods(namespace, label_selector)
        elif action == "get_logs":
            return self._mock_get_logs(pod_name, namespace, container, since_seconds)
        elif action == "get_events":
            return self._mock_get_events(namespace)
        elif action == "describe_pod":
            return self._mock_describe_pod(pod_name, namespace)
        elif action == "top_pods":
            return self._mock_top_pods(namespace)
        else:
            return {"error": f"Unknown action: {action}"}

    def _mock_get_pods(self, namespace: str | None, label_selector: str | None) -> dict[str, Any]:
        """Mock pod listing."""
        return {
            "pods": [
                {
                    "name": "payments-api-7b5c8f9d-xz2m4",
                    "namespace": "payments",
                    "status": "Running",
                    "ready": "2/2",
                    "restarts": 0,
                    "age": "5d",
                    "labels": {"app": "payments-api", "version": "v1.2.3"},
                },
                {
                    "name": "payments-api-7b5c8f9d-k9p21",
                    "namespace": "payments",
                    "status": "CrashLoopBackOff",
                    "ready": "0/2",
                    "restarts": 12,
                    "age": "1h",
                    "labels": {"app": "payments-api", "version": "v1.2.3"},
                },
                {
                    "name": "inventory-service-6d4f8b9c-m7q32",
                    "namespace": "inventory",
                    "status": "Running",
                    "ready": "1/1",
                    "restarts": 0,
                    "age": "3d",
                    "labels": {"app": "inventory-service", "version": "v2.1.0"},
                },
            ],
            "note": "This is mock data. Configure real kubeconfig for production.",
        }

    def _mock_get_logs(
        self, pod_name: str, namespace: str, container: str | None, since_seconds: int
    ) -> dict[str, Any]:
        """Mock pod logs."""
        return {
            "pod": pod_name,
            "namespace": namespace,
            "container": container,
            "logs": f"""2026-08-13 10:23:45 ERROR Failed to connect to database: connection refused
2026-08-13 10:23:46 WARN Retrying in 5 seconds...
2026-08-13 10:23:51 ERROR Failed to connect to database: connection refused
2026-08-13 10:23:56 ERROR Max retries exceeded, exiting
2026-08-13 10:24:01 INFO Starting application v1.2.3
2026-08-13 10:24:02 ERROR Failed to connect to database: connection refused""",
            "note": "This is mock data. Configure real kubeconfig for production.",
        }

    def _mock_get_events(self, namespace: str | None) -> dict[str, Any]:
        """Mock events."""
        return {
            "events": [
                {
                    "type": "Warning",
                    "reason": "BackOff",
                    "object": "pod/payments-api-7b5c8f9d-k9p21",
                    "message": "Back-off restarting failed container",
                    "age": "5m",
                    "count": 12,
                },
                {
                    "type": "Normal",
                    "reason": "Pulled",
                    "object": "pod/payments-api-7b5c8f9d-xz2m4",
                    "message": "Successfully pulled image",
                    "age": "5d",
                    "count": 1,
                },
            ],
            "note": "This is mock data. Configure real kubeconfig for production.",
        }

    def _mock_describe_pod(self, pod_name: str, namespace: str | None) -> dict[str, Any]:
        """Mock pod describe."""
        return {
            "pod": pod_name,
            "namespace": namespace,
            "details": f"""Name: {pod_name}
Namespace: {namespace}
Status: CrashLoopBackOff
Containers:
  app:
    Image: payments-api:v1.2.3
    State: Waiting
    Reason: CrashLoopBackOff
    Last State: Terminated
    Exit Code: 1
    Ready: False
    Restart Count: 12
Events:
  Type     Reason     Age   From               Message
  ----     ------     ----  ----               -------
  Warning  BackOff    5m    kubelet            Back-off restarting failed container
  Normal   Pulled     5d    kubelet            Successfully pulled image""",
            "note": "This is mock data. Configure real kubeconfig for production.",
        }

    def _mock_top_pods(self, namespace: str | None) -> dict[str, Any]:
        """Mock top pods (resource usage)."""
        return {
            "pods": [
                {"name": "payments-api-7b5c8f9d-xz2m4", "cpu": "120m", "memory": "256Mi"},
                {"name": "payments-api-7b5c8f9d-k9p21", "cpu": "5m", "memory": "12Mi"},
                {"name": "inventory-service-6d4f8b9c-m7q32", "cpu": "80m", "memory": "128Mi"},
            ],
            "note": "This is mock data. Configure real kubeconfig for production.",
        }