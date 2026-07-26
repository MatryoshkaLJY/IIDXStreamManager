"""比赛成绩截图的持久化与安全读取。"""

from __future__ import annotations

import base64
import hashlib
import re
import uuid
from pathlib import Path
from urllib.parse import quote
from typing import Any


# Valid 1x1 transparent PNG used by the director test mode.
EMPTY_SCREENSHOT_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class ScreenshotStore:
    """按比赛/回合/机台保存 PNG，并生成只读 URL。"""

    _SAFE = re.compile(r"^[A-Za-z0-9_.-]+$")

    def __init__(self, root: Path | None = None) -> None:
        module_root = Path(__file__).resolve().parents[1]
        self.root = root or module_root / "runtime" / "screenshots"
        self.match_id: str | None = None

    def start_match(self) -> str:
        self.match_id = uuid.uuid4().hex
        (self.root / self.match_id).mkdir(parents=True, exist_ok=True)
        return self.match_id

    def save(self, round_key: str, machine_id: str, png: bytes) -> Path | None:
        if self.match_id is None or not png:
            return None
        path = self._path(self.match_id, round_key, machine_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png)
        return path

    def current_urls(self, session: Any) -> dict[str, str]:
        if self.match_id is None or session is None:
            return {}
        if getattr(session.phase, "value", session.phase) not in (
            "PREP", "LIVE", "REVIEW", "PUSHED"
        ):
            return {}
        round_key = round_key_for_session(session)
        urls: dict[str, str] = {}
        for slot in session.assignments.values():
            machine_id = slot["machine"]
            if self._path(self.match_id, round_key, machine_id).exists():
                urls[machine_id] = (
                    f"/api/screenshot/{self.match_id}/{quote(round_key, safe='')}/"
                    f"{quote(machine_id, safe='')}"
                )
        return urls

    def resolve(self, match_id: str, round_key: str, machine_id: str) -> Path | None:
        if not self._valid_component(match_id) or not self._valid_component(round_key):
            return None
        path = self._path(match_id, round_key, machine_id)
        if not path.is_file():
            return None
        return path

    def _path(self, match_id: str, round_key: str, machine_id: str) -> Path:
        digest = hashlib.sha256(machine_id.encode("utf-8")).hexdigest()[:12]
        slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", machine_id).strip("._") or "machine"
        return self.root / match_id / round_key / f"{slug}-{digest}.png"

    @classmethod
    def _valid_component(cls, value: str) -> bool:
        return bool(value and cls._SAFE.fullmatch(value))


def round_key_for_session(session: Any) -> str:
    info = session.current_round_info()
    if info["mode"] == "team":
        return f"round-{info['round_no']}"
    return f"{info['group']}-round-{info['round_no']}"
