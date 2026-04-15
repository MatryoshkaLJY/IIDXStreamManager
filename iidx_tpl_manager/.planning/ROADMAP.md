# Roadmap: IIDX Tournament Auto-Director

## Milestones

- ✅ **v1.0 Knockout Tournament Scoreboard** — Phase 1 (shipped 2026-04-13)
- ✅ **v1.1 Tournament Rule Refinements** — Phase 2 (shipped 2026-04-15)
- 🚧 **v1.2 Auto-Director Core** — Phases 3-7 (in progress)

## Phases

<details>
<summary>✅ v1.0 Knockout Tournament Scoreboard (Phase 1) — SHIPPED 2026-04-13</summary>

- [x] Phase 1: 16-Player Knockout Tournament Scoreboard (7/7 summaries) — completed 2026-04-13
  - Plan 01: HTML/CSS structure and radial tree layout
  - Plan 02: WebSocket server and client communication
  - Plan 03: Tournament logic and scoring system
  - Fix 01-01: Index alignment (HTML vs JS)
  - Fix 01-02: Finals group mapping
  - Fix 01-03: Visual layout redesign
  - Fix 01-04: Score/points styling

See archive: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

</details>

<details>
<summary>✅ v1.1 Tournament Rule Refinements (Phase 2) — SHIPPED 2026-04-15</summary>

- [x] Phase 2: Tournament Rule Refinements (2/2 plans) — completed 2026-04-15
  - Plan 01: Cleanup and Foundation Fixes (remove trophy, fix init, cumulative scoring)
  - Plan 02: Group Restructure, Progression, and Finals Visuals (E/F groups, active highlighting, sorting, medals)

See archive: [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)

</details>

### 🚧 v1.2 Auto-Director Core (In Progress)

**Milestone Goal:** Unify tournament operation into a single web control panel with OBS scene automation, cabinet monitoring, and score review workflow.

- [ ] **Phase 3: OBS Integration & Scene Control** — Connect to OBS WebSocket v5 and enable programmatic scene/source control
- [ ] **Phase 4: Tournament Setup & Round Prep UI** — Mode selection, config loading, and player-to-cabinet assignment
- [ ] **Phase 5: Cabinet Monitoring & Live Monitor UI** — Real-time 4-cabinet state visualization via background polling
- [ ] **Phase 6: Score Review & Scoreboard Integration** — Human-in-the-loop score confirmation and scoreboard push
- [ ] **Phase 7: Auto-Transitions & Configurable Delays** — State-driven scene automation with operator override controls

## Phase Details

### Phase 3: OBS Integration & Scene Control
**Goal**: Application can reliably connect to OBS and control scenes/sources
**Depends on**: Nothing (first phase of v1.2)
**Requirements**: OBS-01, OBS-02, OBS-03, OBS-04
**Success Criteria** (what must be TRUE):
  1. On startup, the app validates that configured scene names exist in OBS and shows an error if any are missing
  2. Operator can click a button in the web UI to switch OBS to any of the four main scenes (Live, SP team, DP team, individual)
  3. Gameplay scenes show the correct group visibility and text source values for SP vs DP setup
  4. If OBS WebSocket disconnects, the UI displays a warning banner and auto-switching pauses
**Plans**: 4 plans
**UI hint**: yes

Plan list:
- [ ] `03-01-PLAN.md` — Backend Core: RuntimeState, OBSClient, SceneController, and unit tests
- [ ] `03-02-PLAN.md` — Flask Integration: heartbeat thread, routes, SocketIO handlers, and tests
- [ ] `03-03-PLAN.md` — UI: templates, CSS, operator.js SocketIO client
- [ ] `03-04-PLAN.md` — Human Verification: end-to-end OBS connection and scene switching checkpoint

### Phase 4: Tournament Setup & Round Prep UI
**Goal**: Operator can configure tournament mode, load configs, and assign players to cabinets
**Depends on**: Phase 3
**Requirements**: UI-01, UI-02, UI-03, UI-04, AUTO-05
**Success Criteria** (what must be TRUE):
  1. Operator can select "team" or "individual" mode from a dropdown in the web UI
  2. Operator can upload/load a tournament JSON config and see clear validation error messages if it's malformed
  3. On the round-prep page, operator sees current mode, round number, and can assign each player to IIDX#1~#4
  4. After server restart, previously loaded config, round assignments, and delay settings are automatically restored
**Plans**: TBD
**UI hint**: yes

### Phase 5: Cabinet Monitoring & Live Monitor UI
**Goal**: Operator can view real-time cabinet states and captured frames in the browser
**Depends on**: Phase 4
**Requirements**: MON-01, MON-02, MON-03, MON-04
**Success Criteria** (what must be TRUE):
  1. Live monitor page shows a thumbnail or frame capture for each of the 4 cabinets updating at a configurable interval
  2. Each cabinet displays its current state label (live, play, score, blank, etc.) in real time
  3. State updates appear in the browser without page refresh via SocketIO
  4. Frame capture and inference run in the background without blocking the Flask UI
**Plans**: 3 plans
**UI hint**: yes

Plan list:
- [ ] `05-01-PLAN.md` — Extend RuntimeState with monitor_interval, monitoring_active, and source_names
- [ ] `05-02-PLAN.md` — Create CabinetMonitor background worker with SocketIO and JSON console logging
- [ ] `05-03-PLAN.md` — Integrate monitor controls into Flask app, Status page, and operator.js

### Phase 6: Score Review & Scoreboard Integration
**Goal**: Operator can review, correct, and confirm scores before pushing to scoreboard
**Depends on**: Phase 5
**Requirements**: SCR-01, SCR-02, SCR-03, SCR-04, SCR-05, SCR-06
**Success Criteria** (what must be TRUE):
  1. When a cabinet reaches `score` state with valid OCR results, the scores automatically appear in the review UI
  2. Scores flagged as invalid by the recognition service are visually highlighted in the review UI
  3. Operator can click to edit any recognized score before confirming
  4. On confirmation, the app switches OBS to `Scoreboard_web` scene, waits, then pushes the score to the correct scoreboard server (BPL or knockout)
  5. Scoreboard push succeeds using the correct WebSocket protocol for the active tournament mode
**Plans**: TBD
**UI hint**: yes

### Phase 7: Auto-Transitions & Configurable Delays
**Goal**: Broadcast transitions between Live, Gameplay, and Scoreboard_game happen automatically based on cabinet state, with operator override
**Depends on**: Phase 6
**Requirements**: AUTO-01, AUTO-02, AUTO-03, AUTO-04
**Success Criteria** (what must be TRUE):
  1. App automatically switches from Live to Gameplay when cabinets enter play state, and back to Live when appropriate, without operator action
  2. Operator can set custom delay values in the web UI for scoreboard display and return-to-live timing
  3. Setting a delay to `-1` pauses automatic advancement until the operator clicks a manual proceed button
  4. An "Emergency Live" button is always visible; clicking it immediately cuts to the Live camera scene and pauses automation
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 3 → 4 → 5 → 6 → 7

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Knockout Scoreboard | v1.0 | 7/7 | Complete | 2026-04-13 |
| 2. Rule Refinements | v1.1 | 2/2 | Complete | 2026-04-15 |
| 3. OBS Integration & Scene Control | v1.2 | 0/4 | Not started | - |
| 4. Tournament Setup & Round Prep UI | v1.2 | 0/TBD | Not started | - |
| 5. Cabinet Monitoring & Live Monitor UI | v1.2 | 0/TBD | Not started | - |
| 6. Score Review & Scoreboard Integration | v1.2 | 0/TBD | Not started | - |
| 7. Auto-Transitions & Configurable Delays | v1.2 | 0/TBD | Not started | - |
