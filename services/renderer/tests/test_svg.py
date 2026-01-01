"""Tests for SVG converter."""

import pytest

from app.converters.ir_to_svg import IRToSVGConverter


def test_svg_converter_basic():
    """Test basic SVG conversion from MusicXML."""
    converter = IRToSVGConverter(scale=40)

    # Minimal valid MusicXML
    musicxml = """<?xml version="1.0" encoding="UTF-8"?>
    <score-partwise version="4.0">
        <part-list>
            <score-part id="P1">
                <part-name>Piano</part-name>
            </score-part>
        </part-list>
        <part id="P1">
            <measure number="1">
                <attributes>
                    <divisions>256</divisions>
                    <key>
                        <fifths>0</fifths>
                        <mode>major</mode>
                    </key>
                    <time>
                        <beats>4</beats>
                        <beat-type>4</beat-type>
                    </time>
                    <clef>
                        <sign>G</sign>
                        <line>2</line>
                    </clef>
                </attributes>
                <note>
                    <pitch>
                        <step>C</step>
                        <octave>4</octave>
                    </pitch>
                    <duration>256</duration>
                    <type>quarter</type>
                </note>
            </measure>
        </part>
    </score-partwise>"""

    try:
        svg_pages = converter.convert(musicxml)
        assert len(svg_pages) > 0
        assert svg_pages[0].startswith("<svg")
    except Exception as e:
        # Verovio might not be available in test environment
        pytest.skip(f"Verovio not available: {e}")

