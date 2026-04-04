"""Pipeline orchestrator - coordinates all pipeline stages."""

from typing import Callable, Optional
from dataclasses import dataclass

from scripts.utils.session import SessionManager
from scripts.core.exceptions import StageError, StageNotFoundError, SessionNotFoundError

from scripts.core.stages import (
    ingest,
    proxies,
    voice_extract,
    transcribe,
    analyze,
    cutmap,
    assemble,
    export,
)


@dataclass
class StageInfo:
    name: str
    status_key: str
    module: Optional[callable]
    description: str


class Pipeline:
    """
    Pipeline orchestrator for video content processing.

    Coordinates all stages and provides callbacks for UI integration.
    """

    LONGFORM_STAGES = [
        StageInfo("Ingest", "ingested", ingest, "Copy files to session directory"),
        StageInfo("Proxies", "proxied", proxies, "Create proxies and extract audio"),
        StageInfo(
            "VoiceExtract", "voice_extracted", voice_extract, "Extract voice using VAD"
        ),
        StageInfo("Transcribe", "transcribed", transcribe, "Whisper speech-to-text"),
        StageInfo("Analyze", "analyzed", analyze, "Silence/filler/energy detection"),
        StageInfo("Cutmap", "cutmapped", cutmap, "Generate edit decisions"),
        StageInfo("Assemble", "assembled", assemble, "Trim and concatenate"),
        StageInfo("Export", "exported", export, "Render final videos"),
    ]

    SHORTS_STAGES = [
        StageInfo("Ingest", "ingested", ingest, "Copy files to session directory"),
        StageInfo("Proxies", "proxied", proxies, "Create proxies and extract audio"),
        StageInfo(
            "VoiceExtract",
            "voice_extracted",
            voice_extract,
            "Extract voice + noise reduction",
        ),
        StageInfo("Prepare", "cutmapped", None, "Analyze + cutmap"),
        StageInfo("Assemble", "assembled", assemble, "Trim and concatenate"),
        StageInfo("Export", "exported", export, "Render final videos"),
    ]

    def __init__(self, workspace: str):
        """
        Initialize pipeline with workspace.

        Args:
            workspace: Path to workspace root
        """
        self.workspace = workspace
        self.session_manager = SessionManager(workspace)

    def get_stages_for_profile(self, profile: str) -> list[StageInfo]:
        """Get stage list for profile."""
        if profile == "shorts":
            return self.SHORTS_STAGES
        return self.LONGFORM_STAGES

    def run_full(
        self,
        session_id: str,
        on_progress: Optional[Callable[[str, str], None]] = None,
    ) -> dict:
        """
        Run full pipeline for a session.

        Args:
            session_id: The session identifier
            on_progress: Optional callback(stage_name, status)

        Returns:
            dict with results from all stages
        """
        try:
            session = self.session_manager.load_session(session_id)
        except FileNotFoundError:
            raise SessionNotFoundError(f"Session '{session_id}' not found")

        profile = session.profile or "longform"
        stages = self.get_stages_for_profile(profile)

        current_status = session.status or "created"

        start_idx = 0
        for i, stage in enumerate(stages):
            if stage.status_key == current_status:
                start_idx = i
                break

        results = {}
        for stage in stages[start_idx:]:
            if on_progress:
                on_progress(stage.name, "running")

            try:
                if stage.name == "Prepare" and profile == "shorts":
                    result = self._run_prepare(session_id)
                else:
                    result = stage.module.run(session_id, self.workspace)

                results[stage.status_key] = result

                if on_progress:
                    on_progress(stage.name, "done")

            except Exception as e:
                if on_progress:
                    on_progress(stage.name, "failed")
                raise StageError(stage.name, str(e))

        return results

    def run_stage(self, session_id: str, stage_name: str) -> dict:
        """
        Run a single stage.

        Args:
            session_id: The session identifier
            stage_name: Stage name (e.g., "Ingest", "Proxies")

        Returns:
            dict with stage result
        """
        try:
            session = self.session_manager.load_session(session_id)
        except FileNotFoundError:
            raise SessionNotFoundError(f"Session '{session_id}' not found")

        profile = session.profile or "longform"
        stages = self.get_stages_for_profile(profile)

        stage_info = None
        for s in stages:
            if s.name.lower() == stage_name.lower():
                stage_info = s
                break

        if not stage_info:
            raise StageNotFoundError(f"Stage '{stage_name}' not found")

        if stage_info.name == "Prepare" and profile == "shorts":
            return self._run_prepare(session_id)

        if stage_info.module is None:
            raise StageError(stage_info.name, "No module defined for this stage")

        return stage_info.module.run(session_id, self.workspace)

    def _run_prepare(self, session_id: str) -> dict:
        """Run combined prepare stage for shorts (analyze + cutmap)."""
        analyze_result = analyze.run(session_id, self.workspace)

        cutmap_result = cutmap.run(session_id, self.workspace)

        return {
            "analyze": analyze_result,
            "cutmap": cutmap_result,
        }

    def get_session_status(self, session_id: str) -> str:
        """Get current session status."""
        session = self.session_manager.load_session(session_id)
        return session.status or "created"

    def get_available_stages(self, session_id: str) -> list[StageInfo]:
        """Get list of stages with their completion status."""
        try:
            session = self.session_manager.load_session(session_id)
        except FileNotFoundError:
            return []

        profile = session.profile or "longform"
        stages = self.get_stages_for_profile(profile)

        current_status = session.status or "created"

        result = []
        for s in stages:
            completed = self._is_stage_completed(s.status_key, current_status, stages)
            result.append((s, completed))

        return result

    def _is_stage_completed(
        self, stage_key: str, current_status: str, stages: list[StageInfo]
    ) -> bool:
        """Check if a stage is completed based on current status."""
        stage_idx = 0
        current_idx = 0

        for i, s in enumerate(stages):
            if s.status_key == stage_key:
                stage_idx = i
            if s.status_key == current_status:
                current_idx = i

        return stage_idx < current_idx
