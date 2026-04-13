# Architecture

**Analysis Date:** 2026-04-13

## Pattern Overview

**Overall:** Lightweight single-page web application with a Python WebSocket relay server. The architecture follows a simple client-server broadcast pattern where a controller client sends tournament commands to a WebSocket relay, which forwards them to connected browser clients.

**Key Characteristics:**
- No persistent backend state or database
- WebSocket relay server (`server.py`) acts as a pure message broadcaster
- All tournament state and business logic live in the browser client (`app.js`)
- Static HTML/CSS define a fixed-resolution tournament bracket UI (1920x1080)
- JSON-based command protocol for real-time tournament control

## Layers

**Presentation Layer:**
- Purpose: Render the tournament bracket and reflect state changes visually
- Location: `index.html` (structure), `style.css` ( styling)
- Contains: Static HTML nodes for 16 players across 3 stages, CSS positioning and animations
- Depends on: `app.js` for dynamic DOM updates
- Used by: Browser window running as display/scoreboard

**Client Application Layer:**
- Purpose: Manage WebSocket connection, process commands, maintain tournament state, update DOM
- Location: `app.js`
- Contains: `TournamentApp` class, command handlers, state mutations, DOM helpers
- Depends on: WebSocket server at `ws://localhost:8081`
- Used by: Browser client (both display and controller)

**Relay Server Layer:**
- Purpose: Accept WebSocket connections and broadcast JSON messages to all other clients
- Location: `server.py`
- Contains: `asyncio`/`websockets` handler, in-memory client registry
- Depends on: Python 3 with `websockets` library
- Used by: Controller and browser clients

## Data Flow

**Command Flow (Controller → Browser Display):**

1. Operator/controller opens a WebSocket connection to `ws://localhost:8081` and sends a JSON command (e.g., `init`, `score`, `settle`, `reset`)
2. `server.py` receives the message, tags the sender as `controller`, and broadcasts it to every other connected client
3. Browser client (`app.js`) receives the message via `onmessage`, parses JSON, and routes to `handleCommand`
4. Corresponding command handler mutates `this.tournamentState` and updates DOM nodes directly

**State Advancement Flow (on `settle`):**

1. `handleSettle` sorts players by points descending, with total raw score as tiebreaker
2. Top 2 players are marked `advancing`, bottom 2 `eliminated`
3. Advancing players are cloned into the next stage's group (`A`/`B` -> `AB`, `C`/`D` -> `CD`, `AB`/`CD` -> `finals`)
4. DOM for the target stage is updated with the new player names and reset stats
5. Champion is determined when `final` stage is settled

**State Management:**
- Centralized in `TournamentApp.tournamentState` (`app.js`)
- Structure:
  - `tournamentName`: string
  - `groups`: {A, B, C, D, AB, CD} each with `players`, `scores`, `settled`, `advancing`
  - `finals`: {players, scores, settled, champion}
  - `currentStage`: string
- No localStorage or server persistence; `reset` restores defaults

## Key Abstractions

**TournamentApp:**
- Purpose: Encapsulates all client-side behavior for the scoreboard
- Location: `app.js`
- Pattern: Single-class monolithic frontend controller

**Command Protocol:**
- Purpose: Standardized JSON messages for tournament control
- Supported commands:
  - `init`: Initialize groups and player names
  - `score`: Record round scores and update points
  - `settle`: Finalize group, determine advancing players, promote to next stage
  - `reset`: Clear all state
- Documentation: Inline JSDoc at top of `app.js`

**Player Object:**
- Purpose: Uniform representation of a competitor at any stage
- Shape: `{ name, position, rawScores: [null, null, null, null], points, totalRawScore }`
- Used in every group and finals array

## Entry Points

**Browser Client:**
- Location: `index.html`
- Triggers: Direct browser navigation (file:// or served via static HTTP)
- Responsibilities: Load CSS/fonts, render tournament tree, execute `app.js` on `DOMContentLoaded`

**WebSocket Relay Server:**
- Location: `server.py`
- Triggers: `python server.py` (or `python3 server.py`)
- Responsibilities: Start WebSocket server on `localhost:8081`, handle connections, broadcast messages

**JavaScript Application Bootstrap:**
- Location: `app.js` (bottom of file)
- Triggers: `DOMContentLoaded` event
- Responsibilities: Instantiate `TournamentApp`, which immediately opens a WebSocket connection

## Error Handling

**Strategy:** Console logging with defensive checks and silent failures for DOM operations

**Patterns:**
- Missing DOM elements are silently skipped (`if (!node) return`)
- Malformed WebSocket messages are caught with `try/catch` and logged to console
- Invalid commands or missing fields log errors and abort handler execution early
- WebSocket disconnections trigger automatic reconnection every 3 seconds

## Cross-Cutting Concerns

**Logging:** `console.log` / `console.error` with emoji-prefixed messages inside `app.js`; `print()` in `server.py`

**Validation:** Manual field checks inside command handlers (e.g., `if (!data.groups) return`)

**Authentication:** Not implemented; any client can send control commands

---

*Architecture analysis: 2026-04-13*
