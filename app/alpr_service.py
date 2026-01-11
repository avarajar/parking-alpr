import base64
import io
import re
import logging
from dataclasses import dataclass
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class PlateResult:
    """Result of license plate recognition."""
    text: str | None
    confidence: int | None
    success: bool
    error: str | None = None


class ALPRService:
    """Service for Automatic License Plate Recognition."""

    def __init__(self):
        self._alpr = None
        self._initialized = False

    def _initialize(self):
        """Lazy initialization of ALPR model."""
        if self._initialized:
            return

        try:
            from fast_alpr import ALPR
            self._alpr = ALPR(
                detector_model="yolo-v9-t-384-license-plate-end2end",
                ocr_model="global-plates-mobile-vit-v2-model"
            )
            self._initialized = True
            logger.info("ALPR service initialized successfully")
        except ImportError:
            logger.warning("fast-alpr not installed, using mock mode")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize ALPR: {e}")
            raise

    def _normalize_plate(self, text: str) -> str:
        """Normalize license plate text by removing spaces and special characters."""
        if not text:
            return ""
        # Remove spaces, dashes, dots and convert to uppercase
        normalized = re.sub(r"[\s\-\.]", "", text.upper())
        # Keep only alphanumeric characters
        normalized = re.sub(r"[^A-Z0-9]", "", normalized)
        return normalized

    def recognize_from_base64(self, image_base64: str) -> PlateResult:
        """Recognize license plate from base64 encoded image."""
        self._initialize()

        try:
            # Decode base64 image
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data))

            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")

            return self._recognize_image(image)

        except Exception as e:
            logger.error(f"Error processing base64 image: {e}")
            return PlateResult(
                text=None,
                confidence=None,
                success=False,
                error=str(e)
            )

    def recognize_from_file(self, file_path: str) -> PlateResult:
        """Recognize license plate from file path."""
        self._initialize()

        try:
            image = Image.open(file_path)
            if image.mode != "RGB":
                image = image.convert("RGB")

            return self._recognize_image(image)

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return PlateResult(
                text=None,
                confidence=None,
                success=False,
                error=str(e)
            )

    def _recognize_image(self, image: Image.Image) -> PlateResult:
        """Internal method to recognize plate from PIL Image."""
        import numpy as np

        if self._alpr is None:
            # Mock mode for testing without fast-alpr
            logger.warning("ALPR not available, returning mock result")
            return PlateResult(
                text=None,
                confidence=None,
                success=False,
                error="ALPR service not available"
            )

        try:
            # Convert PIL Image to numpy array
            image_array = np.array(image)

            # Run ALPR prediction
            results = self._alpr.predict(image_array)

            if not results:
                return PlateResult(
                    text=None,
                    confidence=None,
                    success=True,
                    error="No license plate detected in image"
                )

            # Get the first (best) result
            best_result = results[0]
            plate_text = self._normalize_plate(best_result.ocr.text)

            # Calculate confidence as percentage
            confidence = int(best_result.ocr.confidence * 100)

            return PlateResult(
                text=plate_text,
                confidence=confidence,
                success=True
            )

        except Exception as e:
            logger.error(f"Error during ALPR recognition: {e}")
            return PlateResult(
                text=None,
                confidence=None,
                success=False,
                error=str(e)
            )


# Singleton instance
alpr_service = ALPRService()
