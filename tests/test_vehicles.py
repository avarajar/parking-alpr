"""Tests for vehicle management endpoints."""
import pytest


class TestListVehicles:
    """Tests for GET /api/v1/vehicles."""

    def test_list_vehicles_empty(self, client, building_headers):
        """Test listing vehicles when none exist."""
        response = client.get("/api/v1/vehicles", headers=building_headers)

        assert response.status_code == 200
        assert response.json() == []

    def test_list_vehicles_with_data(self, client, building_headers, test_vehicle):
        """Test listing vehicles with existing data."""
        response = client.get("/api/v1/vehicles", headers=building_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["license_plate"] == "ABC123"
        assert data[0]["owner_name"] == "John Doe"

    def test_list_vehicles_without_auth(self, client):
        """Test listing vehicles without authentication."""
        response = client.get("/api/v1/vehicles")

        assert response.status_code == 401

    def test_list_vehicles_invalid_token(self, client):
        """Test listing vehicles with invalid token."""
        response = client.get(
            "/api/v1/vehicles",
            headers={"X-API-Key": "invalid-token"},
        )

        assert response.status_code == 401

    def test_list_vehicles_pagination(self, client, building_headers, db_session, test_building):
        """Test vehicle listing pagination."""
        from app.models import Vehicle

        # Create multiple vehicles
        for i in range(5):
            vehicle = Vehicle(
                building_id=test_building.id,
                license_plate=f"TEST{i:03d}",
                owner_name=f"Owner {i}",
            )
            db_session.add(vehicle)
        db_session.commit()

        # Test limit
        response = client.get(
            "/api/v1/vehicles?limit=3",
            headers=building_headers,
        )
        assert len(response.json()) == 3

        # Test skip
        response = client.get(
            "/api/v1/vehicles?skip=3",
            headers=building_headers,
        )
        assert len(response.json()) == 2

    def test_list_vehicles_active_only(self, client, building_headers, db_session, test_building):
        """Test filtering by active status."""
        from app.models import Vehicle

        # Create active and inactive vehicles
        active = Vehicle(
            building_id=test_building.id,
            license_plate="ACTIVE1",
            owner_name="Active Owner",
            is_active=True,
        )
        inactive = Vehicle(
            building_id=test_building.id,
            license_plate="INACTIVE1",
            owner_name="Inactive Owner",
            is_active=False,
        )
        db_session.add_all([active, inactive])
        db_session.commit()

        # Active only (default)
        response = client.get("/api/v1/vehicles", headers=building_headers)
        assert len(response.json()) == 1
        assert response.json()[0]["license_plate"] == "ACTIVE1"

        # Include inactive
        response = client.get(
            "/api/v1/vehicles?active_only=false",
            headers=building_headers,
        )
        assert len(response.json()) == 2


class TestGetVehicle:
    """Tests for GET /api/v1/vehicles/{license_plate}."""

    def test_get_vehicle_success(self, client, building_headers, test_vehicle):
        """Test getting a specific vehicle."""
        response = client.get(
            "/api/v1/vehicles/ABC123",
            headers=building_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["license_plate"] == "ABC123"
        assert data["owner_name"] == "John Doe"
        assert data["apartment"] == "101A"

    def test_get_vehicle_case_insensitive(self, client, building_headers, test_vehicle):
        """Test that plate lookup is case insensitive."""
        response = client.get(
            "/api/v1/vehicles/abc123",
            headers=building_headers,
        )

        assert response.status_code == 200
        assert response.json()["license_plate"] == "ABC123"

    def test_get_vehicle_not_found(self, client, building_headers):
        """Test getting a non-existent vehicle."""
        response = client.get(
            "/api/v1/vehicles/NOTEXIST",
            headers=building_headers,
        )

        assert response.status_code == 404
        assert "Vehicle not found" in response.json()["detail"]


class TestCreateVehicle:
    """Tests for POST /api/v1/vehicles."""

    def test_create_vehicle_success(self, client, building_headers):
        """Test successful vehicle creation."""
        response = client.post(
            "/api/v1/vehicles",
            headers=building_headers,
            json={
                "license_plate": "XYZ789",
                "owner_name": "Jane Smith",
                "apartment": "202B",
                "phone": "+9876543210",
                "vehicle_type": "motorcycle",
                "vehicle_brand": "Honda",
                "vehicle_color": "red",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["license_plate"] == "XYZ789"
        assert data["owner_name"] == "Jane Smith"
        assert data["is_active"] is True

    def test_create_vehicle_minimal(self, client, building_headers):
        """Test vehicle creation with only required fields."""
        response = client.post(
            "/api/v1/vehicles",
            headers=building_headers,
            json={
                "license_plate": "MIN001",
                "owner_name": "Minimal User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["license_plate"] == "MIN001"
        assert data["apartment"] is None

    def test_create_vehicle_normalizes_plate(self, client, building_headers):
        """Test that license plate is normalized (uppercase, no spaces)."""
        response = client.post(
            "/api/v1/vehicles",
            headers=building_headers,
            json={
                "license_plate": "abc 123",
                "owner_name": "Test User",
            },
        )

        assert response.status_code == 201
        assert response.json()["license_plate"] == "ABC123"

    def test_create_vehicle_duplicate(self, client, building_headers, test_vehicle):
        """Test creating a duplicate vehicle."""
        response = client.post(
            "/api/v1/vehicles",
            headers=building_headers,
            json={
                "license_plate": "ABC123",
                "owner_name": "Another Person",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_create_vehicle_missing_required(self, client, building_headers):
        """Test creating vehicle without required fields."""
        response = client.post(
            "/api/v1/vehicles",
            headers=building_headers,
            json={"license_plate": "TEST123"},  # Missing owner_name
        )

        assert response.status_code == 422


class TestUpdateVehicle:
    """Tests for PUT /api/v1/vehicles/{license_plate}."""

    def test_update_vehicle_success(self, client, building_headers, test_vehicle):
        """Test successful vehicle update."""
        response = client.put(
            "/api/v1/vehicles/ABC123",
            headers=building_headers,
            json={
                "apartment": "303C",
                "phone": "+1111111111",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["apartment"] == "303C"
        assert data["phone"] == "+1111111111"
        # Original data preserved
        assert data["owner_name"] == "John Doe"

    def test_update_vehicle_deactivate(self, client, building_headers, test_vehicle):
        """Test deactivating a vehicle via update."""
        response = client.put(
            "/api/v1/vehicles/ABC123",
            headers=building_headers,
            json={"is_active": False},
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_update_vehicle_not_found(self, client, building_headers):
        """Test updating a non-existent vehicle."""
        response = client.put(
            "/api/v1/vehicles/NOTEXIST",
            headers=building_headers,
            json={"apartment": "999"},
        )

        assert response.status_code == 404


class TestDeleteVehicle:
    """Tests for DELETE /api/v1/vehicles/{license_plate}."""

    def test_delete_vehicle_success(self, client, building_headers, test_vehicle):
        """Test successful vehicle deletion (soft delete)."""
        response = client.delete(
            "/api/v1/vehicles/ABC123",
            headers=building_headers,
        )

        assert response.status_code == 200
        assert "deactivated" in response.json()["message"]

        # Verify it's deactivated (not in active list)
        list_response = client.get("/api/v1/vehicles", headers=building_headers)
        assert len(list_response.json()) == 0

    def test_delete_vehicle_not_found(self, client, building_headers):
        """Test deleting a non-existent vehicle."""
        response = client.delete(
            "/api/v1/vehicles/NOTEXIST",
            headers=building_headers,
        )

        assert response.status_code == 404
