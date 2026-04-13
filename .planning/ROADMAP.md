# Roadmap: IIDX Stream Manager

## Milestones

- **v1.0 Knockout Tournament Scoreboard** — Phase 1 (shipped 2026-04-13)

## Phases

<details>
<summary> v1.0 Knockout Tournament Scoreboard (Phase 1) — SHIPPED 2026-04-13</summary>

- [x] Phase 1: 16-Player Knockout Tournament Scoreboard (7/7 summaries) — completed 2026-04-13
  - Plan 01: HTML/CSS structure and radial tree layout
  - Plan 02: WebSocket server and client communication
  - Plan 03: Tournament logic and scoring system
  - Fix 01-01: Index alignment (HTML vs JS)
  - Fix 01-02: Finals group mapping
  - Fix 01-03: Visual layout redesign
  - Fix 01-04: Score/points styling

See archive: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Knockout Scoreboard | v1.0 | 7/7 | Complete | 2026-04-13 |

### v1.1 Tournament Rule Refinements (In Progress)

- [ ] Phase 2: Tournament Rule Refinements (0/1 plans) — started 2026-04-13

## Phase Details

### Phase 2: Tournament Rule Refinements

**Goal**: Refine the knockout tournament scoreboard with improved scoring, group progression, and visual feedback rules.
**Depends on**: Phase 1
**Requirements**:
  - UI-01: Remove champion trophy and related code
  - UI-02: Final stage medal visuals (🥇🥈🥉) and champion gold glow
  - SCOR-01: Cumulative raw score tracking per round
  - SCOR-02: Updated sorting rules (groups by PT→score; final by PT only with extra-round tiebreaker)
  - PROG-01: Restructure semifinals into E/F groups with new composition and match order
  - PROG-02: Active group highlighting that advances automatically after settlement
  - CMD-01: Fix init command to preserve stage-indicator and title-text
**Success Criteria**:
  1. Champion trophy code and UI fully removed
  2. Score commands accumulate raw scores across rounds
  3. E/F group composition and A→B→C→D→E→F→Final order works end-to-end
  4. Active group highlighting advances automatically after settle
  5. Sorting rules match spec for groups and finals
  6. Final stage renders medals and champion gold glow
  7. Init command preserves header structure
**Plans**: 1 plan
  - Plan 01: Implement all v1.1 rule refinements

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Knockout Scoreboard | v1.0 | 7/7 | Complete | 2026-04-13 |
| 2. Rule Refinements | v1.1 | 0/1 | In Progress | - |

---
