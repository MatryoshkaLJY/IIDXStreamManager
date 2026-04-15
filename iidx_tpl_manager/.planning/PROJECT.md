# IIDX Tournament Auto-Director

## What This Is

A web-based intelligent OBS director for beatmania IIDX tournaments. It replaces the existing `web_monitor.py` with a unified control panel that:

1. Captures video frames from 4 arcade cabinets via OBS sources
2. Uses existing AI recognition pipelines (`iidx_state_reco`, `iidx_score_reco`) and state machine (`iidx_state_machine`) to detect game states and scores
3. Automatically drives OBS scene transitions for live broadcasts
4. Feeds confirmed scores into the appropriate scoreboard (team BPL-style or individual knockout)

## Current State

**v1.0 Shipped (2026-04-13):** 16-player knockout tournament scoreboard with vanilla HTML/CSS/JS and a Python WebSocket relay (`iidx_knockout_scoreboard`).

**v1.1 Shipped (2026-04-15):** Knockout scoreboard rule refinements — cumulative raw scoring, E/F semifinal groups, auto-advance active highlighting, tiebreaker logic, and medal styling. Verified with a 6-test jsdom suite.

**In `iidx_tpl_manager` (Auto-Director app):**
- Config loader with Pydantic validation and template generation (`src/config/`)
- Flask app shell with SocketIO on port 5002 (`src/app.py`)
- Runtime state persistence (`src/state.py`)
- Status page with Jinja2 templates and CSS tokens

## Problem

Running an IIDX tournament stream currently requires multiple disconnected tools (`obs_manager`, `switcher.py`, separate scoreboard servers) and a lot of manual scene switching. The operator must watch the game, decide when to switch scenes, read scores, and update scoreboards by hand.

## Solution

Build a single Python web application (`iidx_tpl_manager`) that unifies monitoring, scene automation, and scoreboard integration. The operator only needs to:

- Select tournament mode (team vs individual)
- Load the pre-written tournament JSON configuration
- Assign players to cabinet numbers before each round
- Review and confirm AI-recognized scores (with one-click correction if needed)

## Domain

- **Game:** beatmania IIDX (arcade rhythm game)
- **Hardware:** 4 arcade cabinets (IIDX#1 ~ IIDX#4)
- **Broadcast tool:** OBS Studio with WebSocket
- **AI recognition:** Existing TCP services for state recognition (port 9876) and score OCR (port 9877)
- **Scoreboards:** Existing web-based BPL scoreboard (WebSocket 8080) and 16-player knockout scoreboard (WebSocket 8081)

## Context

### Existing Components (do not reimplement)

| Component | Location | Role |
|-----------|----------|------|
| `iidx_score_reco` | `../iidx_score_reco` | TCP service for digit recognition from screenshots |
| `iidx_state_reco` | `../iidx_state_reco` | TCP service for AI game-state classification |
| `iidx_state_machine` | `../iidx_state_machine` | TCP service tracking game flow across states |
| `iidx_bpl_scoreboard` | `../iidx_bpl_scoreboard` | Web-based team scoreboard (WebSocket 8080) |
| `iidx_knockout_scoreboard` | `../iidx_knockout_scoreboard` | Web-based individual knockout scoreboard (WebSocket 8081) |
| `obs_manager.py` | `../obs_manager/obs_manager.py` | Python library for OBS capture + recognition integration |

### OBS Scenes (target names)

- `现场摄像` — Live camera shots of players/venue
- `SP团队赛` — Gameplay overlay for SP (single play) team matches
- `DP团队赛` — Gameplay overlay for DP (double play) team matches
- `个人赛` — Gameplay overlay for individual matches
- *(Future)* `Scoreboard_game` — In-game score result screen
- *(Future)* `Scoreboard_web` — Web scoreboard browser source

## Next Milestone Goals

- Operator UI for tournament mode selection and round-prep player assignments
- OBS WebSocket integration for programmatic scene switching
- Cabinet monitoring with `obs_manager.py` and real-time state display
- Score review workflow with operator confirmation and scoreboard push

## Requirements

### Validated

- ✓ 16-player knockout tournament scoreboard — v1.0
- ✓ Knockout scoreboard rule refinements (cumulative scoring, E/F groups, medals, tiebreaker) — v1.1
- ✓ Config loader with Pydantic validation and template generation — Phase 01
- ✓ Flask app shell with SocketIO on port 5002 — Phase 01
- ✓ Runtime state persistence — Phase 01

### Active

- [ ] Build a Python web application on port 5002
- [ ] Support two tournament modes: team match (BPL-style) and individual knockout
- [ ] Provide a web UI for operator to select tournament mode and load config
- [ ] Provide a round-prep page where operator assigns each player to one of 4 cabinets before each round
- [ ] Reuse `obs_manager.py` as a library for frame capture and recognition
- [ ] Integrate with `iidx_state_machine` to track game flow across all 4 cabinets
- [ ] Automatically switch OBS scenes for transitions 1, 2, and 4 (Live ↔ Gameplay ↔ Scoreboard_game)
- [ ] On `score` state, capture scores, display them in the web UI for operator review
- [ ] Allow operator to edit recognized scores before confirming
- [ ] On manual confirmation, trigger transition 3 (Scoreboard_game → Scoreboard_web)
- [ ] After transition 3, delay 5s, push score to the active scoreboard, delay 15s, then auto-switch back to Live
- [ ] Make all delays configurable in the web UI (including `-1` for fully manual advance)
- [ ] Control OBS group visibility and text sources for gameplay scenes, similar to `tpl_scene_switcher/switcher.py`
- [ ] Support SP and DP team match scene setup

### Out of Scope

- Reimplementing score recognition, state recognition, or state machine — use existing components
- Reimplementing scoreboard rendering — use existing BPL/knockout servers
- Scene names beyond the listed set — new scenes will be added manually in OBS later
- Multi-event concurrency — one event uses one mode at a time

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + Flask | Operator prefers ease of development over performance; existing stack is Flask-based | ✓ Good — Phase 01 app shell built successfully |
| Port 5002 | Avoids conflict with existing `web_monitor.py` on 5001 | ✓ Good — app runs on 5002 as planned |
| Reuse `obs_manager.py` | Avoids duplicating OBS capture and TCP inference logic | — Pending (next milestone) |
| One mode per event | Simplifies UI and state management | ✓ Good — keeps config and UI simple |
| Delays configurable including `-1` | Gives operator full control over pacing | — Pending (next milestone) |

## Constraints

- Must work with existing TCP inference services (9876, 9877) and WebSocket scoreboards (8080, 8081)
- Must support 4 cabinet sources mapped dynamically per round
- Must run locally on the streaming PC alongside OBS

## Users

- **Primary:** Tournament stream operator — sets up matches, reviews scores, intervenes when AI misreads
- **Secondary:** Scoreboard server viewers — see updated scores after operator confirmation

## Success

- Operator can run a full tournament round with minimal manual scene switching
- Score recognition errors can be caught and fixed in the web UI before going live
- Broadcast transitions feel smooth and timed correctly

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-15 after v1.1 milestone*
