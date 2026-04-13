# Requirements: IIDX Knockout Tournament Scoreboard

**Defined:** 2026-04-13
**Core Value:** Operators can run a complete knockout tournament via simple WebSocket commands, and viewers see a clear, real-time visual bracket with correct advancement and scoring.

## v1 Requirements

### Visual Effects

- [ ] **VISL-01**: Champion trophy code is fully removed from `app.js` (already removed from HTML/CSS)
- [ ] **VISL-02**: Finals stage displays medal emojis (🥇🥈🥉) in the player-points field instead of numeric points
- [ ] **VISL-03**: Champion in finals flashes with a gold light effect distinct from group-stage green

### Scoring Rules

- [ ] **SCOR-01**: Player `score` field accumulates across rounds within a group instead of being overwritten each round
- [ ] **SCOR-02**: Groups A-F sort players primarily by PT (points), with accumulated score as tiebreaker
- [ ] **SCOR-03**: Finals sort players by PT only; score is not accumulated in finals
- [ ] **SCOR-04**: If finals PT ties occur, a tiebreaker round begins where PT is not counted and only score accumulates

### Group Structure

- [ ] **GROUP-01**: Quarterfinal groups A/B/C/D feed into renamed groups E and F with new composition rules
  - E group: A#1, B#2, C#2, D#1
  - F group: A#2, B#1, C#1, D#2
- [ ] **GROUP-02**: Stage order updated to A → B → C → D → E → F → Final

### Tournament Flow

- [ ] **FLOW-01**: On `init`, only Group A players are highlighted (not all 16 players)
- [ ] **FLOW-02**: After a group is settled, highlight automatically advances to the next group in sequence

### DOM & Commands

- [ ] **DOM-01**: `init` command preserves `.stage-indicator` and `.title-text` child elements inside `.tournament-title` while updating the tournament name

## v2 Requirements

(None deferred at this time.)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Persistent server-side state or database | Stateless relay is sufficient for local streaming use |
| WebSocket authentication/authorization | Single-operator local use; unnecessary complexity |
| Mobile/responsive layout | Target is exclusively OBS 1920x1080 Browser Source |
| Build system or package manager | Must remain zero-build vanilla JS |
| Animated connection paths between stages | Deliberately no-op per existing user preference |
| Custom controller UI | External controller sends raw JSON; no controller frontend needed |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| VISL-01 | Phase 1 | Pending |
| VISL-02 | Phase 1 | Pending |
| VISL-03 | Phase 1 | Pending |
| SCOR-01 | Phase 2 | Pending |
| SCOR-02 | Phase 2 | Pending |
| SCOR-03 | Phase 2 | Pending |
| SCOR-04 | Phase 2 | Pending |
| GROUP-01 | Phase 3 | Pending |
| GROUP-02 | Phase 3 | Pending |
| FLOW-01 | Phase 3 | Pending |
| FLOW-02 | Phase 3 | Pending |
| DOM-01 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-13*
*Last updated: 2026-04-13 after roadmap creation*
