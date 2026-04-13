# Testing Patterns

**Analysis Date:** 2026-04-13

## Test Framework

**Runner:** Not detected

- No `jest.config.*`, `vitest.config.*`, `pytest.ini`, `pyproject.toml`, or `tox.ini` present
- No `package.json` scripts or `requirements.txt` test dependencies

**Assertion Library:** Not detected

**Run Commands:** Not applicable (no test suite exists)

## Test File Organization

**Location:** None

**Naming:** Not applicable

## Test Structure

No automated tests exist in the repository. The following patterns are therefore inferred as *manual testing practices* observed from the codebase.

## Manual Testing Practices

### Protocol Documentation as Test Contract

`app.js` begins with a 49-line header comment that documents the WebSocket command protocol with full JSON examples:

- `INIT` — initialize tournament
- `SCORE` — record song scores
- `SETTLE` — finalize round
- `RESET` — clear tournament

This comment block acts as the authoritative contract for manual integration testing between the controller and the browser.

### Runtime Logging for Live Verification

Both `app.js` and `server.py` use extensive emoji-prefixed console/stdout logging to verify behavior during manual tests:

- `app.js`: `console.log('🏆 Initializing tournament:', data.tournamentName)`
- `server.py`: `print(f"\n📨 [{client_id}/{client_type}] Received: {cmd}")`

These logs allow an operator to trace a command from controller → server → browser in real time.

### Defensive Validation as Implicit Smoke Tests

The code contains input-validation guard clauses at every command boundary that would fail loudly during manual testing if malformed data were sent:

- `app.js` `handleScore`: validates `round` is 1-4
- `app.js` `handleInit`: asserts `data.groups` exists and each group is an array of length 4
- `app.js` `handleSettle`: asserts `stage` and `group` fields are present
- `server.py`: wraps `json.loads()` in `try/except JSONDecodeError`

### Reconnection Behavior

`app.js` manually tests/reproduces reconnection by:

1. Closing the WebSocket server
2. Observing `🔴 WebSocket disconnected` in the browser console
3. Waiting for the 3000 ms reconnect interval
4. Restarting the server and confirming `🟢 WebSocket connected`

## CI/CD Pipeline

**Status:** Not configured

- No `.github/workflows/`
- No `.gitlab-ci.yml`
- No pre-commit hooks or automated quality gates

## Coverage

**Requirements:** None enforced

**Current estimated coverage:** 0% (no automated test suite)

## Quality Gaps

### No Automated Tests

- **JavaScript frontend (`app.js`):** No unit tests for `TournamentApp` methods (`calculatePoints`, sorting logic, DOM updates, state transitions)
- **Python backend (`server.py`):** No unit or integration tests for the WebSocket relay, broadcast logic, or client lifecycle
- **CSS (`style.css`):** No visual regression or snapshot tests
- **HTML (`index.html`):** No accessibility or structural tests

### Specific Untested Scenarios

| Scenario | Risk | Files |
|----------|------|-------|
| Tiebreaker logic (sort by points descending, then total raw score descending) | Incorrect advancement on exact ties | `app.js` (`handleSettle`) |
| Quarterfinal → Semifinal → Final player advancement chain | Champion path or DOM state becomes inconsistent | `app.js` (`handleSettle`) |
| WebSocket reconnect with pending server downtime | Memory leaks or duplicate connections | `app.js` (`connectWebSocket`) |
| Broadcasting to multiple simultaneous clients | Message may not reach all browsers | `server.py` (`handler`) |
| JSON parse of malformed/malicious message | Server logs raw message but does not reject sender | `server.py` (`handler`) |
| Player name collision (same name across groups) | `lightChampionPath` uses name equality (`===`) which could match the wrong player | `app.js` (`lightChampionPath`) |

## Recommendations for Adding Tests

### Frontend (Minimal)

- Use a browser-based runner such as **Vitest** or **Jest** with `jsdom` to test `TournamentApp` in isolation
- Mock `WebSocket` global and `document.querySelector` to test command handlers without a real browser
- Priority tests:
  1. `calculatePoints` rank-to-points mapping
  2. `handleScore` updates player state and DOM correctly
  3. `handleSettle` advances exactly top 2 players and resets next-stage scores

### Backend (Minimal)

- Use **`pytest-asyncio`** to test `server.py` handlers
- Use `websockets` test client or mock `websocket` object to verify:
  1. A message from a controller is broadcast to all other connected clients
  2. A `JSONDecodeError` does not crash the connection
  3. Disconnected clients are removed from `clients` dict

### Manual Test Checklist (Immediate)

When modifying any command handler, verify at minimum:

1. Send `init` with 4 groups of 4 players → all nodes populate
2. Send `score` for rounds 1-4 for one group → points and ranks update
3. Send `settle` for that group → top 2 advance, bottom 2 are marked eliminated
4. Repeat for semifinal and final groups
5. Send `reset` → entire board returns to `TBD` / `0` / `-`
6. Close and reopen `server.py` while browser is open → reconnects automatically

---

*Testing analysis: 2026-04-13*
