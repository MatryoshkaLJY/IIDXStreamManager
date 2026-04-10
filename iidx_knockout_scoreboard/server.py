#!/usr/bin/env python3
"""
Knockout Tournament Scoreboard WebSocket Relay Server

Relays messages between controller and browser clients.
Runs on port 8081 (separate from BPL scoreboard's 8080).
"""

import asyncio
import websockets
import json

# Store connected clients: websocket -> {id, type}
clients = {}


async def handler(websocket):
    """Handle WebSocket connections"""
    client_id = f"client-{len(clients)}"
    clients[websocket] = {
        'id': client_id,
        'type': 'unknown'
    }

    print(f"\n🔗 [{client_id}] Client connected (total: {len(clients)})")
    print(f"   Remote: {websocket.remote_address}")

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                cmd = data.get('cmd', 'unknown')

                # Identify controller clients from commands
                if cmd in ('init', 'score', 'settle', 'reset'):
                    clients[websocket]['type'] = 'controller'

                client_type = clients[websocket]['type']
                print(f"\n📨 [{client_id}/{client_type}] Received: {cmd}")

                # Broadcast to all other connected clients
                broadcast_count = 0
                for client, info in list(clients.items()):
                    if client != websocket:
                        try:
                            await client.send(message)
                            broadcast_count += 1
                            print(f"   📤 -> Forwarded to [{info['id']}/{info['type']}]")
                        except websockets.exceptions.ConnectionClosed:
                            print(f"   ⚠️  Client [{info['id']}] disconnected, removing")
                            clients.pop(client, None)

                if broadcast_count == 0:
                    print(f"   ⚠️  No other clients to forward to!")
                    print(f"   💡 Make sure browser is connected to ws://localhost:8081")

            except json.JSONDecodeError:
                print(f"📨 [{client_id}] Raw message: {message}")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"\n🔌 [{client_id}] Connection closed: {e}")
    finally:
        del clients[websocket]
        print(f"   Remaining clients: {len(clients)}")


async def main():
    print("=" * 50)
    print("🌐 Knockout Tournament WebSocket Relay Server")
    print("=" * 50)
    print("\nWaiting for connections...")
    print("  - Browser: open index.html")
    print("  - Controller: send commands to ws://localhost:8081")
    print("\nPress Ctrl+C to stop\n")

    async with websockets.serve(handler, "localhost", 8081):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
