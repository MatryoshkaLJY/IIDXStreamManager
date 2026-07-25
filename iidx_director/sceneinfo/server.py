#!/usr/bin/env python3
"""场景信息 WebSocket 中继（端口 8082）。

与两个 scoreboard 的 relay 同模式：把收到的消息广播给所有其他客户端。
真实场景网页后续替换 sceneinfo/overlay.html 即可，协议先行。
"""

import asyncio
import json

import websockets

PORT = 8082
clients = set()


async def handler(websocket):
    clients.add(websocket)
    print(f"🔗 客户端接入（共 {len(clients)}）: {websocket.remote_address}")
    try:
        async for message in websocket:
            try:
                cmd = json.loads(message).get("cmd", "unknown")
            except json.JSONDecodeError:
                cmd = "invalid-json"
            print(f"📨 收到: {cmd}")
            delivered = 0
            for client in list(clients):
                if client is websocket:
                    continue
                try:
                    await client.send(message)
                    delivered += 1
                except websockets.exceptions.ConnectionClosed:
                    clients.discard(client)
            if delivered == 0:
                print("   ⚠️ 没有其他客户端（overlay.html 是否已打开？）")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        clients.discard(websocket)
        print(f"🔌 客户端断开（剩 {len(clients)}）")


async def main():
    print(f"🌐 场景信息 WS 中继 @ ws://localhost:{PORT}")
    print("   用浏览器 / OBS 浏览器源打开 sceneinfo/overlay.html 查看")
    async with websockets.serve(handler, "localhost", PORT):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 已停止")
