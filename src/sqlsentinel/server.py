"""Lightweight HTTP server for cloud deployment health checks and metrics."""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health, readiness, and metrics endpoints."""

    # Set by start_health_server() before requests arrive
    scheduler_service: Any = None
    state_engine: Any = None

    def do_GET(self) -> None:  # noqa: N802
        """Route GET requests to the appropriate handler."""
        if self.path == "/health":
            self._handle_health()
        elif self.path == "/ready":
            self._handle_ready()
        elif self.path == "/metrics":
            self._handle_metrics()
        else:
            self._send_json(404, {"error": "not found"})

    def _handle_health(self) -> None:
        """Liveness probe — confirms the process is alive and scheduler is running."""
        scheduler = self.__class__.scheduler_service
        if scheduler and scheduler.scheduler.running:
            self._send_json(200, {"status": "healthy"})
        else:
            self._send_json(503, {"status": "unhealthy", "reason": "scheduler not running"})

    def _handle_ready(self) -> None:
        """Readiness probe — checks scheduler and database connectivity."""
        from .health.checks import check_database, check_scheduler

        checks: dict[str, Any] = {}
        healthy = True

        # Check scheduler
        scheduler = self.__class__.scheduler_service
        result = check_scheduler(scheduler)
        checks["scheduler"] = result
        if result["status"] != "healthy":
            healthy = False

        # Check state database
        engine = self.__class__.state_engine
        if engine is not None:
            result = check_database(engine)
            checks["state_database"] = result
            if result["status"] != "healthy":
                healthy = False

        status_code = 200 if healthy else 503
        self._send_json(
            status_code, {"status": "healthy" if healthy else "unhealthy", "checks": checks}
        )

    def _handle_metrics(self) -> None:
        """Prometheus metrics endpoint."""
        from .metrics import get_metrics

        metrics_text = get_metrics().get_metrics_text()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.end_headers()
        self.wfile.write(metrics_text.encode("utf-8"))

    def _send_json(self, status_code: int, body: dict[str, Any]) -> None:
        """Send a JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default stderr logging; use structured logger instead."""
        logger.debug("HTTP %s", format % args)


def start_health_server(
    port: int,
    scheduler_service: Any,
    state_engine: Any = None,
) -> HTTPServer:
    """Start the health/metrics HTTP server in a daemon thread.

    Args:
        port: Port to listen on (typically $PORT or 8080).
        scheduler_service: SchedulerService instance for health checks.
        state_engine: SQLAlchemy engine for readiness checks.

    Returns:
        The running HTTPServer instance.
    """
    HealthHandler.scheduler_service = scheduler_service
    HealthHandler.state_engine = state_engine

    server = HTTPServer(("0.0.0.0", port), HealthHandler)  # nosec B104
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    logger.info(f"Health server listening on port {port}")
    return server
