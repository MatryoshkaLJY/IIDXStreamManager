# Phase 7: Auto-Transitions & Configurable Delays - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Broadcast transitions between Live, Gameplay, and Scoreboard scenes happen automatically based on aggregate cabinet state, with operator override controls and configurable timing delays.

Specifically:
- Live ↔ Gameplay transitions are fully automatic based on cabinet states
- Gameplay → Scoreboard_web transition remains operator-confirmed (via score review panel from Phase 6)
- Operator can configure delays, pause/resume automation, and trigger Emergency Live
- All automation state is visible via a status banner

Out of scope: Gameplay scene source setup (text sources, group visibility), scoreboard protocol details, mobile-responsive UI.
</domain>

<decisions>
## Implementation Decisions

### Auto-transition trigger logic
- **D-01:** Live → Gameplay transition triggers when **all 4 cabinets** enter `play` state simultaneously.
- **D-02:** Gameplay → Live transition triggers when **all cabinets** return to `live` or `blank` state.
- **D-03:** Gameplay → Scoreboard_web transition remains **operator-confirmed** via the existing score review panel and "Confirm & Push" button (Phase 6 behavior is unchanged).
- **D-04:** No automatic transition to Scoreboard_web without operator confirmation.

### Delay configuration model
- **D-05:** Two delay fields are added to `RuntimeState`:
  - `return_to_live_delay` (float, seconds): Time to wait after scoreboard push completes before auto-switching back to Live scene. Default: `5.0`.
  - `gameplay_hold_delay` (float, seconds): Minimum time to hold the Gameplay scene after all cabinets enter `play` before considering a transition back to Live. Default: `3.0`.
- **D-06:** Delays are stored in `runtime/state.json` alongside other `RuntimeState` fields and auto-restore on server restart.
- **D-07:** Delay values of `-1` mean "pause and wait for operator manual proceed" for that specific delay.
- **D-08:** Delays are configurable via a dedicated **Automation page** in the web UI (new nav item).

### Manual proceed (-1 delay) workflow
- **D-09:** When any delay is set to `-1` and its trigger condition is met, automation pauses and a **persistent "Proceed" button** appears on all pages (visible regardless of which page the operator is viewing).
- **D-10:** The Proceed button is context-rich: it displays the pending transition name, current aggregate cabinet states, and what the estimated delay would be if changed from `-1`.
- **D-11:** Clicking Proceed advances the paused transition immediately and resumes normal automation flow.

### Automation controls and state display
- **D-12:** A **Pause/Resume toggle** for auto-transitions is available on both the Automation page and the Status page.
- **D-13:** An **"Emergency Live"** button is always visible on all pages. Clicking it immediately cuts to the `现场摄像` scene and pauses all automation.
- **D-14:** Automation state is displayed via a **status banner** at the top of every page (same pattern as the existing OBS connection banner), showing one of:
  - `Active` (green) — auto-transitions are running
  - `Paused` (yellow) — operator paused or -1 delay is waiting
  - `Emergency` (red) — Emergency Live was triggered
- **D-15:** The banner also shows a one-line reason when not Active (e.g., "Paused: waiting for operator Proceed" or "Emergency: operator triggered Emergency Live").

### Automation prerequisites
- **D-16:** Auto-transitions only run when:
  1. Monitoring is active (`monitoring_active = true`)
  2. OBS is connected and scenes are valid
  3. Automation is not paused or in emergency state
  4. At least one cabinet is assigned (not all "Unassigned")
- **D-17:** If any prerequisite is not met, automation state shows as `Paused` with the reason.

### Claude's Discretion
- Exact styling and placement of the Proceed button (persistent bar vs floating button)
- Exact delay default values (recommendations: return_to_live=5.0, gameplay_hold=3.0)
- How the automation banner coexists with the OBS connection banner (stacked vs combined)
- Whether to show countdown timers for active delays in the banner
- Internal implementation of the aggregate state machine (polling-based vs event-driven)
</decisions>

<canonical_refs>
## Canonical References

### Requirements & project context
- `.planning/REQUIREMENTS.md` — Requirements AUTO-01 through AUTO-04
- `.planning/PROJECT.md` — Project vision, constraints, existing components, target scene names

### Prior phase decisions
- `.planning/phases/03-obs-integration-scene-control/03-CONTEXT.md` — OBS connection, scene switching, heartbeat patterns
- `.planning/phases/05-cabinet-monitoring-live-monitor-ui/05-CONTEXT.md` — Cabinet monitoring loop, `cabinet_update` SocketIO events, monitoring start/stop controls
- `.planning/phases/06-score-review-scoreboard-integration/06-CONTEXT.md` — Score review panel, confirmation workflow, scoreboard_delay, Scoreboard_web scene transition

### Existing code to reuse
- `src/state.py` — `RuntimeState` persistence pattern (JSON to disk)
- `src/app.py` — Flask routes, SocketIO handlers, scene switching, monitoring controls
- `src/obs/scene_controller.py` — `SceneController.switch_to()` for OBS scene transitions
- `src/obs/monitor.py` — `CabinetMonitor` and `process_frame()` result format
- `src/obs/heartbeat.py` — Background thread pattern
- `src/templates/base.html` — Jinja2 base template with nav links
- `src/templates/status.html` — Existing status page with banner/form patterns
- `static/js/operator.js` — Existing SocketIO client handlers
- `static/css/main.css` — Existing CSS tokens and card/label/status classes
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/state.py` (`RuntimeState`): Can be extended with `return_to_live_delay`, `gameplay_hold_delay`, `automation_active`, and `automation_state` fields
- `src/obs/scene_controller.py` (`SceneController`): Already validates scenes and switches between `现场摄像`, `SP团队赛`, `DP团队赛`, `个人赛`, and `Scoreboard_web`
- `src/obs/monitor.py` (`CabinetMonitor`): Already polls all 4 cabinets and emits `cabinet_update` events with `state` field
- `src/app.py`: Central route file where new `/automation` routes and the automation control endpoint can live
- `src/templates/base.html`: Nav link pattern — add "Automation" alongside Status, Config, Round Prep
- `static/js/operator.js`: Existing SocketIO handlers for `cabinet_update`, `obs_status`, `monitoring_status`

### Established Patterns
- Background workers run as daemon threads (CabinetMonitor, OBSHeartbeat)
- Runtime state is eagerly loaded and persisted to JSON on every change
- SocketIO events push real-time state from backend to browser
- POST routes return JSON for controls submitted via fetch
- Status banners use `.status-ok`, `.status-warning`, `.status-error` CSS classes
- UI is server-rendered Jinja2 with minimal JavaScript

### Integration Points
- Auto-transition logic will consume `cabinet_update` SocketIO events to track aggregate cabinet state
- Scene transitions reuse `SceneController.switch_to()`
- New `Automation` page follows the same template pattern as `status.html`, `config.html`, `round_prep.html`
- The Proceed button and automation banner can be injected into `base.html` so they appear on all pages
- Pause/resume and Emergency Live controls can be POST endpoints in `app.py` similar to `/monitor_control`
</code_context>

<specifics>
## Specific Ideas

- Status banner pattern (like OBS connection banner) is already proven — reuse it for automation state
- Automation page should be a single page with all delay inputs, pause/resume toggle, and automation state summary
- Proceed button should be persistent and non-intrusive but clearly visible when needed
- Keep the operator workflow simple: one page for automation setup, banner for state, button for manual override
</specifics>

<deferred>
## Deferred Ideas

- Gameplay scene text source and group visibility setup — already deferred to post-v1.2
- Auto-populating gameplay scene setup (SP/DP team match text sources) — requires additional OBS source control not in scope
- Mobile-responsive operator UI — deferred to post-v1.2 per PROJECT.md
- Advanced automation rules (e.g., per-cabinet scene selection, conditional transitions based on round type) — future enhancement

</deferred>

---

*Phase: 07-auto-transitions-configurable-delays*
*Context gathered: 2026-04-22*
