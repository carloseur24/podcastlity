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

## Common Tasks

### Run full pipeline programmatically
```python
from scripts.utils import ffmpeg, session
from pathlib import Path

# Setup
session.ensure_session_dirs(".", "session_id")

# Ingest
shutil.copy("footage/fulldeco.mp4", "recordings/session_id/camera.mp4")

# Proxy
ffmpeg.create_proxy("recordings/session_id/camera.mp4", 
                    "proxies/session_id/camera_proxy.mp4")

# Audio
ffmpeg.extract_audio("recordings/session_id/camera.mp4",
                     "audio/session_id/camera.wav")
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

## Troubleshooting

### "Import pytest could not be resolved"
- Install pytest: `pip install pytest`

### "No such file or directory" for proxies
- Ensure session directories exist: `session.ensure_session_dirs(workspace, session_id)`

### FFmpeg errors
- FFmpeg is bundled via `imageio-ffmpeg`
- Check: `python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"`

## Architecture

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

## File Paths

- Project root: `/home/carlos/side-projects/mvp-editing-pipeline`
- Test footage: `footage/fulldeco.mp4`
- Config: `config/`
- Sessions: `recordings/<session_id>/`

## Notes

- Tests use `tmp_path` fixture - files are cleaned up after each test
- E2E tests run against temp directories, not the actual workspace
- To see actual output, run the pipeline programmatically (see above)
- Audio preprocessing now uses adaptive filtering based on diagnosis
