# Technology Stack

**Project:** IIDX Tournament Auto-Director
**Researched:** 2026-04-14

## Recommended Stack

### Core Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.13+ | Runtime | Project requires modern async support; Python 3.13 is current stable and supported by all target libraries. |
| Flask | 3.1.3 | Web framework | Operator prefers ease of development; existing stack is Flask-based. Flask 3.1.x is actively maintained (latest Feb 2026), has excellent Jinja2 templating for operator UIs, and integrates cleanly with synchronous OBS/scoreboard code. |
| Flask-SocketIO | 5.6.1 | WebSocket server for UI push | Enables real-time UI updates (cabinet states, scores, scene transitions) without polling. Mature, well-documented, and integrates directly with Flask's request context. |
| python-socketio | 5.16.1 | Socket.IO engine (dependency) | Required by Flask-SocketIO; latest version ensures compatibility with modern JS clients. |

### OBS & External Integrations
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| obsws-python | 1.8.0 | OBS WebSocket v5 client | Actively maintained (latest Jul 2025), purpose-built for OBS WebSocket v5, provides clean sync/async APIs with snake_cased methods. Preferred over `obs-websocket-py` which is unmaintained (last release Feb 2023). |
| simpleobsws | 1.4.3 | Alternative OBS WebSocket v5 client | Actively maintained (latest Jun 2025), async-native, and returns raw JSON. Use this if the project needs lower-level event handling that `obsws-python` does not expose cleanly. |
| websockets | 16.0 | Native WebSocket client for scoreboards | Modern, asyncio-first library with excellent reliability. Use to connect to existing BPL (port 8080) and knockout (port 8081) scoreboard servers. |
| aiohttp | 3.13.5 | Async HTTP client for TCP inference bridges | If `obs_manager.py` needs async HTTP wrappers around the TCP inference services, aiohttp is the standard async choice. |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Jinja2 | 3.1.6 | Server-side HTML templating | Always — Flask's default templating engine for operator UI pages. |
| Werkzeug | 3.1.8 | WSGI utilities | Always — Flask dependency, provides dev server and request/response handling. |
| Pydantic | 2.13.0 | Config validation | Validate `teams.json`, `team_schedule.json`, and `individual_schedule.json` schemas on load. |
| httpx | 0.28.1 | Modern HTTP client | For any outbound HTTP calls (e.g., health checks, future REST bridges). |

### Infrastructure / Dev Tools
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| uvicorn | 0.44.0 | ASGI server | If the project later adds FastAPI endpoints or uses an ASGI-backed Socket.IO server, uvicorn is the standard high-performance choice. |
| gunicorn | 25.3.0 | WSGI production server | For production deployment of the Flask app with multiple workers. Pair with `gunicorn -k eventlet` or `gevent` when using Flask-SocketIO. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Web framework | Flask | FastAPI 0.135.3 | FastAPI is excellent for API-first async apps, but the operator explicitly prefers ease of development and the existing stack is Flask-based. The UI is server-rendered HTML, not a SPA consuming JSON APIs, so FastAPI's auto-docs and Pydantic-native APIs provide less value here. |
| OBS client | obsws-python | obs-websocket-py 1.0 | `obs-websocket-py` is unmaintained (last release Feb 2023, beta status). It does not reliably support OBS WebSocket v5 features and lacks recent bug fixes. |
| OBS client | obsws-python | simpleobsws 1.4.3 | `simpleobsws` is a valid alternative and is async-native. Choose `obsws-python` for synchronous-style code that matches Flask's threading model; choose `simpleobsws` if the project moves to an async architecture. |
| Real-time UI | Flask-SocketIO | HTMX + server-sent events | HTMX with SSE is simpler but less robust for bidirectional real-time control (e.g., operator clicks "confirm score" and the server must immediately trigger OBS/scoreboard actions). Socket.IO handles this more cleanly. |

## Installation

```bash
# Core web framework and real-time UI
pip install Flask==3.1.3 Flask-SocketIO==5.6.1 python-socketio==5.16.1

# OBS WebSocket (choose primary; install both if evaluating)
pip install obsws-python==1.8.0
pip install simpleobsws==1.4.3

# WebSocket client for scoreboards and general networking
pip install websockets==16.0 aiohttp==3.13.5

# Supporting libraries
pip install Jinja2==3.1.6 Werkzeug==3.1.8 Pydantic==2.13.0 httpx==0.28.1

# Dev / production servers
pip install uvicorn==0.44.0 gunicorn==25.3.0
```

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `obs-websocket-py` | Unmaintained since Feb 2023; beta status; no reliable OBS WebSocket v5 support. | `obsws-python` or `simpleobsws` |
| Django | Massive overkill for a single-operator local web app with no ORM needs. Adds unnecessary complexity and boilerplate. | Flask |
| Tornado | Largely superseded by FastAPI/Starlette and asyncio ecosystems; smaller community in 2025. | Flask + Flask-SocketIO or FastAPI |
| Raw `websocket-client` library | Synchronous and blocking; poorly suited for handling multiple concurrent WebSocket connections (OBS + 2 scoreboards). | `websockets` (async) or `obsws-python` (managed) |

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Flask 3.1.3 | Werkzeug 3.1.x, Jinja2 3.1.x | Flask 3.x requires Werkzeug >=3.0. |
| Flask-SocketIO 5.6.1 | python-socketio 5.16.x | Always keep these in sync to avoid protocol mismatches. |
| obsws-python 1.8.0 | OBS WebSocket v5.x | Targets OBS Studio 28+ with built-in WebSocket v5. |
| simpleobsws 1.4.3 | OBS WebSocket >=5.0.0 | Does not support legacy v4 protocol. |
| websockets 16.0 | Python 3.10–3.14 | Requires Python >=3.10. |

## Confidence Assessment

| Recommendation | Confidence | Rationale |
|----------------|------------|-----------|
| Flask 3.1.3 as web framework | HIGH | Verified latest on PyPI; aligns with operator preference and existing stack. |
| obsws-python 1.8.0 for OBS | HIGH | Verified latest on PyPI (Jul 2025); actively maintained; purpose-built for v5. |
| simpleobsws 1.4.3 as OBS alternative | HIGH | Verified latest on PyPI (Jun 2025); actively maintained. |
| websockets 16.0 for scoreboards | HIGH | Verified latest on PyPI (Jan 2026); standard async WebSocket library. |
| Flask-SocketIO 5.6.1 for real-time UI | HIGH | Verified latest on PyPI (Feb 2026); mature integration with Flask. |

## Sources

- [PyPI — Flask 3.1.3](https://pypi.org/project/Flask/) — version and release date verified via `pip index versions`
- [PyPI — FastAPI 0.135.3](https://pypi.org/project/fastapi/) — version verified via `pip index versions`
- [PyPI — obsws-python 1.8.0](https://pypi.org/project/obsws-python/) — version verified via `pip index versions`
- [PyPI — simpleobsws 1.4.3](https://pypi.org/project/simpleobsws/) — version verified via `pip index versions`
- [PyPI — websockets 16.0](https://pypi.org/project/websockets/) — version verified via `pip index versions`
- [PyPI — Flask-SocketIO 5.6.1](https://pypi.org/project/Flask-SocketIO/) — version verified via `pip index versions`
- [GitHub — aatikturk/obsws-python](https://github.com/aatikturk/obsws-python) — API patterns and maintenance status
- [GitHub — IRLToolkit/simpleobsws](https://github.com/IRLToolkit/simpleobsws) — API patterns and usage docs
- [GitHub — pallets/flask](https://github.com/pallets/flask) — release history and changelog
- [FastAPI release notes](https://fastapi.tiangolo.com/release-notes/) — latest version confirmation
