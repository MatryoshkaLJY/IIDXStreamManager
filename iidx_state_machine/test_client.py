"""TCP Client Test Program for IIDX State Machine.

Reads test events from a file and sends them to the state machine TCP server.
"""

import argparse
import json
import socket
import sys
from pathlib import Path
from typing import Optional


def send_event(sock: socket.socket, event: str) -> Optional[dict]:
    """Send a single event to the server and return the response.

    Args:
        sock: Connected TCP socket
        event: Event string to send

    Returns:
        Response dictionary or None if error
    """
    try:
        # Send event with newline
        sock.send(f"{event}\n".encode('utf-8'))

        # Receive response
        response_data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response_data += chunk

            # Try to parse as JSON (complete response)
            try:
                response_text = response_data.decode('utf-8').strip()
                # Handle possible multiple JSON objects
                for line in response_text.split('\n'):
                    if line:
                        return json.loads(line)
            except json.JSONDecodeError:
                # Continue receiving if JSON is incomplete
                continue

        return None
    except Exception as e:
        print(f"Error sending event '{event}': {e}", file=sys.stderr)
        return None


def run_test_client(
    input_file: str,
    host: str = "localhost",
    port: int = 9999,
    simple: bool = False,
    delay: float = 0.0
) -> None:
    """Run TCP client test.

    Args:
        input_file: Path to test input file
        host: Server host
        port: Server port
        simple: Use simple output format
        delay: Delay between events (seconds)
    """
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    # Connect to server
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        print(f"Connected to {host}:{port}")
    except Exception as e:
        print(f"Failed to connect to {host}:{port}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            line_num = 0
            for line in f:
                line_num += 1

                # Skip empty lines and comments
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Remove inline comments
                if '#' in line:
                    line = line.split('#')[0].strip()

                # Skip empty after comment removal
                if not line:
                    continue

                # Send event
                if simple:
                    print(f"[{line_num}] Sending: {line}", end=" -> ")
                else:
                    print(f"\n[{line_num}] Sending: {line}")

                response = send_event(sock, line)

                if response:
                    if simple:
                        state = response.get('current_state', 'N/A')
                        handled = response.get('handled', False)
                        status = "OK" if handled else "IGNORED"
                        print(f"{state} ({status})")
                    else:
                        print(json.dumps(response, indent=2, ensure_ascii=False))
                else:
                    print("No response")

                # Optional delay
                if delay > 0:
                    import time
                    time.sleep(delay)

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        sock.close()
        print("\nDisconnected")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="TCP Client Test for IIDX State Machine"
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Test input file path"
    )
    parser.add_argument(
        "-H", "--host",
        default="localhost",
        help="Server host (default: localhost)"
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=9999,
        help="Server port (default: 9999)"
    )
    parser.add_argument(
        "-s", "--simple",
        action="store_true",
        help="Simple output format"
    )
    parser.add_argument(
        "-d", "--delay",
        type=float,
        default=0.0,
        help="Delay between events in seconds (default: 0)"
    )

    args = parser.parse_args()

    run_test_client(
        input_file=args.input,
        host=args.host,
        port=args.port,
        simple=args.simple,
        delay=args.delay
    )


if __name__ == "__main__":
    main()
