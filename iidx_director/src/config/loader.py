"""赛程配置的加载、校验与模板生成。

路径锚定模块目录（iidx_director/data），不依赖启动时的 cwd。
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .models import KnockoutConfig, KnockoutEFConfig, KnockoutFinalConfig, TeamMatchConfig

MODULE_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = MODULE_ROOT / "data"

TEAM_MATCH_FILE = "team_match.json"
KNOCKOUT_FILE = "knockout.json"
KNOCKOUT_EF_FILE = "knockout_ef.json"
KNOCKOUT_FINAL_FILE = "knockout_final.json"

TEAM_MATCH_TEMPLATE = {
    "playType": "SP",
    "stageName": "レギュラーステージ",
    "matchNumber": 1,
    "leftTeam": {
        "name": "LEFT TEAM",
        "emoji": "🎩",
        "colors": {"primary": "#c0c0c0", "secondary": "#ffffff"},
        "players": ["选手L1", "选手L2"],
    },
    "rightTeam": {
        "name": "RIGHT TEAM",
        "emoji": "🚀",
        "colors": {"primary": "#1a3a6b", "secondary": "#ffffff"},
        "players": ["选手R1", "选手R2"],
    },
    "grabRounds": 0,
    "rounds": [
        {
            "type": "1v1",
            "points": 1,
            "theme": "SCRATCH",
            "judgeBy": "ex",
            "games": [
                {"leftPlayers": ["选手L1"], "rightPlayers": ["选手R1"]},
                {"leftPlayers": ["选手L1"], "rightPlayers": ["选手R1"]},
            ],
        },
        {
            "type": "2v2",
            "points": 2,
            "theme": "CHARGE",
            "games": [
                {"leftPlayers": ["选手L1", "选手L2"], "rightPlayers": ["选手R1", "选手R2"]},
                {"leftPlayers": ["选手L1", "选手L2"], "rightPlayers": ["选手R1", "选手R2"]},
            ],
        },
    ],
}

KNOCKOUT_TEMPLATE = {
    "playType": "SP",
    "tournamentName": "16人淘汰赛",
    "groups": {
        "A": ["A1", "A2", "A3", "A4"],
        "B": ["B1", "B2", "B3", "B4"],
        "C": ["C1", "C2", "C3", "C4"],
        "D": ["D1", "D2", "D3", "D4"],
    },
}

KNOCKOUT_EF_TEMPLATE = {
    "playType": "SP",
    "tournamentName": "8人淘汰赛",
    "groups": {
        "E": ["E1", "E2", "E3", "E4"],
        "F": ["F1", "F2", "F3", "F4"],
    },
}

KNOCKOUT_FINAL_TEMPLATE = {
    "playType": "SP",
    "tournamentName": "淘汰赛决赛",
    "groups": {
        "finals": ["FIN1", "FIN2", "FIN3", "FIN4"],
    },
}

_TEMPLATES = {
    TEAM_MATCH_FILE: TEAM_MATCH_TEMPLATE,
    KNOCKOUT_FILE: KNOCKOUT_TEMPLATE,
    KNOCKOUT_EF_FILE: KNOCKOUT_EF_TEMPLATE,
    KNOCKOUT_FINAL_FILE: KNOCKOUT_FINAL_TEMPLATE,
}


class ConfigError(Exception):
    """配置缺失或校验失败。"""


def ensure_templates(config_dir: Path = CONFIG_DIR) -> None:
    """data/ 下缺少配置文件时生成模板，便于工作组直接编辑。"""
    config_dir.mkdir(parents=True, exist_ok=True)
    for filename, template in _TEMPLATES.items():
        path = config_dir / filename
        if not path.exists():
            path.write_text(
                json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )


def _load(filename: str, model: type[BaseModel], config_dir: Path) -> BaseModel:
    path = config_dir / filename
    if not path.exists():
        raise ConfigError(f"配置文件不存在: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{filename} 不是合法 JSON: {exc}") from exc
    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"{filename} 校验失败: {exc}") from exc


def load_team_match(config_dir: Path = CONFIG_DIR) -> TeamMatchConfig:
    return _load(TEAM_MATCH_FILE, TeamMatchConfig, config_dir)  # type: ignore[return-value]


def load_knockout(config_dir: Path = CONFIG_DIR) -> KnockoutConfig:
    return _load(KNOCKOUT_FILE, KnockoutConfig, config_dir)  # type: ignore[return-value]


def load_knockout_ef(config_dir: Path = CONFIG_DIR) -> KnockoutEFConfig:
    return _load(KNOCKOUT_EF_FILE, KnockoutEFConfig, config_dir)  # type: ignore[return-value]


def load_knockout_final(config_dir: Path = CONFIG_DIR) -> KnockoutFinalConfig:
    return _load(KNOCKOUT_FINAL_FILE, KnockoutFinalConfig, config_dir)  # type: ignore[return-value]


def save_config(filename: str, payload: str | bytes, config_dir: Path = CONFIG_DIR) -> BaseModel:
    """保存上传的赛程 JSON（先校验再落盘，旧文件备份为 .bak）。返回校验后的模型。"""
    if filename not in _TEMPLATES:
        raise ConfigError(f"未知的配置文件名: {filename}")
    model = {
        "team_match.json": TeamMatchConfig,
        "knockout.json": KnockoutConfig,
        "knockout_ef.json": KnockoutEFConfig,
        "knockout_final.json": KnockoutFinalConfig,
    }[filename]
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"上传内容不是合法 JSON: {exc}") from exc
    try:
        validated = model.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"配置校验失败: {exc}") from exc

    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / filename
    if path.exists():
        path.replace(path.with_suffix(".json.bak"))
    path.write_text(
        json.dumps(validated.model_dump(by_alias=True), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return validated
