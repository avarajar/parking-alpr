"""Tests for health check endpoint."""


def test_health_check(client):
    """Test that health endpoint returns ok status."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "parking-alpr"}
