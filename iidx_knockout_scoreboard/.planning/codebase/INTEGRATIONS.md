# External Integrations

**Analysis Date:** 2026-04-13

## APIs & External Services

**Google Fonts:**
- Purpose: Loads Orbitron and Rajdhani fonts for cyberpunk/scoreboard aesthetic
- URL: `https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@400;600;700&display=swap`
- File: `index.html` (lines 8-10)

No other third-party APIs, analytics, or telemetry services detected.

## Network Protocols

**WebSocket:**
- Protocol: WebSocket over TCP (`ws://`)
- Client endpoint: `ws://localhost:8081` (`app.js` line 55)
- Server bind: `localhost:8081` (`server.py` line 76)
- Behavior: Simple broadcast relay; every message from one client is forwarded to all other connected clients
- Message format: JSON with `cmd` and `data` fields

**Supported commands:**
- `init` - Initialize tournament with player groups
- `score` - Record round scores
- `settle` - Finalize a group and determine advancing players
- `reset` - Clear tournament state

## Data Storage

**Databases:** Not applicable - all state is held in memory on both client and server.

**Persistence:** None detected. Server state (`clients` dict) and tournament state are ephemeral.

## Authentication & Identity

- Not implemented
- No auth tokens, sessions, or identity providers
- Any client connecting to `ws://localhost:8081` can send or receive commands

## Monitoring & Observability

- Server logs events to stdout (connections, disconnections, commands received, broadcast counts)
- Client logs to browser console via `console.log` / `console.error`
- No external error tracking, metrics, or logging services

## CI/CD & Deployment

- No CI/CD configuration detected
- No Dockerfile, GitHub Actions, or deployment scripts
- Deployment target: local machine (intended for streaming setups)

## Webhooks & Callbacks

- None

## Data Sources

- Player names and scores injected in real time via WebSocket from an external controller client
- No static data files, JSON fixtures, or external databases

## Environment Configuration

**Required environment:** None (no `.env` file detected)

**Required manual setup:**
- Install Python dependency: `websockets`
- Start server: `python server.py`
- Open `index.html` in browser or OBS Browser Source

---

*Integration audit: 2026-04-13*
