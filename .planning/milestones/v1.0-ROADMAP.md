# Roadmap: IIDX Stream Manager

## Overview

A comprehensive streaming toolkit for Beatmania IIDX, providing real-time score recognition, state management, and visual scoreboards for tournaments and competitive play.

## Phases

- [ ] **Phase 1: 16-Player Knockout Tournament Scoreboard** - Web-based knockout tournament visualization with WebSocket control

## Phase Details

### Phase 1: 16-Player Knockout Tournament Scoreboard
**Goal**: Create a web-based 16-player knockout tournament scoreboard that displays a radial tree structure for tournament progression, with real-time score updates via WebSocket commands.
**Depends on**: Nothing (first phase)
**Requirements**: 
  - KO-01: Tournament tree renders with 16 players in radial layout
  - KO-02: Visual styling matches BPL scoreboard aesthetic
  - KO-03: Resolution 1920x1080 optimized for OBS
  - KO-04: WebSocket server accepts init, score, settle, reset commands
  - KO-05: Client connects and handles real-time updates
  - KO-06: Scoring system with 2/1/0/0 points per song
  - KO-07: Settlement advances top 2 players with path lighting
  - KO-08: Champion presentation with full path illumination
**Success Criteria** (what must be TRUE):
  1. Tournament tree renders correctly with 16 players in proper radial positions
  2. WebSocket server accepts init, score, settle, reset commands
  3. Live scores display on player nodes during active rounds
  4. Settlement correctly calculates points (2/1/0/0) and advances top 2
  5. Advancement paths light up with persistent glow effect
  6. Champion presentation shows name + full path lighting
  7. Visual styling matches BPL scoreboard aesthetic (Orbitron/Rajdhani fonts, cyan/pink accents)
  8. Works at 1920x1080 resolution in OBS browser source
**Plans**: 3 plans in 2 waves
  - Wave 1: Plans 01-02 (HTML/CSS structure, WebSocket server/client)
  - Wave 2: Plan 03 (Tournament logic and scoring)

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Knockout Scoreboard | 3/3 | **Completed** | 2026-04-10 |

## Plan Registry

### Phase 1 Plans

| Plan | File | Wave | Objective | Status |
|------|------|------|-----------|--------|
| 01 | 01-01-PLAN.md | 1 | HTML/CSS structure and radial tree layout | Planned |
| 02 | 01-02-PLAN.md | 1 | WebSocket server and client communication | Planned |
| 03 | 01-03-PLAN.md | 2 | Tournament logic and scoring system | Planned |
