"""Tests for authentication."""
import pytest


class TestBuildingAuthentication:
    """Tests for building API key authentication."""

    def test_missing_api_key(self, client):
        """Test request without API key."""
        response = client.get("/api/v1/vehicles")

        assert response.status_code == 401
        assert "Missing API key" in response.json()["detail"]

    def test_invalid_api_key(self, client):
        """Test request with invalid API key."""
        response = client.get(
            "/api/v1/vehicles",
            headers={"X-API-Key": "invalid-key"},
        )

        assert response.status_code == 401
        assert "Invalid or inactive" in response.json()["detail"]

    def test_valid_api_key(self, client, building_headers):
        """Test request with valid API key."""
        response = client.get("/api/v1/vehicles", headers=building_headers)

        assert response.status_code == 200

    def test_inactive_building(self, client, db_session, test_building):
        """Test that inactive buildings cannot authenticate."""
        # Deactivate the building
        test_building.is_active = False
        db_session.commit()

        response = client.get(
            "/api/v1/vehicles",
            headers={"X-API-Key": test_building.api_token},
        )

        assert response.status_code == 401


class TestBuildingIsolation:
    """Tests for multi-tenant data isolation."""

    def test_building_sees_only_own_vehicles(self, client, db_session, admin_token):
        """Test that buildings can only see their own vehicles."""
        # Create two buildings
        resp1 = client.post(
            f"/admin/buildings?admin_token={admin_token}",
            json={"name": "Building 1"},
        )
        building1_token = resp1.json()["api_token"]

        resp2 = client.post(
            f"/admin/buildings?admin_token={admin_token}",
            json={"name": "Building 2"},
        )
        building2_token = resp2.json()["api_token"]

        # Create vehicle in building 1
        client.post(
            "/api/v1/vehicles",
            headers={"X-API-Key": building1_token},
            json={"license_plate": "BLD1001", "owner_name": "Owner 1"},
        )

        # Create vehicle in building 2
        client.post(
            "/api/v1/vehicles",
            headers={"X-API-Key": building2_token},
            json={"license_plate": "BLD2001", "owner_name": "Owner 2"},
        )

        # Building 1 should only see its vehicle
        resp = client.get(
            "/api/v1/vehicles",
            headers={"X-API-Key": building1_token},
        )
        vehicles = resp.json()
        assert len(vehicles) == 1
        assert vehicles[0]["license_plate"] == "BLD1001"

        # Building 2 should only see its vehicle
        resp = client.get(
            "/api/v1/vehicles",
            headers={"X-API-Key": building2_token},
        )
        vehicles = resp.json()
        assert len(vehicles) == 1
        assert vehicles[0]["license_plate"] == "BLD2001"

    def test_same_plate_different_buildings(self, client, admin_token):
        """Test that same plate can exist in different buildings."""
        # Create two buildings
        resp1 = client.post(
            f"/admin/buildings?admin_token={admin_token}",
            json={"name": "Building A"},
        )
        token_a = resp1.json()["api_token"]

        resp2 = client.post(
            f"/admin/buildings?admin_token={admin_token}",
            json={"name": "Building B"},
        )
        token_b = resp2.json()["api_token"]

        # Same plate in both buildings
        resp1 = client.post(
            "/api/v1/vehicles",
            headers={"X-API-Key": token_a},
            json={"license_plate": "SHARED01", "owner_name": "Owner in A"},
        )
        assert resp1.status_code == 201

        resp2 = client.post(
            "/api/v1/vehicles",
            headers={"X-API-Key": token_b},
            json={"license_plate": "SHARED01", "owner_name": "Owner in B"},
        )
        assert resp2.status_code == 201

    def test_cannot_access_other_building_vehicle(self, client, admin_token):
        """Test that a building cannot access another building's vehicles."""
        # Create building with vehicle
        resp = client.post(
            f"/admin/buildings?admin_token={admin_token}",
            json={"name": "Owner Building"},
        )
        owner_token = resp.json()["api_token"]

        client.post(
            "/api/v1/vehicles",
            headers={"X-API-Key": owner_token},
            json={"license_plate": "PRIVATE1", "owner_name": "Private Owner"},
        )

        # Create another building
        resp = client.post(
            f"/admin/buildings?admin_token={admin_token}",
            json={"name": "Other Building"},
        )
        other_token = resp.json()["api_token"]

        # Other building cannot see the vehicle
        resp = client.get(
            "/api/v1/vehicles/PRIVATE1",
            headers={"X-API-Key": other_token},
        )
        assert resp.status_code == 404
