#!/usr/bin/env python3
"""
BPL Scoreboard WebSocket Relay Server

Relays messages between testbench and browser clients.
"""

import asyncio
import websockets
import json
import os

# Store connected clients
clients = {}
HOST = os.environ.get("IIDX_RELAY_HOST", "127.0.0.1")


async def handler(websocket):
    """Handle WebSocket connections"""
    client_id = f"client-{len(clients)}"
    clients[websocket] = {
        'id': client_id,
        'type': 'unknown'
    }

    print(f"\n[connect] [{client_id}] Client connected (total: {len(clients)})")
    print(f"   Remote: {websocket.remote_address}")

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                cmd = data.get('cmd', 'unknown')

                # Try to identify client type from message
                if cmd == 'init':
                    clients[websocket]['type'] = 'testbench'
                elif cmd in ('score', 'reset'):
                    clients[websocket]['type'] = 'testbench'

                client_type = clients[websocket]['type']
                print(f"\n[recv] [{client_id}/{client_type}] Received: {cmd}")

                # Broadcast to all other clients
                broadcast_count = 0
                for client, info in list(clients.items()):
                    if client != websocket:
                        try:
                            await client.send(message)
                            broadcast_count += 1
                            print(f"   [send] -> Forwarded to [{info['id']}/{info['type']}]")
                        except websockets.exceptions.ConnectionClosed:
                            print(f"   [warn] Client [{info['id']}] disconnected, removing")
                            clients.pop(client, None)

                if broadcast_count == 0:
                    print("   [warn] No other clients to forward to!")
                    print("   [hint] Make sure browser is connected to ws://127.0.0.1:8080")

            except json.JSONDecodeError:
                print(f"[recv] [{client_id}] Raw message: {message}")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"\n[close] [{client_id}] Connection closed: {e}")
    finally:
        del clients[websocket]
        print(f"   Remaining clients: {len(clients)}")


async def main():
    print("=" * 50)
    print("[relay] BPL Scoreboard WebSocket Relay Server")
    print("=" * 50)
    print("\nWaiting for connections...")
    print("  - Browser: open index.html")
    print("  - Testbench: python testbench.py")
    print("\nPress Ctrl+C to stop\n")

    async with websockets.serve(handler, HOST, 8080):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[stop] Server stopped")
