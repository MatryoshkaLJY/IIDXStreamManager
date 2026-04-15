---
phase: 3
slug: obs-integration-scene-control
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-15
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.4 |
| **Config file** | none — default discovery |
| **Quick run command** | `pytest tests/ -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | OBS-01 | T-03-01 | RuntimeState loads old JSON with new OBS fields gracefully | unit | `pytest tests/test_state.py -x` | ✅ | ⬜ pending |
| 03-01-02 | 01 | 1 | OBS-01 | T-03-02 | OBSClient connects lazily and validates scene list | unit | `pytest tests/test_obs_client.py -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | OBS-02 | T-03-03 | SceneController switches to valid scene | unit | `pytest tests/test_scene_controller.py -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | OBS-04 | T-03-04 | Heartbeat emits obs_status on disconnect detection | unit | `pytest tests/test_heartbeat.py -x` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | OBS-02 | T-03-05 | Scene switching route returns error when OBS disconnected | unit | `pytest tests/test_app_obs_routes.py -x` | ❌ W0 | ⬜ pending |
| 03-02-03 | 02 | 2 | OBS-04 | T-03-06 | SocketIO reconnect handler triggers re-validation | unit | `pytest tests/test_app_obs_routes.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_obs_client.py` — stubs for OBS-01
- [ ] `tests/test_scene_controller.py` — stubs for OBS-02
- [ ] `tests/test_app_obs_routes.py` — stubs for OBS-02, OBS-04
- [ ] `tests/test_heartbeat.py` — stubs for OBS-04
- [ ] `src/obs/__init__.py` — package init with public API
- [ ] `static/js/operator.js` — SocketIO client for real-time updates

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-----------------|
| OBS scene actually switches in running OBS Studio | OBS-02 | Requires live OBS WebSocket connection | Start OBS with WebSocket v5 on localhost:4455. Open status page, click each scene button, confirm program scene changes in OBS. |
| Warning banner renders correctly on disconnect | OBS-04 | Visual UI state | Stop OBS. Refresh status page. Confirm red banner appears and scene buttons are disabled. Click Reconnect. Start OBS. Confirm banner hides. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
