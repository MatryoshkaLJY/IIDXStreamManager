# Feature Landscape

**Domain:** Python web-based OBS tournament director for beatmania IIDX
**Researched:** 2026-04-15
**Confidence:** HIGH (derived from direct analysis of existing codebase components, protocols, and operator workflows)

---

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **OBS Scene Switching** | Core purpose of a director tool; must cut between Live, Gameplay, and Scoreboard scenes | Low | Already implemented in `switcher.py` and `obs_manager.py`. New work: port to `obsws-python` v5 inside Flask app. |
| **Multi-Cabinet Monitoring (4x)** | Tournaments use 4 IIDX cabinets; operator must see all | Medium | `obs_manager.py` already registers machines and polls frames. New work: expose per-cabinet state via SocketIO to the web UI. |
| **Game State Detection Integration** | Automatic switching depends on knowing when gameplay starts/ends | Low | TCP service on 9876 (`iidx_state_reco`) + state machine already exists. New work: wire `process_frame()` loop into Flask background thread. |
| **Score OCR Integration** | Feeding scoreboards requires reading arcade screen digits | Low | TCP service on 9877 (`iidx_score_reco`) already exists. New work: trigger capture on `score` state and surface results in UI. |
| **Score Review & Correction UI** | AI misreads are common; operator must fix before broadcast | Medium | Explicit requirement in PROJECT.md. Depends on OCR integration and SocketIO push. |
| **Tournament Mode Selection** | Team (BPL-style) vs Individual (knockout) are the two supported formats | Low | Required by PROJECT.md. UI only; backend mode flag determines which scoreboard to push. |
| **JSON Config Loading** | Teams, schedules, and brackets must be loadable per event | Low | Already built: `src/config/loader.py` with Pydantic validation. |
| **Round Prep / Player-to-Cabinet Assignment** | Players move between cabinets each round; dynamic mapping is essential | Medium | Required by PROJECT.md. Depends on config loader and mode selection. |
| **Gameplay Scene Setup (SP/DP)** | OBS groups and text sources must be configured per match type | Medium | `switcher.py` already implements `set_sp_team_match` and `set_dp_team_match`. New work: port group-visibility and text-source logic into Flask backend. |
| **Scoreboard Push Integration** | Confirmed scores must reach BPL (8080) and knockout (8081) scoreboards | Low | Protocols documented in `PROTOCOL.md` and knockout server. New work: WebSocket client wrapper and confirmation gating. |
| **Configurable Timing Delays** | Different tournaments/streamers want different pacing | Low | PROJECT.md requires delays configurable including `-1` for manual. UI sliders/inputs + backend timer logic. |

---

## Differentiators

Features that set this product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **AI-Assisted Auto-Switching** | Reduces operator cognitive load by automating scene transitions based on real-time state machine output | Medium | Unique because it ties together existing AI services (state reco + state machine) rather than just time-based or manual switching. Depends on multi-cabinet monitoring and OBS integration. |
| **Unified Single-Web-App Control Panel** | Replaces disconnected tools (`obs_manager`, `switcher.py`, separate scoreboard servers) with one interface | Medium | PROJECT.md explicitly frames this as the primary value proposition. Depends on all table-stakes features. |
| **One-Click Score Correction** | Faster than retyping; reduces on-air mistakes | Low | Can be implemented with +/- buttons or preset common errors. Enhances Score Review & Correction UI. |
| **Live State Visualization for All 4 Cabinets** | Operator sees not just video but current detected state per cabinet (IDLE, PLAY, SCORE, etc.) | Medium | Leverages `iidx_state_machine` outputs; adds situational awareness beyond raw video. Depends on game state detection integration and SocketIO. |
| **Delay Override on the Fly** | Operator can pause auto-advance or force immediate transition without leaving the web UI | Low | Configurable `-1` manual mode plus an explicit "Advance Now" button. Enhances configurable timing delays. |
| **Round-Aware Context Preloading** | When operator loads a round, gameplay scene text/groups can be pre-configured before switching | Medium | Reduces visible setup time between rounds. Depends on round prep and gameplay scene setup. |

---

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Reimplement AI Recognition** | Existing `iidx_state_reco` and `iidx_score_reco` services are mature and tested | Integrate via TCP as `obs_manager.py` already does |
| **Reimplement Scoreboard Rendering** | BPL and knockout scoreboards are already built and styled | Push data via WebSocket (`PROTOCOL.md` for BPL; knockout server protocol) |
| **Multi-Event Concurrency** | One event = one mode at a time; adds massive UI/state complexity for no local-streaming benefit | Restrict to one active tournament mode per running instance |
| **Cloud Hosting / Multi-User Login** | Runs locally on the streaming PC; no remote operator requirement | Single-operator local Flask app on port 5002 |
| **Custom OBS Scene Designer** | Scene names are fixed and manually maintained in OBS | Only switch to pre-defined scenes (`现场摄像`, `SP团队赛`, `DP团队赛`, `个人赛`) |
| **Persistent Database / Server-Side State History** | Stateless operation is sufficient for a single-day tournament stream | Keep state in memory; reload from JSON configs on restart |
| **Mobile-Responsive Operator UI** | Operator works from the streaming PC; target is a desktop browser | Build for desktop-first layout; no mobile optimization required |
| **Real-Time Chat / Audience Interaction** | Out of scope for a director tool focused on scene automation and score management | Use existing streaming platform chat (Bilibili, Twitch, etc.) |

---

## Feature Dependencies

```
Tournament Mode Selection
    → JSON Config Loading (already built)
        → Round Prep / Player-to-Cabinet Assignment
            → Gameplay Scene Setup (SP/DP)
                → OBS Scene Switching

Game State Detection Integration
    → Multi-Cabinet Monitoring (4x)
        → Live State Visualization
            → AI-Assisted Auto-Switching
                → Score OCR Integration
                    → Score Review & Correction UI
                        → Scoreboard Push Integration
                            → Configurable Timing Delays
```

### Dependency Notes

- **Round Prep requires JSON Config Loading:** Teams, schedules, and player lists come from validated config files (`data/teams.json`, `team_schedule.json`, `individual_schedule.json`). Config loader is already built.
- **Gameplay Scene Setup requires Round Prep:** SP/DP team match scenes need to know which cabinets are active and which players are assigned.
- **AI-Assisted Auto-Switching requires Multi-Cabinet Monitoring + Game State Detection:** The automation loop polls each cabinet via `obs_manager.py` and feeds labels into `iidx_state_machine`.
- **Score Review UI requires Score OCR Integration:** Scores are only captured when the state machine enters the `score` state; the UI cannot review what has not been captured.
- **Scoreboard Push requires Score Review UI:** Scores must be operator-confirmed before broadcast to prevent AI misreads from going live.
- **Configurable Timing Delays affect Auto-Switching and Scoreboard Push:** Delays control the timing of transitions (e.g., 5s before push, 15s before returning to Live).

---

## MVP Definition

### Launch With (v1.2)

Minimum viable product for the Auto-Director Core milestone.

- [ ] **Tournament Mode Selection + JSON Config Loading** — already built; wire into UI
- [ ] **Round Prep / Player-to-Cabinet Assignment** — required before every round
- [ ] **Multi-Cabinet Monitoring + Game State Detection** — enables automation
- [ ] **AI-Assisted Auto-Switching (Live ↔ Gameplay)** — core value proposition
- [ ] **Score OCR + Review UI** — operator trust depends on this
- [ ] **Scoreboard Push Integration** — delivers end-to-end value
- [ ] **Configurable Timing Delays** — required for flexible pacing

### Add After Validation (v1.2.x)

Features to add once core is working.

- [ ] **Live State Visualization** — operator can infer state from video in early versions
- [ ] **One-Click Score Correction** — start with editable text fields; +/- shortcuts can be added later
- [ ] **Delay Override on the Fly** — manual advance button and pause/resume

### Future Consideration (v1.3+)

Features to defer until product-market fit is established.

- [ ] **Round-Aware Context Preloading** — can be done manually in early versions
- [ ] **Scoreboard_game / Scoreboard_web dedicated scenes** — OBS scenes to be added manually later

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| OBS Scene Switching | HIGH | LOW | P1 |
| Multi-Cabinet Monitoring (4x) | HIGH | MEDIUM | P1 |
| Game State Detection Integration | HIGH | LOW | P1 |
| Score OCR Integration | HIGH | LOW | P1 |
| Score Review & Correction UI | HIGH | MEDIUM | P1 |
| Tournament Mode Selection | HIGH | LOW | P1 |
| JSON Config Loading | HIGH | LOW | P1 (already built) |
| Round Prep / Player-to-Cabinet Assignment | HIGH | MEDIUM | P1 |
| Gameplay Scene Setup (SP/DP) | HIGH | MEDIUM | P1 |
| Scoreboard Push Integration | HIGH | LOW | P1 |
| Configurable Timing Delays | MEDIUM | LOW | P1 |
| AI-Assisted Auto-Switching | HIGH | MEDIUM | P1 |
| Unified Single-Web-App Control Panel | HIGH | MEDIUM | P1 |
| Live State Visualization | MEDIUM | MEDIUM | P2 |
| One-Click Score Correction | MEDIUM | LOW | P2 |
| Delay Override on the Fly | MEDIUM | LOW | P2 |
| Round-Aware Context Preloading | MEDIUM | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | Manual OBS + Chat | tpl_scene_switcher | Our Approach |
|---------|-------------------|--------------------|--------------|
| Scene switching | Operator manually clicks OBS | Serial-triggered scripted switching | AI-driven + operator override via web UI |
| Cabinet monitoring | Watch 4 video feeds in OBS | Not supported | Unified web panel with per-cabinet state labels |
| Score entry | Read screen, type into scoreboard | Not supported | AI OCR + operator review + one-click confirm |
| Round setup | Edit text sources by hand | Hardcoded in Python script | Web UI loads JSON config and assigns players to cabinets |
| Delay control | None | Fixed sleep delays | Configurable per-transition, including manual pause |

---

## Sources

- `/home/matryoshka/Downloads/out_frames/iidx_tpl_manager/.planning/PROJECT.md` — requirements and scope
- `/home/matryoshka/Downloads/out_frames/obs_manager/obs_manager.py` — existing capture/recognition integration
- `/home/matryoshka/Downloads/out_frames/tpl_scene_switcher/switcher.py` — existing OBS scene switching and group visibility logic
- `/home/matryoshka/Downloads/out_frames/iidx_state_machine/state_machine.py` and `state_machine.yaml` — state tracking and transitions
- `/home/matryoshka/Downloads/out_frames/iidx_bpl_scoreboard/PROTOCOL.md` — BPL scoreboard WebSocket protocol
- `/home/matryoshka/Downloads/out_frames/iidx_knockout_scoreboard/.planning/REQUIREMENTS.md` — knockout scoreboard requirements and out-of-scope decisions

---
*Feature research for: IIDX Tournament Auto-Director*
*Researched: 2026-04-15*
