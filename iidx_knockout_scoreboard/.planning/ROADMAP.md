# Roadmap: IIDX Knockout Tournament Scoreboard

## Milestones

- ✅ **v1.0 MVP** - Basic working scoreboard (shipped prior)
- 🚧 **v1.1 Rule Refinements** - Phases 1-3 (in progress)

## Phases

### 🚧 v1.1 Rule Refinements (In Progress)

**Milestone Goal:** Correct scoring rules, streamline visual effects, and improve tournament flow guidance for operators and viewers.

- [ ] **Phase 1: Visual Effects Cleanup** - Remove trophy code and update finals visuals (medals, gold flash)
- [ ] **Phase 2: Scoring Rules** - Implement accumulated scores, stage-specific sorting, and finals tiebreaker logic
- [ ] **Phase 3: Group Structure & Tournament Flow** - Rename/restructure E/F groups, update stage order, auto-advance highlights, and fix DOM init

## Phase Details

### Phase 1: Visual Effects Cleanup
**Goal**: Finals and champion visuals align with the simplified, polished design
**Depends on**: Nothing (first phase of v1.1)
**Requirements**: VISL-01, VISL-02, VISL-03
**Success Criteria** (what must be TRUE):
  1. Champion trophy code is fully removed from `app.js` and no trophy appears on screen
  2. Finals stage shows medal emojis (🥇🥈🥉) in player-points fields instead of numeric points
  3. Champion in finals flashes with a gold light effect distinct from group-stage green highlighting
**Plans**: TBD
**UI hint**: yes

### Phase 2: Scoring Rules
**Goal**: Scoring and sorting behave correctly across all stages and tiebreaker scenarios
**Depends on**: Phase 1
**Requirements**: SCOR-01, SCOR-02, SCOR-03, SCOR-04
**Success Criteria** (what must be TRUE):
  1. Player `score` field accumulates across rounds within A-F groups instead of being overwritten each round
  2. Groups A-F sort players by PT first, then by accumulated score as tiebreaker
  3. Finals sort players by PT only; score does not accumulate in finals
  4. If finals PT ties occur, a tiebreaker round begins where PT is not counted and only score accumulates
**Plans**: TBD

### Phase 3: Group Structure & Tournament Flow
**Goal**: Group advancement and tournament flow match the corrected E/F structure with automatic visual progression
**Depends on**: Phase 2
**Requirements**: GROUP-01, GROUP-02, FLOW-01, FLOW-02, DOM-01
**Success Criteria** (what must be TRUE):
  1. Quarterfinal groups A/B/C/D feed into E (A#1, B#2, C#2, D#1) and F (A#2, B#1, C#1, D#2)
  2. Stage order is A → B → C → D → E → F → Final
  3. On `init`, only Group A players are highlighted (not all 16 players)
  4. After a group is settled, highlight automatically advances to the next group in sequence
  5. `init` command preserves `.stage-indicator` and `.title-text` child elements inside `.tournament-title`
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Visual Effects Cleanup | v1.1 | 0/TBD | Not started | - |
| 2. Scoring Rules | v1.1 | 0/TBD | Not started | - |
| 3. Group Structure & Tournament Flow | v1.1 | 0/TBD | Not started | - |
