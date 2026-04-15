# Phase 5: Cabinet Monitoring & Live Monitor UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-15
**Phase:** 05-cabinet-monitoring-live-monitor-ui
**Areas discussed:** OBS source naming, Frame delivery, Monitor page placement, Polling interval, Auto-start, Configuration surface

---

## OBS source naming

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed names | IIDX#1 ~ IIDX#4 | ✓ |
| Configurable mapping | Store per-cabinet source name in runtime state | |
| Auto-discover | Match from available OBS sources via heuristics | |

**User's choice:** IIDX#1 ~ IIDX#4
**Notes:** Simplest approach that matches existing cabinet assignment naming.

---

## Live Monitor UI scope

| Option | Description | Selected |
|--------|-------------|----------|
| Build browser UI now | 2x2 grid with thumbnails and state labels | |
| Console output only | Defer browser UI until streaming UI is ready | ✓ |

**User's choice:** "具体的直播UI并没有准备好，请先把这个状态输出到控制台上，当直播UI准备好了之后再具体实现"
**Notes:** The browser-based live monitor page is explicitly deferred. Phase 5 will focus on the backend monitoring loop with console output.

---

## SocketIO emissions (adjusted after UI deferral)

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, emit now | Emit cabinet states via SocketIO even without a monitor page | ✓ |
| No, console only | Keep it simple; add SocketIO later | |

**User's choice:** Yes, emit now
**Notes:** Data will flow via SocketIO for downstream Phase 6 score review and future UI.

---

## Polling interval

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed 1 second | Hardcoded interval | |
| Configurable via runtime state | Stored in `runtime/state.json` | ✓ |

**User's choice:** Configurable via runtime state
**Notes:** `monitor_interval` will be added to `RuntimeState`.

---

## Score visibility during monitoring

| Option | Description | Selected |
|--------|-------------|----------|
| Emit both state and scores | Capture and emit OCR results when entering score state | ✓ |
| State labels only | Defer score capture to Phase 6 | |

**User's choice:** Emit both state and scores
**Notes:** `obs_manager.py`'s `process_frame()` already handles this, so scores will be logged and emitted.

---

## Auto-start

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-start | Monitoring begins when app launches | |
| Manual start | Operator clicks a control to start/stop | ✓ |

**User's choice:** Manual start
**Notes:** A start/stop control will be added (e.g., on the Status page or via an API endpoint).

---

## Configuration surface

| Option | Description | Selected |
|--------|-------------|----------|
| Runtime state JSON only | Edit `runtime/state.json` directly | ✓ |
| Simple web form on Status page | Operator-friendly configuration UI | |

**User's choice:** Runtime state JSON only
**Notes:** Fastest path for Phase 5. Web forms can be added later if needed.

---

## Deferred Ideas

- Browser-based live monitor page with 2x2 thumbnail grid
- Web form for source name / polling interval configuration
- Auto-start monitoring on app launch
- Monitor page as a separate nav item

---

*No corrections were made after initial assumptions.*
