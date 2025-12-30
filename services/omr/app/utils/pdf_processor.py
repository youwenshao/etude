"""PDF processing utilities for converting PDFs to images."""

import logging
from typing import List

import numpy as np
from pdf2image import convert_from_bytes
from PIL import Image

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Handle PDF to image conversion for OMR processing."""

    def __init__(self, dpi: int = 300, max_pages: int = 50):
        self.dpi = dpi
        self.max_pages = max_pages

    def pdf_to_images(self, pdf_bytes: bytes) -> List[np.ndarray]:
        """
        Convert PDF to list of images (one per page).

        Args:
            pdf_bytes: PDF file as bytes

        Returns:
            List of numpy arrays (images)
        """
        logger.info(f"Converting PDF to images at {self.dpi} DPI")

        try:
            # Convert PDF to PIL Images
            pil_images = convert_from_bytes(
                pdf_bytes,
                dpi=self.dpi,
                fmt="png",
                first_page=1,
                last_page=self.max_pages,
            )

            logger.info(f"Converted {len(pil_images)} pages")

            # Convert PIL Images to numpy arrays
            images = []
            for i, pil_img in enumerate(pil_images):
                # Convert to RGB if needed
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")

                # Convert to numpy array
                img_array = np.array(pil_img)
                images.append(img_array)

                logger.debug(f"Page {i + 1} shape: {img_array.shape}")

            return images

        except Exception as e:
            logger.error(f"Failed to convert PDF to images: {e}")
            raise ValueError(f"Invalid or corrupted PDF file: {e}")

    def validate_pdf(self, pdf_bytes: bytes, max_size_mb: int = 50) -> None:
        """
        Validate PDF file before processing.

        Args:
            pdf_bytes: PDF file as bytes
            max_size_mb: Maximum allowed file size in MB

        Raises:
            ValueError if validation fails
        """
        size_mb = len(pdf_bytes) / (1024 * 1024)

        if size_mb > max_size_mb:
            raise ValueError(
                f"PDF file too large: {size_mb:.2f} MB (max: {max_size_mb} MB)"
            )

        # Check if it's actually a PDF
        if not pdf_bytes.startswith(b"%PDF"):
            raise ValueError("Invalid PDF file: missing PDF header")

        logger.info(f"PDF validation passed: {size_mb:.2f} MB")

