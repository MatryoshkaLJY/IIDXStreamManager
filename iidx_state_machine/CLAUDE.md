# IIDX Game State Machine

## Overview

This state machine manages the game flow of beatmania IIDX, tracking transitions between different game states based on screen recognition events.

## States (33 total)

### Core States
| State | Description |
|-------|-------------|
| IDLE | Cabinet is idle, showing attract mode (initial state) |
| ENTRY | Player has entered the game, showing entry animation |
| MODESEL | Game entered mode selection |
| LOGOUT | Player has exited the game, showing logout animation |

### Arena Mode States (A_*)
| State | Description |
|-------|-------------|
| A_WAIT | Player is waiting for arena game to start |
| A_SONGSEL | Player is selecting song for arena game |
| A_CONFIRM | Player is confirming song for arena/battle game |
| A_PLAY | Player is playing arena/battle game |
| A_SCORE | Player is viewing score for an arena/battle round |
| A_INTER | Player is in interlude between arena/battle rounds |
| A_RANK | Player is viewing rank for arena game |
| A_SUM | Player is viewing summary for arena game |

### Battle Mode States (B_*)
| State | Description |
|-------|-------------|
| B_WAIT | Player is waiting for battle game to start |
| B_MODESEL | Player is selecting mode for battle game |
| B_SONGSEL | Player is selecting song for battle game |
| B_CONFIRM | Player is confirming song for a battle game |
| B_PLAY | Player is playing a battle game |
| B_SCORE | Player is viewing score for a battle round |
| B_INTER | Player is in interlude between battle rounds |
| B_RANK | Player is viewing rank for battle game |

### Standard Mode States (S_*)
| State | Description |
|-------|-------------|
| S_SONGSEL | Player is selecting song for standard game |
| S_PLAY | Player is playing standard game |
| S_SCORE | Player is viewing score for standard game |
| S_DEATH | Player has failed a song in standard game |
| S_INTER | Player is in interlude between songs in standard game |

### Dan Mode States (D_*)
| State | Description |
|-------|-------------|
| D_SEL | Player is selecting Dan course |
| D_PLAY | Player is playing Dan course |
| D_SCORE_S | Player is viewing score after completing a song |
| D_SCORE_D | Player is viewing score after failing a song |
| D_DEATH | Player has failed a song in Dan course |
| D_INTER_S | Interlude after completing a song in Dan course |
| D_INTER_D | Interlude after failing a song in Dan course |
| D_RANK | Player is viewing rank for Dan course |

## Events (27 total)

| Event | Description |
|-------|-------------|
| idle | Attract mode/standby screen |
| splash | Boot splash screen |
| blank | Black/blank screen |
| entry | Player login/logout screen |
| pay | Payment/credit screen |
| interlude | Interlude/transition screen |
| modesel | Mode selection screen |
| dansel | Dan course selection screen |
| songsel | Song selection screen |
| confirm | Song confirmation screen |
| play1 | 1P gameplay screen |
| play2 | 2P gameplay screen |
| play12 | Versus gameplay screen (1P vs 2P) |
| playd | Double play (DP) mode gameplay screen |
| bwait | Battle mode waiting screen |
| bsel | Battle mode selection screen |
| brank | Battle mode ranking screen |
| death | Stage failed screen |
| score | Stage result/score screen |
| danscore | Dan course result screen |
| lab | Event mode screen |
| others | Other/miscellaneous screens |
| await | Arena mode waiting screen |
| aconfirm | Arena mode confirmation screen |
| arank | Arena mode ranking screen |
| asum | Arena mode summary screen |
| set | Settings screen |

## State Transitions

### Core Flow
```
IDLE --entry--> ENTRY --modesel--> MODESEL
LOGOUT --blank--> IDLE
```

### Arena Mode Flow
```
MODESEL --await--> A_WAIT --songsel--> A_SONGSEL --aconfirm--> A_CONFIRM
  --[play1/play2/play12/playd]--> A_PLAY --score--> A_SCORE --interlude--> A_INTER
  --arank--> A_RANK --asum--> A_SUM --entry--> LOGOUT

# Loop paths
A_PLAY --interlude--> A_INTER --aconfirm--> A_CONFIRM
```

### Battle Mode Flow
```
MODESEL --bwait--> B_WAIT --bsel--> B_MODESEL --songsel--> B_SONGSEL
  --aconfirm--> B_CONFIRM --[play1/play2/play12/playd]--> B_PLAY --score--> B_SCORE
  --interlude--> B_INTER --brank--> B_RANK --entry--> LOGOUT

# Loop paths
B_PLAY --interlude--> B_INTER --aconfirm--> B_CONFIRM
```

### Standard Mode Flow
```
MODESEL --songsel--> S_SONGSEL --[play1/play2/play12/playd]--> S_PLAY

# Normal path
S_PLAY --interlude--> S_INTER --entry--> LOGOUT

# Score path
S_PLAY --score--> S_SCORE --interlude--> S_INTER --[play]--> S_PLAY

# Death paths
S_PLAY --death--> S_DEATH
S_DEATH --[play]--> S_PLAY
S_DEATH --score--> S_SCORE
S_DEATH --interlude--> S_INTER
```

### Dan Mode Flow
```
MODESEL --dansel--> D_SEL --[play]--> D_PLAY

# Success path
D_PLAY --interlude--> D_INTER_S --danscore--> D_RANK --entry--> LOGOUT
D_PLAY --score--> D_SCORE_S --interlude--> D_INTER_S
D_INTER_S --[play]--> D_PLAY

# Death path
D_PLAY --death--> D_DEATH --interlude--> D_INTER_D
D_DEATH --score--> D_SCORE_D --interlude--> D_INTER_D
D_INTER_D --danscore--> D_RANK
```

### Global Transitions
- `* --splash--> IDLE` - Any state can reset to IDLE on splash event (game restart)

## Design Notes

1. **Multi-play Events**: The four play events `[play1, play2, play12, playd]` are interchangeable for gameplay transitions
2. **Dan Mode Score Split**: D_SCORE is split into D_SCORE_S (success) and D_SCORE_D (death) for proper flow tracking
3. **Loop Paths**: Arena/Battle/Standard modes support loop paths for continuous play sessions
4. **Global Reset**: Splash event acts as a global reset to IDLE state
