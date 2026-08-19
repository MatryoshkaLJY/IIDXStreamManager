"""OBS 场景控制连接（唯一的 obsws 控制通道，端口 4455）。

机台截图走 obs_manager.OBSManager 的独立连接（见 monitor.py），
本类只负责场景列表与切换。
"""

from __future__ import annotations

import re
import logging
from collections.abc import Mapping
from typing import Any

import obsws_python

logger = logging.getLogger(__name__)


class OBSClient:
    def __init__(self, host: str = "localhost", port: int = 4455, password: str | None = None,
                 timeout: int = 3) -> None:
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self._client: obsws_python.ReqClient | None = None

    @property
    def connected(self) -> bool:
        return self._client is not None

    def connect(self) -> None:
        self.disconnect()
        self._client = obsws_python.ReqClient(
            host=self.host, port=self.port, password=self.password or "", timeout=self.timeout
        )
        self._client.get_version()  # 验证连接

    def disconnect(self) -> None:
        if self._client is not None:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None

    def get_scenes(self) -> list[str]:
        self._require()
        resp = self._client.send("GetSceneList", raw=True)  # type: ignore[union-attr]
        return [s["sceneName"] for s in resp.get("scenes", [])]

    def switch_scene(self, name: str) -> None:
        self._require()
        self._client.set_current_program_scene(name)  # type: ignore[union-attr]

    def apply_match_visibility(
        self,
        scene: str,
        play_type: str,
        assignments: Mapping[str, Mapping[str, str]],
        team_by_player: Mapping[str, str] | None = None,
        individual: bool = False,
    ) -> None:
        """Apply the OBS source visibility layout for a confirmed round."""
        if scene == "SP_Arena":
            self._apply_sp_arena(assignments, individual=individual)
        elif scene == "DP_Arena":
            self._apply_dp_arena()
        elif scene == "SP_BPL":
            self._apply_sp_bpl(assignments, team_by_player or {})
        elif scene == "DP_BPL":
            self._apply_dp_bpl(assignments, team_by_player or {})

    def _apply_sp_arena(
        self,
        assignments: Mapping[str, Mapping[str, str]],
        *,
        individual: bool = False,
    ) -> None:
        active: set[tuple[int, str]] = set()
        for slot in assignments.values():
            active.add((self._machine_number(slot["machine"]), self._side_name(slot["side"])))

        for machine in range(1, 5):
            for side in ("1P", "2P"):
                self._set_group_enabled(
                    "SP_Arena", f"SP_C{machine}_{side}", (machine, side) in active
                )

        # 个人赛中 MIDUI / SongName / BPM 只展示 1 号机台玩家所在侧的信息
        machine_one_side = next(
            (item_side for machine, item_side in active if machine == 1), None
        )
        for side in ("1P", "2P"):
            if individual and machine_one_side is not None:
                used = side == machine_one_side
            else:
                used = any(item_side == side for _, item_side in active)
            for group in (
                f"SP_MIDUI_{side}",
                f"SP_{side}_SongName",
                f"SP_{side}_BPM",
            ):
                self._set_group_children("SP_Arena", group, "IIDX#1", group_enabled=used)

    def _apply_dp_arena(self) -> None:
        for group in ("Gauges", "DP_SongName", "DP_BPM"):
            self._set_group_children("DP_Arena", group, "IIDX#1")

    def _apply_sp_bpl(
        self,
        assignments: Mapping[str, Mapping[str, str]],
        team_by_player: Mapping[str, str],
    ) -> None:
        players = {
            team: self._team_player(team, assignments, team_by_player)
            for team in ("L", "R")
        }
        mid_targets: dict[str, set[str]] = {"1P": set(), "2P": set()}
        for team in ("L", "R"):
            player = players[team]
            assert player is not None
            side = self._side_name(player["side"])
            machine = self._machine_number(player["machine"])
            mid_targets[side].add(f"IIDX#{machine}")
            for item_side in ("1P", "2P"):
                enabled = item_side == side
                for group in (f"SP_{team}JUDGE_{item_side}", f"SP_{team}UI_{item_side}"):
                    self._set_group_children(
                        "SP_BPL", group, f"IIDX#{machine}" if enabled else None,
                        group_enabled=enabled,
                    )
            camera = f"IIDX#{machine}" if machine in (1, 4) else f"CAM#{machine}"
            self._set_group_children("SP_BPL", f"SP_{team}CAM", camera)
        for side in ("1P", "2P"):
            targets = mid_targets[side]
            for group in (
                f"SP_MIDUI_{side}",
                f"SP_{side}_SongName",
                f"SP_{side}_BPM",
            ):
                self._set_group_children("SP_BPL", group, targets, group_enabled=bool(targets))

    def _apply_dp_bpl(
        self,
        assignments: Mapping[str, Mapping[str, str]],
        team_by_player: Mapping[str, str],
    ) -> None:
        for team in ("L", "R"):
            player = self._team_player(team, assignments, team_by_player)
            if player is None:
                raise RuntimeError(f"未找到 {team} 方的机台分配")
            machine = self._machine_number(player["machine"])
            for group in (f"DP_{team}JUDGE", f"DP_{team}UI"):
                self._set_group_children("DP_BPL", group, f"IIDX#{machine}")
            camera = f"IIDX#{machine}" if machine in (1, 4) else f"CAM#{machine}"
            self._set_group_children("DP_BPL", f"DP_{team}CAM", camera)
        machines: set[str] = set()
        for team in ("L", "R"):
            player = self._team_player(team, assignments, team_by_player)
            assert player is not None
            machine = self._machine_number(player["machine"])
            machines.add(f"IIDX#{machine}")
        for group in ("Gauges", "DP_SongName", "DP_BPM"):
            self._set_group_children("DP_BPL", group, machines)

    @staticmethod
    def _team_player(
        team: str,
        assignments: Mapping[str, Mapping[str, str]],
        team_by_player: Mapping[str, str],
    ) -> Mapping[str, str] | None:
        players = [p for p in assignments if team_by_player.get(p) == team]
        if len(players) != 1:
            raise RuntimeError(f"{team} 方需要恰好一名玩家分配，实际 {len(players)} 名")
        return assignments[players[0]]

    @staticmethod
    def _machine_number(machine: str) -> int:
        match = re.fullmatch(r"IIDX#?(\d+)", str(machine).strip(), re.IGNORECASE)
        if not match:
            raise RuntimeError(f"无效机台编号: {machine!r}")
        number = int(match.group(1))
        if number not in range(1, 5):
            raise RuntimeError(f"机台编号超出范围: {machine!r}")
        return number

    @staticmethod
    def _side_name(side: str) -> str:
        normalized = str(side).strip().lower()
        if normalized not in {"1p", "2p"}:
            raise RuntimeError(f"无效游玩侧: {side!r}")
        return normalized.upper()

    def _set_group_enabled(self, scene: str, group: str, enabled: bool) -> None:
        item = self._find_scene_item(scene, group)
        self._set_item_enabled(scene, item["sceneItemId"], enabled)

    def _set_group_children(
        self,
        scene: str,
        group: str,
        visible_source: str | set[str] | None,
        *,
        group_enabled: bool = True,
    ) -> None:
        self._set_group_enabled(scene, group, group_enabled)
        response = self._send_response("GetGroupSceneItemList", {"sceneName": group})
        items = response.get("sceneItems")
        if not isinstance(items, list):
            raise RuntimeError(f"OBS 组 {group} 返回了无效元素列表")
        names = {item.get("sourceName") for item in items if isinstance(item, dict)}
        visible_sources = ({visible_source} if isinstance(visible_source, str) else visible_source)
        effective_sources = visible_sources if group_enabled else None
        if effective_sources is not None:
            missing = effective_sources - names
            if missing:
                raise RuntimeError(f"OBS 组 {group} 缺少元素 {sorted(missing)}")
        for item in items:
            if not isinstance(item, dict) or "sceneItemId" not in item:
                raise RuntimeError(f"OBS 组 {group} 存在无效元素")
            self._set_item_enabled(
                group,
                item["sceneItemId"],
                effective_sources is not None and item.get("sourceName") in effective_sources,
            )

    def _find_scene_item(self, scene: str, source_name: str) -> dict[str, Any]:
        response = self._send_response("GetSceneItemList", {"sceneName": scene})
        items = response.get("sceneItems")
        if not isinstance(items, list):
            raise RuntimeError(f"OBS 场景 {scene} 返回了无效元素列表")
        for item in items:
            if isinstance(item, dict) and item.get("sourceName") == source_name:
                return item
        raise RuntimeError(f"OBS 场景 {scene} 缺少组 {source_name}")

    def _set_item_enabled(self, scene: str, item_id: Any, enabled: bool) -> None:
        try:
            numeric_id = int(item_id)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"OBS 元素 ID 无效: {item_id!r}") from exc
        self._send(
            "SetSceneItemEnabled",
            {"sceneName": scene, "sceneItemId": numeric_id, "sceneItemEnabled": bool(enabled)},
        )

    def _send(self, request: str, data: dict[str, Any]) -> dict[str, Any] | None:
        self._require()
        try:
            response = self._client.send(request, data, raw=True)  # type: ignore[union-attr]
        except Exception as exc:
            raise RuntimeError(f"OBS 请求 {request} 失败，参数={data}: {exc}") from exc
        logger.debug("OBS 请求 %s 参数=%r 响应=%r", request, data, response)
        if response is not None and not isinstance(response, dict):
            raise RuntimeError(f"OBS 请求 {request} 返回了无效响应，参数={data}，响应={response!r}")
        return response

    def _send_response(self, request: str, data: dict[str, Any]) -> dict[str, Any]:
        response = self._send(request, data)
        if response is None:
            raise RuntimeError(f"OBS 请求 {request} 返回空响应，参数={data}")
        return response

    def _require(self) -> None:
        if self._client is None:
            raise RuntimeError("OBS 未连接")
