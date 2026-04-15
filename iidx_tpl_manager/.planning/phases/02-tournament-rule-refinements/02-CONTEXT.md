# Phase 2: Tournament Rule Refinements - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Source:** Roadmap requirements + existing codebase analysis

<domain>
## Phase Boundary

Refine the existing knockout tournament scoreboard (`iidx_knockout_scoreboard/`) with improved scoring, group progression, and visual feedback rules. The existing scoreboard is a WebSocket relay server (port 8081) with an HTML/CSS/JS frontend that manages a 16-player knockout tournament across groups A→B→C→D→E→F→Finals.

This phase modifies the existing `app.js`, `index.html`, `style.css`, and `server.py` in the `iidx_knockout_scoreboard/` directory.

</domain>

<decisions>
## Implementation Decisions

### UI Changes
- **UI-01 (locked):** Remove champion trophy code and UI entirely. The commented-out champion trophy HTML/CSS in `index.html` and `style.css` must be fully deleted, not just hidden.
- **UI-02 (locked):** Final stage must render medals (🥇🥈🥉) in the player points area and apply champion gold glow to the 1st place finalist. 2nd place gets silver flash, 3rd gets bronze flash. Champion trophy element is replaced by medal display.

### Scoring Changes
- **SCOR-01 (locked):** Score commands must accumulate raw scores across rounds for A-F groups. Each group's players display their cumulative raw score (sum of all rounds so far) during the group stage.
- **SCOR-02 (locked):** Updated sorting rules:
  - **Groups A-F:** Sort by points (PT) descending, then by total raw score descending as tiebreaker.
  - **Finals:** Sort by points (PT) descending only. If tied, enter a tiebreaker round where tiebreaker scores are accumulated and used to break the tie. Extra round acts as the tiebreaker.

### Progression Changes
- **PROG-01 (locked):** Semifinals are restructured into E/F groups with new composition:
  - Group A 1st → E1, Group A 2nd → F1
  - Group B 1st → F2, Group B 2nd → E2
  - Group C 1st → F3, Group C 2nd → E3
  - Group D 1st → E4, Group D 2nd → F4
  - Order: A → B → C → D → E → F → Finals
- **PROG-02 (locked):** Active group highlighting advances automatically after settlement. When a group is settled, the next group in sequence (A→B→C→D→E→F→finals) becomes the active highlighted group without requiring a manual `continue` command. The `continue` command can remain but auto-advance should happen on settle.

### Command Fixes
- **CMD-01 (locked):** Fix `init` command to preserve header structure. The current `handleInit` replaces the entire `.tournament-title` innerHTML, which can remove the `stage-indicator` span. Init must only update `.title-text` and leave `.stage-indicator` intact.

### Claude's Discretion
- Keep WebSocket protocol backward-compatible where possible (same command names: `init`, `score`, `settle`, `reset`).
- The `server.py` relay likely needs no changes unless protocol changes require it (not expected).
- CSS modifications should preserve the existing BPL-compatible dark theme and Orbitron/Rajdhani typography.
- Tiebreaker UI should keep tied players in "active" state until tiebreaker is resolved.

</decisions>

<canonical_refs>
## Canonical References

### Existing Codebase
- `iidx_knockout_scoreboard/app.js` — Tournament logic, command handlers, scoring, settlement
- `iidx_knockout_scoreboard/index.html` — Tournament tree DOM structure
- `iidx_knockout_scoreboard/style.css` — Visual styling including player states and champion trophy
- `iidx_knockout_scoreboard/server.py` — WebSocket relay server

### Project Documents
- `.planning/REQUIREMENTS.md` — Project-level requirements traceability
- `.planning/ROADMAP.md` — Phase 2 goal and success criteria

</canonical_refs>

<specifics>
## Specific Ideas

### Champion Trophy Removal
Delete the commented `<div class="champion-trophy">` block from `index.html` and remove all `.champion-trophy` CSS rules from `style.css`.

### Auto-Advance on Settle
In `handleSettle`, after processing a non-final group's settlement, automatically call `handleContinue()` to advance the active highlight to the next group in sequence. For the final group before finals, auto-advance to finals.

### Init Fix
Change `handleInit` to query `.title-text` directly and update only its `textContent`, rather than rebuilding the `.tournament-title` container.

### Medal Display
Re-use the existing `medals` array in `handleSettle` for finals. Ensure `updatePlayerNode` correctly sets `.player-points` to the medal emoji. The champion gets `.champion` class (gold glow already defined in CSS).

</specifics>

<deferred>
## Deferred Ideas

None — all requirements from Phase 2 are in scope.

</deferred>

---

*Phase: 02-tournament-rule-refinements*
*Context gathered: 2026-04-15 via roadmap + codebase analysis*
