import json
from pathlib import Path
from typing import Any, Dict

from pydantic import ValidationError

from src.config.models import (
    IndividualScheduleConfig,
    TeamScheduleConfig,
    TeamsConfig,
)


class ConfigError(Exception):
    """Raised when a config file cannot be loaded or validated."""

    pass


CONFIG_DIR = Path("data")
CONFIG_FILES: Dict[str, tuple[str, Any]] = {
    "teams": ("teams.json", TeamsConfig),
    "team_schedule": ("team_schedule.json", TeamScheduleConfig),
    "individual_schedule": ("individual_schedule.json", IndividualScheduleConfig),
}

TEMPLATES: Dict[str, dict] = {
    "teams.json": {"teams": []},
    "team_schedule.json": {"weeks": []},
    "individual_schedule.json": {"groups": {}},
}


def ensure_templates(config_dir: Path = CONFIG_DIR) -> None:
    """Generate minimal valid templates for missing config files."""
    config_dir.mkdir(parents=True, exist_ok=True)
    for key, (filename, _) in CONFIG_FILES.items():
        path = config_dir / filename
        if not path.exists():
            template = TEMPLATES[filename]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(template, f, indent=2)


def load_configs(config_dir: Path = CONFIG_DIR) -> Dict[str, Any]:
    """Load and validate all config files, generating templates if missing."""
    ensure_templates(config_dir)
    loaded: Dict[str, Any] = {}
    for key, (filename, model_cls) in CONFIG_FILES.items():
        path = config_dir / filename
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except json.JSONDecodeError as exc:
            raise ConfigError(
                f"Config error: {path.name} is not valid JSON. "
                "Fix the file and reload the page to retry."
            ) from exc
        try:
            loaded[key] = model_cls.model_validate(raw)
        except ValidationError as exc:
            first_error = exc.errors()[0]
            loc = ".".join(str(part) for part in first_error.get("loc", []))
            err_msg = f"{loc}: {first_error.get('msg', 'validation error')}"
            raise ConfigError(
                f"Config error: {path.name} — {err_msg}. "
                "Fix the file and reload the page to retry."
            ) from exc
    return loaded
