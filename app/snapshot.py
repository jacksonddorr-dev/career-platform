import json
import logging
from pathlib import Path

from app.config import get_settings
from app.content import PublicProfile, dict_to_profile

logger = logging.getLogger(__name__)


class SnapshotStore:
    def __init__(self, path: str | None = None):
        self.path = Path(path or get_settings().snapshot_path)

    def save(self, content: PublicProfile | dict) -> None:
        payload = content.to_dict() if isinstance(content, PublicProfile) else content
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self) -> PublicProfile | None:
        if not self.path.exists():
            return None
        try:
            return dict_to_profile(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError) as exc:
            logger.warning("public snapshot unavailable: %s", exc)
            return None


if __name__ == "__main__":
    from app.content import build_public_profile
    from app.db import SessionLocal

    with SessionLocal() as db:
        profile = build_public_profile(db)
        if profile is None:
            raise SystemExit("No published profile is available")
        SnapshotStore().save(profile)
        print("Wrote", SnapshotStore().path)
