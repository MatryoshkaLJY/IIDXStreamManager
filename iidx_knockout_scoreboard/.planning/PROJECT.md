# IIDX Knockout Tournament Scoreboard

## What This Is

A WebSocket-driven browser scoreboard for 16-player knockout tournaments, designed for OBS browser sources at 1920x1080. A Python relay server broadcasts tournament commands (init, score, settle, reset) from a controller client to the display browser, where all tournament state and rendering logic lives.

## Core Value

Operators can run a complete knockout tournament via simple WebSocket commands, and viewers see a clear, real-time visual bracket with correct advancement and scoring.

## Requirements

### Validated

- ✓ WebSocket relay server runs on `localhost:8081` and broadcasts commands to all connected clients — existing
- ✓ Browser scoreboard renders a fixed 1920x1080 tournament bracket with 16 players across 3 stages — existing
- ✓ Tournament command protocol supports `init`, `score`, `settle`, `reset` — existing
- ✓ Real-time DOM updates reflect player names, scores, points, and ranks as commands arrive — existing
- ✓ Player state visualization shows `active`, `eliminated`, and `advancing` statuses with color highlighting — existing
- ✓ Groups A/B/C/D quarterfinals feed into AB/CD semifinals, then finals, with top 2 advancing — existing
- ✓ Champion determined on final settle and name displayed — existing

### Active

- [ ] Remove champion trophy code entirely from `app.js` (already removed from HTML/CSS)
- [ ] Player `score` field accumulates across rounds instead of being overwritten per round
- [ ] Rename/restructure advancement groups: AB → E, CD → F, with new player composition rules; stage order becomes A→B→C→D→E→F→Final
- [ ] Group highlighting tracks current active group: initialize highlights only Group A, auto-advance to next group after settle
- [ ] Different sorting rules per stage: Groups A-F sort by PT then accumulated score; Finals sort by PT only (scores not accumulated), ties trigger a tiebreaker round where PT is not counted and only score accumulates
- [ ] Finals visual effects: champion flashes gold; player-points field shows medal emojis (🥇🥈🥉) instead of numeric points
- [ ] Fix `init` command to preserve `.stage-indicator` and `.title-text` child elements inside `.tournament-title`

### Out of Scope

- Persistent server-side state or database — stateless relay is sufficient for local streaming use
- Authentication/authorization on WebSocket commands — single-operator local use
- Mobile/responsive layout — OBS 1920x1080 source is the only target
- Build system or package manager — keep zero-build vanilla JS
- Connection line/path animations between stages — deliberately no-op per user preference

## Context

This is a brownfield project with 4 files (`index.html`, `style.css`, `app.js`, `server.py`). The frontend is a single-class vanilla JS application (`TournamentApp`) that manages all state and DOM updates. The relay server is a minimal Python `websockets` broadcaster. The UI is styled with a cyberpunk/BPL-compatible dark theme using Google Fonts (Orbitron, Rajdhani).

Previous milestone (v1.0) established the basic working scoreboard. Current work is a refinement milestone (v1.1) focused on rule corrections, visual polish, and tournament flow improvements.

## Constraints

- **Tech stack**: Vanilla JS + Python `websockets`; no build step or frameworks
- **Runtime**: Localhost-only, optimized for OBS Browser Source
- **Resolution**: Fixed 1920x1080 layout
- **Compatibility**: Must keep existing WebSocket command protocol shape so external controllers continue to work

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Remove champion trophy entirely | User explicitly removed from HTML/CSS; JS code should match | — Pending |
| Accumulated score for A-F groups, PT-only for finals | Reflects actual tournament rules | — Pending |
| Auto-advancing group highlight | Better visual guidance during tournament flow | — Pending |