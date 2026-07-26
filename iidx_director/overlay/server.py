#!/usr/bin/env python3
"""OBS overlay WebSocket relay (port 8082).

The relay only transports JSON messages between iidx_director and the OBS
browser source. Rendering and layout live in ``obs-overlay.html``.
"""

import asyncio
import json
import os

import websockets

PORT = 8082
HOST = os.environ.get("IIDX_RELAY_HOST", "127.0.0.1")
clients: set = set()
queued_commands: dict[tuple[str, str], str] = {}
active_command: str | None = None


async def handler(websocket):
    global active_command
    clients.add(websocket)
    try:
        # OBS may unload a browser source while its scene is hidden.  Replay
        # the latest scene commands when that source reconnects.
        replay = list(queued_commands.values())
        if active_command is not None:
            replay.append(active_command)
        for message in replay:
            try:
                await websocket.send(message)
            except websockets.exceptions.ConnectionClosed:
                return
        async for message in websocket:
            try:
                payload = json.loads(message)
            except (TypeError, json.JSONDecodeError):
                payload = None
            if isinstance(payload, dict) and payload.get("cmd") in {"stage", "activate"}:
                scene = str(payload.get("scene") or "")
                if scene:
                    command = str(payload["cmd"])
                    if command == "activate":
                        active_command = message
                    else:
                        queued_commands[(command, scene)] = message
            for client in list(clients):
                if client is websocket:
                    continue
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    clients.discard(client)
            # A relay receipt is enough to advance the pre-switch stage.  The
            # browser source still receives the command and acknowledges it
            # when available; queued replay covers sources loaded after OBS
            # switches scenes.
            if isinstance(payload, dict) and payload.get("cmd") in {"stage", "activate"}:
                request_id = payload.get("request_id")
                if request_id:
                    await websocket.send(json.dumps({
                        "cmd": "ack",
                        "request_id": request_id,
                        "ok": True,
                        "queued": True,
                    }))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        clients.discard(websocket)


async def main():
    print(f"OBS overlay relay @ ws://{HOST}:{PORT}")
    async with websockets.serve(handler, HOST, PORT):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
