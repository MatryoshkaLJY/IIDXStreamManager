---
phase: 01-foundation-config
plan: "01"
subsystem: config
tags:
  - Config
  - Pydantic
  - Validation
  - Foundation
requires: []
provides:
  - src/config/models.py
  - src/config/loader.py
  - src/config/__init__.py
affects:
  - data/teams.json
  - data/team_schedule.json
  - data/individual_schedule.json
tech-stack:
  added:
    - Pydantic v2
  patterns:
    - Factory-style loader with model mapping
    - Template generation for missing config files
key-files:
  created:
    - src/config/__init__.py
    - src/config/models.py
    - src/config/loader.py
    - tests/test_config_models.py
    - tests/test_config_loader.py
  modified: []
decisions:
  - Use Pydantic v2 BaseModel for strict schema validation and clear error messages
  - Auto-generate minimal valid templates on missing files to ensure the app always boots
  - Surface only file names and schema locations in ConfigError messages (no full paths or stack traces)
metrics:
  duration: "10"
  completed_date: "2026-04-15"
---

# Phase 01 Plan 01: Config Schemas and Loader Summary

**One-liner:** Pydantic-based config schemas and robust loader with auto-template generation for tournament JSON configs.

## What Was Built

- `src/config/models.py` — Pydantic v2 models for `teams.json`, `team_schedule.json`, and `individual_schedule.json`, enforcing `round.type` as `"1v1"` or `"2v2"`.
- `src/config/loader.py` — `ensure_templates()` and `load_configs()` with `ConfigError` for validation failures and missing-file template generation.
- `src/config/__init__.py` — Public API re-exports with `__all__`.
- `tests/test_config_models.py` — 5 tests covering valid parsing, invalid `round.type`, and empty structures.
- `tests/test_config_loader.py` — 5 tests covering valid loads, missing-file generation, malformed JSON, schema errors, and generated-template validation.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None. The loader mitigates information disclosure (T-01-02) by surfacing only file names and schema locations, and mitigates DoS from malformed JSON (T-01-03) by catching `json.JSONDecodeError` and `ValidationError` and raising controlled `ConfigError`.

## Self-Check: PASSED

- [x] `src/config/__init__.py` exists
- [x] `src/config/models.py` exists
- [x] `src/config/loader.py` exists
- [x] `tests/test_config_models.py` exists
- [x] `tests/test_config_loader.py` exists
- [x] Commit `810f16c` exists
- [x] Commit `cb45224` exists
- [x] All 10 pytest tests pass
