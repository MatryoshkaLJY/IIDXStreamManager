# Codebase Concerns

**Analysis Date:** 2026-04-13

## Tech Debt

### Hardcoded WebSocket URL
- **Issue:** The WebSocket URL `ws://localhost:8081` is hardcoded in `app.js` (line 55), making deployment to non-localhost environments impossible without editing source code.
- **Files:** `app.js`
- **Impact:** Blocks remote hosting, Docker usage, and any production deployment.
- **Fix approach:** Read the WebSocket URL from `window.location` or an environment/config variable at build time.

### Dead / Stubbed Code
- **Issue:** `lightPath()` and `clearAllPaths()` are no-ops (lines 636--639 and 662--666) with a comment saying "user doesn't want connection lines." Unused SVG connection path styles and HTML champion trophy markup are commented out.
- **Files:** `app.js`, `style.css`, `index.html`
- **Impact:** Increases maintenance burden and indicates incomplete requirements.
- **Fix approach:** Decide whether connection lines and champion trophy are needed. Either implement them fully or remove dead markup, CSS, and JavaScript.

### Magic Numbers & Strings Everywhere
- **Issue:** Tournament structure values (4 players per group, top 2 advance, rounds 1--4, point values) are scattered as literals throughout `app.js`.
- **Files:** `app.js`
- **Impact:** Makes rule changes (e.g., 8 players per group, different point system) error-prone and tedious.
- **Fix approach:** Extract tournament rules into a single configuration object (e.g., `const TOURNAMENT_CONFIG = { playersPerGroup: 4, advancingCount: 2, maxRounds: 4, pointsByRank: [null, 2, 1, 0, 0] }`).

### No Input Validation on Server
- **Issue:** `server.py` blindly forwards any JSON message to all connected clients without validating schema, command types, or rate limits.
- **Files:** `server.py`
- **Impact:** Malformed or malicious messages can crash the browser client or desync the tournament state.
- **Fix approach:** Add a lightweight JSON-schema validation step before broadcasting.

### Global State on Server
- **Issue:** The `clients` dictionary is a module-level mutable global with no synchronization primitives.
- **Files:** `server.py`
- **Impact:** In the current asyncio context it is mostly safe, but it tightly couples connection handling to global state and complicates future testing.
- **Fix approach:** Encapsulate client management in a class.

## Security Concerns

### No Origin Validation
- **Issue:** `websockets.serve` does not restrict origins; any website can open a WebSocket to `ws://localhost:8081`.
- **Files:** `server.py`
- **Impact:** Cross-site WebSocket hijacking (CSWSH) could allow unauthorized clients to inject tournament commands.
- **Current mitigation:** None.
- **Recommendations:** Add an `origin` check or require an authentication token in the first handshake message.

### No Rate Limiting
- **Issue:** A single client can flood the server with messages, and the server will broadcast all of them.
- **Files:** `server.py`
- **Impact:** Denial-of-service to other browsers and potential state corruption.
- **Recommendations:** Add per-client rate limiting (e.g., a token bucket) and maximum payload size enforcement.

### HTML Injection Through Player Names
- **Issue:** Player names received via WebSocket are inserted into the DOM with `textContent` (which is safe), but title updates use `innerHTML` implicitly via template strings? Actually `textContent` is used. However, the score values are rendered via `toLocaleString()` directly. Still, there is no sanitization of custom fields.
- **Files:** `app.js`
- **Impact:** Low under current usage, but any switch to `innerHTML` in the future will open XSS.
- **Recommendations:** Keep using `textContent` or `textContent` equivalents; avoid `innerHTML` for dynamic data.

## Scalability Limitations

### Single-Process Relay
- **Issue:** `server.py` is a single-threaded asyncio process with no load-balancing or horizontal scaling support.
- **Files:** `server.py`
- **Current capacity:** Supports a handful of browser/controller clients.
- **Limit:** CPU-bound JSON parsing and message broadcasting will bottleneck around a few hundred messages per second.
- **Scaling path:** For now acceptable for local tournament use; if scaling is needed, migrate to a Redis-backed pub/sub relay (e.g., `fastapi` + `redis-py`) or a managed WebSocket service.

### Fixed 1920x1080 Viewport
- **Issue:** `style.css` hardcodes a 1920x1080 canvas. On smaller or larger screens the UI will clip or require manual zooming.
- **Files:** `style.css`
- **Impact:** Limits use on laptops, tablets, or alternative display setups.
- **Recommendations:** Use responsive CSS with relative units and CSS Grid/Flexbox instead of absolute pixel positioning.

## Maintainability Issues

### No Separation of Concerns
- **Issue:** `app.js` mixes WebSocket networking, tournament business logic, and DOM manipulation in a single 750-line class.
- **Files:** `app.js`
- **Impact:** Difficult to unit test; any UI change risks breaking state logic.
- **Fix approach:** Split into three modules: `websocket-client.js`, `tournament-logic.js`, and `ui-renderer.js`.

### Inline DOM Queries
- **Issue:** Methods such as `handleInit()`, `handleSettle()`, and `handleReset()` repeatedly call `document.querySelector()` for the same static elements.
- **Files:** `app.js`
- **Impact:** Unnecessary DOM traversal and brittle coupling to HTML structure.
- **Fix approach:** Cache static DOM references in the constructor (already partially done via `this.els`, but not consistently used).

### No Tests
- **Issue:** Zero unit tests, integration tests, or end-to-end tests exist.
- **Files:** Entire repository.
- **Impact:** Regressions are only caught during manual runs.
- **Fix approach:** Add a lightweight test runner (e.g., `vitest` or `jest` for JS; `pytest` with `pytest-asyncio` for Python). At minimum, test `calculatePoints()`, sorting logic, and server broadcast behavior.

### No Dependency Management
- **Issue:** There is no `package.json`, `requirements.txt`, `pyproject.toml`, or lockfile.
- **Files:** Repository root.
- **Impact:** Reproducibility is fragile; a future `pip install websockets` may pull a breaking version.
- **Fix approach:** Add `requirements.txt` (pinning `websockets>=14.0,<15`) and optionally a `package.json` if JS tooling is introduced.

## Missing Critical Features

### No Persistence
- **Problem:** Tournament state exists only in browser memory. Refreshing the page resets the scoreboard to default values.
- **Blocks:** Recovery from crashes, page reloads, or OBS source refreshes.
- **Fix approach:** Have the server maintain authoritative state and re-broadcast it on new client connections, or persist state to a local JSON file.

### No Undo / Replay of Commands
- **Problem:** A mistaken `score` or `settle` command cannot be corrected without sending a full `reset` and `init` sequence.
- **Blocks:** Smooth tournament operation when human error occurs.
- **Fix approach:** Implement a command history on the server and support an `undo` command.

### No Configurable Tournament Size
- **Problem:** The bracket is strictly 16 players, 4 groups, top-2-advance. Supporting 8 players or 32 players would require rewriting large sections of `app.js` and `index.html`.
- **Fix approach:** Refactor the rendering engine to be data-driven: generate DOM nodes from a round/group configuration object rather than hardcoding them in HTML.

### No README or Usage Documentation
- **Problem:** There is no `README.md` explaining how to start the server, open the scoreboard, or send WebSocket commands.
- **Blocks:** Onboarding new tournament operators.
- **Fix approach:** Add a concise `README.md` with quick-start steps and example controller payloads.

## Test Coverage Gaps

### Untested Tournament Logic
- **What is not tested:** Point calculation, tie-breaker sorting, group advancement mapping, championship path tracing.
- **Files:** `app.js`
- **Risk:** Rule misunderstandings or off-by-one errors in round indexing could go unnoticed until a live tournament.
- **Priority:** High.

### Untested Server Relay
- **What is not tested:** Message broadcast loop, client disconnection cleanup, JSON decode failure handling.
- **Files:** `server.py`
- **Risk:** Memory leaks (e.g., stale websocket entries) or silent broadcast failures.
- **Priority:** Medium.

## Suggested Improvement Priorities

1. **High:** Add `requirements.txt` and harden `server.py` with input validation, rate limiting, and origin checks.
2. **High:** Implement server-side state persistence and re-sync on client reconnect.
3. **High:** Write unit tests for `calculatePoints()` and sorting/advancement logic.
4. **Medium:** Remove or fully implement dead connection-line and champion-trophy code.
5. **Medium:** Extract tournament configuration from magic literals into a single config object.
6. **Low:** Replace absolute pixel CSS with responsive layout.
7. **Low:** Add a `README.md`.

---

*Concerns audit: 2026-04-13*
