# Phase 1: Foundation & Config - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Application boots with a working web server and handles tournament configuration reliably. This phase delivers: Flask app shell on port 5002, JSON config loading/validation for three config files, and runtime state persistence with auto-restore.

</domain>

<decisions>
## Implementation Decisions

### Config schemas
- **D-01:** `teams.json` contains team metadata with the following structure: team `id`, `name`, logo `emoji`, `colors` object (`primary`, `secondary`, `accent`), and `players` array (each player has `id`, `name`, `role`)
- **D-02:** `team_schedule.json` contains the season schedule: `weeks` → `matches` → `left_team`, `right_team`, `template`, and `rounds` array (each round has `type` of `1v1` or `2v2`, `theme`, `left_players`, `right_players`)
- **D-03:** `individual_schedule.json` contains knockout groups: group name mapped to a list of 4 player names

### State persistence scope
- **D-04:** Persist only loaded configs and their file paths; re-load from disk on startup. UI preferences and validation history are NOT persisted.

### Config loading behavior
- **D-05:** If a config file is missing, the app auto-generates a valid empty/minimal template in `data/` and starts normally
- **D-06:** Generated templates must contain valid minimal structure (empty arrays/objects) so they pass Pydantic schema validation and the app boots cleanly

### Validation error UX
- **D-07:** If an existing config file has schema errors, the app blocks startup and emits a clear terminal/web error message with actionable detail

### Claude's Discretion
- Exact Pydantic model field types and validators
- Flask app project structure and module organization
- Specific copy for error messages (follow UI-SPEC tone)
- Whether to log validation details to a file in addition to the web UI

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements
- `.planning/ROADMAP.md` §Phase 1 — scope boundary, success criteria, UI hint
- `.planning/REQUIREMENTS.md` §Config & Setup — CONF-02, CONF-03, CONF-05 acceptance criteria
- `.planning/PROJECT.md` §Requirements / §Key Decisions — Flask on port 5002, reuse `obs_manager.py`, one mode per event

### UI contract
- `.planning/phases/01-foundation-config/01-UI-SPEC.md` — color palette, typography, spacing, copywriting, and error-state copy

### External reference data
- `../iidx_bpl_scoreboard/testbench/data.json` — example team metadata, themes, match templates, stages, season schedule, and player assignments used to inform schema decisions
- `../iidx_knockout_scoreboard/testbench.py` — example knockout group structure (groups A–D with 4 players each)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None in this repository yet — this is the first phase
- External library: `../obs_manager/obs_manager.py` will be reused in later phases for frame capture and recognition

### Established Patterns
- None in-repo yet; downstream agents should follow Flask patterns from CLAUDE.md technology stack recommendations

### Integration Points
- Config files will be read from `data/` subdirectory at project root
- State persistence will write to a local file (e.g., `state.json`) in the project root or a `runtime/` folder
- Web UI will be served on port 5002 via Flask

</code_context>

<specifics>
## Specific Ideas

- Config schemas were derived from the existing BPL scoreboard testbench data and knockout testbench structure
- Operator should be able to place config files in `data/` and reload the page to pick them up without restarting the server

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation-config*
*Context gathered: 2026-04-14*
