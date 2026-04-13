# STATE

## Project Reference

**Project**: IIDX Tournament Auto-Director  
**Core Value**: Unify monitoring, scene automation, and scoreboard integration into a single Python web application so the tournament stream operator can run a full round with minimal manual intervention.

## Current Position

**Current Phase**: 1 — Foundation & Config  
**Current Plan**: TBD  
**Status**: Not started  
**Progress**: 0/6 phases

```
[          ] 0%
```

## Performance Metrics

- **Requirements completed**: 0/14
- **Phases completed**: 0/6
- **Last milestone**: —

## Accumulated Context

### Decisions
- Flask on port 5002 (operator preference, avoids conflict with web_monitor.py on 5001)
- Reuse `obs_manager.py` as a library for frame capture and recognition
- One mode per event (simplifies UI and state management)
- Delays configurable including `-1` for fully manual advance

### TODOs
- [ ] Build Flask app shell with SocketIO
- [ ] Implement JSON config loading with Pydantic validation
- [ ] Add runtime state persistence
- [ ] Build round-prep UI for mode selection and player assignment
- [ ] Integrate OBS WebSocket for scene switching
- [ ] Implement 4-cabinet polling thread
- [ ] Build live monitor UI
- [ ] Implement scene automation rules
- [ ] Build score review UI with editing
- [ ] Integrate scoreboard push (BPL 8080, knockout 8081)
- [ ] Add configurable timing delays

### Blockers
- None

## Session Continuity

**Last action**: Roadmap created  
**Next expected action**: `/gsd-plan-phase 1`
