#!/usr/bin/env python3
"""场景信息链路 smoke test（手动验证用，非 pytest）。

真实启动：sceneinfo relay(8082) + 导播台 app(5003) + 假记分板(8080/8081)，
通过 HTTP API 走一遍团队赛单回合流程，断言：
- 8080 收到 init 与 score；
- overlay 客户端(8082)收到 round_start 与 round_result。

用法（iidx_director/ 目录下）：
    python sceneinfo/smoke_test.py
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
APP_URL = "http://localhost:5003"

received: dict[str, list] = {"8080": [], "8081": [], "overlay": []}


def http_post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        APP_URL + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


async def recorder_server(port: str):
    async def handler(ws):
        async for message in ws:
            received[port].append(json.loads(message))

    return await websockets.serve(handler, "localhost", int(port))


async def overlay_client():
    async with websockets.connect("ws://localhost:8082") as ws:
        try:
            while True:
                received["overlay"].append(json.loads(await asyncio.wait_for(ws.recv(), 30)))
        except (asyncio.TimeoutError, websockets.ConnectionClosed):
            pass


async def main() -> int:
    s8080 = await recorder_server("8080")
    s8081 = await recorder_server("8081")

    relay = subprocess.Popen([PYTHON, str(ROOT / "sceneinfo" / "server.py")])
    app_proc = subprocess.Popen(
        [PYTHON, "-m", "src.app"], cwd=ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        # 等服务就绪
        for _ in range(50):
            try:
                urllib.request.urlopen(APP_URL + "/api/state", timeout=1)
                break
            except Exception:
                time.sleep(0.2)
        else:
            print("✗ app 未能启动")
            return 1

        overlay_task = asyncio.create_task(overlay_client())
        await asyncio.sleep(0.5)  # overlay 先连上 relay

        async def post(path: str, body: dict) -> dict:
            # HTTP 是阻塞调用，放到线程里避免饿死本 loop 上的假记分板/overlay
            return await asyncio.to_thread(http_post, path, body)

        assert (await post("/api/mode", {"mode": "team"}))["success"]
        assert (await post("/api/match/start", {}))["success"], "match/start 失败"
        # 模板配置第一回合：1v1，选手L1 vs 选手R1
        assert (await post("/api/round/assign", {
            "assignments": {
                "选手L1": {"machine": "IIDX#1", "side": "1p"},
                "选手R1": {"machine": "IIDX#1", "side": "2p"},
            }
        }))["success"]
        assert (await post("/api/round/begin", {}))["success"]
        await asyncio.sleep(1)
        assert (await post("/api/round/force_review", {"scores": {"选手L1": 2000, "选手R1": 1500}}))["success"]
        assert (await post("/api/round/confirm", {"scores": {"选手L1": 2000, "选手R1": 1500}}))["success"]
        await asyncio.sleep(1)
        await post("/api/match/abort", {})
        overlay_task.cancel()

        cmds_8080 = [m.get("cmd") for m in received["8080"]]
        cmds_overlay = [m.get("cmd") for m in received["overlay"]]
        print(f"8080 收到: {cmds_8080}")
        print(f"overlay 收到: {cmds_overlay}")

        ok = True
        ok &= "init" in cmds_8080 and "score" in cmds_8080
        ok &= "round_start" in cmds_overlay and "round_result" in cmds_overlay
        score = next(m for m in received["8080"] if m.get("cmd") == "score")
        ok &= score["data"] == {"round": 1, "leftScore": 1, "rightScore": 0}
        rs = next(m for m in received["overlay"] if m.get("cmd") == "round_start")
        entries = {e["player"]: e for e in rs["data"]["entries"]}
        ok &= entries["选手L1"]["machine"] == "IIDX#1" and entries["选手L1"]["color"] == "#c0c0c0"

        print("✓ smoke test 通过" if ok else "✗ smoke test 失败")
        return 0 if ok else 1
    finally:
        app_proc.terminate()
        relay.terminate()
        s8080.close()
        s8081.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
