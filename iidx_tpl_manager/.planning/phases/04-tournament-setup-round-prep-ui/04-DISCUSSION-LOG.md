# Phase 4: Tournament Setup & Round Prep UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-15
**Phase:** 04-tournament-setup-round-prep-ui
**Areas discussed:** Mode selection & config loading workflow, Round prep page structure, State persistence scope, Config validation UX, File upload behavior, Player assignment data model, Round navigation, Page organization, Assignment initialization, Round prep validation, Mode switching behavior, Upload UX details, Assignment storage format, Player pool source

---

## Mode selection & config loading workflow

| Option | Description | Selected |
|--------|-------------|----------|
| File-upload flow | Operator uploads JSON configs via web UI; mode selected from dropdown | ✓ |
| Eager auto-load | App reads all configs from data/ at startup without explicit upload | |

**User's choice:** File-upload flow
**Notes:** The operator will select "team" or "individual" from a dropdown and upload the corresponding config file(s) through the web UI.

---

## Round prep page structure

| Option | Description | Selected |
|--------|-------------|----------|
| Dropdown menus | Per-cabinet dropdowns (IIDX#1~IIDX#4) to assign players | ✓ |
| Text inputs | Free-text inputs per cabinet | |
| Drag-and-drop lists | Visual drag-to-cabinet assignment | |

**User's choice:** Dropdown menus
**Notes:** Simple HTML select elements per cabinet, populated from the uploaded config.

---

## State persistence scope

| Option | Description | Selected |
|--------|-------------|----------|
| Extend now | Add mode, current_round, and cabinet_assignments to RuntimeState in Phase 4 | ✓ |
| Defer fields | Only add mode selection in UI; defer persistence to later phases | |

**User's choice:** Extend now
**Notes:** AUTO-05 compliance starts in this phase by persisting mode, round, and assignments to runtime/state.json.

---

## Config validation UX

| Option | Description | Selected |
|--------|-------------|----------|
| Keep current pattern | Config validation errors shown as global banner on Status page | ✓ |
| Move to config page | Errors shown only on Config/Round Prep page | |

**User's choice:** Keep current pattern
**Notes:** Preserve the existing eager-load error banner pattern from Phase 01.

---

## File upload behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Validate first + backup | Validate JSON with Pydantic before saving; create .bak of previous config | ✓ |
| Validate first only | Validate before saving but no backup | |
| Overwrite directly | Save without validation; validation happens at next startup | |

**User's choice:** Validate first + backup
**Notes:** Uploaded configs are validated inline, and the old config is backed up before overwrite.

---

## Player assignment data model

| Option | Description | Selected |
|--------|-------------|----------|
| Empty string | Unassigned cabinet stores "" | |
| 'Unassigned' placeholder | Literal string 'Unassigned' for readability | ✓ |
| Optional/null | Stores null when unassigned | |

**User's choice:** 'Unassigned' placeholder
**Notes:** Makes the UI and persisted state human-readable without requiring optional typing.

---

## Round navigation

| Option | Description | Selected |
|--------|-------------|----------|
| Previous/Next buttons | Step through rounds sequentially | ✓ |
| Round number dropdown | Jump to any available round | |
| Direct number input + buttons | Type a round number with prev/next shortcuts | |

**User's choice:** Previous/Next buttons
**Notes:** Simple sequential navigation on the Round Prep page.

---

## Page organization

| Option | Description | Selected |
|--------|-------------|----------|
| Combined Setup page | Mode + upload + round prep on one page | |
| Separate pages | Config page for mode/upload; Round Prep page for assignments | ✓ |

**User's choice:** Separate pages
**Notes:** Two distinct pages accessible from the nav.

---

## Assignment initialization

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-populate from schedule | Pre-fill assignments from schedule data for the current round | |
| Clear to 'Unassigned' | Reset all cabinets to 'Unassigned' on mode/config change | ✓ |
| Preserve previous assignments | Keep existing assignments across mode/config changes | |

**User's choice:** Clear to 'Unassigned'
**Notes:** Every mode or config change clears assignments to a known default.

---

## Round prep validation

| Option | Description | Selected |
|--------|-------------|----------|
| Allow partial | Some cabinets may remain 'Unassigned' when saving | ✓ |
| Require all 4 | Every cabinet must have a player assigned | |

**User's choice:** Allow partial
**Notes:** Operator can start a round without all 4 cabinets populated.

---

## Mode switching behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Reset everything | Round resets to 1, assignments clear, configs reload | ✓ |
| Keep round, clear assignments | Round number preserved, assignments cleared | |
| Preserve all state | Only active mode changes | |

**User's choice:** Reset everything
**Notes:** Clean slate on every mode switch to avoid stale state.

---

## Upload UX details

| Option | Description | Selected |
|--------|-------------|----------|
| Simple browse button | Standard HTML file input | ✓ |
| Drag-and-drop zone | Larger visual drop area | |
| Browse button + templates | Include download-template buttons | |

**User's choice:** Simple browse button
**Notes:** Minimal JS, reliable for a local operator UI.

---

## Assignment storage format

| Option | Description | Selected |
|--------|-------------|----------|
| List (indexed 0-3) | ['P1', 'P2', 'Unassigned', 'P4'] | |
| Dict by cabinet name | {'IIDX#1': 'P1', 'IIDX#2': 'P2', ...} | ✓ |

**User's choice:** Dict by cabinet name
**Notes:** Self-documenting and less fragile than index-based storage.

---

## Player pool source

| Option | Description | Selected |
|--------|-------------|----------|
| From uploaded config | Team mode → teams.json; Individual mode → individual_schedule.json | ✓ |
| Separate master list | A master players.json file | |

**User's choice:** From uploaded config
**Notes:** No extra file management; player list derives directly from the loaded tournament config.

---

## Claude's Discretion

- Exact visual styling and layout of the Config and Round Prep pages
- Precise wording of nav links and button labels
- Round bounds handling (Previous/Next disable at boundaries)
- Whether to auto-restore last uploaded config on app restart

---

*Phase: 04-tournament-setup-round-prep-ui*
*Discussion date: 2026-04-15*
