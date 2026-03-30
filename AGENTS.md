# Agent Instructions

This document describes how to run, test, and work with the Content-OS project.

## Running the CLI

```bash
python cli.py
```

The CLI is menu-driven. Use arrow keys or number input to navigate.

## Running Tests

```bash
# Activate venv
source .venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_ffmpeg.py -v
python -m pytest tests/test_session.py -v
python -m pytest tests/test_models.py -v
python -m pytest tests/test_filepicker.py -v
python -m pytest tests/test_e2e.py -v

# Run with verbose output
python -m pytest tests/ -vv

# Stop on first failure
python -m pytest tests/ -x
```

## Linting & Type Checking

```bash
# Run pytest (includes some validation)
python -m pytest tests/

# Check Python syntax
python -m py_compile cli.py
python -m py_compile scripts/*.py
python -m py_compile scripts/**/*.py
```

## Test Fixtures

Key fixtures in `tests/conftest.py`:

- `workspace_root` - Creates temp workspace with all directories and config files
- `sample_session_id` - Returns "20250628_test_session"
- `sample_video_path` - Returns path to `footage/fulldeco.mp4` (or None)
- `mock_session` - Returns sample session dict
- `session_dir` - Creates session directory

## Adding Tests

1. Create `tests/test_<module>.py`
2. Import fixtures from `conftest.py`
3. Use `@pytest.fixture` for setup
4. Run with `python -m pytest tests/test_<module>.py -v`

Example:
```python
import pytest
from scripts.utils import session

def test_example(workspace_root, sample_session_id):
    sm = session.SessionManager(str(workspace_root))
    assert sm.session_exists(sample_session_id) is False
```

## Idempotency Testing

Each pipeline stage should be idempotent. Test by running twice:
```python
def test_idempotent(workspace_root):
    # First run
    result = do_something()
    # Second run (should produce same result)
    result2 = do_something()
    assert result == result2
```

## Running E2E Tests

E2E tests use `footage/fulldeco.mp4`:
```bash
python -m pytest tests/test_e2e.py -v
```

These verify:
- Video ingestion
- Proxy creation
- Audio extraction
- Frame extraction
- Idempotency

## Pipeline Architecture

### Pipeline Orchestrator (`scripts/core/pipeline.py`)

The Pipeline class coordinates all stages and provides progress callbacks:

```python
from scripts.core.pipeline import Pipeline

pipeline = Pipeline(workspace="/path/to/workspace")

# Run full pipeline
results = pipeline.run_full(session_id="session_123")

# Run single stage
result = pipeline.run_stage(session_id="session_123", stage_name="Analyze")

# Get available stages
stages = pipeline.get_available_stages(session_id="session_123")
```

### Stages (`scripts/core/stages/`)

Each stage is a separate module with `run(session_id, workspace) -> dict`:

| Stage | Module | Description |
|-------|--------|-------------|
| Ingest | `ingest` | Copy files to session directory |
| Proxies | `proxies` | Create proxies and extract audio |
| Transcribe | `transcribe` | Whisper speech-to-text |
| Analyze | `analyze` | Silence/filler/energy detection |
| Cutmap | `cutmap` | Generate edit decisions |
| Assemble | `assemble` | Trim and concatenate |
| Export | `export` | Render final videos |

### Profile-Specific Stages

- **Longform**: Ingest → Proxies → Transcribe → Analyze → Cutmap → Assemble → Export
- **Shorts**: Ingest → Proxies → Prepare → Assemble → Export

### Exceptions (`scripts/core/exceptions.py`)

```python
from scripts.core.exceptions import StageError, SessionNotFoundError, StageNotFoundError

try:
    pipeline.run_full(session_id="session_123")
except StageError as e:
    print(f"Stage {e.stage} failed: {e}")
except SessionNotFoundError:
    print("Session not found")
```

## Config Architecture

### ConfigProvider (`scripts/config.py`)

Centralized configuration management. Loads from JSON files in `config/`:

```python
from scripts.config import ConfigProvider, get_config

config = ConfigProvider(".")
# Or use singleton: config = get_config()

# General settings
config.get_ffmpeg_path()
config.get_default_profile()
config.get_whisper_model()

# Filter settings
config.get_highpass_settings()
config.get_afftdn_settings()
config.get_egate_settings()
config.get_loudnorm_targets("shorts")  # or "longform"

# Profile settings
config.get_profile("longform")
config.get_profile_silence_threshold("shorts")
```

### AudioEngineer (`scripts/domain/audio_engineer.py`)

Sound engineer skill for adaptive audio preprocessing. Implements diagnose → build_filter_chain → validate:

```python
from scripts.domain.audio_engineer import AudioEngineer

ae = AudioEngineer(config)

# Step 1: Diagnose recording
diagnosis = ae.diagnose(Path("audio/session/master.wav"))
# Returns: {rms_db, peak_db, noise_floor_db, snr_estimate_db, problems_detected[]}

# Step 2: Build adaptive filter chain
filter_chain = ae.build_filter_chain(diagnosis, target="longform")
# Returns FFmpeg filter chain string

# Step 3: Quality gates
errors, warnings = ae.validate(before_report, after_report)

# Main entry point
report = ae.preprocess(input_wav, output_wav, target="longform")
```

### Filter Chain Order (non-negotiable)

1. `highpass` - Remove rumble (f=60-80Hz)
2. `afftdn` - Spectral denoising (only if noise floor > -65dB)
3. `agate` - Noise gate (only if noise floor > -50dB)
4. `equalizer` - Corrective EQ (only confirmed problems)
5. `loudnorm` - Always last

## Common Tasks

### Run full pipeline programmatically
```python
from scripts.core.pipeline import Pipeline

pipeline = Pipeline(".")
results = pipeline.run_full(session_id="session_123")
```

### Run specific stage
```python
from scripts.core.stages import analyze

result = analyze.run("session_123", ".")
```

### Run audio preprocessing
```python
from scripts import audio_preprocess

audio_preprocess.run(session_id="session_123", mode="default", workspace=".")
```

### Check FFmpeg path
```bash
python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
```

### Verify video properties
```python
from scripts.utils import ffmpeg

duration = ffmpeg.get_duration("video.mp4")
width, height = ffmpeg.get_resolution("video.mp4")
frame_count = ffmpeg.get_frame_count("video.mp4")
```

## File Paths

- Project root: `/home/carlos/side-projects/mvp-editing-pipeline`
- Test footage: `footage/fulldeco.mp4`
- Config: `config/`
- Sessions: `recordings/<session_id>/`

## Directory Structure

```
scripts/
├── core/                  # Pipeline orchestration
│   ├── pipeline.py        # Pipeline orchestrator
│   ├── exceptions.py      # Custom exceptions
│   └── stages/           # Pipeline stages
│       ├── ingest.py
│       ├── proxies.py
│       ├── transcribe.py
│       ├── analyze.py
│       ├── cutmap.py
│       ├── assemble.py
│       └── export.py
├── domain/               # Domain logic
│   ├── audio_engineer.py # Audio preprocessing
│   └── __init__.py
├── utils/                # Utilities
│   ├── ffmpeg.py
│   ├── session.py
│   ├── filepicker.py
│   └── validation.py
├── config.py             # ConfigProvider
├── audio_preprocess.py   # Audio preprocessing entry
└── models.py             # Data models

config/
├── settings.json          # General pipeline settings
├── profiles.json          # Per-content-type behavior
├── filters.json           # Audio filter parameters
├── brand.json             # Branding config
└── filler_words_es.txt   # Filler word list
```

## Data Models (`scripts/models.py`)

Pydantic models for all pipeline data structures:

```python
from scripts.models import (
    Session, Transcript, TranscriptSegment, Word,
    SilenceMap, SilenceInterval, FillerMap, FillerWord,
    EnergyMap, EnergyWindow, ChapterMap, Chapter,
    CutMap, KeepInterval, Brief, Metadata
)
```

### Session Model

```python
session = Session(
    session_id="20250628_test",
    topic="Python tips",
    profile="longform",
    status="ingested"
)
session.model_dump()  # Serialize to dict
```

### Stage Return Values

Each stage returns a dict with these keys:

| Key | Type | Description |
|-----|------|-------------|
| `session_status` | str | Updated session status |
| `success` | bool | Whether stage completed |
| `stage` | str | Stage name |
| `session_id` | str | The session ID |
| `data` | dict | Stage-specific output data |

Example:
```python
result = analyze.run("session_id", ".")
# Returns: {
#     "session_status": "analyzed",
#     "success": True,
#     "stage": "Analyze",
#     "session_id": "20250628_test",
#     "data": {"silence_map": {...}, "filler_map": {...}}
# }
```

## Utilities

### SessionManager (`scripts/utils/session.py`)

```python
from scripts.utils.session import SessionManager

sm = SessionManager("/workspace")

# Check if session exists
sm.session_exists("session_id")

# Get session path
session_path = sm.get_session_path("session_id")

# Load session data
session = sm.load_session("session_id")

# Update status
sm.update_status("session_id", "analyzed")

# List all sessions
sessions = sm.list_sessions()
```

### FFmpeg Utils (`scripts/utils/ffmpeg.py`)

```python
from scripts.utils import ffmpeg

# Video operations
duration = ffmpeg.get_duration("video.mp4")
width, height = ffmpeg.get_resolution("video.mp4")
frame_count = ffmpeg.get_frame_count("video.mp4")

# Audio extraction
ffmpeg.extract_audio("video.mp4", "output.wav", mono=True, sample_rate=16000)

# Proxy creation
ffmpeg.create_proxy("input.mp4", "proxy.mp4", width=1280, height=720)

# Video trimming
ffmpeg.trim_video("input.mp4", "output.mp4", start=0, end=30)

# Loudness normalization
ffmpeg.apply_loudnorm("input.wav", "output.wav", profile="shorts")
```

### Validation (`scripts/utils/validation.py`)

```python
from scripts.utils.validation import (
    SessionIdValidator,
    DurationValidator,
    TopicValidator,
    FilePathValidator
)

# Validate inputs
result = SessionIdValidator().validate("20250628_test")
result = DurationValidator().validate("5.5")
result = TopicValidator().validate("My video topic")
result = FilePathValidator().validate("/path/to/video.mp4")

if result.is_valid:
    print(result.value)
else:
    print(result.errors)
```

## Troubleshooting

### "Import pytest could not be resolved"
- Install pytest: `pip install pytest`

### "No such file or directory" for proxies
- Ensure session directories exist: `session.ensure_session_dirs(workspace, session_id)`

### FFmpeg errors
- FFmpeg is bundled via `imageio-ffmpeg`
- Check: `python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"`

## Notes

- Tests use `tmp_path` fixture - files are cleaned up after each test
- E2E tests run against temp directories, not the actual workspace
- To see actual output, run the pipeline programmatically
- Audio preprocessing uses adaptive filtering based on diagnosis
- Each stage returns a dict with `session_status` key for status updates
