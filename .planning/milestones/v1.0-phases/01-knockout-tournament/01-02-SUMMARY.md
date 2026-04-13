# Phase 1 Plan 02: WebSocket Server and Client Summary

## Overview
Created the WebSocket communication layer for the 16-player knockout tournament scoreboard.

## Files Created

### 1. iidx_knockout_scoreboard/server.py
WebSocket relay server running on port 8081.

**Features:**
- Imports: asyncio, websockets, json
- Client tracking: `clients = {}` mapping websocket to {id, type}
- Handler function with:
  - Auto-assigns client_id on connect
  - Parses JSON messages
  - Identifies controller clients (commands: init, score, settle, reset)
  - Broadcasts messages to all other connected clients
  - Graceful disconnect handling
- Main function: serves on localhost:8081
- Entry point with KeyboardInterrupt handling

### 2. iidx_knockout_scoreboard/app.js
Tournament client application with WebSocket communication.

**Features:**
- `TournamentApp` class with:
  - wsUrl: 'ws://localhost:8081'
  - reconnectInterval: 3000ms
  - tournamentState object with groups A, B, C, D, AB, CD and finals
- `connectWebSocket()` method:
  - Creates WebSocket connection
  - onopen: updates status to 'connected'
  - onmessage: parses JSON and calls handleCommand
  - onclose: updates status, schedules reconnection after 3 seconds
  - onerror: logs error, updates status
- `updateConnectionStatus(status)` method:
  - Updates statusDot class
  - Updates statusText (已连接, 连接中..., 离线, 连接错误)
- Command dispatcher `handleCommand(message)`:
  - switch on cmd: init, score, settle, reset
  - Calls appropriate handler method
- Stub handlers: handleInit, handleScore, handleSettle, handleReset
- DOM helper methods:
  - `getPlayerNode(group, position)` - query by data attributes
  - `getPath(from, to)` - query SVG paths
  - `updatePlayerNode(group, position, data)` - update name, score, points, rank
  - `setPlayerState(group, position, state)` - add/remove active/eliminated/advancing classes
  - `lightPath(from, to, isChampion)` - add lit/champion-path classes

## Verification Checklist
- [x] server.py runs on port 8081
- [x] app.js connects to ws://localhost:8081
- [x] Command dispatcher handles init, score, settle, reset
- [x] Reconnection logic with 3-second interval
- [x] Connection status UI updates correctly
- [x] DOM helper methods exist

## Technical Notes
- Server runs on port 8081 (separate from BPL's 8080)
- Follows same patterns as iidx_bpl_scoreboard reference implementation
- Client state structure supports all tournament stages: quarterfinals (A, B, C, D), semifinals (AB, CD), and finals
- DOM helpers use data attributes for element selection (data-group, data-position, data-path)
