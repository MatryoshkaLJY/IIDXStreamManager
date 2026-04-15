---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Auto-Director Core
status: defining_requirements
last_updated: "2026-04-15T13:10:00.000Z"
last_activity: 2026-04-15 -- Milestone v1.2 started
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# State: IIDX Tournament Auto-Director

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-15 -- Milestone v1.2 started

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-15)

**Core value:** Reliable, visually polished tournament scoreboards that integrate cleanly into streaming workflows via WebSocket control.
**Current focus:** Defining v1.2 Auto-Director Core requirements and roadmap

## Accumulated Context

- v1.0 shipped with a 16-player knockout tournament scoreboard using vanilla HTML/CSS/JS and a Python WebSocket relay.
- v1.1 shipped with knockout rule refinements: cumulative scoring, E/F semifinal groups, auto-advance, tiebreaker, and medal styling (6/6 jsdom tests passing).
- Milestone artifacts archived to `.planning/milestones/`.
- `iidx_tpl_manager` has config loader, Flask app shell, and runtime state persistence ready.
- Ready for v1.2: operator UI, OBS integration, cabinet monitoring, score review workflow.
