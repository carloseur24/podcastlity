# Implementation Plan: Config Architecture + Audio Engineer Skill

## Goal

Build a proper configuration architecture for the "content-os" video editing pipeline:
1. Centralize all scattered settings into a ConfigProvider class
2. Implement the sound engineer skill (diagnose → build filter chain → validate) for audio preprocessing
3. Apply DDD (Domain-Driven Design) with a domain layer

---

## Phase 1: Config Architecture

### 1.1 Config Files Structure

```
config/
├── settings.json      # General pipeline settings
├── profiles.json      # Per-content-type behavior
├── filters.json       # Audio filter parameters
├── brand.json         # Branding config
└── filler_words_es.txt
```

### 1.2 ConfigProvider Class (`scripts/config.py`)

```python
class ConfigProvider:
    def __init__(self, workspace_root: str)
    
    # General settings
    def get_ffmpeg_path(self) -> str
    def get_ffmpeg_threads(self) -> int
    def get_whisper_model(self) -> str
    def get_default_profile(self) -> str
    
    # Filter settings
    def get_filter(self, category: str) -> dict
    
    # Profile settings
    def get_profile(self, profile_name: str) -> dict
    
    # Loudnorm targets
    def get_loudnorm_targets(self, profile_name: str) -> dict
```

---

## Phase 2: Domain Layer

### 2.1 Domain Layer Structure

```
scripts/domain/
├── __init__.py
└── audio_engineer.py   # Diagnose → Build Filter Chain → Validate
```

### 2.2 AudioEngineer Class

```python
class AudioEngineer:
    def __init__(self, config: ConfigProvider)
    
    def diagnose(self, input_wav: Path) -> dict
    """Step 1: Measure RMS, peak, noise floor"""
    
    def build_filter_chain(self, diagnosis: dict, target: str) -> str
    """Step 2: Build adaptive filter chain based on diagnosis"""
    
    def validate(self, before_report: dict, after_report: dict) -> tuple[list, list]
    """Step 3: Quality gates - errors and warnings"""
    
    def preprocess(self, input_wav: Path, output_wav: Path, target: str) -> dict
    """Main entry point: diagnose → filter → validate"""
```

### 2.3 Diagnosis Metrics

From FFmpeg `astats` filter:
- `rms_db`: Overall RMS level in dB
- `peak_db`: Peak level in dB
- `noise_floor_db`: Measured noise floor
- `headroom_db`: peak_db - rms_db
- `snr_estimate_db`: rms_db - noise_floor_db

### 2.4 Filter Chain Order (non-negotiable)

1. **highpass** - Remove rumble (f=60-80Hz, poles=2)
2. **afftdn** - Spectral denoising (nr=8-22, nf=floor+5)
3. **agate** - Noise gate (only if noise_floor > -50dB)
4. **equalizer** - Corrective EQ (only confirmed problems)
5. **loudnorm** - Always last

---

## Phase 3: Pipeline Architecture

### 3.1 Pipeline Orchestrator (`scripts/core/pipeline.py`)

```python
from scripts.core.pipeline import Pipeline

pipeline = Pipeline(workspace=".")
results = pipeline.run_full(session_id="session_123")
```

### 3.2 Stages (`scripts/core/stages/`)

Each stage has `run(session_id, workspace) -> dict`:

| Stage | Status | Description |
|-------|--------|-------------|
| Ingest | ✅ | Copy files to session directory |
| Proxies | ✅ | Create proxies and extract audio |
| Transcribe | ✅ | Whisper speech-to-text |
| Analyze | ✅ | Silence/filler/energy detection |
| Cutmap | ✅ | Generate edit decisions |
| Assemble | ✅ | Trim and concatenate |
| Export | ✅ | Render final videos |

### 3.3 Profile-Specific Stages

- **Longform**: Ingest → Proxies → Transcribe → Analyze → Cutmap → Assemble → Export
- **Shorts**: Ingest → Proxies → Prepare → Assemble → Export (Prepare = preprocess + analyze + cutmap)

---

## Phase 4: Quality Gates

| Check | Error/Warning | Threshold |
|-------|---------------|------------|
| Noise floor increased | ERROR | after > before |
| RMS changed too much | ERROR | Δ > 12dB |
| Noise still high | WARNING | after > -48dB |
| SNR too low | WARNING | after < 18dB |

---

## Implementation Status

| # | Task | Status |
|---|------|--------|
| 1 | Create `config/filters.json` | ✅ DONE |
| 2 | Create `config/settings.json` | ✅ DONE |
| 3 | Create `config/profiles.json` | ✅ DONE |
| 4 | Create `scripts/config.py` | ✅ DONE |
| 5 | Create `scripts/domain/__init__.py` | ✅ DONE |
| 6 | Create `scripts/domain/audio_engineer.py` | ✅ DONE |
| 7 | Create `scripts/core/pipeline.py` | ✅ DONE |
| 8 | Create `scripts/core/exceptions.py` | ✅ DONE |
| 9 | Create stage modules | ✅ DONE |
| 10 | Refactor `scripts/audio_preprocess.py` | ✅ DONE |
| 11 | Refactor `scripts/utils/ffmpeg.py` | ✅ DONE |
| 12 | Run E2E test | ✅ DONE |

---

## Key Principles

- **Less is more**: Don't fix what isn't audible
- **Diagnose first**: Always measure before filtering
- **Adaptive chain**: Filter chain depends on diagnosis
- **Quality gates**: Fail fast if preprocessing made things worse
- **Idempotent**: Same input → same output (with new noise floor measurement)
