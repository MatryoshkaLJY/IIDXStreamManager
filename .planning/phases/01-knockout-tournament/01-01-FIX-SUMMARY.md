---
plan: 01-01-FIX
phase: 01-knockout-tournament
status: completed
completed: 2026-04-11
---

# Fix 01-01 Summary: Index Mismatch (1-indexed → 0-indexed)

## Problem Fixed
HTML used `data-position="1", "2", "3", "4"` (1-indexed) while JavaScript used 0-3 array indices (0-indexed), causing:
- INIT command updating wrong player nodes
- SETTLE command applying states to wrong positions
- RESET command unable to clear 4th position

## Changes Made

### index.html
Changed ALL `data-position` attributes from 1-4 to 0-3:
- Group A (A1-A4): positions 1→0, 2→1, 3→2, 4→3
- Group B (B1-B4): positions 1→0, 2→1, 3→2, 4→3
- Group C (C1-C4): positions 1→0, 2→1, 3→2, 4→3
- Group D (D1-D4): positions 1→0, 2→1, 3→2, 4→3
- Group AB (AB1-AB4): positions 1→0, 2→1, 3→2, 4→3
- Group CD (CD1-CD4): positions 1→0, 2→1, 3→2, 4→3
- Finals (F1-F4): positions 1→0, 2→1, 3→2, 4→3

## Tests Fixed
- Test 3: Player Node States Visual
- Test 5: INIT Command - Player Setup
- Test 7: SETTLE Command - Quarterfinal Advancement
- Test 10: RESET Command

## Verification
```bash
# Send INIT command
{"cmd": "init", "data": {"groups": {"A": ["P1", "P2", "P3", "P4"]}}}

# All 4 player names should display in correct positions
# No console errors about missing data
```

## Commit
`2d97626` fix(01-gap-closure): resolve index mismatch, layout, and styling issues
