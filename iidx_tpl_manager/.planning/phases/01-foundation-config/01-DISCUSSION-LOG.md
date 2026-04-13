# Phase 1: Foundation & Config - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-14
**Phase:** 1 — Foundation & Config
**Areas discussed:** Config schemas, State persistence scope, Config loading behavior, Validation error UX

---

## Config schemas

| Option | Description | Selected |
|--------|-------------|----------|
| Looks good — use these schemas | Proceed with the proposed structure for all 3 config files. | ✓ |
| Simplify — fewer fields | I want a leaner schema. | |
| I have sample files / different structure in mind | I'll describe the exact schemas or share sample data. | |
| You decide — standard is fine | Claude can choose the schema. | |

**User's choice:** Looks good — use these schemas
**Notes:** Proposed schema structure accepted:
- `teams.json`: team `id`, `name`, logo `emoji`, `colors` (`primary`, `secondary`, `accent`), `players` (`id`, `name`, `role`)
- `team_schedule.json`: `weeks` → `matches` → `left_team`, `right_team`, `template`, `rounds` (`type` 1v1/2v2, `theme`, `left_players`, `right_players`)
- `individual_schedule.json`: group name → list of 4 player names

---

## State persistence scope

| Option | Description | Selected |
|--------|-------------|----------|
| Loaded configs and file paths only | Persist which config files were loaded and their paths. | ✓ |
| Configs + UI/app settings | Also persist UI preferences and operator-adjusted settings. | |
| Everything including validation history | Persist loaded configs, settings, last validation results, and error history. | |
| You decide | Claude has discretion. | |

**User's choice:** Loaded configs and file paths only
**Notes:** Scope limited to loaded configs and their file paths. UI preferences and validation history are out of scope for persistence.

---

## Config loading behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Require all 3 — refuse to start if any config is missing | Block startup until all config files are present. | |
| Graceful degradation — start and show what's missing | Start web server and display missing files on status page. | |
| Auto-generate empty templates | If missing, create a minimal template and start. | ✓ |
| You decide | Claude has discretion. | |

**User's choice:** Auto-generate empty templates
**Notes:** Missing config files trigger auto-generation of valid empty/minimal templates in `data/`.

---

## Validation error UX

| Option | Description | Selected |
|--------|-------------|----------|
| Block startup — exit with a clear terminal/web error | Refuse to start and print a detailed validation error. | ✓ |
| Start anyway — show errors in the web UI | Start the server and display errors on the status/config page. | |
| You decide | Claude has discretion. | |

**User's choice:** Block startup — exit with a clear terminal/web error
**Notes:** Existing config files with schema errors block startup with a clear actionable error message.

---

## Follow-up: Template validity

| Option | Description | Selected |
|--------|-------------|----------|
| Generated templates must be valid — app starts normally | Templates contain valid minimal structure to pass schema validation. | ✓ |
| Skip validation on first boot after generation | Allow startup even if newly generated templates are effectively empty. | |
| You decide | Claude has discretion. | |

**User's choice:** Generated templates must be valid — app starts normally
**Notes:** Auto-generated templates must be valid JSON with empty arrays/objects so they pass Pydantic validation and the app boots cleanly.

---

## Claude's Discretion

- Exact Pydantic model field types and validators
- Flask app project structure and module organization
- Specific copy for error messages (follow UI-SPEC tone)
- Whether to log validation details to a file in addition to the web UI

## Deferred Ideas

None — discussion stayed within phase scope
