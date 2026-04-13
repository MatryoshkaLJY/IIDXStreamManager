# ROADMAP

## Phases

- [ ] **Phase 1: Foundation & Config** - Flask app shell, JSON config loading/validation, and runtime state persistence
- [ ] **Phase 2: Tournament Setup** - Web UI for mode selection and round-prep player-to-cabinet assignment
- [ ] **Phase 3: OBS Integration** - OBS WebSocket connection, manual scene switching, and scene name validation
- [ ] **Phase 4: Live Monitoring** - Continuous 4-cabinet polling and real-time state display in the web UI
- [ ] **Phase 5: Scene Automation** - Automatic scene transitions based on aggregate game state from the state machine
- [ ] **Phase 6: Score Workflow** - Score capture, review/correction UI, scoreboard push, and configurable post-confirmation timing

## Phase Details

### Phase 1: Foundation & Config
**Goal**: Application boots with a working web server and handles tournament configuration reliably
**Depends on**: Nothing (first phase)
**Requirements**: CONF-02, CONF-03, CONF-05
**Success Criteria** (what must be TRUE):
  1. Operator can start the application and access the web UI at port 5002
  2. Application loads `teams.json`, `team_schedule.json`, and `individual_schedule.json` from `data/` and reports human-readable validation errors
  3. Runtime state (configs, settings) is persisted to disk and auto-restored on restart
**Plans**: TBD
**UI hint**: yes

### Phase 2: Tournament Setup
**Goal**: Operator can configure a tournament round through the web UI
**Depends on**: Phase 1
**Requirements**: CONF-01, CONF-04
**Success Criteria** (what must be TRUE):
  1. Operator can select team match or individual knockout mode from the web UI
  2. Operator can assign each player to one of 4 cabinet numbers on a round-prep page before each round
  3. Round assignments are displayed and can be modified until the round starts
**Plans**: TBD
**UI hint**: yes

### Phase 3: OBS Integration
**Goal**: Application can control OBS scenes programmatically
**Depends on**: Phase 1
**Requirements**: OBS-01, OBS-02
**Success Criteria** (what must be TRUE):
  1. Application connects to OBS WebSocket on startup and reports connection status in the web UI
  2. Operator can switch OBS scenes manually from the web UI
  3. Configured scene names are validated against OBS's actual scene list, with mismatches reported clearly
**Plans**: TBD
**UI hint**: yes

### Phase 4: Live Monitoring
**Goal**: Operator can view real-time game state for all 4 cabinets
**Depends on**: Phase 1
**Requirements**: MON-01, MON-02
**Success Criteria** (what must be TRUE):
  1. Application continuously captures frames and recognizes state for all 4 cabinets via `obs_manager.py`
  2. Web UI displays the current detected state for each cabinet in real time
  3. Monitoring runs in the background without blocking the web UI
**Plans**: TBD
**UI hint**: yes

### Phase 5: Scene Automation
**Goal**: Application automatically switches scenes based on detected game state
**Depends on**: Phase 3, Phase 4
**Requirements**: MON-03
**Success Criteria** (what must be TRUE):
  1. Application automatically switches from Live to Gameplay when cabinets enter play
  2. Application automatically switches from Gameplay to Scoreboard_game when cabinets enter the score state
**Plans**: TBD

### Phase 6: Score Workflow
**Goal**: Operator can review, correct, and publish scores to the broadcast
**Depends on**: Phase 2, Phase 4, Phase 5
**Requirements**: SCR-01, SCR-02, SCR-03, SCR-04
**Success Criteria** (what must be TRUE):
  1. When a cabinet enters the score state, captured scores appear in the web UI with visual validity indicators
  2. Operator can edit recognized scores before confirming
  3. On operator confirmation, application pushes the score to the active scoreboard and triggers the Scoreboard_game → Scoreboard_web transition
  4. After the configured delays, application automatically returns to Live; delays are configurable in the web UI including `-1` for manual advance
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Config | 0/0 | Not started | - |
| 2. Tournament Setup | 0/0 | Not started | - |
| 3. OBS Integration | 0/0 | Not started | - |
| 4. Live Monitoring | 0/0 | Not started | - |
| 5. Scene Automation | 0/0 | Not started | - |
| 6. Score Workflow | 0/0 | Not started | - |
