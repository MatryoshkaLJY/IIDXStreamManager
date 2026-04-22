# Phase 7: Auto-Transitions & Configurable Delays - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 07-auto-transitions-configurable-delays
**Areas discussed:** Auto-transition trigger logic, Delay configuration model, Manual proceed workflow, Automation controls and state display

---

## Auto-transition trigger logic

| Option | Description | Selected |
|--------|-------------|----------|
| Any cabinet enters play | Switch as soon as one cabinet reports play | |
| All cabinets enter play | Switch only when every cabinet is in play | ✓ |
| You decide | Claude decides best heuristic | |

**User's choice:** All cabinets enter play
**Notes:** Gameplay → Scoreboard remains operator-confirmed. Gameplay → Live: user deferred to Claude.

---

## Gameplay → Live trigger

| Option | Description | Selected |
|--------|-------------|----------|
| All cabinets return to live/blank | Conservative approach, waits for full round end | ✓ |
| Any cabinet returns to live/blank | Aggressive, may cut away early | |
| You decide | Claude decides based on typical tournament flow | |

**User's choice:** You decide (Claude will use "all cabinets return to live/blank")
**Notes:** Standard tournament flow — wait for all cabinets to finish before returning to live camera.

---

## Gameplay → Scoreboard transition

| Option | Description | Selected |
|--------|-------------|----------|
| Still operator-confirmed | Score review panel and Confirm & Push remain | ✓ |
| Fully automatic | Remove operator confirmation, auto-transition on score state | |
| Hybrid | Auto-transition but allow score correction during countdown | |

**User's choice:** Still operator-confirmed
**Notes:** Phase 6 score review workflow is unchanged. Auto-transitions only handle Live ↔ Gameplay.

---

## Delay configuration model

| Option | Description | Selected |
|--------|-------------|----------|
| Return-to-live delay only | One new delay field | |
| Return-to-live + gameplay hold | Two delay fields for finer control | |
| You decide | Claude recommends minimal useful set | ✓ |

**User's choice:** You decide
**Notes:** Claude will recommend `return_to_live_delay` and `gameplay_hold_delay`.

---

## Delay UI placement

| Option | Description | Selected |
|--------|-------------|----------|
| Status page card | Inline on existing Status page | |
| Dedicated page | New "Automation" page in nav | ✓ |
| You decide | Claude chooses placement | |

**User's choice:** Dedicated page
**Notes:** New "Automation" nav item alongside Status, Config, Round Prep.

---

## Manual proceed (-1 delay) workflow

| Option | Description | Selected |
|--------|-------------|----------|
| Automation page only | Proceed button only on Automation page | |
| Persistent on all pages | Proceed button visible everywhere | ✓ |
| Modal overlay | Popup blocks UI until operator acts | |
| You decide | Claude chooses best UX | |

**User's choice:** Persistent on all pages
**Notes:** Button should be visible regardless of which page operator is viewing.

---

## Manual proceed state display

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal | Just "Waiting for operator" with Proceed | |
| Context-rich | Pending transition, cabinet states, estimated delay | ✓ |
| You decide | Claude decides based on workflow needs | |

**User's choice:** Context-rich
**Notes:** Show pending transition name, current cabinet states, estimated delay if changed from -1.

---

## Pause/Resume toggle

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, toggle on Automation + Status | Separate from Emergency Live | ✓ |
| No, Emergency Live is sufficient | No separate pause control | |
| You decide | Claude recommends simplest control set | |

**User's choice:** Yes, toggle on Automation + Status
**Notes:** Pause/Resume toggle available on both Automation page and Status page.

---

## Automation state display

| Option | Description | Selected |
|--------|-------------|----------|
| Status banner | Banner at top of every page like OBS banner | ✓ |
| Indicator badge | Small badge in nav/header | |
| Both | Banner for emergency/paused, badge for normal | |
| You decide | Claude chooses based on attention needs | |

**User's choice:** Status banner
**Notes:** Reuse existing OBS connection banner pattern. Show Active (green), Paused (yellow), Emergency (red).

---

## Claude's Discretion

- Exact styling and placement of the Proceed button
- Exact delay default values (recommendations: return_to_live=5.0, gameplay_hold=3.0)
- How automation banner coexists with OBS connection banner
- Whether to show countdown timers for active delays in the banner
- Internal implementation of aggregate state machine (polling vs event-driven)

## Deferred Ideas

- Gameplay scene text source and group visibility setup — post-v1.2
- Mobile-responsive operator UI — post-v1.2
- Advanced per-cabinet automation rules — future enhancement
