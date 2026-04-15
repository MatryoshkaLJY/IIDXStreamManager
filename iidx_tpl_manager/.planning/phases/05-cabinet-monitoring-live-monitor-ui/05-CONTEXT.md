# Phase 5: Cabinet Monitoring & Live Monitor UI - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the backend cabinet monitoring loop that polls all 4 cabinets via `obs_manager.py`, outputs states and scores to the console, and emits updates via SocketIO.

**Explicitly deferred to later:** The browser-based "Live Monitor" page with thumbnail/frame display is NOT built in this phase. It will be added when the streaming UI is ready.
</domain>

<decisions>
## Implementation Decisions

### Live Monitor UI scope
- **D-01:** Phase 5 does **not** implement a browser-based live monitor page with frame thumbnails. Console/terminal output is the primary feedback mechanism for this phase.
- **D-02:** The live monitor UI (2x2 grid of cabinet thumbnails and state labels) is deferred until the streaming UI design is finalized.

### SocketIO emissions
- **D-03:** Cabinet state and score data are emitted via SocketIO immediately, even though there is no monitor page yet. Downstream phases (e.g., Phase 6 score review) and the future monitor UI will consume these events.
- **D-04:** Event name: `cabinet_update`. Payload includes `machine_id`, `label`, `state`, `scores`, and `score_validation_pending`.

### Background monitoring loop
- **D-05:** A background monitoring worker polls all 4 cabinets. It follows the existing `OBSHeartbeat` threading pattern (daemon thread, start/stop lifecycle).
- **D-06:** The worker registers 4 machines with `OBSManager` and calls `process_frame()` for each cabinet in a round-robin loop.
- **D-07:** The monitoring loop does **not** auto-start on app launch. A manual "Start Monitoring" / "Stop Monitoring" control is provided.

### OBS source configuration
- **D-08:** Default OBS source names for the 4 cabinets are `IIDX#1`, `IIDX#2`, `IIDX#3`, `IIDX#4`.
- **D-09:** Source names and polling interval are configured by editing `runtime/state.json` directly in this phase. No web form is built for these settings yet.

### Polling interval
- **D-10:** Polling interval is stored in `RuntimeState` as `monitor_interval` (float, seconds). Default: `1.0`.
- **D-11:** The interval applies to the per-cabinet loop (i.e., time between successive `process_frame()` calls across all cabinets).

### State recognition and scores
- **D-12:** The monitoring loop uses `obs_manager.py`'s `process_frame()` method, which integrates `iidx_state_machine` for state tracking.
- **D-13:** When a cabinet enters `score` state, both the state and the OCR score results are logged to console and emitted via SocketIO.
- **D-14:** Invalid scores (`1p_valid`/`2p_valid` false) are still emitted but flagged with `score_validation_pending: true`.

### Console output format
- **D-15:** Each cabinet update is printed as a single JSON line to stdout (or via Python `logging`) so the operator can watch the stream in a terminal window.

### Claude's Discretion
- Exact implementation of the start/stop control (button on Status page vs simple API endpoint)
- Whether to use `logging.info()` or plain `print()` for console output
- Exact structure of the `cabinet_update` SocketIO payload beyond the required fields
- How to handle OBS connection loss during monitoring (pause loop vs skip cabinets)
- Thread synchronization details between the monitoring worker and Flask request handlers

</decisions>

<canonical_refs>
## Canonical References

### Requirements & project context
- `.planning/REQUIREMENTS.md` — Requirements MON-01 through MON-04
- `.planning/PROJECT.md` — Project vision, constraints, existing components
- `.planning/phases/03-obs-integration-scene-control/03-CONTEXT.md` — Prior phase decisions on OBS connection, state persistence, and SocketIO patterns
- `.planning/phases/04-tournament-setup-round-prep-ui/04-CONTEXT.md` — Prior phase decisions on RuntimeState extension patterns

### Existing code to reuse or reference
- `../obs_manager/obs_manager.py` — `OBSManager` class with `register_machine()`, `process_frame()`, `run()`
- `src/app.py` — Flask app, SocketIO initialization, route patterns
- `src/state.py` — `RuntimeState` persistence pattern
- `src/obs/heartbeat.py` — Background thread pattern for OBS health checks
- `src/templates/status.html` — Existing status page for adding monitor controls
- `static/css/main.css` — Existing CSS tokens

### External components (do not reimplement)
- `iidx_state_machine` — TCP state machine service
- `iidx_state_reco` — TCP state recognition service (port 9876)
- `iidx_score_reco` — TCP score OCR service (port 9877)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/obs/heartbeat.py` (`OBSHeartbeat`): Ready-made daemon thread pattern that can be adapted for the monitoring worker
- `src/app.py`: Flask-SocketIO is initialized; `socketio.emit()` can broadcast cabinet updates
- `src/state.py` (`RuntimeState`): Can be extended with `monitor_interval`, `monitoring_active`, and `source_names` fields
- `../obs_manager/obs_manager.py` (`OBSManager`): Already wraps the full capture → recognize → state machine → score pipeline

### Established Patterns
- Background workers run as daemon threads started in `create_app()`
- Runtime state is eagerly loaded and persisted to JSON on every change
- SocketIO events push state changes from backend threads to the browser
- POST routes return JSON for controls that may be submitted via fetch

### Integration Points
- The monitoring worker will live in a new module (e.g., `src/obs/monitor.py`) and be instantiated in `src/app.py` alongside `OBSHeartbeat`
- `RuntimeState` will gain new fields for monitoring configuration
- A simple start/stop API endpoint (e.g., `/monitor_control`) will be added to `src/app.py`
- `cabinet_update` SocketIO events will be consumed by Phase 6 score review logic
</code_context>

<specifics>
## Specific Ideas

- Console-first approach: operator watches a terminal for cabinet states until the streaming UI is ready
- Keep the monitor control minimal — a start/stop button on the Status page is enough for Phase 5
- Use the same OBS connection credentials already stored in `RuntimeState`
</specifics>

<deferred>
## Deferred Ideas

- **Browser-based live monitor page with 2x2 thumbnail grid** — deferred until streaming UI is ready
- **Web form for source name / polling interval configuration** — operator edits JSON directly for now
- **Auto-start monitoring on app launch** — user explicitly chose manual start/stop
- **Monitor page as a separate nav item** — will be added when the full UI is built

</deferred>

---

*Phase: 05-cabinet-monitoring-live-monitor-ui*
*Context gathered: 2026-04-15*
