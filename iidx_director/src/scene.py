"""OBS scene/overlay coordination state.

The coordinator deliberately keeps pending work in memory.  Runtime state files
may contain old logical scene labels, so all public methods normalize to the
actual OBS scene names before storing anything.
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from typing import Any

from .push.overlay import TEMPLATES, template_for_scene


ACTUAL_SCENES = (
    "SP_BPL",
    "SP_Arena",
    "DP_BPL",
    "DP_Arena",
    "Team_Scoreboard",
    "Knockout_Scoreboard",
    "Live",
    "Scoreboard_web",
    "Grid",
)


class PendingError(RuntimeError):
    """Invalid or conflicting pending scene operation."""


@dataclass
class OverlaySceneSnapshot:
    template: str
    texts: dict[str, Any] = field(default_factory=dict)
    hues: dict[str, Any] = field(default_factory=dict)
    version: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "template": self.template,
            "texts": copy.deepcopy(self.texts),
            "hues": copy.deepcopy(self.hues),
            "version": self.version,
        }


@dataclass
class PendingScene:
    id: str
    scene: str
    template: str
    texts: dict[str, Any]
    hues: dict[str, Any]
    source: str
    action: str | None = None
    action_data: dict[str, Any] = field(default_factory=dict)
    source_scene: str | None = None
    status: str = "pending"
    failed_stage: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "scene": self.scene,
            "template": self.template,
            "texts": copy.deepcopy(self.texts),
            "hues": copy.deepcopy(self.hues),
            "source": self.source,
            "status": self.status,
            "failed_stage": self.failed_stage,
            "error": self.error,
        }


class SceneCoordinator:
    """Normalize scenes and own the one in-flight scene transaction."""

    def __init__(self, scenes: dict[str, str] | None = None) -> None:
        self.aliases = dict(scenes or {})
        self.snapshots: dict[str, OverlaySceneSnapshot] = {}
        self.active_scene: str | None = None
        self.pending: PendingScene | None = None
        self._versions: dict[str, int] = {}
        for scene in ACTUAL_SCENES:
            self._ensure_snapshot(scene, template_for_scene(scene, "team"))

    def update_aliases(self, scenes: dict[str, str]) -> None:
        self.aliases = dict(scenes)

    def resolve(self, requested: str | None) -> str | None:
        if not requested:
            return None
        raw = str(requested).strip()
        if raw in ACTUAL_SCENES:
            return raw
        if raw in self.aliases:
            return self.resolve(self.aliases[raw])
        # Compatibility with old logical labels and custom configured values.
        normalized = raw.lower().replace(" ", "").replace("_", "").replace("-", "")
        aliases = {
            "sp团队赛1v1": "SP_BPL", "sp团队赛2v2": "SP_Arena",
            "sp团队赛": "SP_BPL", "dp团队赛": "DP_BPL",
            "dp团队赛1v1": "DP_BPL", "dp团队赛2v2": "DP_Arena",
            "sp个人赛": "SP_Arena", "dp个人赛": "DP_Arena",
            "现场摄像": "Live", "scoreboard": "Scoreboard_web",
            "scoreboardweb": "Scoreboard_web",
        }
        if normalized in aliases:
            return aliases[normalized]
        return raw if raw in set(self.aliases.values()) else None

    def _ensure_snapshot(self, scene: str, template: str | None = None) -> OverlaySceneSnapshot:
        if scene not in self.snapshots:
            self.snapshots[scene] = OverlaySceneSnapshot(template or "live")
            self._versions[scene] = 0
        return self.snapshots[scene]

    def snapshot(self, scene: str) -> dict[str, Any]:
        return self._ensure_snapshot(scene, template_for_scene(scene, "team")).to_dict()

    def set_snapshot(
        self,
        scene: str,
        template: str,
        texts: dict[str, Any] | None = None,
        hues: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if template not in TEMPLATES:
            raise PendingError(f"未知 overlay 模板: {template!r}")
        current = self._ensure_snapshot(scene, template)
        current.template = template
        if texts is not None:
            current.texts = copy.deepcopy(texts)
        if hues is not None:
            current.hues = copy.deepcopy(hues)
        current.version = self._versions.get(scene, 0) + 1
        self._versions[scene] = current.version
        return current.to_dict()

    def create_pending(
        self,
        scene: str,
        template: str,
        texts: dict[str, Any] | None = None,
        hues: dict[str, Any] | None = None,
        *,
        source: str,
        action: str | None = None,
        action_data: dict[str, Any] | None = None,
        source_scene: str | None = None,
    ) -> PendingScene:
        if self.pending is not None:
            raise PendingError("已有待应用的场景操作")
        actual = self.resolve(scene) or scene
        if template not in TEMPLATES:
            raise PendingError(f"未知 overlay 模板: {template!r}")
        prior = self.snapshot(actual)
        pending = PendingScene(
            id=uuid.uuid4().hex,
            scene=actual,
            template=template,
            texts=copy.deepcopy(prior["texts"] if texts is None else texts),
            hues=copy.deepcopy(prior["hues"] if hues is None else hues),
            source=source,
            action=action,
            action_data=copy.deepcopy(action_data or {}),
            source_scene=source_scene,
        )
        self.pending = pending
        return pending

    def require_pending(self, pending_id: str | None = None) -> PendingScene:
        if self.pending is None:
            raise PendingError("没有待应用的场景操作")
        if pending_id and pending_id != self.pending.id:
            raise PendingError("待应用操作 ID 不匹配")
        return self.pending

    def mark(self, status: str, *, failed_stage: str | None = None, error: str | None = None) -> None:
        pending = self.require_pending()
        pending.status = status
        pending.failed_stage = failed_stage
        pending.error = error

    def complete(self) -> None:
        pending = self.require_pending()
        self.set_snapshot(pending.scene, pending.template, pending.texts, pending.hues)
        self.active_scene = pending.scene
        self.pending = None

    def cancel(self, pending_id: str | None = None) -> PendingScene:
        pending = self.require_pending(pending_id)
        self.pending = None
        return pending

    def public_state(self) -> dict[str, Any]:
        return {
            "active_scene": self.active_scene,
            "snapshots": {scene: snap.to_dict() for scene, snap in self.snapshots.items()},
            "pending": self.pending.to_dict() if self.pending else None,
        }
