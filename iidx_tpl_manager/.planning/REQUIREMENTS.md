# Requirements

## v1 Requirements

### Config & Setup

- [ ] **CONF-01**: Operator can select tournament mode (team match or individual knockout) from the web UI
- [ ] **CONF-02**: Application loads `teams.json`, `team_schedule.json`, and `individual_schedule.json` from a `data/` subdirectory
- [ ] **CONF-03**: Application validates loaded JSON configs against expected schemas and reports human-readable errors
- [ ] **CONF-04**: Operator can assign each player to one of 4 cabinet numbers on a round-prep page before each round
- [ ] **CONF-05**: Runtime state (round assignments, confirmed scores, delay settings, current scene) is persisted to disk and auto-restored on startup

### OBS Integration

- [ ] **OBS-01**: Application can switch OBS scenes programmatically via WebSocket
- [ ] **OBS-02**: Scene name mappings are externalized in config and validated against OBS's actual scene list on startup

### Monitoring & Auto-Switching

- [ ] **MON-01**: Application polls all 4 cabinets continuously using `obs_manager.py` for frame capture and state recognition
- [ ] **MON-02**: Web UI displays the current detected state per cabinet in real time
- [ ] **MON-03**: Application automatically triggers scene transitions 1, 2, and 4 (Live ↔ Gameplay ↔ Scoreboard_game) based on aggregate state machine output

### Score Review & Scoreboard

- [ ] **SCR-01**: When a cabinet enters the `score` state, application captures scores via `iidx_score_reco`
- [ ] **SCR-02**: Recognized scores are displayed in the web UI with visual validity indicators; operator can edit before confirming
- [ ] **SCR-03**: On operator confirmation, application pushes the confirmed score to the active scoreboard (BPL port 8080 or knockout port 8081)
- [ ] **SCR-04**: Post-confirmation timing is configurable in the web UI (default: 5s delay before score push, 15s delay before returning to Live; `-1` enables fully manual advance)

## v2 Requirements

- Gameplay scene setup for SP / DP / individual matches (OBS group visibility and text source configuration)
- Emergency Live button to immediately cut to live camera and pause automation
- One-click score correction shortcuts (+/- buttons for common adjustments)
- Round-aware context preloading (pre-configure gameplay scene before switching)

## Out of Scope

- Reimplementing score recognition, state recognition, or state machine — use existing components
- Reimplementing scoreboard rendering — use existing BPL/knockout servers
- Scene names beyond the listed set — new scenes will be added manually in OBS later
- Multi-event concurrency — one event uses one mode at a time
- Mobile-responsive operator UI — desktop browser only

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONF-01 | Phase 2 | Pending |
| CONF-02 | Phase 1 | Pending |
| CONF-03 | Phase 1 | Pending |
| CONF-04 | Phase 2 | Pending |
| CONF-05 | Phase 1 | Pending |
| OBS-01 | Phase 3 | Pending |
| OBS-02 | Phase 3 | Pending |
| MON-01 | Phase 4 | Pending |
| MON-02 | Phase 4 | Pending |
| MON-03 | Phase 5 | Pending |
| SCR-01 | Phase 6 | Pending |
| SCR-02 | Phase 6 | Pending |
| SCR-03 | Phase 6 | Pending |
| SCR-04 | Phase 6 | Pending |
