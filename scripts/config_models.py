"""
Pydantic models for audio filter configuration validation.
These contracts ensure config values are within valid ranges before FFmpeg runs.
"""

from pydantic import BaseModel, Field, field_validator


class HighpassSettings(BaseModel):
    default_freq: int = Field(default=80, ge=30, le=150)
    deep_voice_freq: int = Field(default=60, ge=30, le=100)
    muffled_voice_freq: int = Field(default=120, ge=80, le=200)
    aggressive_freq: int = Field(default=100, ge=50, le=150)
    poles: int = Field(default=2, ge=1, le=4)


class AfftdnSettings(BaseModel):
    nr_mild: int = Field(default=15, ge=0, le=25, description="Max 25 for voice to avoid artifacts")
    nr_moderate: int = Field(default=25, ge=0, le=35)
    nr_heavy: int = Field(default=35, ge=0, le=50)
    nr_max_voice: int = Field(default=40, ge=0, le=60)
    noise_floor_offset: float = Field(default=5.0, ge=0, le=15)

    @field_validator("nr_mild")
    @classmethod
    def nr_mild_max(cls, v):
        if v > 25:
            raise ValueError(f"nr_mild={v} exceeds 25 - voice artifacts will occur")
        return v


class CompressorSettings(BaseModel):
    threshold_db: float = Field(default=-25, ge=-40, le=-10)
    ratio: float = Field(default=4, ge=1, le=20)
    attack_ms: float = Field(default=20, ge=1, le=100)
    release_ms: float = Field(default=250, ge=50, le=1000)
    makeup_db: float = Field(default=1, ge=1, le=64, description="FFmpeg requires >= 1")
    knee: float = Field(default=1, ge=1, le=8)

    @field_validator("makeup_db")
    @classmethod
    def makeup_min(cls, v):
        if v < 1:
            raise ValueError(f"makeup_db={v} - FFmpeg acompressor requires makeup >= 1")
        return v


class AgateSettings(BaseModel):
    above_floor_db: float = Field(default=6, ge=3, le=15)
    ratio_mild: float = Field(default=8, ge=1, le=20)
    ratio_heavy: float = Field(default=16, ge=4, le=30)
    attack_ms: float = Field(default=3, ge=1, le=50)
    release_ms: float = Field(default=50, ge=10, le=200)


class EQBandSettings(BaseModel):
    freq: int = Field(default=100, ge=20, le=20000)
    width: float = Field(default=1.0, ge=0.1, le=10.0)
    gain: float = Field(default=0, ge=-20, le=20)


class EQSettings(BaseModel):
    grave: EQBandSettings = Field(
        default_factory=lambda: EQBandSettings(freq=160, width=0.8, gain=3)
    )
    mud_cut: EQBandSettings = Field(
        default_factory=lambda: EQBandSettings(freq=350, width=1.2, gain=-2)
    )
    presence: EQBandSettings = Field(
        default_factory=lambda: EQBandSettings(freq=3500, width=1.0, gain=3)
    )
    voice_clarity: EQBandSettings = Field(
        default_factory=lambda: EQBandSettings(freq=4000, width=0.8, gain=2)
    )
    proximity: EQBandSettings = Field(
        default_factory=lambda: EQBandSettings(freq=120, width=1.0, gain=-3)
    )
    boxiness: EQBandSettings = Field(
        default_factory=lambda: EQBandSettings(freq=400, width=1.5, gain=-2)
    )
    sibilance: EQBandSettings = Field(
        default_factory=lambda: EQBandSettings(freq=7000, width=1.0, gain=-3)
    )


class LoudnormProfile(BaseModel):
    I: float = Field(default=-14, ge=-24, le=-9, description="Integrated loudness LUFS")
    TP: float = Field(default=-1, ge=-5, le=0, description="True Peak dB")
    LRA: float = Field(default=9, ge=1, le=20, description="Loudness Range LU")


class LoudnormSettings(BaseModel):
    default: LoudnormProfile = Field(
        default_factory=lambda: LoudnormProfile(I=-16, TP=-1.5, LRA=11)
    )


class StereoSettings(BaseModel):
    extrastereo_m: float = Field(default=1.5, ge=0, le=3, description="0=mono, 1=equal, >1=wide")


class DiagnosticSettings(BaseModel):
    noise_clean_below: float = Field(default=-65, ge=-80, le=-40)
    noise_mild_below: float = Field(default=-50, ge=-70, le=-30)
    noise_moderate_below: float = Field(default=-40, ge=-60, le=-20)
    nr_max_voice: int = Field(default=25, ge=0, le=50)
    rms_delta_max: float = Field(default=12, ge=3, le=30)
    snr_minimum: float = Field(default=18, ge=5, le=40)
    noise_floor_warn: float = Field(default=-48, ge=-70, le=-30)
    muffled_ratio_threshold: float = Field(default=2.0, ge=0.5, le=5.0)
    quiet_voice_rms: float = Field(default=-25, ge=-50, le=-10)
    underwater_peak_hz: int = Field(default=250, ge=100, le=500)


class FiltersConfig(BaseModel):
    highpass: HighpassSettings = Field(default_factory=HighpassSettings)
    afftdn: AfftdnSettings = Field(default_factory=AfftdnSettings)
    compressor: CompressorSettings = Field(default_factory=CompressorSettings)
    agate: AgateSettings = Field(default_factory=AgateSettings)
    eq: EQSettings = Field(default_factory=EQSettings)
    loudnorm: LoudnormSettings = Field(default_factory=LoudnormSettings)
    stereo: StereoSettings = Field(default_factory=StereoSettings)
    diagnostic: DiagnosticSettings = Field(default_factory=DiagnosticSettings)


def validate_filters_config(config_dict: dict) -> tuple[list[str], list[str]]:
    """
    Validate filters.json config and return (errors, warnings).
    Call this at config load time to catch issues early.
    """
    errors = []
    warnings = []

    try:
        FiltersConfig(**config_dict)
    except Exception as e:
        errors.append(f"Config validation failed: {e}")

    afftdn = config_dict.get("afftdn", {})
    nr_mild = afftdn.get("nr_mild", 15)
    if nr_mild > 25:
        warnings.append(f"afftdn.nr_mild={nr_mild} exceeds 25 - voice artifacts likely")

    nr_heavy = afftdn.get("nr_heavy", 35)
    if nr_heavy > 50:
        warnings.append(f"afftdn.nr_heavy={nr_heavy} is very high - severe artifacts expected")

    comp = config_dict.get("compressor", {})
    makeup = comp.get("makeup_db", 1)
    if makeup < 1:
        errors.append(f"compressor.makeup_db={makeup} - FFmpeg requires >= 1")

    return errors, warnings
