"""Tests for plate verification endpoint."""
import pytest
from unittest.mock import patch, MagicMock


class TestVerifyPlate:
    """Tests for POST /api/v1/verify."""

    def test_verify_authorized_vehicle(
        self, client, building_headers, test_vehicle, sample_image_base64
    ):
        """Test verification of an authorized vehicle."""
        # Mock the ALPR service to return the test vehicle's plate
        with patch("app.main.alpr_service") as mock_alpr:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.text = "ABC123"
            mock_result.confidence = 95
            mock_result.error = None
            mock_alpr.recognize_from_base64.return_value = mock_result

            response = client.post(
                "/api/v1/verify",
                headers=building_headers,
                json={"image_base64": sample_image_base64},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["license_plate"] == "ABC123"
        assert data["is_authorized"] is True
        assert data["confidence"] == 95
        assert data["owner_name"] == "John Doe"
        assert data["apartment"] == "101A"
        assert data["message"] == "Vehicle authorized"

    def test_verify_unauthorized_vehicle(
        self, client, building_headers, sample_image_base64
    ):
        """Test verification of an unauthorized vehicle."""
        with patch("app.main.alpr_service") as mock_alpr:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.text = "UNKNOWN1"
            mock_result.confidence = 88
            mock_result.error = None
            mock_alpr.recognize_from_base64.return_value = mock_result

            response = client.post(
                "/api/v1/verify",
                headers=building_headers,
                json={"image_base64": sample_image_base64},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["license_plate"] == "UNKNOWN1"
        assert data["is_authorized"] is False
        assert data["confidence"] == 88
        assert data["owner_name"] is None
        assert "not authorized" in data["message"]

    def test_verify_no_plate_detected(
        self, client, building_headers, sample_image_base64
    ):
        """Test verification when no plate is detected."""
        with patch("app.main.alpr_service") as mock_alpr:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.text = None
            mock_result.confidence = None
            mock_result.error = None
            mock_alpr.recognize_from_base64.return_value = mock_result

            response = client.post(
                "/api/v1/verify",
                headers=building_headers,
                json={"image_base64": sample_image_base64},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["license_plate"] is None
        assert data["is_authorized"] is False
        assert "No license plate detected" in data["message"]

    def test_verify_alpr_failure(self, client, building_headers, sample_image_base64):
        """Test verification when ALPR fails."""
        with patch("app.main.alpr_service") as mock_alpr:
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.text = None
            mock_result.confidence = None
            mock_result.error = "Invalid image format"
            mock_alpr.recognize_from_base64.return_value = mock_result

            response = client.post(
                "/api/v1/verify",
                headers=building_headers,
                json={"image_base64": sample_image_base64},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["is_authorized"] is False
        assert "Failed to read" in data["message"]

    def test_verify_without_auth(self, client, sample_image_base64):
        """Test verification without authentication."""
        response = client.post(
            "/api/v1/verify",
            json={"image_base64": sample_image_base64},
        )

        assert response.status_code == 401

    def test_verify_creates_access_log(
        self, client, building_headers, db_session, test_building, sample_image_base64
    ):
        """Test that verification creates an access log."""
        from app.models import AccessLog

        with patch("app.main.alpr_service") as mock_alpr:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.text = "LOGGED01"
            mock_result.confidence = 90
            mock_result.error = None
            mock_alpr.recognize_from_base64.return_value = mock_result

            client.post(
                "/api/v1/verify",
                headers=building_headers,
                json={"image_base64": sample_image_base64},
            )

        # Check access log was created
        log = db_session.query(AccessLog).filter(
            AccessLog.license_plate == "LOGGED01"
        ).first()
        assert log is not None
        assert log.building_id == test_building.id
        assert log.is_authorized is False
        assert log.confidence == 90

    def test_verify_inactive_vehicle_not_authorized(
        self, client, building_headers, test_vehicle, db_session, sample_image_base64
    ):
        """Test that inactive vehicles are not authorized."""
        # Deactivate the vehicle
        test_vehicle.is_active = False
        db_session.commit()

        with patch("app.main.alpr_service") as mock_alpr:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.text = "ABC123"
            mock_result.confidence = 95
            mock_result.error = None
            mock_alpr.recognize_from_base64.return_value = mock_result

            response = client.post(
                "/api/v1/verify",
                headers=building_headers,
                json={"image_base64": sample_image_base64},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["is_authorized"] is False
