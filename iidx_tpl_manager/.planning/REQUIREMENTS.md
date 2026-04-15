# Requirements: Milestone v1.2 Auto-Director Core

## v1.2 Requirements

### Operator UI / Tournament Setup
- [ ] **UI-01**: Operator can select tournament mode (team BPL-style or individual knockout) from the web UI
- [ ] **UI-02**: Operator can load a pre-written tournament JSON config (`teams.json`, `team_schedule.json`, or `individual_schedule.json`) and see validation errors if malformed
- [ ] **UI-03**: Operator can assign each player to one of 4 cabinets (IIDX#1 ~ IIDX#4) on a round-prep page before each round
- [ ] **UI-04**: Round-prep page displays the current mode, round number, and list of players to assign

### OBS Integration
- [ ] **OBS-01**: Application connects to OBS Studio via WebSocket v5 and validates configured scene names on startup
- [ ] **OBS-02**: Application can programmatically switch OBS scenes: `现场摄像`, `SP团队赛`, `DP团队赛`, `个人赛`
- [ ] **OBS-03**: Application controls group visibility and text sources within gameplay scenes (SP/DP team match setup)
- [ ] **OBS-04**: Connection health is monitored; if OBS becomes unreachable, auto-switching is paused and the UI shows a warning

### Cabinet Monitoring
- [ ] **MON-01**: Background worker polls all 4 cabinets via `obs_manager.py` at a configurable interval
- [ ] **MON-02**: Live monitor page displays real-time state labels (`live`, `play`, `score`, `blank`, etc.) and captured frames/thumbnails for each cabinet
- [ ] **MON-03**: Frame capture and inference do not block the main Flask request thread
- [ ] **MON-04**: State machine transitions per cabinet are emitted to the web UI via SocketIO

### Score Review & Scoreboard Push
- [ ] **SCR-01**: When a cabinet enters `score` state with valid OCR results, the scores appear in the score review UI for operator inspection
- [ ] **SCR-02**: Scores are visually flagged as valid/invalid based on `1p_valid` / `2p_valid` flags from `iidx_score_reco`
- [ ] **SCR-03**: Operator can edit recognized scores before confirming
- [ ] **SCR-04**: On operator confirmation, the director triggers transition to `Scoreboard_web` scene
- [ ] **SCR-05**: After transition to `Scoreboard_web`, the app waits a configurable delay, then pushes the confirmed score to the active scoreboard (BPL on 8080 or knockout on 8081)
- [ ] **SCR-06**: Scoreboard push uses the correct WebSocket protocol for the active tournament mode

### Automation & Delays
- [ ] **AUTO-01**: Auto-transitions 1, 2, and 4 (Live ↔ Gameplay ↔ Scoreboard_game) are driven by aggregate cabinet state without operator intervention
- [ ] **AUTO-02**: All timing delays (scoreboard display, return to live) are configurable in the web UI
- [ ] **AUTO-03**: Delays support `-1` for fully manual advance (operator must click to proceed)
- [ ] **AUTO-04**: An "Emergency Live" button is always visible to immediately cut to `现场摄像` and pause automation
- [ ] **AUTO-05**: Runtime state (round assignments, confirmed scores, delay settings, current scene) persists to disk and auto-restores on server restart

## Future Requirements

- Mobile-responsive operator UI — deferred; target is a desktop browser on the streaming PC
- Multi-event concurrency — one event uses one mode at a time
- Cloud inference or remote OBS — out of scope for local tournament use

## Out of Scope

- Reimplementing `iidx_state_reco`, `iidx_score_reco`, or `iidx_state_machine` — reuse existing TCP services
- Reimplementing BPL or knockout scoreboard rendering — use existing WebSocket servers
- Adding new OBS scene types beyond the listed set — scenes will be added manually in OBS later

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| OBS-01 | Phase 3 | Pending |
| OBS-02 | Phase 3 | Pending |
| OBS-03 | Phase 3 | Pending |
| OBS-04 | Phase 3 | Pending |
| UI-01 | Phase 4 | Pending |
| UI-02 | Phase 4 | Pending |
| UI-03 | Phase 4 | Pending |
| UI-04 | Phase 4 | Pending |
| AUTO-05 | Phase 4 | Pending |
| MON-01 | Phase 5 | Pending |
| MON-02 | Phase 5 | Pending |
| MON-03 | Phase 5 | Pending |
| MON-04 | Phase 5 | Pending |
| SCR-01 | Phase 6 | Pending |
| SCR-02 | Phase 6 | Pending |
| SCR-03 | Phase 6 | Pending |
| SCR-04 | Phase 6 | Pending |
| SCR-05 | Phase 6 | Pending |
| SCR-06 | Phase 6 | Pending |
| AUTO-01 | Phase 7 | Pending |
| AUTO-02 | Phase 7 | Pending |
| AUTO-03 | Phase 7 | Pending |
| AUTO-04 | Phase 7 | Pending |
