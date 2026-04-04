"""Tests for Pipeline and exceptions."""

import pytest

from scripts.core.pipeline import Pipeline
from scripts.core.exceptions import (
    StageError,
    SessionNotFoundError,
    StageNotFoundError,
)


class TestPipeline:
    """Test Pipeline orchestration."""

    def test_pipeline_init(self, workspace_root):
        pipeline = Pipeline(str(workspace_root))
        assert pipeline.workspace == str(workspace_root)

    def test_get_stages_for_profile(self, workspace_root):
        """Test that get_stages_for_profile returns stages list."""
        pipeline = Pipeline(str(workspace_root))
        stages = pipeline.get_stages_for_profile("default")
        assert isinstance(stages, list)
        assert len(stages) > 0

    def test_get_stages_names(self, workspace_root):
        """Test that stages have proper names."""
        pipeline = Pipeline(str(workspace_root))
        stages = pipeline.get_stages_for_profile("default")
        stage_names = [s.name for s in stages]
        # Verify we have expected stages
        assert "Ingest" in stage_names
        assert "Proxies" in stage_names


class TestExceptions:
    """Test exception classes."""

    def test_session_not_found_error(self):
        err = SessionNotFoundError("test_session")
        assert "test_session" in str(err)
        # Basic exception test - message contains the session ID
        assert "not found" in str(err).lower() or "test_session" in str(err)

    def test_stage_not_found_error(self):
        err = StageNotFoundError("InvalidStage")
        assert "InvalidStage" in str(err)
        # Basic exception test
        assert "not found" in str(err).lower() or "InvalidStage" in str(err)

    def test_stage_error(self):
        err = StageError("Proxies", "Something failed")
        assert "Proxies" in str(err)
        assert "Something failed" in str(err)
        assert err.stage == "Proxies"

    def test_stage_error_str(self):
        err = StageError("Test", "error message")
        assert str(err) == "Stage 'Test' failed: error message"
