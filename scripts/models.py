from pathlib import Path
from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class Session(BaseModel):
    session_id: str
    topic: str
    platform_targets: list[str] = Field(
        default_factory=lambda: ["youtube_lf", "shorts"]
    )
    profile: Optional[Literal["longform", "shorts", "both"]] = "longform"
    goal: str = "educativo"
    tone: str = "directo"
    cta: str = "Suscribete"
    rough_duration_min: int = 10
    camera_file: str = ""
    screen_file: str = ""
    sync_offset_seconds: float = 0.0
    sync_method: Literal["manual", "auto"] = "manual"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    status: Optional[
        Literal[
            "created",
            "ingested",
            "proxied",
            "voice_extracted",
            "transcribed",
            "analyzed",
            "cutmapped",
            "assembled",
            "subtitled",
            "exported",
            "done",
        ]
    ] = "created"


class Word(BaseModel):
    word: str
    start: float
    end: float
    probability: float


class TranscriptSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    words: list[Word] = Field(default_factory=list)
    avg_logprob: float = 0.0
    no_speech_prob: float = 0.0


class TranscriptRaw(BaseModel):
    language: str = "es"
    duration: float = 0.0
    segments: list[TranscriptSegment] = Field(default_factory=list)


class Transcript(BaseModel):
    language: str = "es"
    duration: float = 0.0
    segments: list[TranscriptSegment] = Field(default_factory=list)
    text: str = ""


class SilenceInterval(BaseModel):
    start: float
    end: float
    duration: float
    type: Literal["leading", "trailing", "between_sentences"]


class SilenceMap(BaseModel):
    total_silence_s: float = 0.0
    silence_intervals: list[SilenceInterval] = Field(default_factory=list)
    potential_time_saved_s: float = 0.0


class FillerWord(BaseModel):
    word: str
    start: float
    end: float
    segment_id: int
    confidence: float


class FillerMap(BaseModel):
    total_fillers: int = 0
    filler_rate_per_minute: float = 0.0
    fillers: list[FillerWord] = Field(default_factory=list)


class EnergyWindow(BaseModel):
    t: float
    rms_norm: float
    low_energy: bool


class EnergyMap(BaseModel):
    windows: list[EnergyWindow] = Field(default_factory=list)
    low_energy_intervals: list[SilenceInterval] = Field(default_factory=list)


class Chapter(BaseModel):
    scene_id: int
    start_s: float
    title: str


class ChapterMap(BaseModel):
    chapters: list[Chapter] = Field(default_factory=list)


class KeepInterval(BaseModel):
    start: float
    end: float
    type: Literal["hook", "content", "broll", "transition"] = "content"
    scene_id: Optional[int] = None


class CutMap(BaseModel):
    profile: str = "shorts"
    total_input_duration_s: float = 0.0
    total_output_duration_s: float = 0.0
    keep_intervals: list[KeepInterval] = Field(default_factory=list)
    removed_silence_s: float = 0.0
    removed_fillers: int = 0
    hook_start_s: float = 0.0
    agent_notes: str = ""


class BriefHook(BaseModel):
    text: str
    type: Literal["pregunta", "estadistica", "afirmacion", "historia"]
    energy: Literal["alta", "media"] = "media"


class BriefThumbnailConcept(BaseModel):
    texto_principal: str
    subtexto: str
    emocion: str
    colores: list[str]
    composicion: str


class BriefSceneOutline(BaseModel):
    id: int
    titulo: str
    descripcion: str
    duracion_s: int


class Brief(BaseModel):
    titles: list[str] = Field(default_factory=list)
    hooks: list[BriefHook] = Field(default_factory=list)
    thumbnail_concept: Optional[BriefThumbnailConcept] = None
    scene_outline: list[BriefSceneOutline] = Field(default_factory=list)
    broll_ideas: list[str] = Field(default_factory=list)
    motion_style: Literal["energetico", "limpio", "cinematico"] = "limpio"
    retention_notes: list[str] = Field(default_factory=list)
    hook_timestamp_target_s: int = 3
    export_targets: list[str] = Field(default_factory=list)


class Metadata(BaseModel):
    titles: list[str] = Field(default_factory=list)
    hooks: list[str] = Field(default_factory=list)
    descriptions: dict[str, str] = Field(default_factory=dict)
    tags: dict[str, list[str]] = Field(default_factory=dict)
