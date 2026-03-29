import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from scripts.utils import session
from scripts.models import Session


class TestSessionManager:
    def test_session_manager_init(self, workspace_root):
        sm = session.SessionManager(str(workspace_root))
        assert sm.workspace_root == workspace_root
        assert sm.sessions_dir == workspace_root / "recordings"

    def test_get_session_path(self, workspace_root):
        sm = session.SessionManager(str(workspace_root))
        path = sm.get_session_path("test123")
        assert path == workspace_root / "recordings" / "test123"

    def test_session_exists_false(self, workspace_root):
        sm = session.SessionManager(str(workspace_root))
        assert not sm.session_exists("nonexistent")

    def test_session_exists_true(self, workspace_root, mock_session):
        sm = session.SessionManager(str(workspace_root))
        sm.save_session(Session(**mock_session))
        assert sm.session_exists(mock_session["session_id"])

    def test_save_and_load_session(self, workspace_root, mock_session):
        sm = session.SessionManager(str(workspace_root))
        original = Session(**mock_session)
        sm.save_session(original)

        loaded = sm.load_session(mock_session["session_id"])
        assert loaded.session_id == original.session_id
        assert loaded.topic == original.topic
        assert loaded.profile == original.profile

    def test_load_session_raises_on_missing(self, workspace_root):
        sm = session.SessionManager(str(workspace_root))
        with pytest.raises(FileNotFoundError):
            sm.load_session("nonexistent")

    def test_create_session(self, workspace_root):
        sm = session.SessionManager(str(workspace_root))
        new_session = sm.create_session(
            session_id="new_session",
            topic="Test Topic",
            profile="shorts",
            goal="entretenimiento",
            tone="casual",
            cta="Like y subscribe",
            duration=5,
        )

        assert new_session.session_id == "new_session"
        assert new_session.topic == "Test Topic"
        assert new_session.profile == "shorts"
        assert new_session.goal == "entretenimiento"
        assert new_session.tone == "casual"
        assert new_session.cta == "Like y subscribe"
        assert new_session.rough_duration_min == 5
        assert new_session.status == "created"

    def test_list_sessions_empty(self, workspace_root):
        sm = session.SessionManager(str(workspace_root))
        sessions = sm.list_sessions()
        assert sessions == []

    def test_list_sessions_returns_all(self, workspace_root, mock_session):
        sm = session.SessionManager(str(workspace_root))
        sm.save_session(Session(**mock_session))

        sm.save_session(Session(
            session_id="second_session",
            topic="Another Topic",
            profile="longform",
        ))

        sessions = sm.list_sessions()
        assert len(sessions) == 2
        session_ids = [s.session_id for s in sessions]
        assert "second_session" in session_ids
        assert mock_session["session_id"] in session_ids

    def test_update_status(self, workspace_root, mock_session):
        sm = session.SessionManager(str(workspace_root))
        sm.save_session(Session(**mock_session))

        sm.update_status(mock_session["session_id"], "proxied")

        loaded = sm.load_session(mock_session["session_id"])
        assert loaded.status == "proxied"

    def test_get_next_stage(self, workspace_root, mock_session):
        sm = session.SessionManager(str(workspace_root))
        sm.save_session(Session(**mock_session))

        next_stage = sm.get_next_stage(mock_session["session_id"])
        assert next_stage == "ingested"

    def test_get_next_stage_at_end(self, workspace_root):
        sm = session.SessionManager(str(workspace_root))
        sm.save_session(Session(
            session_id="done_session",
            topic="Done",
            status="done",
        ))

        next_stage = sm.get_next_stage("done_session")
        assert next_stage is None


class TestLoadSettings:
    def test_load_settings(self, workspace_root):
        settings = session.load_settings(str(workspace_root))
        assert "recordings_mount" in settings
        assert settings["ffmpeg_path"] == "imageio"

    def test_load_settings_creates_default(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "settings.json").write_text('{"test": "value"}')

        settings = session.load_settings(str(tmp_path))
        assert settings["test"] == "value"


class TestLoadProfile:
    def test_load_profile_longform(self, workspace_root):
        profile = session.load_profile("longform", str(workspace_root))
        assert profile["aspect_ratio"] == "16:9"
        assert profile["silence_threshold_db"] == -42

    def test_load_profile_shorts(self, workspace_root):
        profile = session.load_profile("shorts", str(workspace_root))
        assert profile["aspect_ratio"] == "9:16"
        assert profile["target_duration_s"] == 90

    def test_load_profile_fallback_to_longform(self, workspace_root):
        profile = session.load_profile("nonexistent", str(workspace_root))
        assert profile["aspect_ratio"] == "16:9"


class TestLoadBrand:
    def test_load_brand(self, workspace_root):
        brand = session.load_brand(str(workspace_root))
        assert brand["channel_name"] == "TestChannel"
        assert brand["primary_color"] == "#FFDD00"


class TestLoadFillerWords:
    def test_load_filler_words(self, workspace_root):
        words = session.load_filler_words(str(workspace_root))
        assert "este" in words
        assert "eh" in words
        assert "mm" in words

    def test_load_filler_words_strips_and_lowercases(self, workspace_root):
        words = session.load_filler_words(str(workspace_root))
        assert all(w == w.lower() for w in words)


class TestEnsureSessionDirs:
    def test_ensure_session_dirs_creates_all(self, workspace_root):
        session_id = "test_dirs_session"
        session.ensure_session_dirs(str(workspace_root), session_id)

        expected_dirs = [
            workspace_root / "recordings" / session_id,
            workspace_root / "proxies" / session_id,
            workspace_root / "audio" / session_id,
            workspace_root / "transcripts" / session_id,
            workspace_root / "analysis" / session_id,
            workspace_root / "cutmaps" / session_id,
            workspace_root / "exports" / session_id,
            workspace_root / "thumbnails" / session_id / "frame_grabs",
            workspace_root / "briefs" / session_id,
            workspace_root / "metadata" / session_id,
        ]

        for d in expected_dirs:
            assert d.exists(), f"Expected {d} to exist"

    def test_ensure_session_dirs_idempotent(self, workspace_root):
        session_id = "idempotent_session"
        session.ensure_session_dirs(str(workspace_root), session_id)
        session.ensure_session_dirs(str(workspace_root), session_id)

        assert (workspace_root / "recordings" / session_id).exists()
