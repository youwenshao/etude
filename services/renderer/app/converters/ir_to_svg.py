"""Convert MusicXML to SVG using Verovio."""

import verovio
from typing import List
import logging
import re

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

    def _flatten_svg(self, svg: str) -> str:
        """
        Flatten nested SVG to fix viewBox/dimension mismatch from Verovio.
        
        Verovio generates SVGs with nested <svg> elements where the outer SVG
        has small dimensions (e.g., 840x80px) but the inner SVG has a large
        viewBox (e.g., 0 0 21000 2000) combined with translate transforms,
        causing content to render outside the visible area.
        
        This method:
        1. Detects nested <svg class="definition-scale" viewBox="...">
        2. Extracts the inner viewBox
        3. Replaces outer SVG dimensions with viewBox
        4. Removes the nested SVG wrapper, keeping content
        
        Args:
            svg: Raw SVG string from Verovio
            
        Returns:
            Flattened SVG string with proper viewBox
        """
        if not svg or not svg.strip():
            return svg
        
        # Pattern to match the entire nested SVG structure
        # Matches: <svg class="definition-scale" ...>...</svg>
        # We'll match from the opening tag to the matching closing tag
        nested_svg_start_pattern = re.compile(
            r'<svg\s+class=["\']definition-scale["\'][^>]*?>',
            re.IGNORECASE | re.DOTALL
        )
        
        # Pattern to extract viewBox from inner SVG attributes
        viewbox_pattern = re.compile(
            r'viewBox=["\']([^"\']+)["\']',
            re.IGNORECASE
        )
        
        # Check if we have a nested SVG structure
        nested_start_match = nested_svg_start_pattern.search(svg)
        if not nested_start_match:
            # No nested SVG found, return as-is
            return svg
        
        # Extract viewBox from the nested SVG opening tag
        nested_start_pos = nested_start_match.start()
        nested_start_end = nested_start_match.end()
        nested_tag = svg[nested_start_pos:nested_start_end]
        
        viewbox_match = viewbox_pattern.search(nested_tag)
        if not viewbox_match:
            # No viewBox found in inner SVG, return as-is
            logger.warning("Nested SVG found but no viewBox attribute")
            return svg
        
        viewbox_value = viewbox_match.group(1)
        logger.info(f"Flattening SVG: extracted viewBox={viewbox_value}")
        
        # Find the matching closing tag for the nested SVG
        # Start from after the opening tag
        pos = nested_start_end
        depth = 1
        
        while pos < len(svg) and depth > 0:
            # Look for <svg or </svg>
            svg_tag_pos = svg.find('<svg', pos)
            closing_tag_pos = svg.find('</svg>', pos)
            
            # Determine which comes first
            if closing_tag_pos == -1:
                # No more closing tags found
                logger.warning("Could not find matching closing tag for nested SVG")
                return svg
            
            if svg_tag_pos != -1 and svg_tag_pos < closing_tag_pos:
                # Found another opening tag first
                # Check if it's self-closing
                tag_end = svg.find('>', svg_tag_pos)
                if tag_end != -1 and tag_end < closing_tag_pos:
                    if svg[tag_end - 1] == '/':
                        # Self-closing, skip it
                        pos = tag_end + 1
                    else:
                        # Opening tag, increase depth
                        depth += 1
                        pos = tag_end + 1
                else:
                    # Malformed, try closing tag
                    depth -= 1
                    if depth == 0:
                        # Found the matching closing tag
                        nested_end_pos = closing_tag_pos + 6
                        break
                    pos = closing_tag_pos + 6
            else:
                # Found closing tag first
                depth -= 1
                if depth == 0:
                    # Found the matching closing tag
                    nested_end_pos = closing_tag_pos + 6
                    break
                pos = closing_tag_pos + 6
        
        if depth != 0:
            logger.warning("Could not find matching closing tag for nested SVG")
            return svg
        
        # Extract content between nested SVG tags (excluding the tags themselves)
        inner_content = svg[nested_start_end:nested_end_pos - 6]
        
        # Find and replace outer SVG opening tag
        outer_svg_pattern = re.compile(
            r'<svg[^>]*?>',
            re.IGNORECASE | re.DOTALL
        )
        outer_match = outer_svg_pattern.search(svg)
        if not outer_match:
            logger.warning("Could not find outer SVG opening tag")
            return svg
        
        outer_svg_start = outer_match.start()
        outer_svg_end = outer_match.end()
        outer_svg_tag = outer_match.group(0)
        
        # Extract content between outer SVG opening tag and nested SVG (e.g., <desc>, <style>)
        content_before_nested = svg[outer_svg_end:nested_start_pos]
        
        # Build new outer SVG tag with viewBox
        # Remove existing width, height, viewBox attributes
        outer_tag_clean = re.sub(
            r'\s+(?:width|height|viewBox)=["\'][^"\']+["\']',
            '',
            outer_svg_tag,
            flags=re.IGNORECASE
        )
        # Remove style attribute if it has width/height constraints
        outer_tag_clean = re.sub(
            r'\s+style=["\'][^"\']*width[^"\']*["\']',
            '',
            outer_tag_clean,
            flags=re.IGNORECASE
        )
        
        # Add viewBox and preserveAspectRatio
        # Remove the closing > temporarily to add attributes
        if outer_tag_clean.endswith('>'):
            outer_tag_clean = outer_tag_clean[:-1]
        new_outer_tag = f'{outer_tag_clean.rstrip()} viewBox="{viewbox_value}" preserveAspectRatio="xMidYMid meet" style="width: 100%; max-width: 100%;">'
        
        # Reconstruct SVG: everything before outer SVG + new outer tag + content before nested + inner content + everything after nested SVG
        # We need to remove the nested SVG structure entirely but preserve other content
        flattened = (
            svg[:outer_svg_start] +
            new_outer_tag +
            content_before_nested +
            inner_content +
            svg[nested_end_pos:]
        )
        
        logger.info("SVG flattened successfully")
        return flattened

    def convert(self, musicxml_string: str) -> List[str]:
        """
        Convert MusicXML to SVG pages.

        Args:
            musicxml_string: MusicXML as string

        Returns:
            List of SVG strings (one per page)
            
        Raises:
            ValueError: If MusicXML is invalid or Verovio fails
        """
        try:
            # Validate input
            if not isinstance(musicxml_string, str):
                raise ValueError(f"MusicXML must be a string, got {type(musicxml_string)}")
            if not musicxml_string.strip():
                raise ValueError("MusicXML string is empty")
            
            logger.info("Converting MusicXML to SVG with Verovio")

            # Configure Verovio
            try:
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
            except Exception as e:
                raise ValueError(f"Failed to configure Verovio: {str(e)}") from e

            # Load MusicXML
            try:
                load_success = self.toolkit.loadData(musicxml_string)
                if not load_success:
                    raise ValueError("Verovio failed to load MusicXML data")
            except Exception as e:
                raise ValueError(f"Failed to load MusicXML into Verovio: {str(e)}") from e

            # Get number of pages
            try:
                page_count = self.toolkit.getPageCount()
                if page_count <= 0:
                    raise ValueError(f"Verovio returned invalid page count: {page_count}")
                logger.info(f"Rendering {page_count} pages")
            except Exception as e:
                raise ValueError(f"Failed to get page count from Verovio: {str(e)}") from e

            # Render each page to SVG
            svg_pages = []
            for page_num in range(1, page_count + 1):
                try:
                    svg = self.toolkit.renderToSVG(page_num)
                    if not svg or not svg.strip():
                        raise ValueError(f"Verovio returned empty SVG for page {page_num}")
                    # Flatten nested SVG structure to fix viewBox/dimension mismatch
                    svg = self._flatten_svg(svg)
                    svg_pages.append(svg)
                except Exception as e:
                    raise ValueError(f"Failed to render SVG for page {page_num}: {str(e)}") from e

            if not svg_pages:
                raise ValueError("No SVG pages were generated")

            logger.info(f"SVG rendering complete: {len(svg_pages)} pages")

            return svg_pages
        except ValueError:
            # Re-raise ValueError as-is
            raise
        except Exception as e:
            # Wrap other exceptions
            raise ValueError(f"SVG conversion failed: {type(e).__name__}: {str(e)}") from e

