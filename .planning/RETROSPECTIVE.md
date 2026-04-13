# Project Retrospective

## Milestone: v1.0 — Knockout Tournament Scoreboard

**Shipped:** 2026-04-13
**Phases:** 1 | **Plans:** 3 (+ 4 fix plans)

### What Was Built
- Web-based 16-player knockout tournament scoreboard with radial tree layout
- WebSocket relay server and client for real-time tournament control
- Full tournament logic: scoring, settlement, advancement, and champion presentation

### What Worked
- Plan decomposition into HTML/CSS, WebSocket layer, and tournament logic worked well
- Rapid gap diagnosis and fix planning kept the project on track after UAT
- User feedback loop (screenshots, specific reports) enabled precise fixes

### What Was Inefficient
- Index mismatch between HTML (1-indexed) and JS (0-indexed) caused cascading bugs across multiple tests
- Finals group naming mismatch (`F` vs `finals`) could have been caught earlier with stricter naming conventions
- Visual layout required a full redesign after initial UAT rather than incremental adjustment

### Patterns Established
- Use consistent 0-indexed data attributes in HTML when consumed by JS arrays
- Align DOM group identifiers exactly between HTML, CSS, and JS
- Build horizontal/compact node layouts for dense 1920x1080 scoreboards

### Key Lessons
- UAT early and often — the first UAT caught 6 real issues that unit tests missed
- Fix plans are an effective pattern for post-UAT closure
- Absolute positioning requires tight bounds checking at target resolution

### Cost Observations
- Sessions: ~6 for full phase completion including fixes
- Notable: Most time was spent in gap-closure fix iteration after initial implementation

## Cross-Milestone Trends

| Milestone | Phases | Plans | UAT Issues | Fix Plans |
|-----------|--------|-------|------------|-----------|
| v1.0 | 1 | 3 | 6 | 4 |
