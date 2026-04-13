# Domain Pitfalls

**Domain:** Python web-based OBS tournament director with AI scene switching
**Researched:** 2026-04-14
**Confidence:** HIGH

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Treating OBS WebSocket as a Synchronous, Always-Available Service

**What goes wrong:**
The application assumes OBS WebSocket is connected and responsive at all times. During tournament operation, OBS may crash, be restarted, have its WebSocket plugin disabled, or experience temporary lag from scene transitions. If the director does not handle disconnections gracefully, it will either crash mid-broadcast or queue up blocking calls that stall the entire automation loop, causing missed scene switches.

**Why it happens:**
`obsws-python` exposes a synchronous `ReqClient`. Developers often call `set_current_program_scene()` directly inside the main monitoring loop without timeouts, retries, or circuit breakers. A single hanging WebSocket call blocks frame capture and state recognition for all 4 cabinets.

**Prevention:**
- Wrap every OBS WebSocket call in a short-timeout thread or async executor (max 1-2 seconds).
- Maintain a connection health flag; if OBS becomes unreachable, fall back to a "manual operator" mode that disables auto-switching but keeps the UI alive.
- Never block the frame-processing loop on OBS commands; queue scene-switch requests and apply them asynchronously.

**Detection:**
- Scene switches start arriving late or out of order relative to game state changes.
- The web UI becomes unresponsive during OBS restarts.
- Logs show repeated `ConnectionError` or `TimeoutError` from `obws-python`.

**Phase to address:** Phase 1 (Core Web App + OBS Integration)

---

### Pitfall 2: Blocking the Frame Loop with Synchronous AI Inference

**What goes wrong:**
`process_frame()` in `obs_manager.py` performs sequential blocking operations: capture screenshot from OBS, send to `iidx_state_reco` (TCP), then optionally send to `iidx_score_reco` (TCP). With 4 cabinets and a 1-second interval, any single slow inference (e.g., score OCR on a large 1920x1080 PNG) delays the entire round-robin. At 1 Hz this is tolerable, but if the operator lowers the interval or inference services are under load, cabinets fall behind real-time and scene switches miss critical moments like `play` -> `score`.

**Why it happens:**
The existing `web_monitor.py` uses a single `threading.Thread` that loops over machines sequentially. There is no concurrency per machine, and TCP sockets are created fresh for every request without connection pooling.

**Prevention:**
- Process each cabinet in its own thread or use a small thread pool (e.g., `concurrent.futures.ThreadPoolExecutor` with 4 workers).
- Keep persistent TCP connections to inference services instead of opening/closing sockets per frame.
- Decouple frame capture from scene switching: the state machine should emit events, and a separate executor should handle OBS commands.

**Detection:**
- Frame timestamps drift significantly between machines.
- Logs show large gaps between `capture_source` and `process_event` for the same machine.
- Score recognition happens after the game has already left the `score` screen.

**Phase to address:** Phase 1 (Core Web App + OBS Integration)

---

### Pitfall 3: Over-Automating Scene Transitions Without Operator Override

**What goes wrong:**
The director auto-switches scenes based on AI state recognition, but the AI can misclassify states (e.g., `interlude` mistaken for `score`, or a brief `blank` screen triggering an unwanted cut). Once the scene is on air, the operator has no quick way to undo it without manually switching in OBS, which breaks the director's internal state assumptions.

**Why it happens:**
State recognition models are not 100% accurate, especially during fast transitions or unusual game modes. If the automation logic treats every state change as a command rather than a recommendation, errors propagate directly to the broadcast.

**Prevention:**
- Implement a "pending transition" model: when the director wants to switch scenes, it highlights the proposed switch in the UI and waits for operator confirmation (or a configurable auto-confirm timeout).
- Provide a big, always-visible "EMERGENCY LIVE" button that immediately cuts to the `现场摄像` scene and pauses all automation.
- Log every auto-switch with a one-click "revert" action in the UI.

**Detection:**
- Operator complaints about "the director keeps cutting to the wrong scene."
- Broadcast viewers see jarring, incorrect scene changes.
- Logs show rapid back-to-back scene switches within seconds.

**Phase to address:** Phase 2 (Scene Automation Logic)

---

### Pitfall 4: Losing Scoreboard State on Page Refresh or Server Restart

**What goes wrong:**
The operator refreshes the web UI mid-tournament, or the Flask development server auto-reloads on code change, and all round assignments, confirmed scores, and current scene state are lost. The operator must re-enter everything while the tournament is live.

**Why it happens:**
Flask's default in-memory global state (`_machines`, `_score_history`, round-to-cabinet mappings) disappears on process restart. Without persistent state, a simple `Ctrl+R` or a dev-server reload is catastrophic.

**Prevention:**
- Persist all tournament runtime state to a JSON or SQLite file on every mutation (round assignments, confirmed scores, current scene, delay settings).
- Load this state automatically on server startup.
- Do not rely on Flask's built-in reloader in production; use `debug=False` and a proper WSGI server.

**Detection:**
- After a refresh, the UI shows "No players assigned" despite assignments having been made.
- The scoreboard reverts to an earlier round's scores.
- Development logs show `* Detected change in ... restarting` during active matches.

**Phase to address:** Phase 1 (Core Web App + OBS Integration)

---

### Pitfall 5: Hard-Coding Scene Names and Scoreboard WebSocket Payloads

**What goes wrong:**
Scene names like `SP团队赛`, `DP团队赛`, and `个人赛` are embedded directly in Python `if/else` chains. When the tournament organizer renames a scene in OBS or adds a new one, the director breaks silently. Similarly, scoreboard WebSocket message formats are often copy-pasted into the director without versioning, so a scoreboard server update causes push failures.

**Why it happens:**
It is tempting to write `if mode == "team_sp": obs.set_scene("SP团队赛")` because the scene set is small. But OBS scene names are user-facing strings that change for aesthetic or organizational reasons.

**Prevention:**
- Externalize scene name mappings into the tournament JSON config (e.g., `obs_scenes.team_sp = "SP团队赛"`).
- Validate all configured scene names against OBS's actual scene list on startup and warn the operator if any are missing.
- Abstract scoreboard pushes behind a small adapter class so the WebSocket payload format lives in one place.

**Detection:**
- Scene switch API calls return 404-like errors from OBS.
- Scoreboard updates stop appearing on stream; browser source shows stale data.
- Operator renames a scene in OBS and the director stops switching to it.

**Phase to address:** Phase 1 (Core Web App + OBS Integration)

---

### Pitfall 6: Misaligned Delays Causing Race Conditions Between Scene and Scoreboard

**What goes wrong:**
The director implements the required delay sequence: after operator confirmation, wait 5s, push score to scoreboard, wait 15s, then switch back to Live. If these delays are implemented with simple `time.sleep()` in the main thread, they block all other automation. Worse, if the operator changes the delay setting mid-sequence, the old sleep duration still applies, or the sequence is interrupted inconsistently.

**Why it happens:**
Using `threading.Event.wait()` or `time.sleep()` inside the single monitor loop is the easiest implementation, but it serializes all cabinet processing and makes delay parameters non-dynamic.

**Prevention:**
- Use a per-machine scheduler (e.g., a priority queue or `sched` module) that stores future actions with absolute timestamps.
- Make delay settings take effect for the *next* scheduled action, not retroactively.
- Support `-1` (manual advance) by simply not scheduling the next automatic action until the operator clicks a button.

**Detection:**
- After confirming a score, the director freezes for 20 seconds and misses state changes on other cabinets.
- Changing the delay slider has no effect on an already-running sequence.
- Two cabinets finish at nearly the same time and their sequences interfere.

**Phase to address:** Phase 2 (Scene Automation Logic)

---

### Pitfall 7: Not Handling AI Score Recognition Edge Cases

**What goes wrong:**
The `iidx_score_reco` service returns scores with validation flags (`1p_valid`, `2p_valid`). If the director blindly trusts these flags or ignores the `pending_score_validation` retry logic, invalid scores get pushed to the scoreboard. Conversely, if it retries too aggressively while the cabinet has already left the `score` screen, it wastes inference cycles and may capture the wrong screen.

**Why it happens:**
The existing `obs_manager.py` already has `pending_score_validation` logic, but it is easy to drop this nuance when building a new web UI that focuses on "operator confirmation." A developer might skip validation and just show whatever the AI returns.

**Prevention:**
- In the score review UI, visually distinguish valid vs. invalid scores (e.g., green border for valid, red for invalid, gray for missing).
- Only auto-populate the scoreboard push with scores where at least one side is valid; otherwise default to empty/placeholder and require manual entry.
- Respect the `pending_score_validation` retry window: keep retrying only while the cabinet is still in a `score` state.

**Detection:**
- Scoreboard shows obviously wrong scores (e.g., 0000, 9999, or mismatched digits).
- Operator has to correct almost every score because the AI's invalid results were pre-filled.
- Logs show score recognition happening after the state has already transitioned to `interlude`.

**Phase to address:** Phase 3 (Score Review & Scoreboard Integration)

---

## Moderate Pitfalls

### Pitfall 1: Using Flask's Development Server in Production

**What goes wrong:**
The operator runs the tournament director on the streaming PC using `app.run()`. Under load (4 video streams, WebSocket clients, frequent AJAX polling), the dev server becomes sluggish or drops connections.

**Prevention:**
- Document and script production startup with `waitress` or `gunicorn`.
- Keep `app.run()` only for local development.

**Phase to address:** Phase 1 (Core Web App + OBS Integration)

---

### Pitfall 2: Polling the UI Instead of Pushing Events

**What goes wrong:**
The web UI polls `/api/status` every second to get state updates. This creates unnecessary HTTP overhead and introduces up to 1 second of UI lag compared to the actual game state.

**Prevention:**
- Use Flask-SocketIO or Server-Sent Events (SSE) to push state changes and score captures to the browser in real time.
- If SSE is too much overhead for the milestone, reduce polling interval to 200-500ms for critical phases.

**Phase to address:** Phase 1 (Core Web App + OBS Integration)

---

### Pitfall 3: Missing Cleanup on Shutdown

**What goes wrong:**
When the director process is killed (Ctrl+C), OBS scene items or text sources that were modified remain in their last state, and TCP connections to inference services are left half-open.

**Prevention:**
- Register `atexit` and signal handlers to disconnect OBS, close inference sockets, and reset any temporary scene modifications.
- Implement a graceful shutdown endpoint (`/api/shutdown`) for clean exits.

**Phase to address:** Phase 1 (Core Web App + OBS Integration)

---

## Minor Pitfalls

### Pitfall 1: Logging Too Much to the Browser

**What goes wrong:**
Every frame capture and inference result is sent to the browser log panel. After 10 minutes of tournament runtime, the DOM becomes huge and the UI lags.

**Prevention:**
- Cap the browser-visible log buffer to the most recent 100-200 entries.
- Write full debug logs to a rotating file on disk.

**Phase to address:** Phase 1 (Core Web App + OBS Integration)

---

### Pitfall 2: Not Validating Tournament JSON Schema

**What goes wrong:**
The operator loads a malformed `teams.json` or `team_schedule.json`. The app crashes with a `KeyError` deep in the rendering logic, leaving the operator with a broken UI and no clear error message.

**Prevention:**
- Validate all uploaded/loaded JSON configs against a strict schema (e.g., `pydantic` or `jsonschema`) before accepting them.
- Show human-readable validation errors in the UI (e.g., "Team 'Red' is missing required field 'color'").

**Phase to address:** Phase 1 (Core Web App + OBS Integration)

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Phase 1: Core Web App + OBS Integration | OBS WebSocket blocking the main loop | Async wrappers, connection health checks |
| Phase 1: Core Web App + OBS Integration | In-memory state lost on restart | JSON/SQLite persistence, auto-restore |
| Phase 1: Core Web App + OBS Integration | Hard-coded scene names | Config-driven scene mapping, startup validation |
| Phase 2: Scene Automation Logic | Over-automation without override | Pending transitions, emergency live button |
| Phase 2: Scene Automation Logic | `sleep()`-based delay sequences | Per-machine scheduler, absolute timestamps |
| Phase 3: Score Review & Scoreboard Integration | Blind trust in AI validation flags | Visual score validity indicators, manual fallback |
| Phase 3: Score Review & Scoreboard Integration | Race conditions between score push and scene switch | Unified state machine for director, not just per-cabinet |

## Sources

- Existing codebase analysis: `obs_manager.py`, `web_monitor.py`, `iidx_state_machine/state_machine.py`
- OBS WebSocket 5.x documentation patterns (synchronous `ReqClient` behavior)
- Flask deployment best practices (development server limitations)
- Domain knowledge from real-time broadcast automation systems

---
*Pitfalls research for: IIDX Tournament Auto-Director*
*Researched: 2026-04-14*
