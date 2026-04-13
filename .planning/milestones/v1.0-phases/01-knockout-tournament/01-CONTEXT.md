# Phase 1 Context: 16-Player Knockout Tournament Scoreboard

## Overview
Add a web-based 16-player knockout tournament scoreboard to the IIDX Stream Manager. This is a new module alongside the existing BPL team-based scoreboard, using similar visual styling but with a tree-structure layout for single-player tournaments.

## Core Requirements

### Visual Design
- **Resolution**: 1920x1080 (optimized for OBS streaming)
- **Color Scheme**: Same as `iidx_bpl_scoreboard` (Orbitron/Rajdhani fonts, cyan/pink accents, dark gradient backgrounds)
- **Layout**: Radial tree structure
  - Champion trophy at center (root node)
  - Finals: 4 players around center
  - Semifinals: 8 players (4 left side, 4 right side)
  - Quarterfinals: 16 players (8 outer left, 8 outer right)
  - Leaf nodes evenly distributed on both sides of root

### Tournament Structure
```
Quarterfinals (1/4)          Semifinals (1/2)          Finals
├─ Group A (4 players) ─┐
├─ Group B (4 players) ─┼──┐                    ┌── Champion
├─ Group C (4 players) ─┐  │                    │
├─ Group D (4 players) ─┼──┼── AB Group (4) ────┤
                         │  │                    │
                         └──┼── CD Group (4) ────┘
                            │
```

- **1/4 Finals**: 4 groups (A, B, C, D), 4 players each, top 2 advance
- **1/2 Finals**: 2 groups (AB from A/B winners, CD from C/D winners), 4 players each, top 2 advance
- **Finals**: 4 players, determine champion

### Scoring System
- Each round consists of **4 songs (sub-rounds)**
- Points awarded per song:
  - 1st place: 2 points
  - 2nd place: 1 point
  - 3rd/4th place: 0 points
- After 4 songs, top 2 by total points advance
- Tiebreaker: Higher total raw score ranks higher

### Advancement Mechanics
- **Score command**: Records player scores for current song
- **Settle command**: Finalizes the round, calculates points, determines advancement
- When settled:
  - Top 2 players advance to next stage
  - Their paths light up with persistent glow (advancing player's color)
  - Non-advancing players dimmed or marked eliminated

## Technical Decisions

### File Structure
```
iidx_knockout_scoreboard/
├── index.html          # Tournament tree visualization
├── app.js              # Tournament logic and WebSocket client
├── style.css           # Tree layout and BPL-compatible styling
└── server.py           # Dedicated WebSocket relay server
```

### Communication Protocol
**WebSocket Server**: `ws://localhost:8081` (dedicated server, separate from BPL's 8080)

**Command Format** (same structure as BPL):
```json
{
  "cmd": "command_name",
  "data": { ... }
}
```

#### 1. INIT - Initialize Tournament
```json
{
  "cmd": "init",
  "data": {
    "tournamentName": "16人淘汰赛",
    "groups": {
      "A": ["Player1", "Player2", "Player3", "Player4"],
      "B": ["Player5", "Player6", "Player7", "Player8"],
      "C": ["Player9", "Player10", "Player11", "Player12"],
      "D": ["Player13", "Player14", "Player15", "Player16"]
    }
  }
}
```

#### 2. SCORE - Record Song Scores
```json
{
  "cmd": "score",
  "data": {
    "stage": "quarterfinal",  // or "semifinal", "final"
    "group": "A",             // A, B, C, D, AB, CD
    "round": 1,               // 1-4 (which song in the round)
    "scores": [
      {"player": "Player1", "score": 980000},
      {"player": "Player2", "score": 950000},
      {"player": "Player3", "score": 920000},
      {"player": "Player4", "score": 890000}
    ]
  }
}
```
Server calculates:
- Rank based on score
- Points for this song (2/1/0/0)
- Running total points

#### 3. SETTLE - Finalize Round
```json
{
  "cmd": "settle",
  "data": {
    "stage": "quarterfinal",
    "group": "A"
  }
}
```
Effects:
- Calculate final standings
- Determine top 2 advancing players
- Light up advancement paths with persistent glow
- Advance players to next stage visualization

#### 4. RESET - Clear Tournament
```json
{
  "cmd": "reset"
}
```
Clears all data and returns to initial state.

### Visual States

#### During Active Round (Before Settlement)
- Player nodes show live raw scores
- Current rank indicator (1st, 2nd, 3rd, 4th)
- Running point total
- Paths to parent nodes: dimmed/unlit

#### After Settlement
- Advancing players: Path lights up with persistent glow
- Eliminated players: Node dimmed, "ELIMINATED" indicator
- Next stage nodes populated with advancing player names
- Champion (after Finals settle): Full path lighting + name at trophy

### Champion Presentation
When Finals are settled and champion determined:
1. Champion name displayed prominently in trophy area
2. Full progression path illuminated:
   - Quarterfinal → Semifinal path
   - Semifinal → Finals path
   - All in champion's color with glow effect

## Reusable Assets from BPL Scoreboard

### CSS Patterns (from `iidx_bpl_scoreboard/style.css`)
- Font families: `'Orbitron'`, `'Rajdhani'`
- Color variables: `--bg-dark`, `--border-glow`, `--theme-color`
- Background effects: `.bg-gradient`, `.grid-overlay`, `.glow-effect`
- Animation keyframes: `@keyframes pulse`, score update animations
- Connection status styling

### JavaScript Patterns (from `iidx_bpl_scoreboard/app.js`)
- WebSocket connection handling with reconnection
- Command dispatcher pattern (`handleCommand`)
- DOM element caching pattern
- Animation classes for state transitions

### Server Pattern (from `iidx_bpl_scoreboard/server.py`)
- `websockets` library for WebSocket server
- Client tracking with type identification
- Broadcast to all connected clients
- JSON message parsing

## Implementation Notes

### Tree Layout Algorithm
- Use absolute positioning or CSS Grid/Flexbox for tree structure
- Quarterfinal players at outer edges (left/right)
- Semifinal players in middle ring
- Finals players near center
- Champion trophy at exact center
- Connecting paths as SVG lines or CSS borders

### State Management
Client-side state structure:
```javascript
{
  tournamentName: string,
  groups: {
    A: { players: [...], scores: [...], settled: false, advancing: [] },
    B: { ... }, C: { ... }, D: { ... },
    AB: { players: [...], scores: [...], settled: false, advancing: [] },
    CD: { ... }
  },
  finals: { players: [...], scores: [...], settled: false, champion: null },
  currentStage: 'quarterfinal' | 'semifinal' | 'final'
}
```

### Path Lighting Implementation
- SVG paths connecting player nodes to parent nodes
- CSS classes for path states: `.path-dim`, `.path-lit`, `.path-champion`
- Glow effect using CSS `filter: drop-shadow()` or `box-shadow`
- Color per player - use distinct colors for each player (generate or assign)

## Deferred Ideas
- Multiple tournament format support (not just 16-player)
- Player avatar/images support
- Historical tournament data persistence
- OBS browser source auto-configuration
- Integration with existing score recognition system

## Success Criteria
- [ ] Tournament tree renders correctly with 16 players in proper positions
- [ ] WebSocket server accepts init, score, settle, reset commands
- [ ] Live scores display on player nodes during active rounds
- [ ] Settlement correctly calculates points and advances top 2
- [ ] Advancement paths light up with persistent glow
- [ ] Champion presentation shows name + full path lighting
- [ ] Visual styling matches BPL scoreboard aesthetic
- [ ] Works at 1920x1080 resolution in OBS

## References
- Existing BPL scoreboard: `iidx_bpl_scoreboard/`
- Protocol documentation: `iidx_bpl_scoreboard/PROTOCOL.md`
