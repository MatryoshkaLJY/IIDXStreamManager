# Coding Conventions

**Analysis Date:** 2026-04-13

## Naming Patterns

### JavaScript (`app.js`)

- **Classes**: PascalCase, e.g. `TournamentApp`
- **Methods**: camelCase, e.g. `connectWebSocket`, `updatePlayerNode`, `calculatePoints`
- **Properties/Variables**: camelCase, e.g. `reconnectInterval`, `tournamentState`, `quarterfinalGroups`
- **DOM cache object**: Single-letter abbreviation `els` (elements), e.g. `this.els.statusDot`
- **Private-ish helpers**: No underscore prefix is used; all methods are public on the class

### Python (`server.py`)

- **Functions**: snake_case, e.g. `handler`, `main`
- **Variables**: snake_case, e.g. `client_id`, `broadcast_count`
- **Global mutable state**: Module-level dict `clients` acts as a connection registry

### CSS (`style.css`)

- **CSS Custom Properties (variables)**: kebab-case with `--` prefix, e.g. `--bg-dark`, `--theme-cyan`
- **Class names**: kebab-case, semantic and stateful, e.g. `.player-node`, `.connection-status`, `.status-dot.connected`
- **ID selectors**: Used for absolute positioning hooks, e.g. `#A1`, `#AB2`, `#F3`

### HTML (`index.html`)

- **`data-*` attributes**: Lowercase, hyphenated where needed, e.g. `data-group="A"`, `data-position="0"`

## Code Style

### Formatting

- **No automated linter or formatter detected** (`eslint`, `prettier`, `ruff`, `black`, etc. are not configured)
- Indentation: 4 spaces across all files (JavaScript, Python, CSS, HTML)
- Brace style: K&R / Egyptian brackets for JavaScript
- Line endings: LF assumed

### JavaScript Style Patterns

- ES6 class syntax with explicit `constructor()`
- Template literals for logging: `` `📨 Received command: ${message.cmd}` ``
- Destructuring in method parameters: `const { stage, group, round, scores } = data;`
- Spread operator for array copies: `[...scores].sort(...)` and `[...groupState.players].sort(...)`
- Emoji prefixes used in `console.log`/`console.error` for visual scannability: `🏆`, `📝`, `🏁`, `🔄`
- JSDoc comments on DOM helper methods with `@param` and `@returns`

### Python Style Patterns

- No type hints used
- f-strings for all formatted output
- Emoji prefixes in print statements mirroring the frontend style
- `try/except` blocks wrap JSON parsing and WebSocket send operations
- `asyncio.run(main())` entrypoint pattern

## Commenting & Documentation

- **File header protocol doc**: `app.js` opens with a 49-line block comment documenting the WebSocket command protocol (`INIT`, `SCORE`, `SETTLE`, `RESET`) including example JSON payloads
- **Section separators**: `// ==========================================` headers denote logical sections (WebSocket, Command Handlers, DOM Helpers, Tournament Helpers)
- **JSDoc**: Present on DOM accessor methods (`getPlayerNode`, `getPath`, `updatePlayerNode`, `setPlayerState`, `lightPath`, `calculatePoints`, `clearAllPaths`, `clearChampionDisplay`, `lightChampionPath`)
- **Inline comments**: Sparse but sufficient; explain *why* for business logic (e.g. tiebreaker rules, round indexing)
- **Python docstring**: Single-line docstring on `handler()`; module-level docstring describes purpose and port

## Error Handling

### JavaScript

- **Defensive DOM access**: All DOM element lookups are guarded with `if (el)` before mutation, e.g.:
  ```javascript
  if (titleEl) titleEl.textContent = data.tournamentName;
  ```
- **Input validation at command boundaries**: `handleInit`, `handleScore`, `handleSettle` all validate presence of `data` and required fields before processing
- **Range validation**: `handleScore` validates `round` must be 1-4
- **Graceful degradation**: Unknown commands log a warning and are ignored
- **WebSocket reconnection**: Automatic reconnect with 3000 ms interval both on `onclose` and `onerror`
- **JSON parse safety**: `try/catch` around `JSON.parse(event.data)` in `onmessage`

### Python

- **JSON decode safety**: `json.JSONDecodeError` caught and falls back to raw message print
- **Connection cleanup**: `websockets.exceptions.ConnectionClosed` caught during broadcast; stale clients are removed from `clients` dict
- **No global exception handler**: Unhandled exceptions in `handler` will crash the server task for that connection

## Import Organization

### Python (`server.py`)

1. Standard library: `asyncio`, `json`
2. Third-party: `websockets`

### JavaScript (`app.js`)

- No imports; relies entirely on browser globals (`WebSocket`, `document`, `console`, `setTimeout`)
- Font loaded via `<link>` in `index.html`

## Function Design

### JavaScript

- **Method size**: Generally under 40 lines; larger logic broken into helpers (`handleSettle` is ~170 lines and is the longest method)
- **Early returns** used extensively for guard clauses
- **No arrow functions for class methods**; all methods are standard class member functions

### Python

- **Function size**: Small (`handler` ~45 lines, `main` ~10 lines)
- **Mutable global state**: `clients` dict is mutated across coroutine invocations

## Prohibited / Notable Absences

- No linting config: `.eslintrc*`, `.prettierrc*`, `pyproject.toml`, `setup.cfg`, `tox.ini` absent
- No CI/CD configuration detected (no `.github/workflows/`, no `.gitlab-ci.yml`)
- No tests directory or test config
- No `package.json`, `requirements.txt`, or dependency lockfile
- No bundler or transpiler config

## Recommended Conventions for New Code

- Keep 4-space indentation
- Continue using camelCase for JS and snake_case for Python
- Maintain emoji-prefixed logging for consistency with existing style
- Add JSDoc comments on any new public methods
- Validate incoming message `data` at the top of every new command handler
- Guard all DOM mutations with null checks before element access
- Keep `app.js` methods below ~60 lines; extract DOM or calculation logic into dedicated helpers if growing larger

---

*Convention analysis: 2026-04-13*
