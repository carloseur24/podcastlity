# content-os — Full Technical Implementation Spec
> Planner: minmax2 via opencode | Builder: mimo | Executor: opencode  
> Hardware target: Windows + WSL2 + Ryzen 7 + 16 GB RAM  
> Language: Spanish-only content  
> Platforms: YouTube long-form, YouTube Shorts, Instagram Reels, TikTok

---

## 0. North Star

One recorded master take (two raw files: `camera.mp4` + `screen.mp4`) enters the pipeline.  
Ten publishable assets exit automatically. Human touches only three decisions:  
1. Approve/reject the edit brief before recording.  
2. Select the final hook from the generated list.  
3. QA in Resolve before publish.

Everything else is deterministic CLI + agent automation.

---

## 1. Hardware Constraints & Performance Contract

| Resource | Limit | Pipeline implication |
|---|---|---|
| RAM | 16 GB | Whisper model: `faster-whisper large-v2` with `int8` quantization (~2 GB RAM). Never load full video in memory. |
| CPU | Ryzen 7 (8c/16t) | FFmpeg: `-threads 0` (auto). Python workers: `max_workers=6` (leave 2 for system). |
| GPU | None assumed | All inference on CPU. CTranslate2 backend for Whisper is optimized for this. |
| Disk I/O | NVMe assumed | Use proxy files (720p) for analysis passes. Full-res only at final export. |
| WSL2 | Windows host | All paths use POSIX inside WSL. Bind mount for recordings: `/mnt/c/Users/<user>/Videos`. |

**Proxy rule:** Any FFmpeg operation that doesn't produce a final export works on a 720p proxy. This cuts analysis time ~4×.  
**Chunk rule:** Never pipe a full video file through Python. Always pass file paths to subprocess calls.

---

## 2. Repository Structure (Canonical)

```
content-os/
├── briefs/
│   └── {session_id}/
│       ├── brief.json          # agent output: titles, hooks, scenes, CTA
│       └── brief.md            # human-readable version of the same
├── recordings/
│   └── {session_id}/
│       ├── camera.mp4          # raw camera file (original, never modified)
│       ├── screen.mp4          # raw screen capture (original, never modified)
│       └── session.json        # sync offset, profile, topic metadata
├── proxies/
│   └── {session_id}/
│       ├── camera_proxy.mp4    # 720p proxy of camera
│       └── screen_proxy.mp4    # 720p proxy of screen
├── audio/
│   └── {session_id}/
│       ├── master.wav          # extracted mono 16kHz audio (from camera)
│       └── master_norm.wav     # loudness-normalized copy
├── transcripts/
│   └── {session_id}/
│       ├── raw.json            # faster-whisper word-level output
│       ├── segments.json       # cleaned segments with confidence scores
│       └── transcript.txt      # plain text for human review
├── analysis/
│   └── {session_id}/
│       ├── silence_map.json    # silence intervals [{start, end, duration}]
│       ├── filler_map.json     # filler word hits [{word, start, end, confidence}]
│       ├── energy_map.json     # RMS energy per 500ms window
│       └── chapter_map.json    # topic segments detected by agent
├── cutmaps/
│   └── {session_id}/
│       ├── longform.json       # edit decisions for long-form
│       └── shorts.json         # edit decisions for short-form
├── templates/
│   ├── subtitles/
│   │   ├── default.ass         # base ASS subtitle style (Spanish)
│   │   ├── kinetic.ass         # word-by-word kinetic captions template
│   │   └── minimal.ass         # clean lower-third style
│   ├── exports/
│   │   ├── youtube_lf.json     # FFmpeg export preset: 1920x1080
│   │   ├── shorts.json         # FFmpeg export preset: 1080x1920
│   │   ├── reels.json          # FFmpeg export preset: 1080x1920
│   │   └── tiktok.json         # FFmpeg export preset: 1080x1920
│   └── ffmpeg/
│       ├── filters_shorts.txt  # reusable FFmpeg filter_complex for shorts
│       └── filters_longform.txt
├── remotion/
│   ├── package.json
│   ├── remotion.config.ts
│   └── src/
│       ├── Root.tsx
│       ├── compositions/
│       │   ├── Intro.tsx        # branded 3s intro
│       │   ├── Outro.tsx        # branded 3s outro
│       │   ├── LowerThird.tsx   # name/title lower third
│       │   ├── HookCard.tsx     # full-frame hook title card
│       │   └── KineticCaptions.tsx  # word-by-word animated captions
│       ├── data/
│       │   └── {session_id}.json  # data injected into compositions
│       └── utils/
│           ├── timing.ts
│           └── brand.ts         # colors, fonts, brand constants
├── exports/
│   └── {session_id}/
│       ├── youtube_lf.mp4
│       ├── youtube_shorts.mp4
│       ├── reels.mp4
│       └── tiktok.mp4
├── thumbnails/
│   └── {session_id}/
│       ├── frame_grabs/         # candidate frames extracted by FFmpeg
│       ├── concept.json         # agent-generated thumbnail concept
│       ├── ai_generated.png     # Flux/SD output from concept
│       └── final.png            # text overlay applied on top
├── metadata/
│   └── {session_id}/
│       ├── titles.json          # title candidates + SEO notes
│       ├── hooks.json           # hook candidates + timestamps
│       ├── descriptions.json    # platform-specific descriptions
│       └── tags.json
├── scripts/
│   ├── pipeline.py              # main orchestrator
│   ├── ingest.py                # register session, create proxies
│   ├── sync.py                  # audio-sync offset detection
│   ├── transcribe.py            # faster-whisper runner
│   ├── analyze.py               # silence, filler, energy analysis
│   ├── cutmap.py                # build cutmaps from analysis + agent
│   ├── assemble.py              # FFmpeg rough cut builder
│   ├── subtitle.py              # ASS generation + burn-in
│   ├── export.py                # platform variant exporter
│   ├── thumbnail.py             # thumbnail pipeline runner
│   ├── brief.py                 # agent brief generator (Claude API)
│   └── utils/
│       ├── ffmpeg.py            # FFmpeg subprocess wrappers
│       ├── whisper_utils.py     # transcript helpers
│       └── agent.py             # Claude API client
├── config/
│   ├── profiles.json            # shorts + longform content profiles
│   ├── filler_words_es.txt      # Spanish filler word list
│   ├── brand.json               # colors, fonts, style constants
│   └── settings.json            # API keys, paths, global settings
└── cli.py                       # Click CLI entry point: `content-os`
```

---

## 3. Session JSON Contract

Every session is identified by a `session_id` (format: `YYYYMMDD_{slug}`, e.g. `20250615_python_tips`).

**`recordings/{session_id}/session.json`** — written by `ingest` command:
```json
{
  "session_id": "20250615_python_tips",
  "topic": "5 trucos de Python que no conocías",
  "platform_targets": ["youtube_lf", "shorts", "reels", "tiktok"],
  "profile": "longform",
  "goal": "educativo",
  "tone": "directo y práctico",
  "cta": "Suscríbete para más",
  "rough_duration_min": 12,
  "camera_file": "camera.mp4",
  "screen_file": "screen.mp4",
  "sync_offset_seconds": 0.0,
  "sync_method": "manual",
  "created_at": "2025-06-15T10:30:00",
  "status": "ingested"
}
```

**Status lifecycle:**  
`ingested` → `proxied` → `transcribed` → `analyzed` → `cutmapped` → `assembled` → `exported` → `done`

Each script updates `status` before exiting. Pipeline runner checks status before starting a stage.

---

## 4. CLI Surface (complete)

Entry point: `python cli.py` aliased to `content-os` in `~/.bashrc`.

```bash
# Stage 1 — Create edit brief (agent call, before recording)
content-os brief \
  --topic "5 trucos de Python" \
  --goal educativo \
  --tone "directo y práctico" \
  --cta "Suscríbete" \
  --duration 12 \
  --platform youtube_lf,shorts \
  --session 20250615_python_tips

# Stage 2 — Register session + create proxies
content-os ingest \
  --session 20250615_python_tips \
  --camera /mnt/c/Users/user/Videos/cam.mp4 \
  --screen /mnt/c/Users/user/Videos/screen.mp4 \
  --offset 0.0          # positive = screen starts AFTER camera

# Stage 3 — Detect sync offset automatically (optional, uses audio cross-correlation)
content-os sync --session 20250615_python_tips

# Stage 4 — Transcribe (Spanish, word-level timestamps)
content-os transcribe --session 20250615_python_tips

# Stage 5 — Analyze (silence + filler + energy + chapters)
content-os analyze --session 20250615_python_tips

# Stage 6 — Generate cut map (uses analysis + agent for priorities)
content-os cutmap --session 20250615_python_tips --profile shorts
content-os cutmap --session 20250615_python_tips --profile longform

# Stage 7 — Assemble rough cut
content-os assemble --session 20250615_python_tips --profile shorts
content-os assemble --session 20250615_python_tips --profile longform

# Stage 8 — Generate + burn subtitles
content-os subtitle \
  --session 20250615_python_tips \
  --style kinetic \
  --profile shorts

# Stage 9 — Export platform variants
content-os export --session 20250615_python_tips --targets all

# Stage 10 — Thumbnail pipeline
content-os thumbnail --session 20250615_python_tips

# Full pipeline (runs stages 4-10 sequentially, checks status each step)
content-os run --session 20250615_python_tips

# Utility commands
content-os status --session 20250615_python_tips
content-os list-sessions
content-os reset --session 20250615_python_tips --stage analyze  # re-run from stage
content-os preview --session 20250615_python_tips --profile shorts  # open in mpv
```

All commands support `--dry-run` (prints what would happen, no file writes).  
All commands support `--verbose` (full subprocess stdout).  
All commands write a `{stage}.log` file under `analysis/{session_id}/logs/`.

---

## 5. Stage 0: Brief Generation (Agent)

**Script:** `scripts/brief.py`  
**Trigger:** Before recording.  
**Agent call:** Claude API (`claude-sonnet-4-20250514`), single call, JSON output.

### System prompt
```
Eres un productor de contenido experto para redes sociales en español. 
Generas briefs de edición estructurados para creadores de contenido.
Responde SOLO con JSON válido, sin texto adicional.
```

### User prompt template
```
Genera un brief de contenido completo para:
- Tema: {topic}
- Plataformas: {platforms}
- Objetivo: {goal}
- Tono: {tone}
- CTA: {cta}
- Duración estimada: {duration} minutos

Devuelve un JSON con exactamente estas claves:
{
  "titles": [str x5],
  "hooks": [{"text": str, "type": "pregunta|estadistica|afirmacion|historia", "energy": "alta|media"} x5],
  "thumbnail_concept": {"texto_principal": str, "subtexto": str, "emocion": str, "colores": [str], "composicion": str},
  "scene_outline": [{"id": int, "titulo": str, "descripcion": str, "duracion_s": int} x N],
  "broll_ideas": [str x5],
  "motion_style": "energetico|limpio|cinematico",
  "retention_notes": [str x3],
  "hook_timestamp_target_s": int,
  "export_targets": [str]
}
```

**Output:** `briefs/{session_id}/brief.json` + `briefs/{session_id}/brief.md`

---

## 6. Stage 1: Ingest

**Script:** `scripts/ingest.py`

### Steps
1. Validate both input files exist and are readable.
2. Copy (not move) to `recordings/{session_id}/`. Preserve originals.
3. Write `session.json` with all metadata.
4. Create proxy files (720p, fast encode):

```python
# camera proxy
ffmpeg -i camera.mp4 \
  -vf scale=1280:720 \
  -c:v libx264 -preset ultrafast -crf 28 \
  -c:a aac -b:a 128k \
  proxies/{session_id}/camera_proxy.mp4

# screen proxy
ffmpeg -i screen.mp4 \
  -vf scale=1280:720 \
  -c:v libx264 -preset ultrafast -crf 28 \
  -c:a aac -b:a 128k \
  proxies/{session_id}/screen_proxy.mp4
```

5. Extract mono 16kHz WAV for Whisper:
```python
ffmpeg -i camera.mp4 \
  -vn -ac 1 -ar 16000 -sample_fmt s16 \
  audio/{session_id}/master.wav
```

6. Update `session.json` status → `proxied`.

---

## 7. Stage 2: Sync Detection

**Script:** `scripts/sync.py`  
**Problem:** Camera and screen are two separate files. They must be aligned.

### Auto-sync via audio cross-correlation
Both files likely share a clap, countdown, or audio from the screen.

```python
import numpy as np
from scipy.signal import correlate
from scipy.io import wavfile

def detect_sync_offset(camera_wav: str, screen_wav: str) -> float:
    """
    Returns offset in seconds: positive means screen starts AFTER camera.
    Crops both to first 60 seconds for speed.
    """
    sr_cam, cam = wavfile.read(camera_wav)
    sr_scr, scr = wavfile.read(screen_wav)
    
    # Normalize + crop first 60s
    cam = cam[:sr_cam * 60].astype(np.float32)
    scr = scr[:sr_scr * 60].astype(np.float32)
    cam /= np.max(np.abs(cam))
    scr /= np.max(np.abs(scr))
    
    corr = correlate(cam, scr, mode='full')
    lag = np.argmax(corr) - (len(scr) - 1)
    return lag / sr_cam
```

If auto-detection confidence is low (max correlation < 0.3), prompt user for manual offset:
```
[sync] Auto-detection uncertain (score: 0.18).
[sync] Enter manual offset in seconds (positive = screen starts after camera): _
```

Offset is written to `session.json` → `sync_offset_seconds`.

---

## 8. Stage 3: Transcription

**Script:** `scripts/transcribe.py`  
**Engine:** `faster-whisper` (CTranslate2 backend)

### Model selection
```python
# settings.json
{
  "whisper_model": "large-v2",  # Best Spanish accuracy
  "whisper_compute_type": "int8",  # RAM-safe on 16GB CPU
  "whisper_device": "cpu",
  "whisper_language": "es",
  "whisper_beam_size": 5,
  "whisper_word_timestamps": true,
  "whisper_vad_filter": true,      # Silero VAD built into faster-whisper
  "whisper_vad_min_silence_duration_ms": 500
}
```

### Word-level output format (`transcripts/{session_id}/raw.json`)
```json
{
  "language": "es",
  "duration": 742.3,
  "segments": [
    {
      "id": 0,
      "start": 1.24,
      "end": 4.87,
      "text": "Hoy te voy a mostrar cinco trucos de Python",
      "words": [
        {"word": "Hoy", "start": 1.24, "end": 1.52, "probability": 0.98},
        {"word": "te", "start": 1.55, "end": 1.71, "probability": 0.97},
        ...
      ],
      "avg_logprob": -0.18,
      "no_speech_prob": 0.04
    }
  ]
}
```

### Post-processing (`transcripts/{session_id}/segments.json`)
- Filter out segments with `no_speech_prob > 0.6`
- Merge segments shorter than 0.3s into adjacent segment
- Flag segments with `avg_logprob < -0.5` as low-confidence

---

## 9. Stage 4: Analysis

**Script:** `scripts/analyze.py`  
This is the highest-priority pain point. Three sub-analyses run in parallel via `concurrent.futures`.

### 9.1 Silence Detection
**Method:** FFmpeg `silencedetect` filter on proxy audio.

```bash
ffmpeg -i audio/{session_id}/master.wav \
  -af silencedetect=noise=-40dB:d=0.4 \
  -f null - 2>&1 | grep silence
```

**Parameters (`config/profiles.json`):**
```json
{
  "shorts": {
    "silence_threshold_db": -40,
    "silence_min_duration_s": 0.3,
    "trim_pad_before_s": 0.05,
    "trim_pad_after_s": 0.08
  },
  "longform": {
    "silence_threshold_db": -42,
    "silence_min_duration_s": 0.5,
    "trim_pad_before_s": 0.1,
    "trim_pad_after_s": 0.12
  }
}
```

**Output (`analysis/{session_id}/silence_map.json`):**
```json
{
  "total_silence_s": 94.2,
  "silence_intervals": [
    {"start": 0.0, "end": 1.24, "duration": 1.24, "type": "leading"},
    {"start": 4.87, "end": 5.30, "duration": 0.43, "type": "between_sentences"},
    ...
  ],
  "potential_time_saved_s": 78.4
}
```

### 9.2 Filler Word Detection
**Method:** Scan word-level timestamps from transcript against filler list.

**`config/filler_words_es.txt`:**
```
este
eh
eee
mm
mmm
o sea
bueno
entonces
básicamente
literalmente
tipo
pues
```

**Output (`analysis/{session_id}/filler_map.json`):**
```json
{
  "total_fillers": 47,
  "filler_rate_per_minute": 3.8,
  "fillers": [
    {"word": "este", "start": 12.4, "end": 12.7, "segment_id": 3, "confidence": 0.94},
    ...
  ]
}
```

### 9.3 Energy Map
**Method:** FFmpeg `astats` per 500ms window.

```bash
ffmpeg -i audio/{session_id}/master.wav \
  -af astats=length=0.5:metadata=1,ametadata=print:file=- \
  -f null -
```

Parse RMS level per window. Normalize 0–1. Flag windows below `0.3` as low-energy.

**Output (`analysis/{session_id}/energy_map.json`):**
```json
{
  "windows": [
    {"t": 0.0, "rms_norm": 0.0, "low_energy": true},
    {"t": 0.5, "rms_norm": 0.72, "low_energy": false},
    ...
  ],
  "low_energy_intervals": [...]
}
```

### 9.4 Chapter Detection (Agent-assisted)
Send the plain transcript to Claude with scene outline from brief:

```python
# agent call: maps transcript to chapters
prompt = f"""
Transcript: {transcript_text[:4000]}
Expected scenes: {brief['scene_outline']}

Identifica los timestamps de inicio de cada escena. 
Devuelve JSON: [{{"scene_id": int, "start_s": float, "title": str}}]
"""
```

**Output:** `analysis/{session_id}/chapter_map.json`

---

## 10. Stage 5: Cut Map Generation

**Script:** `scripts/cutmap.py`  
This translates all analysis into concrete edit decisions (keep/cut intervals).

### Algorithm

```python
def build_cutmap(session_id: str, profile: str) -> list[dict]:
    """
    Returns list of keep intervals: [{"start": float, "end": float, "type": str}]
    """
    cfg = load_profile(profile)  # shorts or longform
    silence = load_silence_map(session_id)
    fillers = load_filler_map(session_id)
    energy = load_energy_map(session_id)
    duration = get_audio_duration(session_id)
    
    # Start with all time as "keep"
    cuts = CutTimeline(start=0.0, end=duration)
    
    # 1. Remove leading/trailing silence
    cuts.remove_interval(0.0, silence['silence_intervals'][0]['end'])
    
    # 2. Collapse inter-sentence silences beyond threshold
    for s in silence['silence_intervals']:
        if s['type'] == 'between_sentences':
            if s['duration'] > cfg['silence_min_duration_s']:
                # Keep a small natural pause
                keep_pause = cfg['collapse_to_s']  # e.g., 0.15s for shorts
                cuts.trim_interval(
                    s['start'] + cfg['trim_pad_before_s'],
                    s['end'] - cfg['trim_pad_after_s'] - keep_pause
                )
    
    # 3. Remove filler words (with padding)
    if cfg['remove_fillers']:
        for f in fillers['fillers']:
            if f['confidence'] > cfg['filler_confidence_threshold']:
                cuts.remove_interval(
                    f['start'] - 0.05,
                    f['end'] + 0.08
                )
    
    # 4. Flag low-energy sections (don't auto-remove, mark for agent review)
    for interval in energy['low_energy_intervals']:
        if interval['duration'] > cfg['low_energy_min_duration_s']:
            cuts.mark(interval['start'], interval['end'], tag='low_energy')
    
    return cuts.to_json()
```

### Agent-assisted priority pass (shorts only)
After the algorithmic cut map is built, a second Claude call refines priorities:

```python
# Send cutmap summary + hook candidates to agent
# Agent returns: hook_start_s, suggested_cut_order, recommended_total_duration_s
```

**Output (`cutmaps/{session_id}/shorts.json`):**
```json
{
  "profile": "shorts",
  "total_input_duration_s": 742.3,
  "total_output_duration_s": 87.4,
  "keep_intervals": [
    {"start": 1.24, "end": 4.87, "type": "hook", "scene_id": 0},
    {"start": 5.30, "end": 18.42, "type": "content", "scene_id": 1},
    ...
  ],
  "removed_silence_s": 78.4,
  "removed_fillers": 41,
  "hook_start_s": 1.24,
  "agent_notes": "Hook fuerte en 1.24s, corte en 87.4s antes de bajada de energía"
}
```

---

## 11. Stage 6: Assembly

**Script:** `scripts/assemble.py`  
**Core principle:** Every FFmpeg call works on proxies. Final export gets full-res.

### 11.1 Two-File Composition Strategy

Camera and screen are composited depending on profile and scene context:

**Shorts (9:16 — 1080×1920):**
- Camera face gets ~30% of frame (bottom-right corner, rounded mask)
- Screen fills 100% background (cropped/scaled to 9:16)
- Punch-ins on screen content at key moments

**Long-form (16:9 — 1920×1080):**
- Primary track: screen (1920×1080)
- Camera PiP: bottom-right, 320×180, with padding
- Scene switches: full-camera cuts for emphasis

### 11.2 Assembly FFmpeg Filter Chain (Shorts)

```bash
ffmpeg \
  -ss {keep_start} -t {keep_duration} -i proxies/{sid}/camera_proxy.mp4 \
  -ss {keep_start_with_offset} -t {keep_duration} -i proxies/{sid}/screen_proxy.mp4 \
  -filter_complex "
    [1:v]scale=1080:1920:force_original_aspect_ratio=increase,
         crop=1080:1920,
         setsar=1[screen_bg];
    [0:v]scale=324:576,
         format=yuva420p,
         geq='a=255*gt(min(min(X/8,Y/8),(min(W-X,H-Y))/8),0)':
              'lum=lum(X,Y)':'cb=cb(X,Y)':'cr=cr(X,Y)',
         pad=344:596:10:10:color=black@0[cam_pip];
    [screen_bg][cam_pip]overlay=W-w-20:H-h-20[v_composed];
    [0:a]loudnorm=I=-14:TP=-1:LRA=7[a_norm]
  " \
  -map "[v_composed]" -map "[a_norm]" \
  -c:v libx264 -preset fast -crf 23 \
  -c:a aac -b:a 192k \
  proxies/{sid}/assembled_shorts_proxy.mp4
```

### 11.3 Assembly FFmpeg Filter Chain (Long-form)

```bash
ffmpeg \
  -ss {keep_start} -t {keep_duration} -i proxies/{sid}/camera_proxy.mp4 \
  -ss {keep_start_with_offset} -t {keep_duration} -i proxies/{sid}/screen_proxy.mp4 \
  -filter_complex "
    [1:v]scale=1280:720,setsar=1[screen_main];
    [0:v]scale=320:180[cam_pip];
    [screen_main][cam_pip]overlay=W-w-20:H-h-20[v_composed];
    [0:a]loudnorm=I=-16:TP=-1.5:LRA=11[a_norm]
  " \
  -map "[v_composed]" -map "[a_norm]" \
  -c:v libx264 -preset fast -crf 22 \
  -c:a aac -b:a 192k \
  proxies/{sid}/assembled_longform_proxy.mp4
```

### 11.4 Batch Cut Assembly
Build the cut timeline as a concat demuxer list:

```python
def build_concat_list(keep_intervals: list, proxy_dir: str, output: str):
    """Write FFmpeg concat demuxer input file."""
    lines = []
    for i, interval in enumerate(keep_intervals):
        segment_path = f"{proxy_dir}/seg_{i:04d}.mp4"
        # Trim segment first
        run_ffmpeg([
            '-ss', str(interval['start']),
            '-to', str(interval['end']),
            '-i', camera_proxy,
            '-c', 'copy',
            segment_path
        ])
        lines.append(f"file '{segment_path}'")
    
    concat_file = f"{proxy_dir}/concat_list.txt"
    Path(concat_file).write_text('\n'.join(lines))
    
    # Concat all segments
    run_ffmpeg(['-f', 'concat', '-safe', '0',
                '-i', concat_file,
                '-c', 'copy', output])
```

---

## 12. Stage 7: Subtitle Generation

**Script:** `scripts/subtitle.py`  
**Style:** Burned-in, hardcoded, stylized. ASS format for full styling control.

### 12.1 ASS Subtitle Style Definitions

**`templates/subtitles/default.ass`** — Clean white with black outline:
```ass
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat,68,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,1,3,0,2,80,80,180,1
```

**`templates/subtitles/kinetic.ass`** — Word-by-word highlight (shorts style):
```ass
[V4+ Styles]
Style: Base,Montserrat,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,1,2,1,2,80,80,200,1
Style: Highlight,Montserrat,72,&H0000FFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,1,2,1,2,80,80,200,1
```

### 12.2 Subtitle Generation Logic

```python
def generate_ass_kinetic(segments: list, style_file: str, output: str):
    """
    Generate kinetic (word-by-word) ASS subtitles from word timestamps.
    Each dialogue line shows 3-4 words max.
    Active word switches to Highlight style.
    """
    events = []
    
    for seg in segments:
        words = seg['words']
        # Group into chunks of MAX_WORDS_PER_LINE (3 for shorts, 5 for longform)
        for chunk in chunk_words(words, max_words=3):
            for i, active_word in enumerate(chunk):
                # Build line with highlighted active word
                parts = []
                for j, word in enumerate(chunk):
                    if j == i:
                        parts.append(f"{{\\rHighlight}}{word['word']}{{\\rBase}}")
                    else:
                        parts.append(word['word'])
                
                line = ' '.join(parts)
                events.append(ASSDialogue(
                    start=active_word['start'],
                    end=active_word['end'],
                    style='Base',
                    text=line
                ))
    
    write_ass_file(style_file, events, output)
```

### 12.3 Subtitle Burn-in

```bash
ffmpeg -i assembled_{profile}_proxy.mp4 \
  -vf "ass=transcripts/{session_id}/subtitles_kinetic.ass" \
  -c:v libx264 -preset fast -crf 22 \
  -c:a copy \
  proxies/{session_id}/subtitled_{profile}_proxy.mp4
```

**Font install (WSL2):**
```bash
# Run once during setup
sudo apt install fonts-montserrat
fc-cache -fv
```

---

## 13. Stage 8: Export

**Script:** `scripts/export.py`  
**Rule:** This is the only stage that touches original full-resolution files.  
The assembled proxy's CUT DECISIONS are replayed on full-res input.

### Export Presets

**`templates/exports/shorts.json`** (YouTube Shorts / Reels / TikTok):
```json
{
  "resolution": "1080x1920",
  "fps": 30,
  "video_codec": "libx264",
  "video_preset": "slow",
  "video_crf": 18,
  "video_profile": "high",
  "video_level": "4.1",
  "audio_codec": "aac",
  "audio_bitrate": "192k",
  "audio_sample_rate": 44100,
  "movflags": "+faststart",
  "max_file_size_mb": 250
}
```

**`templates/exports/youtube_lf.json`** (YouTube long-form):
```json
{
  "resolution": "1920x1080",
  "fps": 30,
  "video_codec": "libx264",
  "video_preset": "slow",
  "video_crf": 17,
  "video_profile": "high",
  "video_level": "4.2",
  "audio_codec": "aac",
  "audio_bitrate": "320k",
  "audio_sample_rate": 48000,
  "movflags": "+faststart"
}
```

### Platform-specific notes
- **TikTok:** `max_muxing_queue_size 9999` flag required for some inputs.
- **Reels:** Identical to Shorts preset. Different output filename only.
- **YouTube Shorts:** Same as Shorts preset. YT detects aspect ratio automatically.
- **Long-form:** Encode pass 1 → stats → pass 2 for tightest quality at 1 hour+.

### Final export command template
```python
def export_final(session_id: str, target: str, cutmap: dict):
    preset = load_preset(target)
    cfg = load_session(session_id)
    offset = cfg['sync_offset_seconds']
    
    # Rebuild filter chain on original files using same cutmap
    build_concat_list(
        intervals=cutmap['keep_intervals'],
        camera_file=f"recordings/{session_id}/camera.mp4",
        screen_file=f"recordings/{session_id}/screen.mp4",
        offset=offset,
        resolution=preset['resolution'],
        fps=preset['fps'],
        output=f"exports/{session_id}/{target}.mp4",
        preset=preset
    )
```

---

## 14. Stage 9: Thumbnail Pipeline

**Script:** `scripts/thumbnail.py`  
**Approach:** Three methods chained in sequence.

### Step 1: Frame Grab Candidates
Extract top candidate frames from the assembled video at high-energy, non-silence moments:

```python
def extract_thumbnail_candidates(session_id: str, n_candidates: int = 12):
    energy_map = load_energy_map(session_id)
    # Find top N high-energy, non-silence moments
    candidates = sorted(
        [w for w in energy_map['windows'] if not w['low_energy']],
        key=lambda x: x['rms_norm'],
        reverse=True
    )[:n_candidates]
    
    for i, frame in enumerate(candidates):
        ffmpeg -ss {frame['t']} \
               -i recordings/{session_id}/camera.mp4 \
               -vframes 1 -q:v 2 \
               thumbnails/{session_id}/frame_grabs/frame_{i:03d}.jpg
```

### Step 2: AI Concept Generation (Agent)
```python
prompt = f"""
Genera un concepto de thumbnail para YouTube para este video:
- Título candidato: {titles[0]}
- Hook: {hooks[0]['text']}
- Concepto de thumbnail del brief: {brief['thumbnail_concept']}

Devuelve JSON:
{{
  "flux_prompt": str,  # prompt en inglés para generar imagen con IA
  "texto_principal": str,  # máx 4 palabras, impacto máximo
  "subtexto": str,  # máx 6 palabras
  "composicion": "cara_izquierda|cara_derecha|cara_centro|sin_cara",
  "emocion_facial": str,
  "colores_dominantes": [str, str],
  "estilo": str
}}
"""
# Output: thumbnails/{session_id}/concept.json
```

### Step 3: AI Image Generation (Flux via local or API)
```python
# Option A: Replicate API (fast, costs ~$0.003/image)
import replicate
output = replicate.run(
    "black-forest-labs/flux-schnell",
    input={"prompt": concept['flux_prompt'], "aspect_ratio": "16:9"}
)

# Option B: ComfyUI local (free, ~3min on CPU)
# Configured separately, called via REST API on localhost:8188
```

### Step 4: Text Overlay via FFmpeg
```bash
ffmpeg -i thumbnails/{session_id}/ai_generated.png \
  -vf "
    drawtext=fontfile='/usr/share/fonts/truetype/montserrat/Montserrat-ExtraBold.ttf':
             text='{texto_principal}':
             fontsize=120:fontcolor=white:
             x=(w-text_w)/2:y=h*0.65:
             shadowcolor=black:shadowx=4:shadowy=4,
    drawtext=fontfile='/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf':
             text='{subtexto}':
             fontsize=56:fontcolor=yellow:
             x=(w-text_w)/2:y=h*0.82:
             shadowcolor=black:shadowx=3:shadowy=3
  " \
  -frames:v 1 \
  thumbnails/{session_id}/final.png
```

**Output:** `thumbnails/{session_id}/final.png` (1280×720)

---

## 15. Remotion Component Architecture

**Purpose:** Motion assets only — intros, outros, lower thirds, kinetic captions, hook cards.  
**NOT used for:** cutting, audio, or export. Rendered outputs get composited back via FFmpeg.

### Component Tree

```
src/
├── Root.tsx
│   └── Composition registry
│       ├── Intro (3s, 90 frames @ 30fps)
│       ├── Outro (3s, 90 frames)
│       ├── LowerThird (5s, 150 frames)
│       ├── HookCard (2s, 60 frames)
│       └── KineticCaptions (dynamic duration)
│
├── compositions/
│   ├── Intro.tsx
│   │   Props: { brandName, tagline, bgColor }
│   │   Sequence: [logo fade in (0-20f)] → [tagline slide (20-60f)] → [hold (60-90f)]
│   │
│   ├── Outro.tsx
│   │   Props: { cta, channelName, socialHandles }
│   │   Sequence: [cta text (0-40f)] → [social handles (40-80f)] → [fade out (80-90f)]
│   │
│   ├── LowerThird.tsx
│   │   Props: { name, title, startFrame, duration }
│   │   Sequence: [slide in from left (0-15f)] → [hold] → [slide out (last 15f)]
│   │
│   ├── HookCard.tsx
│   │   Props: { hookText, bgColor, accentColor }
│   │   Sequence: [text scales in (0-10f)] → [hold] → [cut/fade]
│   │
│   └── KineticCaptions.tsx
│       Props: { words: [{text, startFrame, endFrame}], style }
│       Sequence: word-by-word, each word interpolates scale 0.8→1.0
│
└── utils/
    ├── brand.ts
    │   export const BRAND = {
    │     primaryColor: '#FFDD00',  // from brand.json
    │     bgColor: '#0A0A0A',
    │     fontFamily: 'Montserrat',
    │     fontWeightBold: 800
    │   }
    │
    └── timing.ts
        export const fps = 30;
        export const framesToMs = (f: number) => (f / fps) * 1000;
```

### Remotion render pipeline
```bash
# Render a single composition to transparent PNG sequence
npx remotion render \
  --composition=Intro \
  --props='{"brandName":"TuCanal","tagline":"Código que importa"}' \
  --output=exports/{session_id}/motion/intro.mov \
  --codec=prores-4444  # transparent background

# Composite over video via FFmpeg
ffmpeg -i exports/{session_id}/youtube_lf.mp4 \
       -i exports/{session_id}/motion/intro.mov \
       -filter_complex "[0:v][1:v]overlay=0:0:enable='between(t,0,3)'" \
       exports/{session_id}/youtube_lf_final.mp4
```

### `remotion/src/data/{session_id}.json` schema
```json
{
  "brand": { "name": "TuCanal", "tagline": "...", "colors": {} },
  "lowerThird": { "name": "Nombre Apellido", "title": "Desarrollador" },
  "hook": { "text": "¿Por qué nadie te enseñó esto?" },
  "outro": { "cta": "Suscríbete ya", "socials": ["@tucanal"] }
}
```

---

## 16. Agent Integration Points

All agent calls use `scripts/utils/agent.py`:

```python
import anthropic

client = anthropic.Anthropic(api_key=settings['anthropic_api_key'])

def call_agent(system: str, user: str, max_tokens: int = 1024) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}]
    )
    text = response.content[0].text
    # Strip markdown fences if present
    clean = text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
    return json.loads(clean)
```

### Agent call inventory

| Stage | Purpose | Input tokens est. | Output tokens est. |
|---|---|---|---|
| `brief` | Full edit brief from topic | ~300 | ~600 |
| `cutmap` | Hook/cut priorities from transcript | ~2000 | ~400 |
| `analyze` | Chapter detection from transcript | ~2500 | ~300 |
| `metadata` | Titles + descriptions + tags | ~500 | ~800 |
| `thumbnail` | Thumbnail concept + Flux prompt | ~400 | ~300 |

**Total per session: ~5700 input + ~2400 output tokens ≈ $0.02 per full pipeline run.**

---

## 17. Metadata Package Generation

**Script:** `scripts/brief.py` (re-runs post-assembly)

After assembly, a second agent call generates platform-specific metadata:

```python
# Input: final titles, hook used, chapter map, CTA
# Output: metadata/{session_id}/
#   titles.json — 5 title candidates with SEO reasoning
#   descriptions.json — YouTube, Reels, TikTok descriptions
#   tags.json — 15 tags per platform
#   hooks.json — final hook selection + alternatives
```

Descriptions are platform-specific:
- **YouTube:** 500-800 chars, timestamps of chapters, links, hashtags
- **Reels/TikTok:** 150 chars max, 5 hashtags, emoji-friendly

---

## 18. Configuration Files

### `config/settings.json`
```json
{
  "anthropic_api_key": "${ANTHROPIC_API_KEY}",
  "replicate_api_key": "${REPLICATE_API_KEY}",
  "recordings_mount": "/mnt/c/Users/user/Videos",
  "ffmpeg_threads": 0,
  "whisper_model": "large-v2",
  "whisper_compute_type": "int8",
  "default_profile": "longform",
  "proxy_resolution": "1280x720",
  "logs_level": "INFO"
}
```

### `config/brand.json`
```json
{
  "channel_name": "TuCanal",
  "tagline": "...",
  "primary_color": "#FFDD00",
  "bg_color": "#0A0A0A",
  "accent_color": "#FF4444",
  "font_primary": "Montserrat",
  "font_weight_title": 800,
  "font_weight_body": 600,
  "lower_third_name": "Nombre Apellido",
  "lower_third_title": "Tu Título",
  "social_handles": {
    "youtube": "@tucanal",
    "instagram": "@tucanal",
    "tiktok": "@tucanal"
  }
}
```

### `config/profiles.json`
```json
{
  "shorts": {
    "silence_threshold_db": -40,
    "silence_min_duration_s": 0.3,
    "collapse_to_s": 0.12,
    "trim_pad_before_s": 0.05,
    "trim_pad_after_s": 0.08,
    "remove_fillers": true,
    "filler_confidence_threshold": 0.75,
    "low_energy_min_duration_s": 2.0,
    "target_duration_s": 90,
    "max_duration_s": 60,
    "caption_words_per_line": 3,
    "caption_style": "kinetic",
    "pip_position": "bottom_right",
    "pip_size_ratio": 0.3,
    "aspect_ratio": "9:16",
    "resolution": "1080x1920"
  },
  "longform": {
    "silence_threshold_db": -42,
    "silence_min_duration_s": 0.5,
    "collapse_to_s": 0.25,
    "trim_pad_before_s": 0.1,
    "trim_pad_after_s": 0.12,
    "remove_fillers": false,
    "filler_confidence_threshold": 0.9,
    "low_energy_min_duration_s": 5.0,
    "target_duration_s": null,
    "max_duration_s": null,
    "caption_words_per_line": 7,
    "caption_style": "default",
    "pip_position": "bottom_right",
    "pip_size_ratio": 0.167,
    "aspect_ratio": "16:9",
    "resolution": "1920x1080"
  }
}
```

---

## 19. Python Dependencies

**`requirements.txt`:**
```
faster-whisper==1.1.0
anthropic>=0.40.0
click>=8.1.0
scipy>=1.12.0
numpy>=1.26.0
pydantic>=2.0.0
rich>=13.0.0         # beautiful CLI output
replicate>=0.33.0    # for Flux thumbnail generation
pathlib
concurrent-futures
```

**System dependencies (WSL2 apt):**
```bash
sudo apt update && sudo apt install -y \
  ffmpeg \
  fonts-montserrat \
  python3-pip \
  python3-venv \
  mpv              # for preview command
```

---

## 20. `scripts/pipeline.py` — Orchestrator

```python
STAGES = [
    ('transcribe', transcribe.run),
    ('analyze',    analyze.run),
    ('cutmap',     cutmap.run),
    ('assemble',   assemble.run),
    ('subtitle',   subtitle.run),
    ('export',     export.run),
    ('thumbnail',  thumbnail.run),
    ('metadata',   metadata.run),
]

def run_pipeline(session_id: str, from_stage: str = None):
    session = load_session(session_id)
    start_idx = 0
    
    if from_stage:
        start_idx = [s[0] for s in STAGES].index(from_stage)
    
    for name, fn in STAGES[start_idx:]:
        console.print(f"[bold cyan]→ {name}[/]")
        try:
            fn(session_id)
            update_status(session_id, name)
            console.print(f"[bold green]✓ {name} done[/]")
        except Exception as e:
            console.print(f"[bold red]✗ {name} failed: {e}[/]")
            console.print(f"[yellow]Resume with: content-os run --session {session_id} --from {name}[/]")
            raise SystemExit(1)
```

---

## 21. DaVinci Resolve QA Layer

Only triggered manually after pipeline completes. No automation required.

### What to check in Resolve
1. Open `exports/{session_id}/youtube_lf.mp4` (or shorts).
2. Spot-check silence removal — listen at 1.5× speed.
3. Check subtitle sync at 3 random timestamps.
4. Audio loudness meter: confirm LUFS between -14 (shorts) and -16 (long-form).
5. Color: quick LUT or no-op if lighting was clean.
6. Export overwrite if corrections needed.

### Resolve API automation (optional, Phase 2)
Resolve's Python API can automate project setup:
```python
# scripts/resolve_setup.py
import DaVinciResolveScript as dvr
resolve = dvr.scriptapp("Resolve")
pm = resolve.GetProjectManager()
project = pm.CreateProject(session_id)
mp = project.GetMediaPool()
mp.ImportMedia([f"exports/{session_id}/youtube_lf.mp4"])
```

---

## 22. MVP Build Order (for opencode)

Build in this exact sequence. Each item is a working, testable deliverable.

| # | Deliverable | Files to build | Test command |
|---|---|---|---|
| 1 | CLI skeleton + session management | `cli.py`, `scripts/ingest.py`, `config/settings.json` | `content-os ingest --help` |
| 2 | Transcription | `scripts/transcribe.py`, `scripts/utils/whisper_utils.py` | `content-os transcribe --session test` |
| 3 | Silence detection + filler removal | `scripts/analyze.py` (silence + filler only) | `content-os analyze --session test` → check `silence_map.json` |
| 4 | Cut map generation (algorithmic only) | `scripts/cutmap.py` (no agent yet) | `content-os cutmap --session test --profile shorts` |
| 5 | FFmpeg rough cut | `scripts/assemble.py`, `scripts/utils/ffmpeg.py` | `content-os assemble --session test --profile shorts` → watch proxy |
| 6 | Subtitle generation + burn-in | `scripts/subtitle.py`, `templates/subtitles/` | `content-os subtitle --session test` → check burned proxy |
| 7 | Export presets (all 4 platforms) | `scripts/export.py`, `templates/exports/` | `content-os export --session test --targets all` |
| 8 | Brief generation (agent) | `scripts/brief.py`, `scripts/utils/agent.py` | `content-os brief --topic "test"` → verify `brief.json` |
| 9 | Cut map agent pass | Add agent call to `scripts/cutmap.py` | Compare cutmaps before/after agent |
| 10 | Thumbnail pipeline | `scripts/thumbnail.py` | `content-os thumbnail --session test` → check `thumbnails/` |
| 11 | Metadata generation | Add to `scripts/brief.py` | `content-os brief --post-assembly --session test` |
| 12 | Remotion compositions | `remotion/src/` | `npx remotion preview` |
| 13 | Sync detection | `scripts/sync.py` | `content-os sync --session test` → verify offset |
| 14 | Full pipeline runner | `scripts/pipeline.py` | `content-os run --session test` → 10 assets out |

---

## 23. Error Handling Contract

Every script must:
1. Check that all input files from previous stage exist before running.
2. Write outputs atomically (write to `.tmp`, rename on success).
3. Log all FFmpeg stderr to `analysis/{session_id}/logs/{stage}.log`.
4. On failure: print the exact re-run command. Never silently skip.
5. Validate JSON outputs with Pydantic models before writing.

```python
# Example Pydantic model
class SilenceInterval(BaseModel):
    start: float
    end: float
    duration: float
    type: Literal['leading', 'trailing', 'between_sentences']

class SilenceMap(BaseModel):
    total_silence_s: float
    silence_intervals: list[SilenceInterval]
    potential_time_saved_s: float
```

---

## 24. Setup Script

**`scripts/setup.sh`** — run once in WSL2:
```bash
#!/bin/bash
set -e

echo "→ Installing system deps..."
sudo apt update && sudo apt install -y ffmpeg fonts-montserrat mpv python3-pip python3-venv

echo "→ Creating Python virtualenv..."
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

echo "→ Installing Remotion..."
cd remotion && npm install && cd ..

echo "→ Setting up CLI alias..."
echo 'alias content-os="source /path/to/content-os/.venv/bin/activate && python /path/to/content-os/cli.py"' >> ~/.bashrc

echo "→ Verifying FFmpeg..."
ffmpeg -version | head -1

echo "→ Verifying Whisper (downloads model on first run)..."
python -c "from faster_whisper import WhisperModel; print('Whisper OK')"

echo "✓ Setup complete. Edit config/settings.json to add your API keys."
```

---

## 25. Typical Daily Workflow

```bash
# 1. Generate brief (5 min before recording)
content-os brief \
  --topic "Cómo estructuro mis componentes React" \
  --goal educativo --tone "directo" \
  --duration 10 --platform youtube_lf,shorts \
  --session 20250615_react_components

# 2. Review brief
cat briefs/20250615_react_components/brief.md

# 3. Record (external — OBS or camera)

# 4. Register files
content-os ingest \
  --session 20250615_react_components \
  --camera /mnt/c/Users/user/Videos/cam.mp4 \
  --screen /mnt/c/Users/user/Videos/screen.mp4

# 5. Auto-detect sync
content-os sync --session 20250615_react_components

# 6. Run full pipeline (~8-15 min on Ryzen 7)
content-os run --session 20250615_react_components

# 7. Review status
content-os status --session 20250615_react_components

# 8. Preview shorts cut
content-os preview --session 20250615_react_components --profile shorts

# 9. Open in Resolve for QA (optional)
# exports/20250615_react_components/ contains all 4 platform variants

# 10. Publish
```

**Estimated pipeline runtime on Ryzen 7, 16GB RAM:**
- Transcription (12 min audio, large-v2 int8): ~4 min
- Analysis: ~1 min
- Cut map: ~30s
- Assembly (proxy): ~2 min
- Subtitles: ~1 min
- Export (full res, 4 targets): ~6 min
- Thumbnail: ~2 min (Replicate API) or ~4 min (local)
- **Total: ~16-20 min for 10 publishable assets**
