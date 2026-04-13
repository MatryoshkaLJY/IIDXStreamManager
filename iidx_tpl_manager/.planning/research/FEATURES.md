# Feature Landscape

**Domain:** Python web-based OBS tournament director for beatmania IIDX
**Researched:** 2026-04-14
**Confidence:** HIGH (derived from direct analysis of existing codebase components, protocols, and operator workflows)

---

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **OBS Scene Switching** | Core purpose of a director tool; must cut between Live, Gameplay, and Scoreboard scenes | Low | Already implemented in `switcher.py` and `obs_manager.py` |
| **Multi-Cabinet Monitoring (4x)** | Tournaments use 4 IIDX cabinets; operator must see all | Medium | `obs_manager.py` already registers machines and polls frames |
| **Game State Detection Integration** | Automatic switching depends on knowing when gameplay starts/ends | Low | TCP service on 9876 (`iidx_state_reco`) + state machine already exists |
| **Score OCR Integration** | Feeding scoreboards requires reading arcade screen digits | Low | TCP service on 9877 (`iidx_score_reco`) already exists |
| **Score Review & Correction UI** | AI misreads are common; operator must fix before broadcast | Medium | Explicit requirement in PROJECT.md |
| **Tournament Mode Selection** | Team (BPL-style) vs Individual (knockout) are the two supported formats | Low | Required by PROJECT.md |
| **JSON Config Loading** | Teams, schedules, and brackets must be loadable per event | Low | `data/teams.json`, `team_schedule.json`, `individual_schedule.json` |
| **Round Prep / Player-to-Cabinet Assignment** | Players move between cabinets each round; dynamic mapping is essential | Medium | Required by PROJECT.md |
| **Gameplay Scene Setup (SP/DP)** | OBS groups and text sources must be configured per match type | Medium | `switcher.py` already implements `set_sp_team_match` and `set_dp_team_match` |
| **Scoreboard Push Integration** | Confirmed scores must reach BPL (8080) and knockout (8081) scoreboards | Low | Protocols documented in `PROTOCOL.md` and knockout server |
| **Configurable Timing Delays** | Different tournaments/streamers want different pacing | Low | PROJECT.md requires delays configurable including `-1` for manual |

---

## Differentiators

Features that set this product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **AI-Assisted Auto-Switching** | Reduces operator cognitive load by automating scene transitions based on real-time state machine output | Medium | Unique because it ties together existing AI services (state reco + state machine) rather than just time-based or manual switching |
| **Unified Single-Web-App Control Panel** | Replaces disconnected tools (`obs_manager`, `switcher.py`, separate scoreboard servers) with one interface | Medium | PROJECT.md explicitly frames this as the primary value proposition |
| **One-Click Score Correction** | Faster than retyping; reduces on-air mistakes | Low | Can be implemented with +/- buttons or preset common errors |
| **Live State Visualization for All 4 Cabinets** | Operator sees not just video but current detected state per cabinet (IDLE, PLAY, SCORE, etc.) | Medium | Leverages `iidx_state_machine` outputs; adds situational awareness beyond raw video |
| **Delay Override on the Fly** | Operator can pause auto-advance or force immediate transition without leaving the web UI | Low | Configurable `-1` manual mode plus an explicit "Advance Now" button |
| **Round-Aware Context Preloading** | When operator loads a round, gameplay scene text/groups can be pre-configured before switching | Medium | Reduces visible setup time between rounds |

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
    → JSON Config Loading
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

**Critical path for MVP:**
1. Tournament Mode Selection + JSON Config Loading
2. Round Prep / Player-to-Cabinet Assignment
3. Multi-Cabinet Monitoring + Game State Detection
4. AI-Assisted Auto-Switching (Live ↔ Gameplay)
5. Score OCR + Review UI
6. Scoreboard Push + configurable delays

---

## MVP Recommendation

**Prioritize:**
1. **OBS Scene Switching** — foundation everything else builds on
2. **Multi-Cabinet Monitoring + State Detection** — enables automation
3. **Round Prep / Player-to-Cabinet Assignment** — required before every round
4. **Score Review & Correction UI** — operator trust depends on this
5. **Scoreboard Push Integration** — delivers end-to-end value

**Defer:**
- **Live State Visualization**: Nice to have, but operator can infer state from video
- **One-Click Score Correction**: Start with editable text fields; +/- shortcuts can be added later
- **Round-Aware Context Preloading**: Can be done manually in early versions

---

## Sources

- `/home/matryoshka/Downloads/out_frames/iidx_tpl_manager/.planning/PROJECT.md` — requirements and scope
- `/home/matryoshka/Downloads/out_frames/obs_manager/obs_manager.py` — existing capture/recognition integration
- `/home/matryoshka/Downloads/out_frames/tpl_scene_switcher/switcher.py` — existing OBS scene switching and group visibility logic
- `/home/matryoshka/Downloads/out_frames/iidx_state_machine/state_machine.py` and `state_machine.yaml` — state tracking and transitions
- `/home/matryoshka/Downloads/out_frames/iidx_bpl_scoreboard/PROTOCOL.md` — BPL scoreboard WebSocket protocol
- `/home/matryoshka/Downloads/out_frames/iidx_knockout_scoreboard/.planning/REQUIREMENTS.md` — knockout scoreboard requirements and out-of-scope decisions
