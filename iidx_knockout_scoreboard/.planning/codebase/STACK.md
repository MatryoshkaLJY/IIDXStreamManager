# Technology Stack

**Analysis Date:** 2026-04-13

## Languages

**Primary:**
- JavaScript (ES6+) - Client-side tournament logic and WebSocket communication (`app.js`)
- Python 3 - WebSocket relay server (`server.py`)
- CSS3 - Styling and visual effects (`style.css`)
- HTML5 - Markup structure (`index.html`)

## Runtime

**Frontend:**
- Runs in standard web browsers (no build step)
- Target viewport: 1920x1080 (designed for OBS browser sources)

**Backend:**
- Python 3 asyncio event loop
- Execution: `python server.py` or `./server.py` (shebang present)

## Frameworks & Libraries

**Backend:**
- `websockets` - Async WebSocket server library for Python
- `asyncio` - Python standard library for async I/O
- `json` - Python standard library for message serialization

**Frontend:**
- Vanilla JavaScript (no frameworks)
- Native WebSocket API (`new WebSocket()`)
- Native DOM APIs (`document.querySelector`, `addEventListener`)

**External Assets:**
- Google Fonts - Orbitron and Rajdhani font families loaded from `https://fonts.googleapis.com`

## Key Dependencies

**Python (no requirements.txt detected; manually installed):**
- `websockets` - Required to run `server.py`

**Browser:**
- Modern browser with WebSocket and CSS custom properties (variables) support

## Build / Package Management

- None detected
- No `package.json`, `requirements.txt`, `pyproject.toml`, `Pipfile`, or equivalent manifests present
- Project is intended to run directly without a build step

## Configuration

**Hardcoded values:**
- WebSocket URL: `ws://localhost:8081` in `app.js` line 55
- Server bind address: `localhost:8081` in `server.py` line 76
- Port chosen to avoid conflict with BPL scoreboard on port 8080 (noted in `server.py` docstring)

**No environment configuration system detected.**

## Platform Requirements

**Development:**
- Python 3.x with `websockets` installed (`pip install websockets`)
- Any modern web browser

**Production / Streaming:**
- Localhost runtime (server and browser on same machine)
- Optimized for OBS Studio Browser Source at 1920x1080 resolution

---

*Stack analysis: 2026-04-13*
