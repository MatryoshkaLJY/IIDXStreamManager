"""IIDX Game State Machine Implementation.

Supports two IO modes:
- Debug mode: File input → Console output
- Application mode: TCP server input/output
"""

import json
import logging
import socket
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

import yaml


@dataclass
class State:
    """State definition."""
    id: str
    description: str = ""
    is_initial: bool = False


@dataclass
class Transition:
    """Transition definition."""
    from_state: str
    to_state: Optional[str]  # None means no state change
    events: List[str]  # Multiple events supported
    guards: List[Dict[str, Any]]
    actions: List[str]


@dataclass
class Variable:
    """Variable definition."""
    name: str
    description: str
    var_type: str
    initial_value: Any
    scope: str


class IIDXStateMachine:
    """IIDX Game State Machine.

    Supports file input (debug) and TCP server (application) modes.
    Outputs structured JSON logs.
    """

    def __init__(self, config_path: str, log_level: str = "INFO", simple_mode: bool = False):
        """Initialize state machine.

        Args:
            config_path: Path to YAML configuration file
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            simple_mode: Enable simple output format for local testing
        """
        self.config_path = Path(config_path)
        self.simple_mode = simple_mode
        self.states: Dict[str, State] = {}
        self.transitions: List[Transition] = []
        self.variables: Dict[str, Any] = {}
        self.variable_defs: Dict[str, Variable] = {}
        self.actions: Set[str] = set()
        self.events: Set[str] = set()

        self.current_state: str = ""
        self.blank_counter: int = 0

        # Setup logging
        self._setup_logging(log_level)

        # Load configuration
        self._load_config()

        # Initialize state
        self._reset_state()

        self.logger.info(f"State machine initialized. Current state: {self.current_state}")

    def _setup_logging(self, log_level: str) -> None:
        """Setup logger with JSON formatter."""
        self.logger = logging.getLogger("IIDXStateMachine")
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Clear existing handlers
        self.logger.handlers.clear()

        # Console handler with custom formatter
        handler = logging.StreamHandler()
        formatter = JsonLogFormatter()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _load_config(self) -> None:
        """Load YAML configuration."""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Load states
        for state_data in config.get('states', []):
            state = State(
                id=state_data['id'],
                description=state_data.get('description', ''),
                is_initial=state_data.get('is_initial', False)
            )
            self.states[state.id] = state
            if state.is_initial:
                self.current_state = state.id

        # Load variables
        for var_data in config.get('variables', []):
            var = Variable(
                name=var_data['name'],
                description=var_data.get('description', ''),
                var_type=var_data.get('type', 'integer'),
                initial_value=var_data.get('initial_value', 0),
                scope=var_data.get('scope', 'global')
            )
            self.variable_defs[var.name] = var
            self.variables[var.name] = var.initial_value

        # Load events
        self.events = set(config.get('events', []))

        # Load actions
        for action_data in config.get('actions', []):
            self.actions.add(action_data['name'])

        # Load transitions
        for trans_data in config.get('transitions', []):
            events = trans_data['event']
            if not isinstance(events, list):
                events = [events]

            transition = Transition(
                from_state=trans_data['from'],
                to_state=trans_data.get('to'),
                events=events,
                guards=trans_data.get('guards', []),
                actions=trans_data.get('actions', [])
            )
            self.transitions.append(transition)

        self.logger.debug(f"Loaded {len(self.states)} states, {len(self.transitions)} transitions")

    def _reset_state(self) -> None:
        """Reset state machine to initial state."""
        for state in self.states.values():
            if state.is_initial:
                self.current_state = state.id
                break

        # Reset all variables
        for var_name, var_def in self.variable_defs.items():
            self.variables[var_name] = var_def.initial_value

        self.blank_counter = 0

    def _init_all_counters(self) -> None:
        """Initialize all mode counters to 0."""
        counter_vars = ['arena_round', 'battle_round', 'std_song_count',
                       'std_retry_count', 'dan_song_count']
        for var in counter_vars:
            if var in self.variables:
                self.variables[var] = 0
        self.logger.debug(f"All counters initialized: {self._get_counter_values()}")

    def _init_arena_round(self) -> None:
        """Initialize arena_round to 0."""
        self.variables['arena_round'] = 0

    def _increment_arena_round(self) -> None:
        """Increment arena_round by 1."""
        self.variables['arena_round'] += 1

    def _init_battle_round(self) -> None:
        """Initialize battle_round to 0."""
        self.variables['battle_round'] = 0

    def _increment_battle_round(self) -> None:
        """Increment battle_round by 1."""
        self.variables['battle_round'] += 1

    def _init_std_song_count(self) -> None:
        """Initialize std_song_count to 0."""
        self.variables['std_song_count'] = 0

    def _increment_std_song_count(self) -> None:
        """Increment std_song_count by 1."""
        self.variables['std_song_count'] += 1

    def _init_std_retry_count(self) -> None:
        """Initialize std_retry_count to 0."""
        self.variables['std_retry_count'] = 0

    def _increment_std_retry_count(self) -> None:
        """Increment std_retry_count by 1."""
        self.variables['std_retry_count'] += 1

    def _init_dan_song_count(self) -> None:
        """Initialize dan_song_count to 0."""
        self.variables['dan_song_count'] = 0

    def _increment_dan_song_count(self) -> None:
        """Increment dan_song_count by 1."""
        self.variables['dan_song_count'] += 1

    def _reset_blank_counter(self) -> None:
        """Reset blank_counter to 0."""
        self.blank_counter = 0

    def _increment_blank_counter(self) -> None:
        """Increment blank_counter by 1."""
        self.blank_counter += 1

    def _init_play_type(self) -> None:
        """Initialize play_type to 0."""
        self.variables['play_type'] = 0

    def _set_play_type_1(self) -> None:
        """Set play_type to 1 (play1)."""
        self.variables['play_type'] = 1

    def _set_play_type_2(self) -> None:
        """Set play_type to 2 (play2)."""
        self.variables['play_type'] = 2

    def _set_play_type_3(self) -> None:
        """Set play_type to 3 (play12)."""
        self.variables['play_type'] = 3

    def _set_play_type_4(self) -> None:
        """Set play_type to 4 (playd)."""
        self.variables['play_type'] = 4

    def _get_action_handler(self, action_name: str) -> Optional[Callable[[], None]]:
        """Get action handler by name."""
        action_map = {
            'init_all_counters': self._init_all_counters,
            'init_arena_round': self._init_arena_round,
            'increment_arena_round': self._increment_arena_round,
            'init_battle_round': self._init_battle_round,
            'increment_battle_round': self._increment_battle_round,
            'init_std_song_count': self._init_std_song_count,
            'increment_std_song_count': self._increment_std_song_count,
            'init_std_retry_count': self._init_std_retry_count,
            'increment_std_retry_count': self._increment_std_retry_count,
            'init_dan_song_count': self._init_dan_song_count,
            'increment_dan_song_count': self._increment_dan_song_count,
            'reset_blank_counter': self._reset_blank_counter,
            'increment_blank_counter': self._increment_blank_counter,
            'init_play_type': self._init_play_type,
            'set_play_type_1': self._set_play_type_1,
            'set_play_type_2': self._set_play_type_2,
            'set_play_type_3': self._set_play_type_3,
            'set_play_type_4': self._set_play_type_4,
            # Event actions - these are logged but don't change state
            'enter_play_mode': lambda: None,
            'exit_play_mode': lambda: None,
            'get_score': lambda: None,
            'inform_dan_pass': lambda: None,
            'inform_dan_fail': lambda: None,
        }
        return action_map.get(action_name)

    def _execute_action(self, action_name: str) -> None:
        """Execute action by name."""
        handler = self._get_action_handler(action_name)
        if handler:
            handler()
            self.logger.debug(f"Action executed: {action_name}")
        else:
            self.logger.warning(f"Unknown action: {action_name}")

    def _check_guard(self, guard: Dict[str, Any]) -> bool:
        """Check if guard condition is satisfied.

        Args:
            guard: Guard definition dictionary

        Returns:
            True if guard passes, False otherwise
        """
        guard_type = guard.get('type')

        if guard_type == 'not_in_states':
            excluded_states = guard.get('states', [])
            return self.current_state not in excluded_states

        elif guard_type == 'blank_counter_exceeded':
            threshold = guard.get('threshold', 5)
            return self.blank_counter >= threshold

        elif guard_type == 'blank_counter_not_exceeded':
            threshold = guard.get('threshold', 5)
            return self.blank_counter < threshold

        elif guard_type == 'not_blank_event':
            # This guard is used for non-blank events to reset counter
            return True

        else:
            self.logger.warning(f"Unknown guard type: {guard_type}")
            return True

    def _find_transition(self, event: str) -> Optional[Transition]:
        """Find applicable transition for current state and event.

        Args:
            event: Input event

        Returns:
            Matching transition or None
        """
        candidates = []

        for trans in self.transitions:
            # Check event match
            if event not in trans.events and '*' not in trans.events:
                continue

            # Check state match
            if trans.from_state != '*' and trans.from_state != self.current_state:
                continue

            # Check guards
            if trans.guards:
                all_guards_pass = all(self._check_guard(g) for g in trans.guards)
                if not all_guards_pass:
                    continue

            candidates.append(trans)

        # Priority: specific state > wildcard state
        # Within same priority, first match wins
        specific = [t for t in candidates if t.from_state != '*']
        if specific:
            return specific[0]

        wildcard = [t for t in candidates if t.from_state == '*']
        if wildcard:
            return wildcard[0]

        return None

    def _get_counter_values(self) -> Dict[str, Any]:
        """Get current counter variable values."""
        counters = ['arena_round', 'battle_round', 'std_song_count',
                   'std_retry_count', 'dan_song_count', 'blank_counter', 'play_type']
        return {k: self.variables.get(k, self.blank_counter if k == 'blank_counter' else 0)
                for k in counters}

    def process_event(self, event: str) -> Dict[str, Any]:
        """Process a single event.

        Args:
            event: Input event string

        Returns:
            Result dictionary with transition details
        """
        old_state = self.current_state

        # Reset blank counter on non-blank events
        if event != 'blank' and self.blank_counter > 0:
            self._reset_blank_counter()
            self.logger.debug(f"Blank counter reset due to non-blank event: {event}")

        # Find applicable transition
        transition = self._find_transition(event)

        result = {
            "timestamp": self._get_timestamp(),
            "input": event,
            "old_state": old_state,
            "transition": None,
            "actions_triggered": [],
            "variables_before": self._get_counter_values(),
            "variables_after": {},
            "current_state": old_state,
            "handled": False
        }

        if transition is None:
            return result

        # Check if this is a no-op transition (to_state is None)
        if transition.to_state is None:
            # Execute actions but keep state
            for action in transition.actions:
                if isinstance(action, dict):
                    action_name = action.get('type', '')
                else:
                    action_name = action
                self._execute_action(action_name)
                result["actions_triggered"].append(action_name)

            result["current_state"] = self.current_state
            result["variables_after"] = self._get_counter_values()
            result["handled"] = True

            self._log_transition(result)
            return result

        # Execute transition
        self.current_state = transition.to_state
        result["current_state"] = self.current_state

        # Execute actions
        for action in transition.actions:
            if isinstance(action, dict):
                action_name = action.get('type', '')
            else:
                action_name = action
            self._execute_action(action_name)
            result["actions_triggered"].append(action_name)

        result["transition"] = {
            "from": old_state,
            "to": transition.to_state,
            "event": event
        }
        result["variables_after"] = self._get_counter_values()
        result["handled"] = True

        self._log_transition(result)
        return result

    def _get_timestamp(self) -> str:
        """Get current ISO format timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()

    def _log_transition(self, result: Dict[str, Any]) -> None:
        """Log transition in JSON format."""
        log_data = {
            "timestamp": result["timestamp"],
            "event": result["input"],
            "state_change": {
                "from": result["old_state"],
                "to": result["current_state"]
            } if result["old_state"] != result["current_state"] else None,
            "actions": result["actions_triggered"],
            "variables": result["variables_after"]
        }

        if result.get("error"):
            log_data["error"] = result["error"]
            self.logger.warning(json.dumps(log_data, ensure_ascii=False))
        else:
            self.logger.info(json.dumps(log_data, ensure_ascii=False))

    def run_file_mode(self, input_path: str) -> None:
        """Run in file input mode (debug mode).

        Args:
            input_path: Path to input file (one event per line)
        """
        input_file = Path(input_path)
        mode_str = "SIMPLE" if self.simple_mode else "JSON"
        self.logger.info(f"Starting file mode ({mode_str}) with input: {input_file}")

        with open(input_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                # Skip empty lines and comments
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Remove inline comments
                if '#' in line:
                    line = line.split('#')[0].strip()

                self.logger.debug(f"Processing line {line_num}: {line}")
                result = self.process_event(line)

                # Print result to console
                if self.simple_mode:
                    print(self._format_simple_output(result))
                else:
                    print(json.dumps(result, indent=2, ensure_ascii=False))

        self.logger.info("File mode completed")

    def _format_simple_output(self, result: Dict[str, Any]) -> str:
        """Format result in simple readable format.

        Args:
            result: Result dictionary from process_event

        Returns:
            Simple formatted string
        """
        old_state = result["old_state"]
        new_state = result["current_state"]
        event = result["input"]
        actions = result.get("actions_triggered", [])
        vars_after = result.get("variables_after", {})

        # Format state transition
        if old_state != new_state:
            state_str = f"[{old_state}] --{event}--> [{new_state}]"
        else:
            state_str = f"[{new_state}] --{event}--> (no change)"

        # Format actions (abbreviated)
        if actions:
            # Abbreviate common action names
            abbrev_actions = []
            for a in actions:
                if a == 'enter_play_mode':
                    abbrev_actions.append('enter_play')
                elif a == 'exit_play_mode':
                    abbrev_actions.append('exit_play')
                elif a.startswith('increment_'):
                    abbrev_actions.append(a.replace('increment_', '+'))
                elif a.startswith('init_'):
                    abbrev_actions.append(a.replace('init_', '0'))
                else:
                    abbrev_actions.append(a)
            action_str = f"a: {', '.join(abbrev_actions)}"
        else:
            action_str = "a: -"

        # Format variables (abbreviated)
        vars_short = []
        if vars_after:
            for k, v in vars_after.items():
                if k == 'arena_round':
                    vars_short.append(f"ar={v}")
                elif k == 'battle_round':
                    vars_short.append(f"br={v}")
                elif k == 'std_song_count':
                    vars_short.append(f"sc={v}")
                elif k == 'std_retry_count':
                    vars_short.append(f"rc={v}")
                elif k == 'dan_song_count':
                    vars_short.append(f"dc={v}")
                elif k == 'blank_counter':
                    vars_short.append(f"bc={v}")
                elif k == 'play_type':
                    vars_short.append(f"pt={v}")
        var_str = f"v: {', '.join(vars_short)}" if vars_short else "v: -"

        return f"{state_str} | {action_str} | {var_str}"

    def run_tcp_mode(self, host: str = "0.0.0.0", port: int = 9999) -> None:
        """Run in TCP server mode (application mode).

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        self.logger.info(f"Starting TCP server on {host}:{port}")

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen(5)

        self.logger.info(f"Server listening on {host}:{port}")

        try:
            while True:
                client, addr = server.accept()
                self.logger.info(f"Client connected from {addr}")

                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self._handle_tcp_client,
                    args=(client, addr)
                )
                client_thread.daemon = True
                client_thread.start()

        except KeyboardInterrupt:
            self.logger.info("Server shutting down...")
        finally:
            server.close()

    def _handle_tcp_client(self, client: socket.socket, addr: tuple) -> None:
        """Handle TCP client connection.

        Args:
            client: Client socket
            addr: Client address tuple
        """
        try:
            buffer = ""
            while True:
                data = client.recv(1024).decode('utf-8')
                if not data:
                    break

                buffer += data

                # Process complete lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()

                    if not line:
                        continue

                    # Handle JSON or plain text input
                    try:
                        json_input = json.loads(line)
                        event = json_input.get('event', '')
                    except json.JSONDecodeError:
                        event = line

                    if event:
                        result = self.process_event(event)
                        response = json.dumps(result, ensure_ascii=False) + '\n'
                        client.send(response.encode('utf-8'))

        except ConnectionResetError:
            self.logger.info(f"Client {addr} disconnected")
        except Exception as e:
            self.logger.error(f"Error handling client {addr}: {e}")
        finally:
            client.close()
            self.logger.info(f"Client {addr} connection closed")


class JsonLogFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }

        # Add extra fields if present
        if hasattr(record, 'extra'):
            log_data.update(record.extra)

        return json.dumps(log_data, ensure_ascii=False)


class IIDXStateMachineManager:
    """Manager for multiple IIDXStateMachine instances.

    Each machine (cabinet) gets its own isolated state machine,
    allowing concurrent tracking of multiple game sessions.
    """

    def __init__(self, config_path: str, log_level: str = "INFO", simple_mode: bool = False):
        """Initialize the manager.

        Args:
            config_path: Path to YAML configuration file
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            simple_mode: Enable simple output format for local testing
        """
        self.config_path = config_path
        self.log_level = log_level
        self.simple_mode = simple_mode
        self.machines: Dict[str, IIDXStateMachine] = {}

    def add_machine(self, machine_id: str) -> None:
        """Add a new machine state tracker."""
        if machine_id in self.machines:
            raise ValueError(f"Machine '{machine_id}' already exists")
        self.machines[machine_id] = IIDXStateMachine(
            self.config_path, self.log_level, self.simple_mode
        )

    def remove_machine(self, machine_id: str) -> None:
        """Remove a machine state tracker."""
        if machine_id in self.machines:
            del self.machines[machine_id]

    def process_event(self, machine_id: str, event: str) -> Dict[str, Any]:
        """Process an event for a specific machine.

        Args:
            machine_id: Machine identifier
            event: Input event string

        Returns:
            Result dictionary with machine_id injected
        """
        if machine_id not in self.machines:
            raise ValueError(f"Machine '{machine_id}' not found")
        result = self.machines[machine_id].process_event(event)
        result["machine_id"] = machine_id
        return result

    def get_machine_state(self, machine_id: str) -> Dict[str, Any]:
        """Get current state info for a specific machine.

        Args:
            machine_id: Machine identifier

        Returns:
            Dictionary with current_state, variables, and blank_counter
        """
        if machine_id not in self.machines:
            raise ValueError(f"Machine '{machine_id}' not found")
        sm = self.machines[machine_id]
        return {
            "machine_id": machine_id,
            "current_state": sm.current_state,
            "variables": sm.variables.copy(),
            "blank_counter": sm.blank_counter,
        }

    def list_machines(self) -> List[str]:
        """Return list of registered machine IDs."""
        return list(self.machines.keys())


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="IIDX State Machine")
    parser.add_argument("--config", "-c", default="state_machine.yaml",
                       help="Path to state machine YAML config")
    parser.add_argument("--mode", "-m", choices=["file", "tcp"], default="file",
                       help="Input mode: file or tcp")
    parser.add_argument("--input", "-i", help="Input file path (for file mode)")
    parser.add_argument("--host", default="0.0.0.0", help="TCP host (for tcp mode)")
    parser.add_argument("--port", "-p", type=int, default=9999, help="TCP port")
    parser.add_argument("--log-level", "-l", default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level")
    parser.add_argument("--simple", "-s", action="store_true",
                       help="Enable simple output format for local testing")

    args = parser.parse_args()

    # Create state machine
    sm = IIDXStateMachine(args.config, args.log_level, args.simple)

    # Run in selected mode
    if args.mode == "file":
        input_file = args.input or "input.txt"
        sm.run_file_mode(input_file)
    else:
        sm.run_tcp_mode(args.host, args.port)


if __name__ == "__main__":
    main()
