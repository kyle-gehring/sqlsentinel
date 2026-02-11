"""Tests for the HTTP health/metrics server."""

import json
from http.client import HTTPConnection
from unittest.mock import MagicMock, Mock

import pytest
from sqlsentinel.server import HealthHandler, start_health_server


@pytest.fixture()
def mock_scheduler():
    """Create a mock scheduler service."""
    scheduler = Mock()
    scheduler.scheduler = Mock()
    scheduler.scheduler.running = True
    scheduler.scheduler.get_jobs.return_value = [Mock(), Mock()]
    return scheduler


@pytest.fixture()
def mock_engine():
    """Create a mock SQLAlchemy engine."""
    engine = Mock()
    mock_conn = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_conn
    mock_context.__exit__.return_value = None
    engine.connect.return_value = mock_context
    return engine


@pytest.fixture()
def server(mock_scheduler, mock_engine):
    """Start a test HTTP server and yield the connection info."""
    srv = start_health_server(
        port=0,  # OS picks a free port
        scheduler_service=mock_scheduler,
        state_engine=mock_engine,
    )
    host, port = srv.server_address
    yield srv, host, port
    srv.shutdown()


def _get(host, port, path):
    """Helper to make a GET request and return (status, body)."""
    conn = HTTPConnection(host, port, timeout=5)
    conn.request("GET", path)
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    status = resp.status
    conn.close()
    return status, body


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_200_when_healthy(self, server):
        srv, host, port = server
        status, body = _get(host, port, "/health")
        assert status == 200
        data = json.loads(body)
        assert data["status"] == "healthy"

    def test_health_returns_503_when_scheduler_stopped(self, server, mock_scheduler):
        srv, host, port = server
        mock_scheduler.scheduler.running = False
        status, body = _get(host, port, "/health")
        assert status == 503
        data = json.loads(body)
        assert data["status"] == "unhealthy"

    def test_health_returns_503_when_no_scheduler(self, server):
        srv, host, port = server
        HealthHandler.scheduler_service = None
        status, body = _get(host, port, "/health")
        assert status == 503


class TestReadyEndpoint:
    """Tests for GET /ready."""

    def test_ready_returns_200_when_all_healthy(self, server):
        srv, host, port = server
        status, body = _get(host, port, "/ready")
        assert status == 200
        data = json.loads(body)
        assert data["status"] == "healthy"
        assert "checks" in data

    def test_ready_returns_503_when_scheduler_not_running(self, server, mock_scheduler):
        srv, host, port = server
        mock_scheduler.scheduler.running = False
        status, body = _get(host, port, "/ready")
        assert status == 503
        data = json.loads(body)
        assert data["status"] == "unhealthy"

    def test_ready_returns_503_when_db_fails(self, server, mock_engine):
        srv, host, port = server
        mock_engine.connect.side_effect = Exception("Connection refused")
        status, body = _get(host, port, "/ready")
        assert status == 503

    def test_ready_works_without_state_engine(self, server, mock_scheduler):
        srv, host, port = server
        HealthHandler.state_engine = None
        status, body = _get(host, port, "/ready")
        # Should still work, just no DB check
        data = json.loads(body)
        assert "checks" in data


class TestMetricsEndpoint:
    """Tests for GET /metrics."""

    def test_metrics_returns_200(self, server):
        srv, host, port = server
        status, body = _get(host, port, "/metrics")
        assert status == 200
        # Prometheus text format contains TYPE and HELP lines
        assert "sqlsentinel" in body or "python" in body

    def test_metrics_content_type(self, server):
        srv, host, port = server
        conn = HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/metrics")
        resp = conn.getresponse()
        content_type = resp.getheader("Content-Type")
        assert "text/plain" in content_type
        conn.close()


class TestNotFound:
    """Tests for unknown paths."""

    def test_unknown_path_returns_404(self, server):
        srv, host, port = server
        status, body = _get(host, port, "/unknown")
        assert status == 404
        data = json.loads(body)
        assert data["error"] == "not found"


class TestServerLifecycle:
    """Tests for server start/stop."""

    def test_server_starts_on_free_port(self, mock_scheduler):
        srv = start_health_server(
            port=0,
            scheduler_service=mock_scheduler,
        )
        _, port = srv.server_address
        assert port > 0
        # Confirm it responds
        status, _ = _get("127.0.0.1", port, "/health")
        assert status == 200
        srv.shutdown()

    def test_server_shutdown_is_clean(self, mock_scheduler):
        srv = start_health_server(
            port=0,
            scheduler_service=mock_scheduler,
        )
        _, port = srv.server_address
        srv.shutdown()
        srv.server_close()
        # After shutdown and close, connections should fail
        with pytest.raises(OSError):
            _get("127.0.0.1", port, "/health")
