"""Convert Symbolic IR v2 to MusicXML with fingering annotations."""

from lxml import etree as ET
from typing import Any, Dict, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class IRToMusicXMLConverter:
    """
    Convert Symbolic IR v2 to MusicXML with fingering annotations.

    This is the final, lossy transformation that commits to:
    - Specific quantization
    - Voice assignments
    - Layout decisions
    - Engraving choices
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        include_fingering: bool = True,
        include_dynamics: bool = True,
        musicxml_version: str = "4.0",
    ):
        self.include_fingering = include_fingering
        self.include_dynamics = include_dynamics
        self.musicxml_version = musicxml_version

    def convert(self, ir_v2: Dict[str, Any]) -> str:
        """
        Convert IR v2 to MusicXML string.

        Args:
            ir_v2: Symbolic Score IR v2 with fingering

        Returns:
            MusicXML as string
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        try:
            logger.info("Converting IR v2 to MusicXML")
            
            # Validate required fields
            if "notes" not in ir_v2:
                raise ValueError("IR v2 missing required field 'notes'")
            if "staves" not in ir_v2:
                raise ValueError("IR v2 missing required field 'staves'")
            if not isinstance(ir_v2["notes"], list):
                raise ValueError(f"IR v2 'notes' must be a list, got {type(ir_v2['notes'])}")
            if not isinstance(ir_v2["staves"], list):
                raise ValueError(f"IR v2 'staves' must be a list, got {type(ir_v2['staves'])}")
            if len(ir_v2["staves"]) == 0:
                raise ValueError("IR v2 must have at least one staff")
            
            logger.info(f"Notes: {len(ir_v2['notes'])}, Staves: {len(ir_v2['staves'])}")

            # Build MusicXML structure
            root = self._create_root()

            # Add metadata (handle missing metadata gracefully)
            metadata = ir_v2.get("metadata", {})
            if not isinstance(metadata, dict):
                logger.warning(f"IR v2 'metadata' is not a dict, got {type(metadata)}, using empty dict")
                metadata = {}
            self._add_metadata(root, metadata)

            # Add part list
            part_list = self._create_part_list(ir_v2["staves"])
            root.append(part_list)
        except KeyError as e:
            raise ValueError(f"Missing required field in IR v2: {str(e)}") from e
        except (TypeError, AttributeError) as e:
            raise ValueError(f"Invalid data type in IR v2: {str(e)}") from e

        # Add parts (one per staff or combined for piano)
        if self._is_piano_score(ir_v2["staves"]):
            part = self._create_piano_part(ir_v2)
            root.append(part)
        else:
            for staff in ir_v2["staves"]:
                part = self._create_single_staff_part(ir_v2, staff)
                root.append(part)

        # Convert to string
        xml_string = ET.tostring(
            root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
        ).decode("utf-8")

        logger.info("MusicXML conversion complete")

        return xml_string

    def _create_root(self) -> ET.Element:
        """Create root score-partwise element."""
        root = ET.Element("score-partwise", version=self.musicxml_version)
        return root

    def _add_metadata(self, root: ET.Element, metadata: Dict[str, Any]):
        """Add work and identification metadata."""
        # Work
        if metadata.get("title"):
            work = ET.SubElement(root, "work")
            work_title = ET.SubElement(work, "work-title")
            work_title.text = metadata["title"]

        # Identification
        identification = ET.SubElement(root, "identification")

        if metadata.get("composer"):
            creator = ET.SubElement(identification, "creator", type="composer")
            creator.text = metadata["composer"]

        # Encoding
        encoding = ET.SubElement(identification, "encoding")
        software = ET.SubElement(encoding, "software")
        software.text = "Étude Renderer Service"
        encoding_date = ET.SubElement(encoding, "encoding-date")
        encoding_date.text = datetime.utcnow().strftime("%Y-%m-%d")

    def _is_piano_score(self, staves: List[Dict]) -> bool:
        """Check if this is a piano score (grand staff)."""
        return len(staves) == 2

    def _create_part_list(self, staves: List[Dict]) -> ET.Element:
        """Create part-list element."""
        part_list = ET.Element("part-list")

        if self._is_piano_score(staves):
            # Single part for piano with multiple staves
            score_part = ET.SubElement(part_list, "score-part", id="P1")
            part_name = ET.SubElement(score_part, "part-name")
            part_name.text = "Piano"

            # Instrument
            score_instrument = ET.SubElement(score_part, "score-instrument", id="P1-I1")
            instrument_name = ET.SubElement(score_instrument, "instrument-name")
            instrument_name.text = "Piano"
        else:
            # Multiple parts
            for i, staff in enumerate(staves, start=1):
                score_part = ET.SubElement(part_list, "score-part", id=f"P{i}")
                part_name = ET.SubElement(score_part, "part-name")
                part_name.text = staff.get("part_name", f"Part {i}")

        return part_list

    def _create_piano_part(self, ir_v2: Dict[str, Any]) -> ET.Element:
        """Create a piano part with grand staff."""
        part = ET.Element("part", id="P1")

        # Group notes by measure
        notes_by_measure = self._group_by_measure(ir_v2["notes"])

        for measure_num in sorted(notes_by_measure.keys()):
            measure_notes = notes_by_measure[measure_num]
            measure = self._create_measure(
                measure_num, measure_notes, ir_v2, is_grand_staff=True
            )
            part.append(measure)

        return part

    def _create_single_staff_part(
        self, ir_v2: Dict[str, Any], staff: Dict[str, Any]
    ) -> ET.Element:
        """Create a single-staff part."""
        staff_id = staff["staff_id"]
        part_num = int(staff_id.split("_")[-1]) + 1

        part = ET.Element("part", id=f"P{part_num}")

        # Filter notes for this staff
        staff_notes = [
            n for n in ir_v2["notes"] if n["spatial"]["staff_id"] == staff_id
        ]

        # Group by measure
        notes_by_measure = self._group_by_measure(staff_notes)

        for measure_num in sorted(notes_by_measure.keys()):
            measure_notes = notes_by_measure[measure_num]
            measure = self._create_measure(
                measure_num, measure_notes, ir_v2, is_grand_staff=False
            )
            part.append(measure)

        return part

    def _group_by_measure(self, notes: List[Dict]) -> Dict[int, List[Dict]]:
        """Group notes by measure number."""
        by_measure = {}
        for note in notes:
            measure = note["time"]["measure"]
            if measure not in by_measure:
                by_measure[measure] = []
            by_measure[measure].append(note)
        return by_measure

    def _create_measure(
        self,
        measure_num: int,
        notes: List[Dict],
        ir_v2: Dict[str, Any],
        is_grand_staff: bool,
    ) -> ET.Element:
        """Create a measure element with notes."""
        measure = ET.Element("measure", number=str(measure_num))

        # Add attributes for first measure
        if measure_num == 1:
            attributes = self._create_attributes(ir_v2, is_grand_staff)
            measure.append(attributes)

        # Sort notes by onset time - validate time structure first
        for i, n in enumerate(notes):
            if "time" not in n:
                raise ValueError(f"Note {i} in measure {measure_num} missing required field 'time'")
            time_data = n["time"]
            if not isinstance(time_data, dict):
                raise ValueError(f"Note {i} in measure {measure_num} 'time' must be a dict, got {type(time_data)}")
            if "onset_seconds" not in time_data and "absolute_beat" not in time_data:
                raise ValueError(f"Note {i} in measure {measure_num} 'time' missing 'onset_seconds' or 'absolute_beat'")
        
        # Use onset_seconds if available, otherwise fall back to absolute_beat
        def get_onset(note):
            time_data = note["time"]
            if "onset_seconds" in time_data:
                return time_data["onset_seconds"]
            elif "absolute_beat" in time_data:
                return time_data["absolute_beat"]
            return 0.0
        
        sorted_notes = sorted(notes, key=get_onset)

        # Add notes
        for note_data in sorted_notes:
            note_elem = self._create_note(note_data, ir_v2, is_grand_staff)
            measure.append(note_elem)

        return measure

    def _create_attributes(
        self, ir_v2: Dict[str, Any], is_grand_staff: bool
    ) -> ET.Element:
        """Create attributes element (clef, time, key)."""
        attributes = ET.Element("attributes")

        # Divisions (ticks per quarter note)
        divisions = ET.SubElement(attributes, "divisions")
        divisions.text = "256"  # 256 divisions per quarter note

        # Key signature - validate before accessing
        if "key_signature" not in ir_v2:
            raise ValueError("IR v2 missing required field 'key_signature'")
        key_sig = ir_v2["key_signature"]
        if not isinstance(key_sig, dict):
            raise ValueError(f"IR v2 'key_signature' must be a dict, got {type(key_sig)}")
        if "fifths" not in key_sig:
            raise ValueError("IR v2 'key_signature' missing required field 'fifths'")
        if "mode" not in key_sig:
            raise ValueError("IR v2 'key_signature' missing required field 'mode'")
        
        key = ET.SubElement(attributes, "key")
        fifths = ET.SubElement(key, "fifths")
        fifths.text = str(key_sig["fifths"])
        mode = ET.SubElement(key, "mode")
        mode.text = str(key_sig["mode"])

        # Time signature - validate before accessing
        if "time_signature" not in ir_v2:
            raise ValueError("IR v2 missing required field 'time_signature'")
        time_sig = ir_v2["time_signature"]
        if not isinstance(time_sig, dict):
            raise ValueError(f"IR v2 'time_signature' must be a dict, got {type(time_sig)}")
        if "numerator" not in time_sig:
            raise ValueError("IR v2 'time_signature' missing required field 'numerator'")
        if "denominator" not in time_sig:
            raise ValueError("IR v2 'time_signature' missing required field 'denominator'")
        
        time = ET.SubElement(attributes, "time")
        beats = ET.SubElement(time, "beats")
        beats.text = str(time_sig["numerator"])
        beat_type = ET.SubElement(time, "beat-type")
        beat_type.text = str(time_sig["denominator"])

        # Staves (for grand staff)
        if is_grand_staff:
            staves = ET.SubElement(attributes, "staves")
            staves.text = "2"

        # Clef
        for i, staff in enumerate(ir_v2["staves"], start=1):
            clef = ET.SubElement(attributes, "clef")
            if is_grand_staff:
                clef.set("number", str(i))

            sign = ET.SubElement(clef, "sign")
            sign.text = staff["clef"][0].upper()  # "treble" → "G", "bass" → "F"

            line = ET.SubElement(clef, "line")
            line.text = "2" if staff["clef"] == "treble" else "4"

        return attributes

    def _create_note(
        self, note_data: Dict[str, Any], ir_v2: Dict, is_grand_staff: bool
    ) -> ET.Element:
        """Create a note element with fingering."""
        note = ET.Element("note")

        # Validate pitch structure
        if "pitch" not in note_data:
            raise ValueError(f"Note missing required field 'pitch'")
        pitch_data = note_data["pitch"]
        if not isinstance(pitch_data, dict):
            raise ValueError(f"Note 'pitch' must be a dict, got {type(pitch_data)}")
        if "pitch_class" not in pitch_data and "midi_note" not in pitch_data:
            raise ValueError(f"Note 'pitch' missing 'pitch_class' or 'midi_note'")
        if "octave" not in pitch_data:
            raise ValueError(f"Note 'pitch' missing required field 'octave'")

        # Pitch
        pitch = ET.SubElement(note, "pitch")
        step = ET.SubElement(pitch, "step")
        # Extract step from pitch_class (remove accidentals)
        pitch_class = pitch_data.get("pitch_class", "")
        if not pitch_class:
            # Fallback: derive from midi_note if available
            if "midi_note" in pitch_data:
                midi_note = pitch_data["midi_note"]
                note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
                pitch_class = note_names[midi_note % 12]
            else:
                raise ValueError(f"Note 'pitch' missing both 'pitch_class' and 'midi_note'")
        step.text = pitch_class[0].upper()  # First character is the step

        octave = ET.SubElement(pitch, "octave")
        octave.text = str(pitch_data["octave"])

        # Accidental
        if "#" in pitch_class:
            alter = ET.SubElement(pitch, "alter")
            alter.text = "1"
        elif "b" in pitch_class.lower():
            alter = ET.SubElement(pitch, "alter")
            alter.text = "-1"

        # Validate duration structure
        if "duration" not in note_data:
            raise ValueError(f"Note missing required field 'duration'")
        duration_data = note_data["duration"]
        if not isinstance(duration_data, dict):
            raise ValueError(f"Note 'duration' must be a dict, got {type(duration_data)}")
        
        # Duration
        duration = ET.SubElement(note, "duration")
        # Convert beats to divisions (256 divisions per quarter)
        duration_beats = note_data.get("quantized_duration_beats")
        if duration_beats is None:
            if "duration_beats" not in duration_data:
                raise ValueError(f"Note 'duration' missing 'duration_beats' or 'quantized_duration_beats'")
            duration_beats = duration_data["duration_beats"]
        duration.text = str(int(duration_beats * 256))

        # Type
        note_type_data = note_data.get("quantized_note_type")
        if note_type_data:
            note_type_str, dots = note_type_data
        else:
            note_type_str = note_data["duration"]["note_type"]
            dots = note_data["duration"].get("dots", 0)

        type_elem = ET.SubElement(note, "type")
        type_elem.text = note_type_str

        # Dots
        for _ in range(dots if isinstance(dots, int) else 0):
            ET.SubElement(note, "dot")

        # Staff (for grand staff)
        if is_grand_staff:
            staff_id = note_data["spatial"]["staff_id"]
            # Determine staff number (1 = treble, 2 = bass)
            if "0" in staff_id or "treble" in staff_id.lower():
                staff = ET.SubElement(note, "staff")
                staff.text = "1"  # Treble staff
            elif "1" in staff_id or "bass" in staff_id.lower():
                staff = ET.SubElement(note, "staff")
                staff.text = "2"  # Bass staff

        # Voice
        voice = ET.SubElement(note, "voice")
        voice.text = str(note_data.get("resolved_voice", 1))

        # Fingering
        if self.include_fingering and note_data.get("fingering"):
            fingering_data = note_data["fingering"]
            # Skip if finger is 0 (no fingering)
            if fingering_data.get("finger", 0) > 0:
                notations = ET.SubElement(note, "notations")
                technical = ET.SubElement(notations, "technical")
                fingering = ET.SubElement(technical, "fingering")
                fingering.text = str(fingering_data["finger"])

                # Add placement hint based on hand
                if fingering_data.get("hand") == "right":
                    fingering.set("placement", "above")
                else:
                    fingering.set("placement", "below")

        # Dynamics
        if self.include_dynamics and note_data.get("dynamics"):
            dynamics = ET.SubElement(note, "dynamics")
            dynamic_type = ET.SubElement(dynamics, note_data["dynamics"].lower())
            # MusicXML uses specific dynamic types: p, pp, ppp, f, ff, fff, mp, mf, etc.

        return note

