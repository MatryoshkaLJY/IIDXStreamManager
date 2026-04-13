# Project: IIDX Stream Manager

## What This Is

A comprehensive streaming toolkit for Beatmania IIDX, providing real-time score recognition, state management, and visual scoreboards for tournaments and competitive play.

## Core Value

Reliable, visually polished tournament scoreboards that integrate cleanly into streaming workflows via WebSocket control.

## Requirements

### Validated

- Tournament tree renders with 16 players in radial layout — v1.0
- Visual styling matches BPL scoreboard aesthetic — v1.0
- Resolution 1920x1080 optimized for OBS — v1.0
- WebSocket server accepts init, score, settle, reset commands — v1.0
- Client connects and handles real-time updates — v1.0
- Scoring system with 2/1/0/0 points per song — v1.0
- Settlement advances top 2 players with path lighting — v1.0
- Champion presentation with full path illumination — v1.0

### Active

(None — planning next milestone)

### Out of Scope

- Mobile-responsive layouts — OBS/browser source target only
- Persistent database/storage — stateless tournament sessions

## Context

- Shipped v1.0 with ~11,800 LOC across HTML, CSS, JS, and Python.
- Tech stack: vanilla HTML/CSS/JS, Python websockets library.
- UAT identified 6 gaps; all addressed through 4 fix plans.

## Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| Use absolute positioning for radial tree layout | Precise control over 1920x1080 OBS resolution | Good |
| Vanilla JS without frameworks | Minimizes runtime dependencies for browser source | Good |
| Python websockets for relay server | Simple, lightweight broadcast server | Good |
| Horizontal player node layout (late change) | Better fit at 1920x1080, clearer score/points emphasis | Good |

---

*Last updated: 2026-04-13 after v1.0 milestone*
