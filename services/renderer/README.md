# Renderer Service

The Renderer Service is the **presentation layer** of Étude, converting enriched Symbolic IR v2 (with fingering annotations) into user-facing formats:

- **IR v2 → MusicXML**: Engraving-optimized notation with fingering tags
- **IR v2 → MIDI**: Playback format with accurate timing
- **IR v2 → SVG**: Visual rendering using Verovio

## Features

- Quantization of continuous time to discrete note durations
- Voice assignment for polyphonic music
- Fingering annotation preservation in MusicXML
- Multi-format output (MusicXML, MIDI, SVG)
- Caching for performance optimization

## API Endpoints

- `GET /health` - Health check
- `POST /render` - Render IR v2 to requested formats
- `POST /render/musicxml` - Render to MusicXML only
- `POST /render/midi` - Render to MIDI only
- `POST /render/svg` - Render to SVG only

## Configuration

Environment variables (prefixed with `RENDERER_`):

- `RENDERER_DEFAULT_MUSICXML_VERSION` - MusicXML version (default: "4.0")
- `RENDERER_DEFAULT_MIDI_TEMPO` - Default MIDI tempo (default: 120)
- `RENDERER_DEFAULT_SVG_SCALE` - Verovio scale (default: 40)
- `RENDERER_QUANTIZATION_TOLERANCE` - Quantization tolerance in beats (default: 0.05)
- `RENDERER_INCLUDE_FINGERING` - Include fingering in output (default: true)

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

## Testing

```bash
pytest tests/
```

