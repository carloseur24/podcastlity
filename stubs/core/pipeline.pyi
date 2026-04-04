"""Type stubs for scripts.core.pipeline module."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class StageInfo:
    name: str
    status_key: str
    module: Optional[Callable[..., dict[str, Any]]]
    description: str

class Pipeline:
    STAGES: list[StageInfo]

    def __init__(self, workspace: str) -> None: ...
    def get_stages_for_profile(self, profile: str = "default") -> list[StageInfo]: ...
    def run_full(
        self,
        session_id: str,
        on_progress: Optional[Callable[[str, str], None]] = None,
    ) -> dict[str, dict[str, Any]]: ...
    def run_stage(
        self,
        session_id: str,
        stage_name: str,
    ) -> dict[str, Any]: ...
    def get_available_stages(
        self,
        session_id: str,
    ) -> list[StageInfo]: ...
