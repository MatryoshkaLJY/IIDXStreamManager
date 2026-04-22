# Codebase Structure

**Analysis Date:** 2026-04-22

## Directory Layout

```
/home/matryoshka/Downloads/out_frames/iidx_tpl_manager/
├── src/                        # Application source code
│   ├── app.py                  # Flask app factory, routes, SocketIO handlers
│   ├── state.py                # RuntimeState dataclass and JSON persistence
│   ├── config/                 # Configuration loading and validation
│   │   ├── __init__.py         # Barrel exports
│   │   ├── loader.py           # JSON config loader with Pydantic validation
│   │   └── models.py           # Pydantic models for teams, schedules, rounds
│   ├── obs/                    # OBS WebSocket integration
│   │   ├── __init__.py         # Barrel exports
│   │   ├── client.py           # OBSClient wrapper (obsws-python)
│   │   ├── scene_controller.py # Scene validation and switching
│   │   ├── heartbeat.py        # Background OBS health monitor
│   │   ├── monitor.py          # CabinetMonitor (AI frame polling)
│   │   └── auto_transition.py  # AutoTransitionController (scene automation)
│   ├── scoreboard/             # Scoreboard WebSocket integration
│   │   ├── __init__.py         # Barrel exports
│   │   └── pusher.py           # ScoreboardPusher (BPL + knockout)
│   ├── templates/              # Jinja2 HTML templates
│   │   ├── base.html           # Base layout with nav, automation banner
│   │   ├── status.html         # Dashboard: OBS, monitoring, scene switch, score review
│   │   ├── config.html         # Tournament mode selection and config upload
│   │   ├── round_prep.html     # Player-to-cabinet assignment and round navigation
│   │   └── automation.html     # Automation delay settings and pause/resume
│   └── data/                   # Runtime copies of tournament configs
│       ├── teams.json          # Team definitions with players and colors
│       ├── team_schedule.json  # Weekly match schedule with rounds
│       └── individual_schedule.json  # Group-based individual schedule
├── static/                     # Static assets
│   ├── css/
│   │   └── main.css            # Dark theme CSS with component styles
│   └── js/
│       └── operator.js         # SocketIO client, score review UI, automation controls
├── data/                       # Primary tournament config data (symlinked/copied)
│   ├── teams.json
│   ├── team_schedule.json
│   ├── individual_schedule.json
│   └── team_schedule.json.bak  # Backup from upload
├── runtime/                    # Runtime state persistence
│   └── state.json              # Persisted RuntimeState (OBS, mode, assignments, scores)
├── tests/                      # pytest test suite
│   ├── conftest.py             # sys.path setup for sibling obs_manager import
│   ├── test_app_obs_routes.py  # Flask route tests (scene switch, OBS config, reconnect)
│   ├── test_config_loader.py   # Config loading, validation, template generation
│   ├── test_config_models.py   # Pydantic model validation tests
│   ├── test_state.py           # RuntimeState save/load roundtrip tests
│   ├── test_obs_client.py      # OBSClient wrapper tests
│   ├── test_scene_controller.py # Scene validation and switching tests
│   └── test_heartbeat.py       # OBSHeartbeat thread tests
├── .planning/                  # GSD planning artifacts
│   └── codebase/               # Codebase analysis documents
│       ├── ARCHITECTURE.md
│       └── STRUCTURE.md
├── .planning_old/              # Legacy planning documents from earlier iterations
│   ├── PROJECT.md
│   ├── REQUIREMENTS.md
│   ├── ROADMAP.md
│   ├── STATE.md
│   ├── MILESTONES.md
│   ├── milestones/
│   └── phases/
├── .claude/                    # Claude session logs and settings
│   ├── logs/
│   └── settings.local.json
├── CLAUDE.md                   # Project instructions for Claude
└── .pytest_cache/              # pytest cache
```

## Directory Purposes

**`src/`:**
- Purpose: All application source code
- Contains: Python modules, Jinja2 templates, runtime data copies
- Key files: `src/app.py` (676 lines, main entry point), `src/state.py` (74 lines)

**`src/config/`:**
- Purpose: Tournament configuration schema, loading, and validation
- Contains: Pydantic models, loader with auto-template generation
- Key files: `src/config/loader.py`, `src/config/models.py`

**`src/obs/`:**
- Purpose: OBS WebSocket client, scene control, monitoring, automation
- Contains: 6 Python modules totaling ~590 lines
- Key files: `src/obs/client.py`, `src/obs/scene_controller.py`, `src/obs/monitor.py`, `src/obs/auto_transition.py`

**`src/scoreboard/`:**
- Purpose: Push confirmed scores to external scoreboard WebSocket servers
- Contains: Single module `pusher.py`

**`src/templates/`:**
- Purpose: Jinja2 server-rendered HTML pages
- Contains: 5 templates extending `base.html`

**`static/`:**
- Purpose: CSS and JavaScript served by Flask
- Contains: `main.css` (dark theme), `operator.js` (SocketIO client logic)

**`data/`:**
- Purpose: Tournament JSON configuration files (primary location)
- Contains: `teams.json`, `team_schedule.json`, `individual_schedule.json`
- Note: `src/data/` contains copies/symlinks of the same files

**`runtime/`:**
- Purpose: Persisted runtime state across app restarts
- Contains: `state.json` — single JSON file with all mutable state
- Generated: Yes (auto-created on first save)
- Committed: No (should be gitignored)

**`tests/`:**
- Purpose: pytest test suite
- Contains: 8 test files covering routes, config, state, OBS integration

## Key File Locations

**Entry Points:**
- `src/app.py`: Flask application factory and route definitions
- `src/app.py` line 674-676: `if __name__ == "__main__":` direct execution block

**Configuration:**
- `src/config/models.py`: Pydantic schemas for `TeamsConfig`, `TeamScheduleConfig`, `IndividualScheduleConfig`
- `src/config/loader.py`: `CONFIG_FILES` dict mapping keys to `(filename, model_class)` tuples
- `data/teams.json`, `data/team_schedule.json`, `data/individual_schedule.json`: Runtime tournament data

**Core Logic:**
- `src/app.py`: HTTP route handlers, form validation, score confirmation logic
- `src/obs/auto_transition.py`: Automation state machine and scene transition logic
- `src/obs/monitor.py`: Cabinet polling and pending score persistence
- `src/scoreboard/pusher.py`: Scoreboard WebSocket message construction and sending

**Testing:**
- `tests/conftest.py`: Adds parent directory to `sys.path` for `obs_manager` import
- `tests/test_app_obs_routes.py`: Flask test client tests for OBS-related routes
- `tests/test_scene_controller.py`: Scene validation and switching unit tests

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `auto_transition.py`, `scene_controller.py`)
- Test files: `test_<module>.py` (e.g., `test_scene_controller.py`)
- Templates: `<page>.html` (e.g., `round_prep.html`, `automation.html`)
- Config files: `<name>.json` (e.g., `team_schedule.json`)

**Directories:**
- Source packages: descriptive nouns (e.g., `config/`, `obs/`, `scoreboard/`)
- No `__pycache__` or nested package depth beyond 2 levels

## Where to Add New Code

**New Feature (e.g., new automation rule):**
- Primary code: `src/obs/auto_transition.py` (add logic to `_tick()` or new method)
- State fields: `src/state.py` (add to `RuntimeState` dataclass)
- UI: `src/templates/automation.html` or `src/templates/status.html`
- Tests: `tests/test_scene_controller.py` or new `tests/test_auto_transition.py`

**New Component/Module (e.g., new external integration):**
- Implementation: Create new package under `src/` (e.g., `src/recorder/`)
- Barrel file: Add `__init__.py` with `__all__`
- Registration: Import and instantiate in `src/app.py` `create_app()`

**Utilities:**
- Shared helpers: Add to existing module or create `src/utils/` package
- Follow pattern: module-level logger, type hints, specific exception catching

**New Config Schema:**
- Model: `src/config/models.py` (new Pydantic class)
- Loader: `src/config/loader.py` (add to `CONFIG_FILES` and `TEMPLATES`)
- Export: `src/config/__init__.py` (add to `__all__`)

**New Route/Endpoint:**
- Route handler: `src/app.py` (add function with `@app.route` decorator)
- Form validation: Define Pydantic model in `src/app.py` near other form classes
- UI: Add to appropriate template or create new template in `src/templates/`
- JS: Add handler in `static/js/operator.js`

## Special Directories

**`.planning_old/`:**
- Purpose: Legacy GSD planning documents from earlier project iterations
- Contains: Milestones, phase plans, research docs, UAT results
- Generated: No (manually maintained)
- Committed: Yes

**`.claude/logs/`:**
- Purpose: Session logs from Claude Code interactions
- Generated: Yes (auto-generated per session)
- Committed: No (should be gitignored)

**`src/data/` vs `data/`:**
- Both contain identical tournament config JSON files
- `data/` is the primary location referenced by `src/config/loader.py` (`CONFIG_DIR = Path("data")`)
- `src/data/` appears to be a copy or symlink for packaging convenience

---

*Structure analysis: 2026-04-22*
