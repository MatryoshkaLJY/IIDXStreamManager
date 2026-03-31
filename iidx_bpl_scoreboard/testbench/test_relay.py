#!/usr/bin/env python3
"""
Test script to verify WebSocket relay server works correctly
"""

import asyncio
import websockets
import json
import time


async def mock_browser():
    """Simulate browser client"""
    print("🌐 [Browser] Connecting...")
    async with websockets.connect("ws://localhost:8080") as ws:
        print("🌐 [Browser] Connected! Waiting for messages...")

        # Wait for init and score messages
        message_count = 0
        while message_count < 5:  # init + 4 scores
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                data = json.loads(msg)
                cmd = data.get('cmd', 'unknown')

                if cmd == 'init':
                    print(f"🌐 [Browser] Received: init")
                    print(f"   Match: {data['data']['leftTeam']['name']} vs {data['data']['rightTeam']['name']}")
                elif cmd == 'score':
                    r = data['data']['round']
                    l = data['data']['leftScore']
                    rgt = data['data']['rightScore']
                    print(f"🌐 [Browser] Received: score round {r} ({l}-{rgt})")

                message_count += 1

            except asyncio.TimeoutError:
                print("🌐 [Browser] Timeout waiting for message")
                break

        print("🌐 [Browser] Done!")


async def mock_testbench():
    """Simulate testbench client"""
    await asyncio.sleep(0.5)  # Wait for browser to connect first

    print("\n🎮 [Testbench] Connecting...")
    async with websockets.connect("ws://localhost:8080") as ws:
        print("🎮 [Testbench] Connected!")

        # Send init
        init_msg = {
            "cmd": "init",
            "data": {
                "stageName": "レギュラーステージ",
                "matchNumber": 1,
                "leftTeam": {"name": "SILK HAT", "logo": "🎩", "colors": {"primary": "#c0c0c0"}},
                "rightTeam": {"name": "APA", "logo": "🌟", "colors": {"primary": "#4ecdc4"}},
                "matches": [
                    {"type": "1v1", "leftPlayers": ["CHEPY."], "rightPlayers": ["DORON"], "theme": "SCRATCH"},
                    {"type": "2v2", "leftPlayers": ["LOOT", "IGW."], "rightPlayers": ["NCHO", "POTESARA"], "theme": "2V2"},
                    {"type": "1v1", "leftPlayers": ["VENUS"], "rightPlayers": ["MAO"], "theme": "NOTES"},
                    {"type": "1v1", "leftPlayers": ["???"], "rightPlayers": ["???"], "theme": "FINAL"}
                ]
            }
        }
        await ws.send(json.dumps(init_msg))
        print("🎮 [Testbench] Sent: init")
        await asyncio.sleep(0.5)

        # Send scores
        scores = [(1, 2, 1), (2, 3, 3), (3, 1, 2), (4, 2, 2)]
        for round_num, left, right in scores:
            score_msg = {
                "cmd": "score",
                "data": {"round": round_num, "leftScore": left, "rightScore": right}
            }
            await ws.send(json.dumps(score_msg))
            print(f"🎮 [Testbench] Sent: score round {round_num} ({left}-{right})")
            await asyncio.sleep(0.5)

        print("🎮 [Testbench] Done!")


async def main():
    print("=" * 60)
    print("🧪 Testing WebSocket Relay Server")
    print("=" * 60)
    print()

    # Run browser and testbench simultaneously
    await asyncio.gather(
        mock_browser(),
        mock_testbench()
    )

    print()
    print("=" * 60)
    print("✅ Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
