"""Convert Symbolic IR v2 to MIDI for playback."""

import mido
from typing import Any, Dict, List
import logging
import io

logger = logging.getLogger(__name__)


class IRToMIDIConverter:
    """
    Convert Symbolic IR v2 to MIDI for playback.

    MIDI doesn't support fingering annotations, but provides
    accurate timing and playback.
    """

    VERSION = "1.0.0"

    def __init__(self, tempo: int = 120, ticks_per_beat: int = 480):
        self.tempo = tempo
        self.ticks_per_beat = ticks_per_beat

    def convert(self, ir_v2: Dict[str, Any]) -> bytes:
        """
        Convert IR v2 to MIDI file bytes.

        Args:
            ir_v2: Symbolic Score IR v2

        Returns:
            MIDI file as bytes
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        try:
            logger.info("Converting IR v2 to MIDI")

            # Validate required fields
            if "notes" not in ir_v2:
                raise ValueError("IR v2 missing required field 'notes'")
            if not isinstance(ir_v2["notes"], list):
                raise ValueError(f"IR v2 'notes' must be a list, got {type(ir_v2['notes'])}")
            if "time_signature" not in ir_v2:
                raise ValueError("IR v2 missing required field 'time_signature'")
            time_sig = ir_v2["time_signature"]
            if not isinstance(time_sig, dict):
                raise ValueError(f"IR v2 'time_signature' must be a dict, got {type(time_sig)}")
            if "numerator" not in time_sig or "denominator" not in time_sig:
                raise ValueError("IR v2 'time_signature' missing 'numerator' or 'denominator'")

            # Create MIDI file
            mid = mido.MidiFile(ticks_per_beat=self.ticks_per_beat)

            # Create track
            track = mido.MidiTrack()
            mid.tracks.append(track)

            # Add tempo - handle missing tempo gracefully
            tempo_data = ir_v2.get("tempo", {})
            if not isinstance(tempo_data, dict):
                logger.warning(f"IR v2 'tempo' is not a dict, got {type(tempo_data)}, using default tempo")
                tempo_bpm = self.tempo
            else:
                tempo_bpm = tempo_data.get("bpm", self.tempo)
            track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo_bpm)))

            # Add time signature
            track.append(
                mido.MetaMessage(
                    "time_signature",
                    numerator=time_sig["numerator"],
                    denominator=time_sig["denominator"],
                )
            )

            # Convert notes to MIDI events
            midi_events = self._notes_to_midi_events(ir_v2["notes"])
        except KeyError as e:
            raise ValueError(f"Missing required field in IR v2: {str(e)}") from e
        except (TypeError, AttributeError) as e:
            raise ValueError(f"Invalid data type in IR v2: {str(e)}") from e

        # Sort by time
        midi_events.sort(key=lambda x: x["time"])

        # Add events to track with delta times
        current_time = 0
        for event in midi_events:
            delta = event["time"] - current_time
            delta_ticks = int(delta * self.ticks_per_beat)

            if event["type"] == "note_on":
                track.append(
                    mido.Message(
                        "note_on",
                        note=event["note"],
                        velocity=event["velocity"],
                        time=delta_ticks,
                    )
                )
            elif event["type"] == "note_off":
                track.append(
                    mido.Message(
                        "note_off", note=event["note"], velocity=0, time=delta_ticks
                    )
                )

            current_time = event["time"]

        # Add end of track
        track.append(mido.MetaMessage("end_of_track", time=0))

        # Convert to bytes
        buffer = io.BytesIO()
        mid.save(file=buffer)
        midi_bytes = buffer.getvalue()

        logger.info(f"MIDI conversion complete: {len(midi_bytes)} bytes")

        return midi_bytes

    def _notes_to_midi_events(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert IR v2 notes to MIDI events.

        Args:
            notes: List of note dictionaries from IR v2

        Returns:
            List of MIDI events with time, type, note, velocity
            
        Raises:
            ValueError: If note structure is invalid
        """
        events = []

        for i, note in enumerate(notes):
            try:
                # Validate note structure
                if not isinstance(note, dict):
                    raise ValueError(f"Note {i} must be a dictionary, got {type(note)}")
                
                # Get timing information - validate structure
                if "time" not in note:
                    raise ValueError(f"Note {i} missing required field 'time'")
                time_data = note["time"]
                if not isinstance(time_data, dict):
                    raise ValueError(f"Note {i} 'time' must be a dict, got {type(time_data)}")
                if "absolute_beat" not in time_data:
                    raise ValueError(f"Note {i} 'time' missing required field 'absolute_beat'")
                
                if "duration" not in note:
                    raise ValueError(f"Note {i} missing required field 'duration'")
                duration_data = note["duration"]
                if not isinstance(duration_data, dict):
                    raise ValueError(f"Note {i} 'duration' must be a dict, got {type(duration_data)}")
                if "duration_beats" not in duration_data:
                    raise ValueError(f"Note {i} 'duration' missing required field 'duration_beats'")
                
                onset_beats = time_data["absolute_beat"]
                duration_beats = duration_data["duration_beats"]
                offset_beats = onset_beats + duration_beats

                # Get pitch - validate structure
                if "pitch" not in note:
                    raise ValueError(f"Note {i} missing required field 'pitch'")
                pitch_data = note["pitch"]
                if not isinstance(pitch_data, dict):
                    raise ValueError(f"Note {i} 'pitch' must be a dict, got {type(pitch_data)}")
                if "midi_note" not in pitch_data:
                    raise ValueError(f"Note {i} 'pitch' missing required field 'midi_note'")
                
                midi_note = pitch_data["midi_note"]
                
                # Validate midi_note range
                if not isinstance(midi_note, int) or midi_note < 0 or midi_note > 127:
                    raise ValueError(f"Note {i} 'pitch.midi_note' must be an integer between 0-127, got {midi_note}")
            except (KeyError, TypeError) as e:
                raise ValueError(f"Note {i} has invalid structure: {str(e)}") from e

            # Get velocity (default to 64 for mf)
            velocity = 64
            if note.get("dynamics"):
                # Map dynamics to velocity
                dynamics_map = {
                    "ppp": 20,
                    "pp": 30,
                    "p": 45,
                    "mp": 55,
                    "mf": 70,
                    "f": 85,
                    "ff": 100,
                    "fff": 115,
                }
                velocity = dynamics_map.get(note["dynamics"].lower(), 64)

            # Create note_on event
            events.append(
                {
                    "time": onset_beats,
                    "type": "note_on",
                    "note": midi_note,
                    "velocity": velocity,
                }
            )

            # Create note_off event
            events.append(
                {
                    "time": offset_beats,
                    "type": "note_off",
                    "note": midi_note,
                    "velocity": 0,
                }
            )

        return events

