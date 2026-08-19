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
    """按比赛/回合/机台保存成绩截图（真实抓分为 JPEG，测试模式为 PNG），并生成只读 URL。"""

    _SAFE = re.compile(r"^[A-Za-z0-9_.-]+$")
    _EXTS = (".jpg", ".png")

    def __init__(self, root: Path | None = None) -> None:
        module_root = Path(__file__).resolve().parents[1]
        self.root = root or module_root / "runtime" / "screenshots"
        self.match_id: str | None = None

    def start_match(self) -> str:
        self.match_id = uuid.uuid4().hex
        (self.root / self.match_id).mkdir(parents=True, exist_ok=True)
        return self.match_id

    def save(self, round_key: str, machine_id: str, data: bytes, ext: str = ".png") -> Path | None:
        if self.match_id is None or not data:
            return None
        if ext not in self._EXTS:
            raise ValueError(f"不支持的截图格式: {ext!r}")
        path = self._path(self.match_id, round_key, machine_id, ext)
        path.parent.mkdir(parents=True, exist_ok=True)
        # 同一机台/回合只保留一份截图，清掉另一格式的旧文件（如重抓后 PNG→JPEG）
        for other in self._EXTS:
            if other != ext:
                self._path(self.match_id, round_key, machine_id, other).unlink(missing_ok=True)
        path.write_bytes(data)
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
            if self._existing_path(self.match_id, round_key, machine_id) is not None:
                urls[machine_id] = (
                    f"/api/screenshot/{self.match_id}/{quote(round_key, safe='')}/"
                    f"{quote(machine_id, safe='')}"
                )
        return urls

    def resolve(self, match_id: str, round_key: str, machine_id: str) -> Path | None:
        if not self._valid_component(match_id) or not self._valid_component(round_key):
            return None
        return self._existing_path(match_id, round_key, machine_id)

    def _existing_path(self, match_id: str, round_key: str, machine_id: str) -> Path | None:
        for ext in self._EXTS:
            path = self._path(match_id, round_key, machine_id, ext)
            if path.is_file():
                return path
        return None

    def _path(self, match_id: str, round_key: str, machine_id: str, ext: str = ".png") -> Path:
        digest = hashlib.sha256(machine_id.encode("utf-8")).hexdigest()[:12]
        slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", machine_id).strip("._") or "machine"
        # 文件名带上回合信息（如 round-3-game1_IIDX_2-e7ca4ea2c3eb.jpg），
        # 方便导播直接在目录里按回合辨认截图。
        return self.root / match_id / round_key / f"{round_key}_{slug}-{digest}{ext}"

    @classmethod
    def _valid_component(cls, value: str) -> bool:
        return bool(value and cls._SAFE.fullmatch(value))


def round_key_for_session(session: Any) -> str:
    info = session.current_round_info()
    game_suffix = f"-game{info['game_no']}" if info.get("total_games", 1) > 1 else ""
    if info["mode"] == "team":
        return f"round-{info['round_no']}{game_suffix}"
    return f"{info['group']}-round-{info['round_no']}{game_suffix}"
