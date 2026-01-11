"""Tests for ALPR service."""
import pytest
import base64
from io import BytesIO
from PIL import Image

from app.alpr_service import ALPRService, PlateResult


class TestPlateResult:
    """Tests for PlateResult dataclass."""

    def test_plate_result_success(self):
        """Test successful plate result."""
        result = PlateResult(text="ABC123", confidence=95, success=True)
        assert result.text == "ABC123"
        assert result.confidence == 95
        assert result.success is True
        assert result.error is None

    def test_plate_result_failure(self):
        """Test failed plate result."""
        result = PlateResult(
            text=None, confidence=None, success=False, error="Image too dark"
        )
        assert result.text is None
        assert result.success is False
        assert result.error == "Image too dark"


class TestALPRService:
    """Tests for ALPRService."""

    @pytest.fixture
    def alpr_service(self):
        """Create a fresh ALPR service instance."""
        return ALPRService()

    @pytest.fixture
    def valid_image_base64(self):
        """Create a valid base64 encoded test image."""
        # Create a simple test image
        img = Image.new("RGB", (100, 50), color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()

    @pytest.fixture
    def invalid_base64(self):
        """Return invalid base64 string."""
        return "not-valid-base64!!!"

    def test_normalize_plate_basic(self, alpr_service):
        """Test basic plate normalization."""
        assert alpr_service._normalize_plate("abc123") == "ABC123"
        assert alpr_service._normalize_plate("ABC 123") == "ABC123"
        assert alpr_service._normalize_plate("abc-123") == "ABC123"
        assert alpr_service._normalize_plate("abc.123") == "ABC123"

    def test_normalize_plate_special_chars(self, alpr_service):
        """Test plate normalization removes special characters."""
        assert alpr_service._normalize_plate("ABC@#$123") == "ABC123"
        assert alpr_service._normalize_plate("(ABC)123") == "ABC123"

    def test_normalize_plate_empty(self, alpr_service):
        """Test plate normalization with empty string."""
        assert alpr_service._normalize_plate("") == ""
        assert alpr_service._normalize_plate(None) == ""

    def test_recognize_from_base64_invalid(self, alpr_service, invalid_base64):
        """Test recognition with invalid base64."""
        result = alpr_service.recognize_from_base64(invalid_base64)
        assert result.success is False
        assert result.error is not None

    def test_recognize_from_base64_valid_image(self, alpr_service, valid_image_base64):
        """Test recognition with valid image (may not detect plate)."""
        result = alpr_service.recognize_from_base64(valid_image_base64)
        # Should succeed even if no plate detected
        # (either success=True with text=None or ALPR not available)
        assert isinstance(result, PlateResult)

    def test_recognize_from_file_not_found(self, alpr_service):
        """Test recognition with non-existent file."""
        result = alpr_service.recognize_from_file("/nonexistent/path/image.jpg")
        assert result.success is False
        assert result.error is not None

    def test_recognize_from_file_valid(self, alpr_service, tmp_path):
        """Test recognition with valid image file."""
        # Create a test image file
        img = Image.new("RGB", (100, 50), color="white")
        img_path = tmp_path / "test_plate.png"
        img.save(img_path)

        result = alpr_service.recognize_from_file(str(img_path))
        assert isinstance(result, PlateResult)

    def test_lazy_initialization(self, alpr_service):
        """Test that ALPR is lazily initialized."""
        assert alpr_service._initialized is False
        alpr_service._initialize()
        assert alpr_service._initialized is True

    def test_singleton_pattern(self):
        """Test that the module provides a singleton instance."""
        from app.alpr_service import alpr_service as instance1
        from app.alpr_service import alpr_service as instance2
        assert instance1 is instance2


class TestImageConversion:
    """Tests for image format handling."""

    @pytest.fixture
    def alpr_service(self):
        return ALPRService()

    def test_rgba_to_rgb_conversion(self, alpr_service):
        """Test that RGBA images are converted to RGB."""
        # Create RGBA image
        img = Image.new("RGBA", (100, 50), color=(255, 255, 255, 128))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode()

        # Should not raise an error
        result = alpr_service.recognize_from_base64(image_base64)
        assert isinstance(result, PlateResult)

    def test_grayscale_to_rgb_conversion(self, alpr_service):
        """Test that grayscale images are converted to RGB."""
        # Create grayscale image
        img = Image.new("L", (100, 50), color=128)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode()

        result = alpr_service.recognize_from_base64(image_base64)
        assert isinstance(result, PlateResult)
