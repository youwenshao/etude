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
        """
        logger.info("Converting IR v2 to MIDI")

        # Create MIDI file
        mid = mido.MidiFile(ticks_per_beat=self.ticks_per_beat)

        # Create track
        track = mido.MidiTrack()
        mid.tracks.append(track)

        # Add tempo
        tempo_bpm = ir_v2.get("tempo", {}).get("bpm", self.tempo)
        track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo_bpm)))

        # Add time signature
        ts = ir_v2["time_signature"]
        track.append(
            mido.MetaMessage(
                "time_signature",
                numerator=ts["numerator"],
                denominator=ts["denominator"],
            )
        )

        # Convert notes to MIDI events
        midi_events = self._notes_to_midi_events(ir_v2["notes"])

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
        """
        events = []

        for note in notes:
            # Get timing information
            onset_beats = note["time"]["absolute_beat"]
            duration_beats = note["duration"]["duration_beats"]
            offset_beats = onset_beats + duration_beats

            # Get pitch
            midi_note = note["pitch"]["midi_note"]

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

