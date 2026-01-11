"""Tests for access logs endpoints."""
import pytest
from app.models import AccessLog


class TestListAccessLogs:
    """Tests for GET /api/v1/logs."""

    def test_list_logs_empty(self, client, building_headers):
        """Test listing logs when none exist."""
        response = client.get("/api/v1/logs", headers=building_headers)

        assert response.status_code == 200
        assert response.json() == []

    def test_list_logs_with_data(self, client, building_headers, db_session, test_building):
        """Test listing logs with existing data."""
        # Create some logs
        log1 = AccessLog(
            building_id=test_building.id,
            license_plate="LOG001",
            is_authorized=True,
            confidence=95,
        )
        log2 = AccessLog(
            building_id=test_building.id,
            license_plate="LOG002",
            is_authorized=False,
            confidence=80,
        )
        db_session.add_all([log1, log2])
        db_session.commit()

        response = client.get("/api/v1/logs", headers=building_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_logs_ordered_by_date(self, client, building_headers, db_session, test_building):
        """Test that logs are ordered by date descending."""
        import time

        log1 = AccessLog(
            building_id=test_building.id,
            license_plate="FIRST",
            is_authorized=True,
        )
        db_session.add(log1)
        db_session.commit()

        time.sleep(0.1)  # Ensure different timestamps

        log2 = AccessLog(
            building_id=test_building.id,
            license_plate="SECOND",
            is_authorized=True,
        )
        db_session.add(log2)
        db_session.commit()

        response = client.get("/api/v1/logs", headers=building_headers)

        data = response.json()
        assert data[0]["license_plate"] == "SECOND"  # Most recent first
        assert data[1]["license_plate"] == "FIRST"

    def test_list_logs_filter_authorized(self, client, building_headers, db_session, test_building):
        """Test filtering logs by authorization status."""
        log_auth = AccessLog(
            building_id=test_building.id,
            license_plate="AUTH001",
            is_authorized=True,
        )
        log_unauth = AccessLog(
            building_id=test_building.id,
            license_plate="UNAUTH01",
            is_authorized=False,
        )
        db_session.add_all([log_auth, log_unauth])
        db_session.commit()

        # Only authorized
        response = client.get(
            "/api/v1/logs?authorized_only=true",
            headers=building_headers,
        )
        data = response.json()
        assert len(data) == 1
        assert data[0]["license_plate"] == "AUTH001"

        # Only unauthorized
        response = client.get(
            "/api/v1/logs?authorized_only=false",
            headers=building_headers,
        )
        data = response.json()
        assert len(data) == 1
        assert data[0]["license_plate"] == "UNAUTH01"

    def test_list_logs_pagination(self, client, building_headers, db_session, test_building):
        """Test log listing pagination."""
        for i in range(5):
            log = AccessLog(
                building_id=test_building.id,
                license_plate=f"PAGE{i:03d}",
                is_authorized=True,
            )
            db_session.add(log)
        db_session.commit()

        response = client.get(
            "/api/v1/logs?limit=2",
            headers=building_headers,
        )
        assert len(response.json()) == 2

        response = client.get(
            "/api/v1/logs?skip=3",
            headers=building_headers,
        )
        assert len(response.json()) == 2


class TestGetVehicleLogs:
    """Tests for GET /api/v1/logs/{license_plate}."""

    def test_get_vehicle_logs(self, client, building_headers, db_session, test_building):
        """Test getting logs for a specific vehicle."""
        # Create logs for different vehicles
        for _ in range(3):
            log = AccessLog(
                building_id=test_building.id,
                license_plate="TARGET01",
                is_authorized=True,
            )
            db_session.add(log)

        log_other = AccessLog(
            building_id=test_building.id,
            license_plate="OTHER001",
            is_authorized=True,
        )
        db_session.add(log_other)
        db_session.commit()

        response = client.get(
            "/api/v1/logs/TARGET01",
            headers=building_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all(log["license_plate"] == "TARGET01" for log in data)

    def test_get_vehicle_logs_case_insensitive(
        self, client, building_headers, db_session, test_building
    ):
        """Test that plate lookup is case insensitive."""
        log = AccessLog(
            building_id=test_building.id,
            license_plate="UPPER001",
            is_authorized=True,
        )
        db_session.add(log)
        db_session.commit()

        response = client.get(
            "/api/v1/logs/upper001",
            headers=building_headers,
        )

        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_get_vehicle_logs_empty(self, client, building_headers):
        """Test getting logs for vehicle with no history."""
        response = client.get(
            "/api/v1/logs/NOHISTORY",
            headers=building_headers,
        )

        assert response.status_code == 200
        assert response.json() == []


class TestLogIsolation:
    """Tests for multi-tenant log isolation."""

    def test_building_sees_only_own_logs(self, client, admin_token, db_session):
        """Test that buildings can only see their own logs."""
        from app.models import Building, AccessLog

        # Create two buildings
        resp1 = client.post(
            f"/admin/buildings?admin_token={admin_token}",
            json={"name": "Log Building 1"},
        )
        b1_id = resp1.json()["id"]
        b1_token = resp1.json()["api_token"]

        resp2 = client.post(
            f"/admin/buildings?admin_token={admin_token}",
            json={"name": "Log Building 2"},
        )
        b2_id = resp2.json()["id"]
        b2_token = resp2.json()["api_token"]

        # Create logs for each building
        log1 = AccessLog(
            building_id=b1_id,
            license_plate="B1LOG01",
            is_authorized=True,
        )
        log2 = AccessLog(
            building_id=b2_id,
            license_plate="B2LOG01",
            is_authorized=True,
        )
        db_session.add_all([log1, log2])
        db_session.commit()

        # Building 1 sees only its logs
        resp = client.get("/api/v1/logs", headers={"X-API-Key": b1_token})
        logs = resp.json()
        assert len(logs) == 1
        assert logs[0]["license_plate"] == "B1LOG01"

        # Building 2 sees only its logs
        resp = client.get("/api/v1/logs", headers={"X-API-Key": b2_token})
        logs = resp.json()
        assert len(logs) == 1
        assert logs[0]["license_plate"] == "B2LOG01"
