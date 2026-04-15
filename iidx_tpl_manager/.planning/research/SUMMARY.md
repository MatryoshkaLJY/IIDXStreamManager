# Research Summary

**Project:** IIDX Tournament Auto-Director  
**Milestone:** v1.2 Auto-Director Core  
**Date:** 2026-04-15

---

## Stack

- **Flask 3.1.3** — Web framework (operator prefers ease of development; existing stack is Flask)
- **Flask-SocketIO 5.6.1** — Real-time UI push updates
- **obsws-python 1.8.0** — OBS WebSocket v5 client (actively maintained, sync/async support)
- **websockets 16.0** — Async WebSocket client for scoreboard servers (8080 / 8081)
- **Pydantic 2.13.0** — JSON config validation

## Table Stakes

- OBS scene switching (Live ↔ Gameplay ↔ Scoreboard)
- 4-cabinet monitoring via existing `obs_manager.py`
- Integration with `iidx_state_reco` (9876), `iidx_score_reco` (9877), and `iidx_state_machine`
- Score review & correction UI (AI OCR is imperfect)
- Tournament mode selection (team vs individual)
- JSON config loading (`teams.json`, `team_schedule.json`, `individual_schedule.json`)
- Round prep / player-to-cabinet assignment
- Gameplay scene setup for SP/DP team matches
- Scoreboard push integration (BPL 8080, knockout 8081)
- Configurable timing delays (including `-1` for manual)

## Differentiators

- AI-assisted auto-switching unified in a single control panel
- Human-in-the-loop score confirmation before broadcast
- Live state visualization for all 4 cabinets
- One-click delay override and emergency live button

## Watch Out For

1. **OBS WebSocket blocking** — Wrap calls in timeouts; never block the frame loop.
2. **Sequential inference bottleneck** — Use per-cabinet threads or a thread pool for 4x capture.
3. **Over-automation** — Provide pending transitions, emergency live button, and revert actions.
4. **State loss on refresh/restart** — Persist runtime state (round assignments, scores, delays) to disk.
5. **Hard-coded scene names** — Externalize scene mappings in config and validate against OBS on startup.
6. **Sleep-based delays** — Use a scheduler with absolute timestamps, not blocking sleeps.
7. **AI score validation edge cases** — Visually flag invalid scores and only auto-fill validated ones.

## Architecture Takeaway

Build a monolithic Flask app with a central `TournamentDirector` controller, background polling thread for 4-cabinet recognition, and SocketIO for real-time UI updates. Keep all scene-switching decisions server-side.

## Suggested Build Order

1. OBS Client + Scene Controller — validates OBS WebSocket connectivity
2. Round Prep UI + Runtime State Extension — enables operator match setup
3. Cabinet Worker + Live Monitor UI — brings real-time cabinet state to browser
4. Scoreboard Client + Score Review UI — closes human-in-the-loop confirmation flow
5. Auto-Transition Rules + Configurable Delays — cross-cutting polish; lowest dependency risk
