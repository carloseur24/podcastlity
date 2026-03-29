# Content-OS

Video content pipeline CLI for creating high-quality YouTube/TikTok/Reels content in Spanish.

## Features

- **Menu-driven TUI** - Interactive Rich-based interface
- **7-stage pipeline**: Ingest → Proxies → Transcribe → Analyze → Cutmap → Assemble → Export
- **100% idempotent** - Safe to re-run any stage
- **No external AI APIs** - Manual "skills" approach
- **Multi-platform export** - YouTube Long-form, Shorts, Reels, TikTok

## Requirements

- Python 3.12+
- WSL2 (Linux) with 16GB RAM
- No GPU required

## Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify FFmpeg (bundled via imageio-ffmpeg)
python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
```

## Usage

```bash
# Run the interactive CLI
python cli.py
```

### Menu Options

1. **Nueva Sesion** - Create new recording session
2. **Continuar Sesion** - Resume existing session
3. **Listar Sesiones** - Show all sessions
4. **Configuracion** - Settings management
0. **Salir** - Exit

### Pipeline Stages

| Stage | Description |
|-------|-------------|
| 1. Ingest | Copy camera/screen recordings to session |
| 2. Proxies | Create low-res proxies for fast editing |
| 3. Transcribe | Extract audio + Whisper transcription |
| 4. Analyze | Detect silence, fillers, energy levels |
| 5. Cutmap | Define keep/remove intervals |
| 6. Assemble | Concatenate clips with transitions |
| 7. Export | Render final videos per platform |

## Configuration

Edit `config/` files:

- `settings.json` - Global settings (paths, Whisper model)
- `profiles.json` - Platform profiles (shorts/longform)
- `brand.json` - Channel branding (colors, fonts)
- `filler_words_es.txt` - Spanish filler words to remove

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_ffmpeg.py -v

# Run with coverage
python -m pytest tests/ --cov=scripts
```

## Test Footage

Sample video located at `footage/fulldeco.mp4` (~42 seconds, 720x1280 portrait).

## Project Structure

```
.
├── cli.py                 # Main entry point (TUI)
├── pytest.ini             # Test configuration
├── requirements.txt       # Python dependencies
├── config/                # Configuration files
│   ├── settings.json
│   ├── profiles.json
│   ├── brand.json
│   └── filler_words_es.txt
├── scripts/
│   ├── core/              # Backend (reusable by future API)
│   │   ├── __init__.py
│   │   ├── exceptions.py  # PipelineError, StageError
│   │   ├── pipeline.py    # Pipeline orchestrator
│   │   └── stages/        # Pipeline stage modules
│   │       ├── ingest.py
│   │       ├── proxies.py
│   │       ├── transcribe.py
│   │       ├── analyze.py
│   │       ├── cutmap.py
│   │       ├── assemble.py
│   │       └── export.py
│   ├── models.py          # Pydantic data models
│   ├── ui/
│   │   └── menus.py        # Rich TUI components
│   └── utils/
│       ├── ffmpeg.py       # FFmpeg wrappers
│       ├── session.py     # Session management
│       └── filepicker.py  # File selection
├── templates/
│   └── subtitles/          # Subtitle styles
├── docs/
│   ├── base-plan.md        # Technical specification
│   └── brief-skill.md      # Manual brief generation
├── tests/
│   ├── conftest.py         # Pytest fixtures
│   ├── test_ffmpeg.py
│   ├── test_session.py
│   ├── test_filepicker.py
│   ├── test_models.py
│   └── test_e2e.py
└── footage/
    └── fulldeco.mp4        # Test video
```

## Backend API Usage

The pipeline can be used programmatically:

```python
from scripts.core import Pipeline

pipeline = Pipeline("/path/to/workspace")

# Run full pipeline
pipeline.run_full("session_id")

# Run single stage
pipeline.run_stage("session_id", "transcribe")

# With progress callback
pipeline.run_full("session_id", on_progress=lambda stage, status: print(f"{stage}: {status}"))
```

## License

MIT
