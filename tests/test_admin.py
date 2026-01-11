"""Tests for admin endpoints."""
import pytest


class TestCreateBuilding:
    """Tests for POST /admin/buildings."""

    def test_create_building_success(self, client, admin_token):
        """Test successful building creation."""
        response = client.post(
            f"/admin/buildings?admin_token={admin_token}",
            json={"name": "Tower A", "address": "456 Main St"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Tower A"
        assert data["address"] == "456 Main St"
        assert data["is_active"] is True
        assert "api_token" in data
        assert len(data["api_token"]) > 20  # Token should be long enough

    def test_create_building_without_address(self, client, admin_token):
        """Test building creation without optional address."""
        response = client.post(
            f"/admin/buildings?admin_token={admin_token}",
            json={"name": "Tower B"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Tower B"
        assert data["address"] is None

    def test_create_building_invalid_admin_token(self, client):
        """Test building creation with invalid admin token."""
        response = client.post(
            "/admin/buildings?admin_token=wrong-token",
            json={"name": "Tower C"},
        )

        assert response.status_code == 401
        assert "Invalid admin token" in response.json()["detail"]

    def test_create_building_missing_admin_token(self, client):
        """Test building creation without admin token."""
        response = client.post(
            "/admin/buildings",
            json={"name": "Tower D"},
        )

        assert response.status_code == 422  # Missing required parameter

    def test_create_building_missing_name(self, client, admin_token):
        """Test building creation without required name."""
        response = client.post(
            f"/admin/buildings?admin_token={admin_token}",
            json={"address": "123 Street"},
        )

        assert response.status_code == 422


class TestListBuildings:
    """Tests for GET /admin/buildings."""

    def test_list_buildings_empty(self, client, admin_token):
        """Test listing buildings when none exist."""
        response = client.get(f"/admin/buildings?admin_token={admin_token}")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_buildings_with_data(self, client, admin_token):
        """Test listing buildings after creating some."""
        # Create buildings
        client.post(
            f"/admin/buildings?admin_token={admin_token}",
            json={"name": "Building 1"},
        )
        client.post(
            f"/admin/buildings?admin_token={admin_token}",
            json={"name": "Building 2"},
        )

        response = client.get(f"/admin/buildings?admin_token={admin_token}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Building 1"
        assert data[1]["name"] == "Building 2"

    def test_list_buildings_invalid_token(self, client):
        """Test listing buildings with invalid admin token."""
        response = client.get("/admin/buildings?admin_token=wrong")

        assert response.status_code == 401


class TestRegenerateToken:
    """Tests for POST /admin/buildings/{id}/regenerate-token."""

    def test_regenerate_token_success(self, client, admin_token):
        """Test successful token regeneration."""
        # Create a building
        create_response = client.post(
            f"/admin/buildings?admin_token={admin_token}",
            json={"name": "Test Building"},
        )
        building_id = create_response.json()["id"]
        old_token = create_response.json()["api_token"]

        # Regenerate token
        response = client.post(
            f"/admin/buildings/{building_id}/regenerate-token?admin_token={admin_token}"
        )

        assert response.status_code == 200
        new_token = response.json()["api_token"]
        assert new_token != old_token
        assert len(new_token) > 20

    def test_regenerate_token_not_found(self, client, admin_token):
        """Test token regeneration for non-existent building."""
        response = client.post(
            f"/admin/buildings/999/regenerate-token?admin_token={admin_token}"
        )

        assert response.status_code == 404
        assert "Building not found" in response.json()["detail"]
