# Codebase Structure

**Analysis Date:** 2026-04-13

## Directory Layout

```
iidx_knockout_scoreboard/
├── app.js         # Client application: TournamentApp class, WS client, state + DOM logic
├── index.html     # Single-page tournament bracket UI (28 player nodes + header)
├── style.css      # Fixed 1920x1080 styling, animations, player states, grid layout
└── server.py      # Python WebSocket relay: broadcasts JSON commands to all clients
```

## Directory Purposes

**Root directory (`iidx_knockout_scoreboard/`):**
- Purpose: Contains the entire application; no subdirectories
- Contains: Static frontend assets and a minimal Python relay server
- Key files: `app.js`, `index.html`, `style.css`, `server.py`

## Key File Locations

**Entry Points:**
- `index.html`: Browser entry point; loads `style.css` and `app.js`
- `server.py`: Server entry point; starts WebSocket relay on `localhost:8081`

**Configuration:**
- Not detected; no config files exist
- Hardcoded values:
  - WebSocket URL: `ws://localhost:8081` in `app.js` line 55
  - Resolution: `1920px x 1080px` in `style.css` lines 41-42
  - Reconnect interval: `3000ms` in `app.js` line 54

**Core Logic:**
- `app.js` lines 51-750: `TournamentApp` class with state management, command handlers, and DOM manipulation
- `server.py` lines 17-64: `handler` coroutine that forwards messages between clients

**Testing:**
- Not detected

## Naming Conventions

**Files:**
- Lowercase with descriptive suffixes: `index.html`, `style.css`, `app.js`, `server.py`

**CSS Classes:**
- kebab-case: `.player-node`, `.quarterfinal`, `.group-a-label`, `.connection-status`

**JavaScript:**
- Class: `PascalCase` (`TournamentApp`)
- Methods/variables: `camelCase` (`handleScore`, `tournamentState`, `reconnectInterval`)
- Group identifiers: uppercase single/double letters (`A`, `B`, `AB`, `CD`)

**Python:**
- Functions/variables: `snake_case` (`client_id`, `broadcast_count`)

## Where to Add New Code

**New UI Components (e.g., new bracket nodes, overlays, timers):**
- HTML markup: add nodes inside `<main class="tournament-tree">` in `index.html`
- Styling: add rules in `style.css` after the Finals positioning section (around line 388)
- Behavior: add helper methods to `TournamentApp` in `app.js` after the existing DOM helper block

**New WebSocket Commands:**
- Protocol docs: update header comment block in `app.js` (lines 1-49)
- Routing: add a `case` in `handleCommand` (`app.js` lines 147-171)
- Handler: implement a new `handleXxx(data)` method in `app.js` after `handleReset`

**Server-side Enhancements (e.g., state persistence, auth, logging):**
- Implementation: extend `server.py` inside `handler` or add utility functions
- Current server is a thin relay; most logic intentionally lives in the browser

## Special Directories

- Not applicable; the project is flat with no special/generated directories

---

*Structure analysis: 2026-04-13*
