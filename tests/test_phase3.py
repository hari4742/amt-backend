"""
Tests for Phase 3 API endpoints implementation.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, client: TestClient):
        """Test basic health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert data["status"] == "healthy"

    def test_detailed_health_check(self, client: TestClient):
        """Test detailed health check endpoint."""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "database" in data["components"]
        assert "filesystem" in data["components"]
        assert "configuration" in data["components"]

    def test_readiness_check(self, client: TestClient):
        """Test readiness check endpoint."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_liveness_check(self, client: TestClient):
        """Test liveness check endpoint."""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


class TestUtilityEndpoints:
    """Test utility endpoints."""

    def test_supported_formats(self, client: TestClient):
        """Test supported formats endpoint."""
        response = client.get("/api/formats")
        assert response.status_code == 200
        data = response.json()
        assert "supported_formats" in data
        assert "audio" in data["supported_formats"]
        assert "output" in data["supported_formats"]
        assert "wav" in data["supported_formats"]["audio"]
        assert "mp3" in data["supported_formats"]["audio"]
        assert "midi" in data["supported_formats"]["output"]

    def test_system_info(self, client: TestClient):
        """Test system info endpoint."""
        response = client.get("/api/info")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "system" in data
        assert "resources" in data
        assert "configuration" in data
        assert data["service"]["name"] == "AMT Backend"

    def test_service_stats(self, client: TestClient):
        """Test service stats endpoint."""
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "transcriptions" in data
        assert "storage" in data
        assert "performance" in data

    def test_ping(self, client: TestClient):
        """Test ping endpoint."""
        response = client.get("/api/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "pong"


class TestEnhancedTranscriptionEndpoints:
    """Test enhanced transcription endpoints."""

    def test_list_transcriptions_pagination(self, client: TestClient):
        """Test transcription listing with pagination."""
        response = client.get("/api/transcriptions?page=1&size=5")
        assert response.status_code == 200
        data = response.json()
        assert "transcriptions" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert data["page"] == 1
        assert data["size"] == 5

    def test_download_midi_not_found(self, client: TestClient):
        """Test MIDI download for non-existent transcription."""
        response = client.get("/api/transcribe/non-existent-id/download")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_download_midi_not_completed(self, client: TestClient):
        """Test MIDI download for incomplete transcription."""
        # This would require a transcription in pending/processing state
        # For now, just test the endpoint structure
        pass


class TestMiddleware:
    """Test middleware functionality."""

    def test_rate_limit_headers(self, client: TestClient):
        """Test that rate limit headers are present."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    def test_process_time_header(self, client: TestClient):
        """Test that process time header is present."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers

    def test_security_headers(self, client: TestClient):
        """Test that security headers are present."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers

    def test_cors_headers(self, client: TestClient):
        """Test that CORS headers are present."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers


class TestErrorHandling:
    """Test error handling."""

    def test_404_error(self, client: TestClient):
        """Test 404 error handling."""
        response = client.get("/api/non-existent-endpoint")
        assert response.status_code == 404

    def test_422_error(self, client: TestClient):
        """Test 422 error handling for invalid parameters."""
        response = client.get("/api/transcriptions?page=invalid")
        assert response.status_code == 422

    @patch('app.api.v1.endpoints.health.detailed_health_check')
    def test_500_error_handling(self, mock_health_check, client: TestClient):
        """Test 500 error handling."""
        mock_health_check.side_effect = Exception("Test error")
        response = client.get("/health/detailed")
        assert response.status_code == 500
        data = response.json()
        assert "error" in data


if __name__ == "__main__":
    pytest.main([__file__])
