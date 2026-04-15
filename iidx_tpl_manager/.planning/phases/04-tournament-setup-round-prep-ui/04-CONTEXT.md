# Phase 4: Tournament Setup & Round Prep UI - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Operator-facing web UI for selecting tournament mode, loading tournament configs, and assigning players to cabinets before each round.

This phase delivers:
- A "Config" page for tournament mode selection and JSON config file upload
- A "Round Prep" page for assigning players to IIDX#1~IIDX#4 cabinets
- Persistence of mode, current round, and cabinet assignments to `runtime/state.json`

Scene automation, cabinet monitoring, and score review are out of scope for this phase.
</domain>

<decisions>
## Implementation Decisions

### Mode selection & config loading workflow
- **D-01:** The operator selects mode ("team" or "individual") from a dropdown.
- **D-02:** Configs are loaded via a file-upload flow. The operator uploads `teams.json`, `team_schedule.json`, or `individual_schedule.json` through the web UI.
- **D-03:** Uploaded files are validated with Pydantic before being saved to `data/`.
- **D-04:** The previous config file is backed up (e.g., `teams.json.bak`) before overwriting.

### Config validation UX
- **D-05:** Config validation errors are shown as a global banner on the Status page, preserving the existing eager-load pattern at app startup.

### Round prep page structure
- **D-06:** Round prep uses dropdown menus per cabinet (IIDX#1 ~ IIDX#4) to assign players.
- **D-07:** Unassigned cabinets store the literal string `"Unassigned"`.
- **D-08:** Partial assignments are allowed — the operator can save round prep even if some cabinets are "Unassigned".

### Round navigation
- **D-09:** The operator moves between rounds using Previous/Next buttons on the Round Prep page.
- **D-10:** Round numbers start at 1 and increment sequentially.

### Page organization
- **D-11:** Two separate pages in the nav:
  - **Config** — mode selection + file upload
  - **Round Prep** — round navigation + cabinet assignment

### State persistence
- **D-12:** Extend `RuntimeState` in this phase with:
  - `mode: str = ""` ("team" or "individual")
  - `current_round: int = 1`
  - `cabinet_assignments: Dict[str, str]` mapping `IIDX#1`..`IIDX#4` to player names, defaulting all to `"Unassigned"`

### Assignment initialization
- **D-13:** When mode is switched or a new config is uploaded, all cabinet assignments reset to `"Unassigned"` and `current_round` resets to 1.

### Upload UX
- **D-14:** File upload uses a standard HTML browse button (no drag-and-drop).

### Player pool source
- **D-15:** Dropdown options are populated from the uploaded config file:
  - Team mode: all player names from `teams.json`
  - Individual mode: all player names from `individual_schedule.json`

### Assignment storage format
- **D-16:** Cabinet assignments are stored as a dict by cabinet name: `{"IIDX#1": "Player A", "IIDX#2": "Unassigned", ...}`

### Claude's Discretion
- Exact visual styling and layout of the Config and Round Prep pages
- Precise wording of nav links and button labels
- How round bounds are handled (e.g., Previous disabled at round 1) — standard disable-when-at-bounds pattern is recommended
- Whether to auto-load the last uploaded config on app restart vs. requiring the operator to re-upload

</decisions>

<canonical_refs>
## Canonical References

### Requirements & project context
- `.planning/REQUIREMENTS.md` — Requirements UI-01 through UI-04, AUTO-05
- `.planning/PROJECT.md` — Project vision, constraints, existing components, config formats
- `.planning/phases/03-obs-integration-scene-control/03-CONTEXT.md` — Prior phase decisions on state persistence and UI patterns

### Existing code to reuse or reference
- `src/config/loader.py` — Config loading, Pydantic validation, and template generation patterns
- `src/config/models.py` — Pydantic models for `TeamsConfig`, `TeamScheduleConfig`, `IndividualScheduleConfig`
- `src/state.py` — `RuntimeState` persistence pattern (JSON to disk with `.get()` fallbacks)
- `src/app.py` — Flask routes, SocketIO, and status page pattern
- `src/templates/base.html` — Jinja2 base template with nav links
- `src/templates/status.html` — Existing status page with banner/form patterns
- `static/css/main.css` — Existing CSS tokens and card/label/form classes

### Data files
- `data/teams.json` — Team and player definitions
- `data/team_schedule.json` — Team match schedule
- `data/individual_schedule.json` — Individual group schedule
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/config/loader.py` (`load_configs`, `ensure_templates`): Already validates all three config types with Pydantic
- `src/state.py` (`RuntimeState`): Can be extended with `mode`, `current_round`, and `cabinet_assignments`
- `src/templates/base.html`: Nav link pattern — "Status" and "Config" links already exist; "Round Prep" can be added
- `static/css/main.css`: `.form-row`, `.button-row`, and `.card` classes exist from Phase 3

### Established Patterns
- Config/state lives on disk as JSON and is eagerly loaded at app startup
- UI is server-rendered Jinja2 with minimal JavaScript
- Error messages are rendered inline in HTML templates
- POST routes return JSON for forms that may be submitted via fetch

### Integration Points
- `src/app.py` is the central Flask app — new routes for `/config` and `/round_prep` go here
- `load_configs()` is called eagerly inside `app.app_context()` on startup
- Runtime state is read/written via `load_runtime_state()` and `save_runtime_state()`
</code_context>

<specifics>
## Specific Ideas

- Keep the UI simple: server-rendered Jinja2 pages, not a SPA
- Config upload should feel safe: validation + backup before overwrite
- Round prep should be quick to use: dropdowns per cabinet, Previous/Next for rounds
</specifics>

<deferred>
## Deferred Ideas

- Drag-and-drop file upload — not needed for a local operator UI
- Mobile-responsive layout — deferred to post-v1.2
- Auto-populating assignments from schedule data — user chose manual assignment with "Unassigned" defaults
- Separate master player list — player pool comes from uploaded config only

</deferred>

---

*Phase: 04-tournament-setup-round-prep-ui*
*Context gathered: 2026-04-15*
