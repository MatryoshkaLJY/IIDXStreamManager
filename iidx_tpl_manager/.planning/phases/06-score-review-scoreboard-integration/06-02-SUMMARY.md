---
phase: 06-score-review-scoreboard-integration
plan: 02
status: complete
completed_at: "2026-04-22T00:00:00Z"
---

# Plan 06-02 Summary: Wire Up Score Review Backend Logic

## What Was Built

Connected the cabinet monitor loop to state persistence and exposed operator endpoints for delay configuration and score confirmation.

### Changes

1. **CabinetMonitor persists pending scores** (`src/obs/monitor.py`)
   - When a cabinet reaches `score` state with `score_validation_pending=True`, the score data is saved to `RuntimeState.pending_scores`
   - When a cabinet leaves the `score` state, its entry is removed from `pending_scores`
   - Added `save_runtime_state` import

2. **Scoreboard_web scene added** (`src/obs/scene_controller.py`)
   - Added `"scoreboard": "Scoreboard_web"` to `REQUIRED_SCENES`
   - Scene controller can now switch to the scoreboard overlay scene

3. **New Flask routes** (`src/app.py`)
   - `POST /api/scoreboard_delay` — validates delay (0.0–300.0s), persists to RuntimeState, emits `scoreboard_delay_updated` event
   - `POST /confirm_score` — full confirmation workflow:
     - Validates all pending scores have `1p_valid=True` and `2p_valid=True`
     - Switches OBS to `Scoreboard_web` scene
     - For **team mode**: flattens schedule to find current round, computes winner by EX score comparison (1v1) or ranking (2v2), pushes via `push_team_score`
     - For **individual mode**: maps round to group, determines stage, pushes via `push_individual_score`
     - Clears pending scores and emits `scores_pushed` event
   - `status()` route now passes `scoreboard_delay` and `pending_scores` to the template

## Key Files

- `src/obs/monitor.py`
- `src/obs/scene_controller.py`
- `src/app.py`

## Verification

- `/api/scoreboard_delay` accepts valid delays and persists them (tested: 7.5s)
- `/confirm_score` rejects when no pending scores or invalid scores exist
- ScoreboardPusher is instantiated in `create_app()`
- Scoreboard_web is a recognized OBS scene

## Self-Check: PASSED
