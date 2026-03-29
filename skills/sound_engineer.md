# AUDIO_ENGINEER_SKILL.md
> Agent skill: Voice audio analysis and adaptive FFmpeg filter chain generation.
> Use this skill when processing any voice recording before silence detection, assembly, or export.

---

## Your role

You are a sound engineer with deep knowledge of voice acoustics and FFmpeg audio filters.
Your job is NOT to apply a preset. Your job is to **diagnose the recording first**, then
build a filter chain that corrects exactly what is wrong — nothing more.

The cardinal rule: **less is more. If a problem isn't audible, don't fix it.**

---

## Step 1 — Diagnose before touching anything

Run this FFmpeg measurement command first. Never skip this.

```bash
ffmpeg -i {input_wav} \
  -af "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:key=lavfi.astats.Overall.Peak_level:key=lavfi.astats.Overall.Noise_floor" \
  -f null - 2>&1 | grep -E "RMS_level|Peak_level|Noise_floor"
```

Also get the frequency spectrum of the first 10 seconds (noise profile window):
```bash
ffmpeg -i {input_wav} -t 5 \
  -af "aformat=s16,asetnsamples=n=8192,afftfilt=real='hypot(re,im)'" \
  -f null - 2>&1
```

From the measurements, build this diagnosis JSON before writing any filter:

```json
{
  "rms_db": -28.4,
  "peak_db": -6.2,
  "noise_floor_db": -58.0,
  "headroom_db": 6.2,
  "snr_estimate_db": 29.6,
  "problems_detected": ["noise_floor_high", "low_headroom"],
  "problems_not_present": ["clipping", "sibilance", "proximity_effect"],
  "environment_guess": "condenser_quiet_room"
}
```

SNR estimate = `rms_db - noise_floor_db`. If SNR < 20dB, noise is the dominant problem.

---

## Step 2 — Problem identification map

Match measurements to problems. Only flag a problem if the measurement confirms it.

### Noise floor (measured: `noise_floor_db`)
| Noise floor | Verdict | Action |
|---|---|---|
| Below -65dB | Clean | No denoising needed |
| -65 to -50dB | Mild noise | `afftdn=nr=8:nf={noise_floor+5}` |
| -50 to -40dB | Moderate noise | `afftdn=nr=15:nf={noise_floor+5}` + `agate` |
| Above -40dB | Heavy noise | `afftdn=nr=22:nf={noise_floor+3}` + `agate` + re-check |

**afftdn parameters:**
- `nr` = noise reduction strength (0–97). Never exceed 25 for voice — artifacts appear above this.
- `nf` = estimated noise floor in dB. Set to `noise_floor_measured + 5`. This is the most important parameter to get right. Too low = no reduction. Too high = voice artifacts.
- Do NOT use `om=so` — deprecated in FFmpeg 7.x.

### Noise gate (`agate`) — use only when noise floor > -50dB
```
agate=threshold={linear}:ratio={r}:attack=10:release=50
```
Convert dB threshold to linear: `threshold_linear = 10^(dB/20)`
- Noise floor -45dB → linear = 0.0056 → use `threshold=0.008` (slightly above floor)
- Noise floor -40dB → linear = 0.010 → use `threshold=0.014`
- `ratio`: 4–8 for mild noise, 10–15 for heavy noise
- `attack`: always 10ms minimum to avoid clicks on voice onset
- `release`: 50ms for fast speech, 80ms for slow/deliberate speech

### Low-frequency rumble
Present when: recording near AC, fan, traffic, or with condenser mic close to desk.
Signature: `rms_db` at 20–80Hz band is within 20dB of `rms_db` overall.

Fix: `highpass=f=80:poles=2` (gentle roll-off, safe for all voices)
If voice is deep (fundamental ~100Hz): use `highpass=f=60:poles=2` instead.
Never use a high-pass above 100Hz — you will cut the fundamental and voice loses body.

### Boxiness (300–500Hz buildup)
Present when: recorded in small untreated room, close-mic'd in enclosed space.
Signature: voice sounds hollow/cardboard when played back.
Fix (only if confirmed by ear): `equalizer=f=400:t=q:w=1.5:g=-2`
Do NOT apply this preemptively. Only on confirmed boxy recordings.

### Proximity effect (excess bass from close-mic)
Present when: `rms_db` 80–200Hz band is disproportionately high vs. midrange.
Signature: voice sounds unnaturally boomy, pressure-y.
Fix: `equalizer=f=120:t=q:w=1.0:g=-3` to `g=-5` depending on severity.

### Nasal resonance (1–2kHz)
Present when: voice sounds like speaker has a cold.
Fix (only if confirmed): `equalizer=f=1500:t=q:w=1.2:g=-2`
This is a corrective cut only — never boost 1–2kHz on voice.

### Sibilance (5–10kHz harshness)
Present when: S, SH, CH sounds are piercing or distorted.
Do NOT add a high-frequency boost if sibilance is present.
Fix: `equalizer=f=7000:t=q:w=1.0:g=-2` to `g=-4`

### Air/presence boost (8–12kHz) — use sparingly
Only when: recording is muffled (condenser with windscreen, dynamic mic muffled environment).
Fix: `equalizer=f=10000:t=q:w=0.8:g=2`
Maximum boost: +3dB. If you need more, the problem isn't EQ — it's the recording.

### Loudness normalization — always last in chain
Always apply. Standard targets:
- Shorts/Reels/TikTok: `loudnorm=I=-14:TP=-1:LRA=7`
- YouTube long-form: `loudnorm=I=-16:TP=-1.5:LRA=11`
- Analysis-only (for silence detection): `loudnorm=I=-16:TP=-1.5:LRA=11`

---

## Step 3 — Build the filter chain

Order is non-negotiable:
```
1. highpass (remove rumble)
2. afftdn (spectral denoising)
3. agate (noise gate)
4. equalizer corrections (only confirmed problems)
5. loudnorm (always last)
```

**Template:**
```python
def build_filter_chain(diagnosis: dict, target: str = "analysis") -> str:
    filters = []

    # 1. High-pass — always apply, frequency depends on voice
    hp_freq = 60 if diagnosis.get("deep_voice") else 80
    filters.append(f"highpass=f={hp_freq}:poles=2")

    # 2. Spectral denoising — only if noise floor > -65dB
    nf = diagnosis["noise_floor_db"]
    if nf > -65:
        if nf > -50:
            nr = 22 if nf > -40 else 15
        else:
            nr = 8
        filters.append(f"afftdn=nr={nr}:nf={nf + 5}")

    # 3. Noise gate — only if noise floor > -50dB
    if nf > -50:
        import math
        linear = 10 ** ((nf + 8) / 20)  # 8dB above floor
        ratio = 12 if nf > -40 else 6
        filters.append(
            f"agate=threshold={linear:.4f}:ratio={ratio}:attack=10:release=60"
        )

    # 4. Corrective EQ — only confirmed problems
    if "proximity_effect" in diagnosis["problems_detected"]:
        filters.append("equalizer=f=120:t=q:w=1.0:g=-3")
    if "boxiness" in diagnosis["problems_detected"]:
        filters.append("equalizer=f=400:t=q:w=1.5:g=-2")
    if "sibilance" in diagnosis["problems_detected"]:
        filters.append("equalizer=f=7000:t=q:w=1.0:g=-3")
    if "muffled" in diagnosis["problems_detected"]:
        filters.append("equalizer=f=10000:t=q:w=0.8:g=2")

    # 5. Loudness normalization — always
    lufs = "-14" if target in ("shorts", "reels", "tiktok") else "-16"
    tp = "-1.0" if target in ("shorts", "reels", "tiktok") else "-1.5"
    lra = "7" if target in ("shorts", "reels", "tiktok") else "11"
    filters.append(f"loudnorm=I={lufs}:TP={tp}:LRA={lra}")

    return ",".join(filters)
```

---

## Step 4 — Silence detection threshold calibration

After preprocessing, measure the new noise floor of `master_clean.wav`.
Set `silence_threshold_db` = `new_noise_floor + 8`.

If new noise floor after preprocessing is:
- -60dB → set threshold to -52dB
- -55dB → set threshold to -47dB
- -50dB → set threshold to -42dB

A gap must drop **below** the threshold to be detected as silence.
With well-preprocessed audio, you should see at minimum 15–30 silence intervals
in a 10-minute recording (every breath pause, sentence gap).

If silence count is still 0–2 after preprocessing:
1. Run `afftdn` with `nr` increased by +5.
2. Increase `agate threshold` by ×1.5.
3. Re-measure noise floor. Repeat until floor is at least 8dB below threshold.

---

## Step 5 — Quality gates (fail fast)

After generating `master_clean.wav`, run these checks. Fail loudly if any fail.

```python
def validate_preprocessing(report: dict) -> list[str]:
    warnings = []
    errors = []

    rms_after = report["rms_after_db"]
    noise_after = report["noise_floor_after_db"]
    snr_after = rms_after - noise_after

    # Error: noise reduction made it worse
    if report["noise_floor_after_db"] > report["noise_floor_before_db"]:
        errors.append("FAIL: noise floor increased after preprocessing — filter chain error")

    # Error: voice was destroyed (RMS dropped too much)
    delta_rms = abs(report["rms_after_db"] - report["rms_before_db"])
    if delta_rms > 12:
        errors.append(f"FAIL: RMS changed by {delta_rms:.1f}dB — voice likely damaged")

    # Warning: still not clean enough for reliable silence detection
    if noise_after > -48:
        warnings.append(f"WARN: noise floor still {noise_after:.1f}dB — try --mode heavy")

    # Warning: SNR too low even after processing
    if snr_after < 18:
        warnings.append(f"WARN: SNR is {snr_after:.1f}dB — silence detection may be unreliable")

    return errors, warnings
```

---

## What NOT to do (common LLM mistakes to avoid)

- **Never apply a V-curve EQ** (`bass boost + treble boost + mid scoop`). This is cargo-cult audio engineering. Every voice and mic combination is different.
- **Never add EQ boosts to compensate for noise** — boosting frequencies lifts noise equally.
- **Never use `nr` > 25 in `afftdn`** — voice artifacts (metallic, watery distortion) appear above this.
- **Never set high-pass above 100Hz** — you cut the vocal fundamental and the voice loses body.
- **Never apply `loudnorm` twice** in the same chain — the second pass will fight the first.
- **Never use narrow notch filters speculatively** — if you can't hear the problem, the filter does nothing except introduce phase artifacts.
- **Never output AAC from `audio_preprocess.py`** — analysis tools (scipy, silence detection) require PCM WAV. Always output `-c:a pcm_s16le`.

---

## Reference: FFmpeg filter quick lookup

| Problem | Filter | Key params |
|---|---|---|
| Rumble / low-freq noise | `highpass` | `f=80, poles=2` |
| Broadband noise (fan, AC, hiss) | `afftdn` | `nr=8–22, nf=floor+5` |
| Noise in silences | `agate` | `threshold=linear, ratio=6–12` |
| Proximity effect (boominess) | `equalizer` | `f=120, t=q, w=1.0, g=-3 to -5` |
| Boxiness (room resonance) | `equalizer` | `f=400, t=q, w=1.5, g=-2` |
| Nasality | `equalizer` | `f=1500, t=q, w=1.2, g=-2` |
| Sibilance | `equalizer` | `f=7000, t=q, w=1.0, g=-3` |
| Muffled/dull (windscreen) | `equalizer` | `f=10000, t=q, w=0.8, g=+2` |
| Loudness normalization | `loudnorm` | `I=-14/-16, TP=-1/-1.5, LRA=7/11` |
| Stereo width (export only) | `extrastereo` | `m=1.5` |

---

## Integration into content-os pipeline

```
ingest
  └─→ transcribe          (uses master.wav — raw, before any processing)
  └─→ audio_preprocess    (diagnose → build chain → output master_clean.wav)
        └─→ analyze       (uses master_clean.wav for silence + energy detection)
        └─→ cutmap
        └─→ assemble      (replaces audio track with master_clean.wav)
        └─→ export        (run_enhance_audio for EQ/stereo here, after cuts)
```

`run_enhance_audio` (EQ + stereo widening) is **export-time only**, not analysis-time.
`audio_preprocess` is **analysis-time only** — its job is a clean noise floor, not a beautiful sound.
