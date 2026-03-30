# IIDX Game State Machine

Python implementation of IIDX game state machine with dual IO modes.

## Features

- **Dual IO Modes**: File input (debug) and TCP server (application)
- **Structured Logging**: JSON format for easy parsing
- **Variable Tracking**: Automatic counter management for arena/battle/standard/dan modes
- **Guard Conditions**: Support for conditional state transitions
- **Action System**: Trigger events on state changes

## Quick Start

### Debug Mode (File Input)

```bash
python state_machine.py -c state_machine.yaml -i test_input.txt
```

### Application Mode (TCP Server)

```bash
python state_machine.py -m tcp --host 0.0.0.0 --port 9999
```

Connect with netcat or any TCP client:
```bash
nc localhost 9999
# Then type events:
entry
modesel
await
songsel
...
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-c, --config` | YAML config file path | `state_machine.yaml` |
| `-m, --mode` | Input mode: `file` or `tcp` | `file` |
| `-i, --input` | Input file (file mode) | `input.txt` |
| `--host` | TCP host (tcp mode) | `0.0.0.0` |
| `-p, --port` | TCP port (tcp mode) | `9999` |
| `-l, --log-level` | Logging level | `INFO` |
| `-s, --simple` | Simple output format for testing | `false` |

## Input Format

### File Input
One event per line, supports comments with `#`:
```
# Start game
entry
modesel
await

# Play arena
songsel
aconfirm
play1
score
```

### TCP Input
Plain text or JSON:
```
play1
{"event": "score", "seq": 1}
```

## Output Format

### JSON Output Structure

Both file mode and TCP mode return results in the following JSON structure:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 timestamp of the event processing |
| `input` | string | The input event that was processed |
| `old_state` | string | State before processing the event |
| `current_state` | string | State after processing the event |
| `transition` | object \| null | State transition details (null if no state change) |
| `transition.from` | string | Source state of the transition |
| `transition.to` | string | Target state of the transition |
| `transition.event` | string | Event that triggered the transition |
| `actions_triggered` | array | List of action names executed |
| `variables_before` | object | Variable values before processing |
| `variables_after` | object | Variable values after processing |
| `handled` | boolean | `true` if event was processed, `false` if no transition matched |

### Variables Object

The `variables_before` and `variables_after` objects contain:

| Field | Description |
|-------|-------------|
| `arena_round` | Arena mode round counter (ar) |
| `battle_round` | Battle mode round counter (br) |
| `std_song_count` | Standard mode song count (sc) |
| `std_retry_count` | Standard mode retry count (rc) |
| `dan_song_count` | Dan mode song count (dc) |
| `blank_counter` | Consecutive blank screen counter (bc) |
| `play_type` | Play mode type: 0=none, 1=play1, 2=play2, 3=play12, 4=playd (pt) |

### Example JSON Output

**Successful state transition:**
```json
{
  "timestamp": "2026-03-30T18:34:36.781150",
  "input": "entry",
  "old_state": "IDLE",
  "transition": {
    "from": "IDLE",
    "to": "ENTRY",
    "event": "entry"
  },
  "actions_triggered": ["init_all_counters", "init_play_type"],
  "variables_before": {
    "arena_round": 0,
    "battle_round": 0,
    "std_song_count": 0,
    "std_retry_count": 0,
    "dan_song_count": 0,
    "blank_counter": 0,
    "play_type": 0
  },
  "variables_after": {
    "arena_round": 0,
    "battle_round": 0,
    "std_song_count": 0,
    "std_retry_count": 0,
    "dan_song_count": 0,
    "blank_counter": 0,
    "play_type": 0
  },
  "current_state": "ENTRY",
  "handled": true
}
```

**No transition matched (unhandled event):**
```json
{
  "timestamp": "2026-03-30T18:34:36.782123",
  "input": "invalid_event",
  "old_state": "IDLE",
  "transition": null,
  "actions_triggered": [],
  "variables_before": {
    "arena_round": 0,
    "battle_round": 0,
    "std_song_count": 0,
    "std_retry_count": 0,
    "dan_song_count": 0,
    "blank_counter": 0,
    "play_type": 0
  },
  "variables_after": {},
  "current_state": "IDLE",
  "handled": false
}
```

**No-op transition (event handled but no state change):**
```json
{
  "timestamp": "2026-03-30T18:34:37.123456",
  "input": "blank",
  "old_state": "IDLE",
  "transition": null,
  "actions_triggered": ["increment_blank_counter"],
  "variables_before": {
    "arena_round": 0,
    "battle_round": 0,
    "std_song_count": 0,
    "std_retry_count": 0,
    "dan_song_count": 0,
    "blank_counter": 0,
    "play_type": 0
  },
  "variables_after": {
    "arena_round": 0,
    "battle_round": 0,
    "std_song_count": 0,
    "std_retry_count": 0,
    "dan_song_count": 0,
    "blank_counter": 1,
    "play_type": 0
  },
  "current_state": "IDLE",
  "handled": true
}
```

### TCP Output
Same JSON format as console output, sent back to client with newline termination.

### Log Output
Structured JSON logs:
```json
{"timestamp": "2026-03-30T18:34:36,780", "level": "INFO", "logger": "IIDXStateMachine", "message": "..."}
```

### Simple Output Mode (Testing)
Use `-s` or `--simple` for compact readable output during local testing:

```bash
python state_machine.py -i test_input.txt -s
```

Output format:
```
[IDLE] --entry--> [ENTRY] | a: 0all_counters | v: ar=0, br=0, sc=0, rc=0, dc=0, bc=0
[ENTRY] --modesel--> [MODESEL] | a: - | v: ar=0, br=0, sc=0, rc=0, dc=0, bc=0
[A_SONGSEL] --aconfirm--> [A_CONFIRM] | a: +arena_round | v: ar=1, br=0, sc=0, rc=0, dc=0, bc=0
```

Abbreviations:
- `a:` = actions triggered
- `v:` = variables (ar=arena, br=battle, sc=std_song, rc=std_retry, dc=dan_song, bc=blank, pt=play_type)
- `0` prefix = init to 0
- `+` prefix = increment
- `-` = no action/state change

## State Machine Variables

| Variable | Description |
|----------|-------------|
| `arena_round` | Arena mode round counter |
| `battle_round` | Battle mode round counter |
| `std_song_count` | Standard mode song count |
| `std_retry_count` | Standard mode retry count per song |
| `dan_song_count` | Dan mode song count |
| `blank_counter` | Consecutive blank screen counter |
| `play_type` | Play mode type: 1=play1, 2=play2, 3=play12, 4=playd |

## Project Structure

```
.
├── state_machine.yaml    # State machine definition
├── state_machine.py      # Python implementation
├── test_client.py        # TCP client test program
├── CLAUDE.md            # Design documentation
├── test_input.txt       # Sample test input (arena mode)
├── test_standard.txt    # Sample test input (standard mode)
└── README.md            # This file
```

## Testing

### File Mode Test

Run arena mode test:
```bash
python state_machine.py -i test_input.txt -l DEBUG
```

Run standard mode test (with retry logic):
```bash
python state_machine.py -i test_standard.txt -l DEBUG
```

### TCP Mode Test

Start the server:
```bash
# Terminal 1: Start server
python state_machine.py -m tcp -p 9999
```

Use netcat to send events:
```bash
# Terminal 2: Send events
echo "entry" | nc localhost 9999
echo "modesel" | nc localhost 9999
```

### TCP Client Test Program

Use `test_client.py` for automated TCP testing:

```bash
# Basic usage
python test_client.py -i test_input.txt

# Connect to remote host
python test_client.py -i test_input.txt -H 192.168.1.100 -p 9999

# Simple output format
python test_client.py -i test_input.txt -s

# With delay between events (0.5 seconds)
python test_client.py -i test_blank.txt -d 0.5
```

#### TCP Client Options

| Option | Description | Default |
|--------|-------------|---------|
| `-i, --input` | Test input file (required) | - |
| `-H, --host` | Server host | `localhost` |
| `-p, --port` | Server port | `9999` |
| `-s, --simple` | Simple output format | `false` |
| `-d, --delay` | Delay between events (seconds) | `0.0` |

## Dependencies

- Python 3.8+
- PyYAML

Install dependency:
```bash
pip install pyyaml
```

## State Machine Events

| Event | Description |
|-------|-------------|
| `idle` | Attract mode/standby screen |
| `splash` | Boot splash screen (global reset) |
| `blank` | Black/blank screen |
| `entry` | Player login/logout screen |
| `modesel` | Mode selection screen |
| `await` | Arena mode waiting screen |
| `bwait` | Battle mode waiting screen |
| `songsel` | Song selection screen |
| `aconfirm` | Arena/battle confirmation screen |
| `play1/2/12/d` | Gameplay screens |
| `score` | Score display screen |
| `interlude` | Interlude/transition screen |
| `death` | Stage failed screen |
| ... | ... |

See `CLAUDE.md` for complete state and event documentation.
