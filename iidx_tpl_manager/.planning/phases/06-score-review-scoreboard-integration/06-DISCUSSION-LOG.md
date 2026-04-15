# Phase 6: Score Review & Scoreboard Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-15
**Phase:** 06-score-review-scoreboard-integration
**Areas discussed:** Review UI placement, Score-to-scoreboard mapping, Confirmation workflow, Multiple score states

---

## Review UI placement

| Option | Description | Selected |
|--------|-------------|----------|
| New 'Score Review' nav page | Dedicated fourth nav item | |
| Integrated into Status page | Show as a card/section on Status | |
| Expandable panel on Status | Collapsible panel that expands when scores are ready | ✓ |

**User's choice:** Expandable panel on Status
**Notes:** Panel auto-expands when pending scores exist, can be manually collapsed.

---

## Score-to-scoreboard mapping

### Team mode (BPL)

| Option | Description | Selected |
|--------|-------------|----------|
| Winner-take-all | Compare total left EX vs total right EX, winner gets 1 point | |
| Per-matchup scoring | Count individual left vs right matchup wins | |
| Config-driven points | 1v1 points from `team_schedule.json`; 2v2 points from EX rank | ✓ |

**User's choice:** 在组队赛模式中，每回合1V1比赛的分值应该写入比赛信息的json文件中，每回合2V2比赛根据exscore排名顺序决定，每个顺位对应一个得分。
**Notes:** A new field must be added to `team_schedule.json` for 1v1 round point values. 2v2 rounds rank 4 EX scores and map ranks to points.

### Individual mode (knockout)

| Option | Description | Selected |
|--------|-------------|----------|
| Send all 4 as one group | Send all 4 assigned cabinet scores in one `score` command | ✓ |
| Only active group | Send scores only for the currently active group | |
| Flexible | Defer mapping to implementation | |

**User's choice:** Send all 4 assigned cabinet scores as one group

---

## Confirmation workflow

### Confirm button

| Option | Description | Selected |
|--------|-------------|----------|
| One global button | Single "Confirm & Push" for all pending scores | ✓ |
| Per-cabinet buttons | Each cabinet has its own Confirm button | |
| Both | Individual confirm + global "Confirm All" | |

**User's choice:** One global "Confirm & Push" button

### Delay indication

| Option | Description | Selected |
|--------|-------------|----------|
| Countdown timer | Show exact seconds remaining before push | ✓ |
| Static message | Show "Pushing soon..." without exact time | |
| No indication | Silent auto-push after delay | |

**User's choice:** Show a countdown timer in the review panel

### Invalid score handling

| Option | Description | Selected |
|--------|-------------|----------|
| Allow with warning | Operator can confirm despite invalid scores | |
| Block until fixed | Button disabled until all invalid scores are corrected | ✓ |

**User's choice:** Disabled until all invalid scores are fixed.

---

## Multiple score states

| Option | Description | Selected |
|--------|-------------|----------|
| Queue one at a time | Show first pending score, advance after confirm | |
| Show all at once | All pending scores appear together in the panel | ✓ |
| Ignore extras | Only accept the first cabinet in score state | |

**User's choice:** Show all pending scores in the panel at once

---

## Delay configuration

| Option | Description | Selected |
|--------|-------------|----------|
| Separate `scoreboard_delay` | Dedicated field in `RuntimeState` | ✓ |
| Reuse Phase 7 delays | Share the same delay setting | |

**User's choice:** Separate setting (`scoreboard_delay` added to `RuntimeState`)

---

## Claude's Discretion

- Exact expandable panel styling and countdown timer visuals
- Warning/highlight styling for invalid scores
- Where to expose the `scoreboard_delay` input in the UI
- Internal queueing/push timing when multiple scoreboard messages are involved

---

## Deferred Ideas

- Auto-transition to `Scoreboard_web` without operator confirmation — Phase 7
- Gameplay scene source setup — Phase 4/7
- Scoreboard `init` command generation — may be split with Phase 4
