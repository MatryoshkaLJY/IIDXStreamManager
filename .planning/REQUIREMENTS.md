# Requirements: IIDX Stream Manager

**Defined:** 2026-04-13
**Core Value:** Reliable, visually polished tournament scoreboards that integrate cleanly into streaming workflows via WebSocket control.

## v1.1 Requirements

### UI / Visual

- [ ] **UI-01**: Champion trophy and all related champion presentation code are removed from HTML, CSS, and JS
- [ ] **UI-02**: Final stage uses distinct medal visuals: champion glows gold, player-points replaced with 🥇🥈🥉 emojis

### Scoring & Settlement Logic

- [ ] **SCOR-01**: `player-score` accumulates across rounds instead of being overwritten on each `score` command
- [ ] **SCOR-02**: ABCDEF groups sort by PT descending, tie-broken by cumulative player-score descending; Final stage sorts by PT only, with tie-breaker extra round that tracks only player-score (no PT)

### Progression & Groups

- [ ] **PROG-01**: Semifinals restructured into E group (A1 + B2 + C2 + D1) and F group (A2 + B1 + C1 + D2), with match order A → B → C → D → E → F → Final
- [ ] **PROG-02**: Only the currently active group is highlighted on initialization and after each settlement; advancing to the next group happens automatically after settle

### Commands & Integration

- [ ] **CMD-01**: `init` command updates the tournament title without destroying the `stage-indicator` and `title-text` elements

## v2 Requirements

(None — deferred for future milestones)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Mobile-responsive layouts | OBS/browser source target only |
| Persistent database/storage | Stateless tournament sessions by design |
| New tournament formats (double elimination, league) | Out of scope for v1.1; may be v1.2+ |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| UI-01 | Phase 2 | Pending |
| UI-02 | Phase 2 | Pending |
| SCOR-01 | Phase 2 | Pending |
| SCOR-02 | Phase 2 | Pending |
| PROG-01 | Phase 2 | Pending |
| PROG-02 | Phase 2 | Pending |
| CMD-01 | Phase 2 | Pending |

**Coverage:**
- v1.1 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0

---
*Requirements defined: 2026-04-13*
*Last updated: 2026-04-13 after milestone v1.1 start*
