import json
from pathlib import Path
from typing import Optional
from ..models import Session


class SessionManager:
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.sessions_dir = self.workspace_root / "recordings"
    
    def get_session_path(self, session_id: str) -> Path:
        return self.sessions_dir / session_id
    
    def session_exists(self, session_id: str) -> bool:
        return (self.get_session_path(session_id) / "session.json").exists()
    
    def load_session(self, session_id: str) -> Session:
        session_file = self.get_session_path(session_id) / "session.json"
        if not session_file.exists():
            raise FileNotFoundError(f"Session {session_id} not found")
        data = json.loads(session_file.read_text())
        return Session(**data)
    
    def save_session(self, session: Session) -> None:
        session_dir = self.get_session_path(session.session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        session_file = session_dir / "session.json"
        session_file.write_text(session.model_dump_json(indent=2))
    
    def create_session(
        self,
        session_id: str,
        topic: str,
        profile: str = "longform",
        goal: str = "educativo",
        tone: str = "directo",
        cta: str = "Suscribete",
        duration: int = 10,
    ) -> Session:
        session = Session(
            session_id=session_id,
            topic=topic,
            profile=profile,  # type: ignore
            goal=goal,
            tone=tone,
            cta=cta,
            rough_duration_min=duration,
        )
        self.save_session(session)
        return session
    
    def list_sessions(self) -> list[Session]:
        sessions = []
        if not self.sessions_dir.exists():
            return sessions
        for session_dir in sorted(self.sessions_dir.iterdir()):
            if session_dir.is_dir():
                session_file = session_dir / "session.json"
                if session_file.exists():
                    try:
                        session = self.load_session(session_dir.name)
                        sessions.append(session)
                    except Exception:
                        pass
        return sessions
    
    def update_status(self, session_id: str, status: str) -> None:
        session = self.load_session(session_id)
        session.status = status  # type: ignore
        self.save_session(session)
    
    def get_next_stage(self, session_id: str) -> Optional[str]:
        status_order = [
            "created", "ingested", "proxied", "transcribed",
            "analyzed", "cutmapped", "assembled", "exported", "done"
        ]
        session = self.load_session(session_id)
        current_idx = status_order.index(session.status) if session.status in status_order else 0
        if current_idx < len(status_order) - 1:
            return status_order[current_idx + 1]
        return None


def load_settings(workspace_root: str) -> dict:
    settings_file = Path(workspace_root) / "config" / "settings.json"
    return json.loads(settings_file.read_text())


def load_profile(profile_name: str, workspace_root: str) -> dict:
    profiles_file = Path(workspace_root) / "config" / "profiles.json"
    profiles = json.loads(profiles_file.read_text())
    return profiles.get(profile_name, profiles["longform"])


def load_brand(workspace_root: str) -> dict:
    brand_file = Path(workspace_root) / "config" / "brand.json"
    return json.loads(brand_file.read_text())


def load_filler_words(workspace_root: str) -> list[str]:
    filler_file = Path(workspace_root) / "config" / "filler_words_es.txt"
    return [w.strip().lower() for w in filler_file.read_text().splitlines() if w.strip()]


def ensure_session_dirs(workspace_root: str, session_id: str) -> None:
    base = Path(workspace_root)
    dirs = [
        base / "recordings" / session_id,
        base / "proxies" / session_id,
        base / "audio" / session_id,
        base / "transcripts" / session_id,
        base / "analysis" / session_id,
        base / "cutmaps" / session_id,
        base / "exports" / session_id,
        base / "thumbnails" / session_id / "frame_grabs",
        base / "briefs" / session_id,
        base / "metadata" / session_id,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
