"""Type stubs for scripts.models module."""

from datetime import datetime
from typing import Any, Literal, Optional

class Session:
    session_id: str
    topic: str
    platform_targets: list[str]
    profile: Optional[Literal["default"]]
    cta: str
    rough_duration_min: int
    video_file: str
    created_at: str
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
    ]

    def __init__(
        self,
        session_id: str,
        topic: str,
        platform_targets: Optional[list[str]] = None,
        profile: Optional[Literal["default"]] = ...,
        cta: str = ...,
        rough_duration_min: int = ...,
        video_file: str = ...,
        created_at: Optional[str] = None,
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
        ] = None,
    ) -> None: ...
    def model_dump(self) -> dict[str, Any]: ...
    def model_dump_json(self, indent: Optional[int] = None) -> str: ...

class Word:
    word: str
    start: float
    end: float
    probability: float

    def __init__(
        self,
        word: str,
        start: float,
        end: float,
        probability: float,
    ) -> None: ...

class TranscriptSegment:
    id: int
    start: float
    end: float
    text: str
    words: list[Word]

    def __init__(
        self,
        id: int,
        start: float,
        end: float,
        text: str,
        words: Optional[list[Word]] = None,
    ) -> None: ...

class Transcript:
    language: str
    duration: float
    segments: list[TranscriptSegment]
    text: str

    def __init__(
        self,
        language: str = ...,
        duration: float = ...,
        segments: Optional[list[TranscriptSegment]] = None,
        text: str = ...,
    ) -> None: ...

class TranscriptRaw:
    text: str
    segments: list[dict[str, Any]]

    def __init__(
        self,
        text: str,
        segments: Optional[list[dict[str, Any]]] = None,
    ) -> None: ...

class SilenceInterval:
    start: float
    end: float
    type: Literal["leading", "trailing", "middle"]
    energy_db: Optional[float]

    def __init__(
        self,
        start: float,
        end: float,
        type: Literal["leading", "trailing", "middle"],
        energy_db: Optional[float] = None,
    ) -> None: ...

class SilenceMap:
    silence_intervals: list[SilenceInterval]
    min_silence_duration_s: float
    silence_threshold_db: float
    potential_time_saved_s: float

    def __init__(
        self,
        silence_intervals: Optional[list[SilenceInterval]] = None,
        min_silence_duration_s: float = ...,
        silence_threshold_db: float = ...,
        potential_time_saved_s: float = ...,
    ) -> None: ...

class FillerWord:
    word: str
    start: float
    end: float
    confidence: float

    def __init__(
        self,
        word: str,
        start: float,
        end: float,
        confidence: float,
    ) -> None: ...

class FillerMap:
    fillers: list[FillerWord]
    total_count: int

    def __init__(
        self,
        fillers: Optional[list[FillerWord]] = None,
        total_count: int = ...,
    ) -> None: ...

class EnergyWindow:
    start: float
    end: float
    rms_db: float

    def __init__(
        self,
        start: float,
        end: float,
        rms_db: float,
    ) -> None: ...

class EnergyMap:
    windows: list[EnergyWindow]
    low_energy_intervals: list[dict[str, float]]
    avg_rms_db: float

    def __init__(
        self,
        windows: Optional[list[EnergyWindow]] = None,
        low_energy_intervals: Optional[list[dict[str, float]]] = None,
        avg_rms_db: float = ...,
    ) -> None: ...

class Chapter:
    title: str
    start: float
    end: float

    def __init__(
        self,
        title: str,
        start: float,
        end: float,
    ) -> None: ...

class ChapterMap:
    chapters: list[Chapter]

    def __init__(
        self,
        chapters: Optional[list[Chapter]] = None,
    ) -> None: ...

class KeepInterval:
    start: float
    end: float
    type: Literal["hook", "content", "broll", "transition"]
    scene_id: Optional[int]

    def __init__(
        self,
        start: float,
        end: float,
        type: Literal["hook", "content", "broll", "transition"] = ...,
        scene_id: Optional[int] = None,
    ) -> None: ...

class CutMap:
    profile: str
    total_input_duration_s: float
    total_output_duration_s: float
    keep_intervals: list[KeepInterval]
    removed_silence_s: float
    removed_fillers: int
    hook_start_s: float
    agent_notes: str

    def __init__(
        self,
        profile: str = ...,
        total_input_duration_s: float = ...,
        total_output_duration_s: float = ...,
        keep_intervals: Optional[list[KeepInterval]] = None,
        removed_silence_s: float = ...,
        removed_fillers: int = ...,
        hook_start_s: float = ...,
        agent_notes: str = ...,
    ) -> None: ...

class BriefHook:
    text: str
    type: Literal["pregunta", "estadistica", "afirmacion", "historia"]
    energy: Literal["alta", "media"]

    def __init__(
        self,
        text: str,
        type: Literal["pregunta", "estadistica", "afirmacion", "historia"] = ...,
        energy: Literal["alta", "media"] = ...,
    ) -> None: ...

class BriefThumbnailConcept:
    description: str
    type: Literal["text_overlay", "scene_highlight", "graphic"]

    def __init__(
        self,
        description: str,
        type: Literal["text_overlay", "scene_highlight", "graphic"] = ...,
    ) -> None: ...

class BriefSceneOutline:
    topic: str
    duration_s: float
    key_points: list[str]

    def __init__(
        self,
        topic: str,
        duration_s: float,
        key_points: Optional[list[str]] = None,
    ) -> None: ...

class Brief:
    session_id: str
    topic: str
    target_duration_s: float
    hooks: list[BriefHook]
    thumbnail_concepts: list[BriefThumbnailConcept]
    scene_outlines: list[BriefSceneOutline]

    def __init__(
        self,
        session_id: str,
        topic: str,
        target_duration_s: float,
        hooks: Optional[list[BriefHook]] = None,
        thumbnail_concepts: Optional[list[BriefThumbnailConcept]] = None,
        scene_outlines: Optional[list[BriefSceneOutline]] = None,
    ) -> None: ...

class Metadata:
    session_id: str
    topic: str
    duration_s: float
    resolution: str
    fps: int
    codec: str
    bitrate_kbps: int

    def __init__(
        self,
        session_id: str,
        topic: str,
        duration_s: float,
        resolution: str,
        fps: int,
        codec: str,
        bitrate_kbps: int,
    ) -> None: ...
