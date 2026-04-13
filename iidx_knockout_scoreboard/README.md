# IIDX Knockout Tournament Scoreboard

A WebSocket-driven browser scoreboard for 16-player knockout tournaments, designed for OBS browser sources at 1920x1080.

## File Structure

- `index.html` + `style.css` + `app.js` — Browser scoreboard frontend
- `server.py` — Python WebSocket relay server (port 8081)
- `testbench.py` — Python testbench for automated/manual testing

## Quick Start

1. **Start the relay server**
   ```bash
   python server.py
   ```

2. **Open the scoreboard in a browser**
   Open `index.html` directly in a browser (or add as an OBS Browser Source).
   The page will auto-connect to `ws://localhost:8081`.

3. **Send commands**
   Use any WebSocket client, or run the included testbench:
   ```bash
   # Full automated run (A → B → C → D → E → F → Finals)
   python testbench.py

   # Finals tiebreaker scenario
   python testbench.py -s tiebreaker

   # Finals no-tie scenario
   python testbench.py -s notie

   # Interactive manual mode
   python testbench.py -s manual
   ```

## WebSocket Command Protocol

All commands are JSON messages broadcasted to `ws://localhost:8081`.

### 1. INIT — Initialize tournament
```json
{
  "cmd": "init",
  "data": {
    "tournamentName": "16人淘汰赛",
    "groups": {
      "A": ["A1", "A2", "A3", "A4"],
      "B": ["B1", "B2", "B3", "B4"],
      "C": ["C1", "C2", "C3", "C4"],
      "D": ["D1", "D2", "D3", "D4"]
    }
  }
}
```
- Only groups A–D are provided; E, F, and finals are populated automatically as the tournament progresses.
- After `init`, only **Group A** is highlighted as active, and the stage indicator shows `1/4决赛 第一场`.

### 2. SCORE — Record round scores
```json
{
  "cmd": "score",
  "data": {
    "stage": "quarterfinal",
    "group": "A",
    "round": 1,
    "scores": [
      {"player": "A1", "score": 990000},
      {"player": "A2", "score": 980000},
      {"player": "A3", "score": 970000},
      {"player": "A4", "score": 960000}
    ]
  }
}
```
- For **A–F groups**, scores **accumulate** across rounds and the display shows total raw score.
- For the **finals**, only the **current round score** is displayed (not accumulated), but PTs are awarded normally.
- **Auto-settle**: For A–F groups, once 4 rounds of `score` are received, the group **automatically settles**.

### 3. SETTLE — Manually finalize a round
```json
{
  "cmd": "settle",
  "data": {
    "stage": "quarterfinal",
    "group": "A"
  }
}
```
- Usually not needed for A–F groups because of auto-settle, but can be sent explicitly.
- **Required for finals** because finals do not auto-settle.
- After settle:
  - A–F: top 2 advance with strong green glow; bottom 2 turn red/eliminated.
  - The stage indicator does **not** change yet.

### 4. CONTINUE — Advance to the next stage
```json
{
  "cmd": "continue"
}
```
- Moves the active highlight to the next group in sequence:
  `A → B → C → D → E → F → finals`
- When leaving a group, the previous group’s advancing players **dim** from strong green glow to weak green.
- The **stage indicator** updates automatically, e.g.:
  - A: `1/4决赛 第一场`
  - B: `1/4决赛 第二场`
  - ...
  - E: `半决赛 第一场`
  - F: `半决赛 第二场`
  - finals: `决赛`

### 5. RESET — Clear everything
```json
{
  "cmd": "reset"
}
```
- Resets all players, scores, stages, medals, and champion/second/third glow effects.

## Finals & Tiebreaker Rules

### Normal Finals
- Finals sort by **PT only** (scores are not accumulated).
- After `settle`, if there are **no PT ties**, medals are assigned immediately:
  - 1st: `🥇` + gold glow
  - 2nd: `🥈` + silver glow
  - 3rd: `🥉` + bronze glow
  - 4th: empty

### Tiebreaker
- If there is a **PT tie**, only the tied players remain **active** and enter the tiebreaker.
- Players whose ranks are **already determined** receive their medals immediately (e.g., `8pt, 4pt, 0pt, 0pt` → 1st/2nd get 🥇🥈, bottom 2 tiebreak).
- During tiebreaker rounds, send `score` with `"stage": "final"`. In tiebreaker mode:
  - **No PTs are awarded**.
  - Only the **tiebreaker score accumulates**.
- After tiebreaker rounds, send `settle` again to resolve ties by accumulated tiebreaker score and assign remaining medals.

## Advancement Mapping

### Quarterfinals → Semifinals
| Group | #1 → | #2 → |
|-------|------|------|
| A | E-0 | F-0 |
| B | F-1 | E-1 |
| C | F-2 | E-2 |
| D | E-3 | F-3 |

### Semifinals → Finals
| Group | #1 → | #2 → |
|-------|------|------|
| E | finals-0 | finals-1 |
| F | finals-2 | finals-3 |

## Testbench Scenarios

```bash
python testbench.py -s auto        # Full A→B→C→D→E→F→Finals flow
python testbench.py -s tiebreaker  # Finals with partial tie (8/4/0/0)
python testbench.py -s notie       # Finals with clean medal assignment
python testbench.py -s manual      # Interactive command prompt
```

### Manual Mode Shortcuts
- `a1`–`d4` — auto-send 4 rounds for a quarterfinal group
- `e1`–`f4` — auto-send 4 rounds for a semifinal group
- `final` — auto-send 4 finals rounds + settle
- `tie` — run the tiebreaker scenario
- `continue`, `reset`, `init` — direct commands

## OBS Setup

- Resolution: **1920×1080**
- Source: **Browser Source**
- URL: `file:///path/to/index.html` (or serve via local HTTP)
- No build step or bundler required — plain HTML/CSS/JS.
