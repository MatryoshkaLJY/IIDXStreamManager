# Phase 6: Score Review & Scoreboard Integration - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Operator can review, correct, and confirm AI-recognized scores before pushing them to the correct scoreboard server (BPL on port 8080 or knockout on port 8081).

This phase delivers:
- A score review UI where pending scores appear for operator inspection and editing
- Visual flagging of invalid OCR results
- A confirmation workflow that switches OBS to `Scoreboard_web`, waits a configurable delay, then pushes the confirmed score
- Correct scoreboard protocol mapping for both team (BPL) and individual (knockout) modes

Auto-transitions to `Scoreboard_web` without operator confirmation, and gameplay scene source setup, are out of scope.
</domain>

<decisions>
## Implementation Decisions

### Review UI placement
- **D-01:** The score review UI lives as an expandable panel on the existing **Status page**, not a separate nav item.
- **D-02:** The panel auto-expands when one or more cabinets have pending `score` state results, and can be manually collapsed by the operator.

### Score-to-scoreboard mapping
- **D-03:** **Team mode (BPL):**
  - 1v1 rounds: the round's point value comes from a new field added to `team_schedule.json` per round.
  - 2v2 rounds: rank the 4 EX scores and assign points based on rank position (higher EX score = more points).
- **D-04:** **Individual mode (knockout):** send all 4 assigned cabinet scores as a single group in one `score` command.

### Confirmation workflow
- **D-05:** One global **"Confirm & Push"** button applies to all pending scores shown in the panel.
- **D-06:** The button is **disabled until all invalid scores are corrected** by the operator.
- **D-07:** After confirmation, the app:
  1. Switches OBS to the `Scoreboard_web` scene
  2. Shows a **countdown timer** in the review panel for `scoreboard_delay` seconds
  3. Pushes the confirmed score to the active scoreboard server

### Multiple score states
- **D-08:** If 2+ cabinets enter `score` state simultaneously, **all pending scores are shown in the panel at once**, each in its own editable row.

### Delay configuration
- **D-09:** A dedicated `scoreboard_delay` field is added to `RuntimeState` (float, seconds). Default: `5.0`.
- **D-10:** This delay is separate from Phase 7's auto-transition delays.

### Score validation UI
- **D-11:** Scores flagged invalid by `iidx_score_reco` (`1p_valid` or `2p_valid` false) are visually highlighted in the review panel (e.g., with a warning style or icon).
- **D-12:** The operator can click any score value to edit it inline before confirming.

### Claude's Discretion
- Exact styling of the expandable panel and countdown timer
- Warning/highlight styling for invalid scores
- How `scoreboard_delay` is exposed in the UI (e.g., inline form on Status page)
- Internal queueing strategy when pushing multiple scoreboard messages
- Whether to clear the panel immediately on confirm or after the push succeeds
</decisions>

<canonical_refs>
## Canonical References

### Requirements & project context
- `.planning/REQUIREMENTS.md` — Requirements SCR-01 through SCR-06
- `.planning/PROJECT.md` — Existing components, target scene names, and scoreboard constraints
- `.planning/phases/05-cabinet-monitoring-live-monitor-ui/05-CONTEXT.md` — Cabinet monitoring loop, `cabinet_update` SocketIO events

### Scoreboard protocols
- `../iidx_bpl_scoreboard/PROTOCOL.md` — BPL WebSocket protocol (`init`, `score`, `reset`)
- `../iidx_knockout_scoreboard/app.js` — Knockout protocol (`init`, `score`, `settle`)

### Config and state
- `src/config/models.py` — Pydantic models for `TeamScheduleConfig`, `IndividualScheduleConfig`
- `src/config/loader.py` — Config loading and validation patterns
- `src/state.py` — `RuntimeState` persistence pattern

### Existing code to reuse
- `src/app.py` — Flask routes, SocketIO handlers, scene switching
- `src/obs/scene_controller.py` — `SceneController.switch_to()` for OBS scene transitions
- `src/obs/monitor.py` — `CabinetMonitor` and `process_frame()` result format
- `static/js/operator.js` — Existing SocketIO client handlers
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/state.py` (`RuntimeState`): Can be extended with `scoreboard_delay` and pending-score fields
- `src/obs/monitor.py` (`CabinetMonitor`): Already emits `cabinet_update` events containing `scores` and `score_validation_pending`
- `src/obs/scene_controller.py` (`SceneController`): Provides `switch_to(scene_name)` for transitioning to `Scoreboard_web`
- `src/app.py`: Central route file where new `/confirm_score` or similar endpoint can live

### Established Patterns
- Background workers run as daemon threads
- POST routes return JSON for controls submitted via fetch
- SocketIO events push real-time state from backend to browser
- Runtime state is eagerly loaded and persisted to JSON on every change

### Integration Points
- Score review panel is rendered in `templates/status.html` and updated via `operator.js`
- Scoreboard push logic will open WebSocket connections to `ws://localhost:8080` (BPL) or `ws://localhost:8081` (knockout)
- `obs_manager.py` `process_frame()` result contains `scores` with keys like `1p_score`, `2p_score`, `1p_valid`, `2p_valid`
</code_context>

<specifics>
## Specific Ideas

- Keep score review on the Status page so the operator never has to leave the main monitoring view
- Countdown timer gives the operator confidence about exactly when the push will happen
- Panel should feel lightweight: expand when needed, collapse when idle
</specifics>

<deferred>
## Deferred Ideas

- **Auto-transition to `Scoreboard_web` without operator confirmation** — belongs in Phase 7 (Auto-Transitions)
- **Gameplay scene text source and group visibility setup** — already deferred to Phase 4/7 per prior context
- **Scoreboard `init` command generation** — may be partially handled in Phase 4 or Phase 6 depending on planner breakdown; the key deliverable here is the `score` push
</deferred>

---

*Phase: 06-score-review-scoreboard-integration*
*Context gathered: 2026-04-15*
