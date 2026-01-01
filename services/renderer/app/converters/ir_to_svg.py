"""Convert MusicXML to SVG using Verovio."""

import verovio
from typing import List
import logging

logger = logging.getLogger(__name__)


class IRToSVGConverter:
    """
    Convert MusicXML to SVG using Verovio.

    Verovio takes MusicXML as input, so we first convert to MusicXML,
    then render to SVG.
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        scale: int = 40,
        page_height: int = 2970,
        page_width: int = 2100,
        page_margin: int = 100,
    ):
        self.scale = scale
        self.page_height = page_height
        self.page_width = page_width
        self.page_margin = page_margin

        # Initialize Verovio toolkit
        self.toolkit = verovio.toolkit()

    def convert(self, musicxml_string: str) -> List[str]:
        """
        Convert MusicXML to SVG pages.

        Args:
            musicxml_string: MusicXML as string

        Returns:
            List of SVG strings (one per page)
        """
        logger.info("Converting MusicXML to SVG with Verovio")

        # Configure Verovio
        self.toolkit.setOptions(
            {
                "scale": self.scale,
                "pageHeight": self.page_height,
                "pageWidth": self.page_width,
                "pageMarginTop": self.page_margin,
                "pageMarginBottom": self.page_margin,
                "pageMarginLeft": self.page_margin,
                "pageMarginRight": self.page_margin,
                "adjustPageHeight": True,
                "breaks": "auto",
            }
        )

        # Load MusicXML
        self.toolkit.loadData(musicxml_string)

        # Get number of pages
        page_count = self.toolkit.getPageCount()
        logger.info(f"Rendering {page_count} pages")

        # Render each page to SVG
        svg_pages = []
        for page_num in range(1, page_count + 1):
            svg = self.toolkit.renderToSVG(page_num)
            svg_pages.append(svg)

        logger.info(f"SVG rendering complete: {len(svg_pages)} pages")

        return svg_pages

