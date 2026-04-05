# Content-OS

Video content pipeline CLI for creating high-quality YouTube content in Spanish.

## Overview

Content-OS is a unified video editing pipeline that handles audio processing, subtitles, and optional coloring. It's designed for a streamlined workflow where editing happens externally.

## Architecture

```
data/                       # Input files
├── recordings/             # Raw camera/screen recordings
│   └── {session_id}/
│       └── camera.mp4
└── footage/                # Additional footage

output/                     # Generated files
├── proxies/                # Video proxies
├── audio/                  # Extracted/processed audio
├── transcripts/             # Whisper transcripts
├── analysis/               # Silence/filler/energy analysis
├── cutmaps/                # Edit decision maps
├── subtitles/              # Rendered subtitle videos
└── exports/                # Final exports
```

## Pipeline Stages

| Stage | Module | Description |
|-------|--------|-------------|
| Ingest | `ingest` | Copy files to session directory |
| Proxies | `proxies` | Create proxies and extract audio |
| VoiceExtract | `voice_extract` | Extract clean voice using VAD + noise reduction |
| Transcribe | `transcribe` | Whisper speech-to-text (manual trigger) |
| Analyze | `analyze` | Silence/filler/energy detection |
| Cutmap | `cutmap` | Generate edit decisions (optional, disabled by default) |
| Assemble | `assemble` | Trim and concatenate segments |
| Subtitles | `subtitles` | Apply Remotion kinetic subtitles |
| Export | `export` | Render final videos |

**Note**: Not all stages need to run. Use the CLI to select specific stages.

## Quick Start

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the interactive CLI
python cli.py
```

## CLI Commands

### Main Menu

```
=== Content-OS ===

  1. [green]Nueva Sesion[/green]          Create new recording session
  2. [cyan]Continuar Sesion[/cyan]        Resume existing session
  3. [magenta]Listar Sesiones[/magenta]   Show all sessions
  4. [yellow]Configuracion[/yellow]      Settings management
  0. [dim]Salir[/dim]                    Exit
```

### Session Menu

For each session, you can:

```
=== {session_id} ===

  1. [green]Ejecutar todo el pipeline[/green]   Run all stages
  2. [cyan]Ejecutar etapa especifica[/cyan]      Run specific stage
  3. [magenta]Ver resultados[/magenta]           View results
  0. [dim]Volver al menu principal[/dim]        Back
```

### Configuration Menu

```
=== Configuracion ===

  1. Audio Presets      - Manage audio processing presets
  2. Subtitle Presets  - Manage subtitle style presets
  3. Color Presets     - Manage color grading presets
  4. Filter Settings   - Adjust audio filter parameters
  5. View Config       - View current configuration
  0. Volver            - Back
```

## Usage Patterns

### Pattern 1: Full Audio Processing (Stage 1)

Process audio through the full pipeline:

1. Select session → **Ejecutar etapa especifica**
2. Choose stages in order:
   - `Ingest` → `Proxies` → `VoiceExtract` → `Analyze` → `Cutmap` → `Assemble` → `Export`

Or run the full pipeline and it will process all stages automatically.

### Pattern 2: Add Subtitles (Stage 3)

Add kinetic subtitles to existing video:

1. Ensure audio is processed (Stage 1 complete)
2. Select session → **Ejecutar etapa especifica**
3. Choose:
   - `Transcribe` (if not done)
   - `Subtitles`

### Pattern 3: Optional Coloring (Stage 4)

Color grading (future integration):

- Currently handled externally
- Import colored footage via `Ingest`

## Session Management

### Create Session

```
Session ID: 20250628_python_tips
Topic: Python Tips for Beginners
Duration (minutes): 10
```

### Session Status

| Status | Description |
|--------|-------------|
| `created` | Session created, files not yet copied |
| `ingested` | Files copied to session directory |
| `proxied` | Video proxies created, audio extracted |
| `voice_extracted` | Clean voice extracted with VAD |
| `transcribed` | Whisper transcript complete |
| `analyzed` | Silence/filler/energy analysis done |
| `cutmapped` | Edit decisions generated |
| `assembled` | Video segments concatenated |
| `subtitled` | Subtitles rendered |
| `exported` | Final videos exported |

## Configuration Files

### `config/settings.json`

```json
{
  "whisper_model": "large-v2",
  "whisper_language": "es",
  "default_profile": "default"
}
```

### `config/profiles.json`

Single "default" profile for all content:

```json
{
  "default": {
    "silence_threshold_db": -40,
    "silence_min_duration_s": 0.8,
    "enable_cutting": false,
    "aspect_ratio": "16:9",
    "resolution": "1920x1080"
  }
}
```

### `config/audio_presets.json`

Audio processing presets (highpass, denoise, loudnorm):

```json
{
  "default": {
    "name": "Default",
    "highpass_freq": 80,
    "loudnorm_I": -16
  }
}
```

### `config/subtitle_presets.json`

Subtitle styling presets:

```json
{
  "default": {
    "name": "Default",
    "font_family": "Montserrat",
    "font_size": 60,
    "read_only": true
  }
}
```

### `config/filters.json`

Detailed audio filter parameters:

```json
{
  "highpass": {"default_freq": 80},
  "afftdn": {"nr_mild": 10, "nr_moderate": 18},
  "loudnorm": {"default": {"I": -16, "TP": -1.5, "LRA": 11}}
}
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_config.py -v

# Run with coverage
python -m pytest tests/ --cov=scripts --cov-report=term-missing
```

## Idempotency

Each pipeline stage is idempotent - safe to re-run:

```python
# Running twice produces the same result
result = pipeline.run_stage(session_id, "Proxies")
result = pipeline.run_stage(session_id, "Proxies")  # Same output
```

## Tips & Recommendations

1. **Start with small tests** - Use short video clips to test the pipeline
2. **Check intermediate outputs** - Inspect `output/audio/` and `output/proxies/` 
3. **Use presets** - Create audio/subtitle presets for consistency
4. **Disable cutting initially** - Set `enable_cutting: false` in profile until you're ready
5. **External editing** - The tool handles processing; use external tools for fine editing

## Troubleshooting

### "Session not found"
- Check session ID exists in `data/recordings/`
- Verify session file exists: `data/recordings/{session_id}/session.json`

### "Audio not found"
- Run `Proxies` stage first to extract audio from video
- Check `output/audio/{session_id}/master.wav` exists

### FFmpeg errors
- FFmpeg is bundled via `imageio-ffmpeg`
- Check: `python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"`

## Project Structure

```
.
├── cli.py                    # Main CLI entry point
├── scripts/
│   ├── config.py             # Configuration provider
│   ├── models.py             # Pydantic data models
│   ├── preset_manager.py     # Preset CRUD operations
│   ├── core/
│   │   ├── pipeline.py       # Pipeline orchestration
│   │   ├── exceptions.py     # Custom exceptions
│   │   └── stages/           # Pipeline stages
│   │       ├── ingest.py
│   │       ├── proxies.py
│   │       ├── voice_extract.py
│   │       ├── transcribe.py
│   │       ├── analyze.py
│   │       ├── cutmap.py
│   │       ├── assemble.py
│   │       ├── subtitles.py
│   │       └── export.py
│   ├── utils/
│   │   ├── ffmpeg.py         # FFmpeg utilities
│   │   ├── session.py        # Session management
│   │   └── validation.py    # Input validators
│   └── ui/
│       └── menus.py          # CLI menu functions
├── config/                   # Configuration files
│   ├── settings.json
│   ├── profiles.json
│   ├── filters.json
│   ├── audio_presets.json
│   ├── subtitle_presets.json
│   ├── color_presets.json
│   └── brand.json
├── data/                     # Input files
│   ├── recordings/
│   └── footage/
├── output/                   # Generated files
│   ├── proxies/
│   ├── audio/
│   ├── transcripts/
│   ├── analysis/
│   ├── cutmaps/
│   ├── subtitles/
│   └── exports/
└── tests/                    # Test suite
    ├── conftest.py
    ├── test_config.py
    ├── test_models.py
    ├── test_session.py
    └── ...
```

## License

MIT
