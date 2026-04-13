#!/usr/bin/env python3
"""
Knockout Tournament Scoreboard Testbench

Connects to the WebSocket relay server and sends test commands
to verify all new features:
  - Auto-settle after 4 rounds
  - Continue command for stage advancement
  - Advancing highlight dimming after continue
  - Finals tiebreaker with partial medal assignment

Usage:
  1. Start the server: python server.py
  2. Open index.html in a browser (must connect before testbench runs)
  3. Run testbench: python testbench.py [--scenario auto|manual|tiebreaker|notie]
"""

import asyncio
import json
import sys
import argparse

import websockets

WS_URL = "ws://localhost:8081"


def make_cmd(cmd: str, data: dict | None = None) -> str:
    msg = {"cmd": cmd}
    if data is not None:
        msg["data"] = data
    return json.dumps(msg, ensure_ascii=False)


async def sleep(seconds: float, reason: str = ""):
    if reason:
        print(f"  [sleep {seconds}s] {reason}")
    await asyncio.sleep(seconds)


async def send(ws, cmd: str, data: dict | None = None):
    msg = make_cmd(cmd, data)
    print(f"\n>>> SEND: {msg}")
    await ws.send(msg)


# ---------------------------------------------------------------------------
# Helpers: build score data
# ---------------------------------------------------------------------------

def build_score(stage: str, group: str, round_num: int, scores: list[int]) -> dict:
    """Build a SCORE command data payload."""
    player_names = [f"{group}{i+1}" for i in range(4)]
    return {
        "stage": stage,
        "group": group,
        "round": round_num,
        "scores": [
            {"player": name, "score": s} for name, s in zip(player_names, scores)
        ],
    }


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

async def scenario_auto(ws):
    """Full auto-run: A -> B -> C -> D -> E -> F -> Finals (no tie)."""
    print("\n========== SCENARIO: AUTO FULL RUN ==========")

    # 1. INIT
    await send(ws, "init", {
        "tournamentName": "Test Tournament",
        "groups": {
            "A": ["PA1", "PA2", "PA3", "PA4"],
            "B": ["PB1", "PB2", "PB3", "PB4"],
            "C": ["PC1", "PC2", "PC3", "PC4"],
            "D": ["PD1", "PD2", "PD3", "PD4"],
        }
    })
    await sleep(2, "Observe: only Group A highlighted")

    # 2. Group A: 4 rounds -> auto-settle
    await send(ws, "score", build_score("quarterfinal", "A", 1, [990000, 980000, 970000, 960000]))
    await sleep(1)
    await send(ws, "score", build_score("quarterfinal", "A", 2, [995000, 985000, 975000, 965000]))
    await sleep(1)
    await send(ws, "score", build_score("quarterfinal", "A", 3, [992000, 982000, 972000, 962000]))
    await sleep(1)
    await send(ws, "score", build_score("quarterfinal", "A", 4, [998000, 988000, 978000, 968000]))
    await sleep(2, "Observe: Group A auto-settled, top 2 strong green glow")

    # 3. CONTINUE -> next group
    await send(ws, "continue")
    await sleep(2, "Observe: Group A advancing dimmed, Group B active")

    # 4. Group B
    await send(ws, "score", build_score("quarterfinal", "B", 1, [990000, 980000, 970000, 960000]))
    await sleep(0.5)
    await send(ws, "score", build_score("quarterfinal", "B", 2, [995000, 985000, 975000, 965000]))
    await sleep(0.5)
    await send(ws, "score", build_score("quarterfinal", "B", 3, [992000, 982000, 972000, 962000]))
    await sleep(0.5)
    await send(ws, "score", build_score("quarterfinal", "B", 4, [998000, 988000, 978000, 968000]))
    await sleep(2, "Observe: Group B auto-settled")

    await send(ws, "continue")
    await sleep(1)

    # 5. Group C
    await send(ws, "score", build_score("quarterfinal", "C", 1, [990000, 980000, 970000, 960000]))
    await sleep(0.5)
    await send(ws, "score", build_score("quarterfinal", "C", 2, [995000, 985000, 975000, 965000]))
    await sleep(0.5)
    await send(ws, "score", build_score("quarterfinal", "C", 3, [992000, 982000, 972000, 962000]))
    await sleep(0.5)
    await send(ws, "score", build_score("quarterfinal", "C", 4, [998000, 988000, 978000, 968000]))
    await sleep(2)

    await send(ws, "continue")
    await sleep(1)

    # 6. Group D
    await send(ws, "score", build_score("quarterfinal", "D", 1, [990000, 980000, 970000, 960000]))
    await sleep(0.5)
    await send(ws, "score", build_score("quarterfinal", "D", 2, [995000, 985000, 975000, 965000]))
    await sleep(0.5)
    await send(ws, "score", build_score("quarterfinal", "D", 3, [992000, 982000, 972000, 962000]))
    await sleep(0.5)
    await send(ws, "score", build_score("quarterfinal", "D", 4, [998000, 988000, 978000, 968000]))
    await sleep(2)

    await send(ws, "continue")
    await sleep(2, "Observe: Group E active (semifinals)")

    # Advancement mapping with identical scores:
    # E positions: 0=PA1, 1=PB2, 2=PC2, 3=PD1
    # F positions: 0=PA2, 1=PB1, 2=PC1, 3=PD2
    e_names = ["PA1", "PB2", "PC2", "PD1"]
    f_names = ["PA2", "PB1", "PC1", "PD2"]

    # 7. Group E (semifinal)
    for r in range(1, 5):
        await send(ws, "score", {
            "stage": "semifinal", "group": "E", "round": r,
            "scores": [{"player": n, "score": s} for n, s in zip(e_names, [990000, 980000, 970000, 960000])]
        })
        await sleep(0.5)
    await sleep(2)

    await send(ws, "continue")
    await sleep(2, "Observe: Group F active")

    # 8. Group F (semifinal)
    for r in range(1, 5):
        await send(ws, "score", {
            "stage": "semifinal", "group": "F", "round": r,
            "scores": [{"player": n, "score": s} for n, s in zip(f_names, [990000, 980000, 970000, 960000])]
        })
        await sleep(0.5)
    await sleep(2)

    await send(ws, "continue")
    await sleep(2, "Observe: Finals active")

    # Finals advancement: E top2 -> pos0, pos1 ; F top2 -> pos2, pos3
    # E sorted: PA1 > PB2 > PC2 > PD1 => PA1, PB2 advance
    # F sorted: PA2 > PB1 > PC1 > PD2 => PA2, PB1 advance
    finals_names = ["PA1", "PB2", "PA2", "PB1"]

    # 9. Finals (no tie)
    for r in range(1, 5):
        scores = [990000 - i * 10000 for i in range(4)]
        await send(ws, "score", {
            "stage": "final",
            "group": "final",
            "round": r,
            "scores": [{"player": name, "score": s} for name, s in zip(finals_names, scores)],
        })
        await sleep(0.5)

    await send(ws, "settle", {"stage": "final", "group": "final"})
    await sleep(2, "Observe: Medals assigned, champion gold flash")

    # 10. RESET
    await send(ws, "reset")
    await sleep(2, "Done")


async def scenario_tiebreaker(ws):
    """Finals with a partial tie: 8pt, 4pt, 0pt, 0pt -> only bottom 2 tiebreak."""
    print("\n========== SCENARIO: FINALS TIEBREAKER ==========")

    await send(ws, "init", {
        "tournamentName": "Tiebreaker Test",
        "groups": {
            "A": ["A1", "A2", "A3", "A4"],
            "B": ["B1", "B2", "B3", "B4"],
            "C": ["C1", "C2", "C3", "C4"],
            "D": ["D1", "D2", "D3", "D4"],
        }
    })
    await sleep(2)

    # Fast-forward A-D (auto-settle after 4 rounds each)
    for grp in ["A", "B", "C", "D"]:
        for r in range(1, 5):
            await send(ws, "score", build_score("quarterfinal", grp, r, [990000, 980000, 970000, 960000]))
            await sleep(0.3)
        await sleep(1)
        await send(ws, "continue")
        await sleep(1)

    # Advancement mapping with identical scores:
    # E positions: 0=A1, 1=B2, 2=C2, 3=D1
    # F positions: 0=A2, 1=B1, 2=C1, 3=D2
    e_names = ["A1", "B2", "C2", "D1"]
    f_names = ["A2", "B1", "C1", "D2"]

    # E and F semifinals
    for grp, names in [("E", e_names), ("F", f_names)]:
        for r in range(1, 5):
            await send(ws, "score", {
                "stage": "semifinal", "group": grp, "round": r,
                "scores": [{"player": n, "score": s} for n, s in zip(names, [990000, 980000, 970000, 960000])]
            })
            await sleep(0.3)
        await sleep(1)
        await send(ws, "continue")
        await sleep(1)

    # Finals advancement: E top2 -> pos0, pos1 ; F top2 -> pos2, pos3
    # E sorted: A1 > B2 > C2 > D1 => A1, B2 advance
    # F sorted: A2 > B1 > C1 > D2 => A2, B1 advance
    finals_names = ["A1", "B2", "A2", "B1"]

    # Finals rounds: A1 always 1st (8pt), B2 always 2nd (4pt),
    # A2 and B1 tied 3rd/4th (0pt each) -> trigger partial tiebreaker
    for r in range(1, 5):
        await send(ws, "score", {
            "stage": "final", "group": "finals", "round": r,
            "scores": [
                {"player": "A1", "score": 990000},
                {"player": "B2", "score": 980000},
                {"player": "A2", "score": 970000 if r % 2 == 1 else 960000},
                {"player": "B1", "score": 960000 if r % 2 == 1 else 970000},
            ]
        })
        await sleep(0.5)

    # After 4 rounds: A1=8pt, B2=4pt, A2=0pt, B1=0pt
    # Settle -> A1 gold, B2 silver, A2/B1 enter tiebreaker (active)
    await send(ws, "settle", {"stage": "final", "group": "finals"})
    await sleep(3, "Observe: Gold + Silver assigned; bottom 2 active (tiebreaker)")

    # Tiebreaker round 1: A2 beats B1
    await send(ws, "score", {
        "stage": "final", "group": "finals", "round": 1,
        "scores": [
            {"player": "A2", "score": 985000},
            {"player": "B1", "score": 975000},
        ]
    })
    await sleep(2)

    # Tiebreaker round 2: A2 beats B1 again
    await send(ws, "score", {
        "stage": "final", "group": "finals", "round": 2,
        "scores": [
            {"player": "A2", "score": 986000},
            {"player": "B1", "score": 976000},
        ]
    })
    await sleep(2)

    await send(ws, "settle", {"stage": "final", "group": "final"})
    await sleep(3, "Observe: Bronze assigned to A2, B1 gets 4th")

    await send(ws, "reset")
    await sleep(1)


async def scenario_notie(ws):
    """Quick finals with no ties."""
    print("\n========== SCENARIO: FINALS NO TIE ==========")

    await send(ws, "init", {
        "tournamentName": "No-Tie Test",
        "groups": {
            "A": ["A1", "A2", "A3", "A4"],
            "B": ["B1", "B2", "B3", "B4"],
            "C": ["C1", "C2", "C3", "C4"],
            "D": ["D1", "D2", "D3", "D4"],
        }
    })
    await sleep(1)

    for grp in ["A", "B", "C", "D"]:
        for r in range(1, 5):
            await send(ws, "score", build_score("quarterfinal", grp, r, [990000, 980000, 970000, 960000]))
        await send(ws, "continue")
        await sleep(0.3)

    # E positions: 0=A1, 1=B2, 2=C2, 3=D1
    # F positions: 0=A2, 1=B1, 2=C1, 3=D2
    e_names = ["A1", "B2", "C2", "D1"]
    f_names = ["A2", "B1", "C1", "D2"]

    for grp, names in [("E", e_names), ("F", f_names)]:
        for r in range(1, 5):
            await send(ws, "score", {
                "stage": "semifinal", "group": grp, "round": r,
                "scores": [{"player": n, "score": s} for n, s in zip(names, [990000, 980000, 970000, 960000])]
            })
        await send(ws, "continue")
        await sleep(0.3)

    # Finals players: A1, B2, A2, B1
    finals_names = ["A1", "B2", "A2", "B1"]

    # Finals: distinct PTs
    for r in range(1, 5):
        await send(ws, "score", {
            "stage": "final", "group": "finals", "round": r,
            "scores": [
                {"player": "A1", "score": 990000},
                {"player": "B2", "score": 980000},
                {"player": "A2", "score": 970000},
                {"player": "B1", "score": 960000},
            ]
        })
        await sleep(0.3)

    await send(ws, "settle", {"stage": "final", "group": "finals"})
    await sleep(3, "Observe: Medals 🥇🥈🥉 assigned, no tiebreaker")

    await send(ws, "reset")
    await sleep(1)


async def scenario_manual(ws):
    """Interactive prompt for manual testing."""
    print("\n========== SCENARIO: MANUAL ==========")
    print("Available commands: init, score, settle, continue, reset")
    print("Special shortcuts: a1-a4 (auto 4 rounds for group A), b1-b4, c1-c4, d1-d4, e1-e4, f1-f4")
    print("                   final (auto 4 finals rounds + settle)")
    print("                   tie  (run tiebreaker scenario)")
    print("Type 'quit' to exit.\n")

    while True:
        try:
            user_input = await asyncio.to_thread(input, ">>> ")
        except EOFError:
            break

        user_input = user_input.strip()
        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            break

        low = user_input.lower()

        if low in ("a1", "a2", "a3", "a4", "b1", "b2", "b3", "b4",
                   "c1", "c2", "c3", "c4", "d1", "d2", "d3", "d4"):
            grp = low[0].upper()
            for r in range(1, 5):
                await send(ws, "score", build_score("quarterfinal", grp, r, [990000, 980000, 970000, 960000]))
                await sleep(0.2)
            print(f"  Sent 4 rounds for Group {grp} (quarterfinal).")
            continue

        if low in ("e1", "e2", "e3", "e4", "f1", "f2", "f3", "f4"):
            grp = low[0].upper()
            for r in range(1, 5):
                await send(ws, "score", build_score("semifinal", grp, r, [990000, 980000, 970000, 960000]))
                await sleep(0.2)
            print(f"  Sent 4 rounds for Group {grp} (semifinal).")
            continue

        if low == "final":
            # Actual finals players after default a-d + e-f fast-forward:
            # A1, B2, A2, B1
            for r in range(1, 5):
                await send(ws, "score", {
                    "stage": "final", "group": "finals", "round": r,
                    "scores": [
                        {"player": "A1", "score": 990000},
                        {"player": "B2", "score": 980000},
                        {"player": "A2", "score": 970000},
                        {"player": "B1", "score": 960000},
                    ]
                })
                await sleep(0.2)
            await send(ws, "settle", {"stage": "final", "group": "finals"})
            print("  Sent 4 finals rounds + settle.")
            continue

        if low == "tie":
            await scenario_tiebreaker(ws)
            continue

        # Parse as JSON if it looks like a JSON command
        if user_input.startswith("{"):
            try:
                data = json.loads(user_input)
                print(f"\n>>> SEND (raw): {user_input}")
                await ws.send(user_input)
            except json.JSONDecodeError as e:
                print(f"Invalid JSON: {e}")
            continue

        # Simple text shortcuts
        parts = user_input.split()
        cmd = parts[0].lower()
        if cmd == "init":
            await send(ws, "init", {
                "tournamentName": "Manual Tournament",
                "groups": {
                    "A": ["A1", "A2", "A3", "A4"],
                    "B": ["B1", "B2", "B3", "B4"],
                    "C": ["C1", "C2", "C3", "C4"],
                    "D": ["D1", "D2", "D3", "D4"],
                }
            })
        elif cmd == "continue":
            await send(ws, "continue")
        elif cmd == "reset":
            await send(ws, "reset")
        elif cmd == "score":
            # score quarterfinal A 1 990000 980000 970000 960000
            if len(parts) < 7:
                print("Usage: score <stage> <group> <round> <s1> <s2> <s3> <s4>")
                continue
            stage = parts[1]
            group = parts[2]
            round_num = int(parts[3])
            scores = list(map(int, parts[4:8]))
            await send(ws, "score", build_score(stage, group, round_num, scores))
        elif cmd == "settle":
            # settle quarterfinal A
            if len(parts) < 3:
                print("Usage: settle <stage> <group>")
                continue
            await send(ws, "settle", {"stage": parts[1], "group": parts[2]})
        else:
            print(f"Unknown command: {cmd}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(description="Knockout Tournament Testbench")
    parser.add_argument(
        "--scenario", "-s",
        choices=["auto", "manual", "tiebreaker", "notie"],
        default="auto",
        help="Test scenario to run (default: auto)"
    )
    args = parser.parse_args()

    print(f"Connecting to {WS_URL} ...")
    try:
        async with websockets.connect(WS_URL) as ws:
            print("Connected!")
            if args.scenario == "auto":
                await scenario_auto(ws)
            elif args.scenario == "manual":
                await scenario_manual(ws)
            elif args.scenario == "tiebreaker":
                await scenario_tiebreaker(ws)
            elif args.scenario == "notie":
                await scenario_notie(ws)
    except ConnectionRefusedError:
        print("ERROR: Could not connect. Is the server running on localhost:8081?")
        sys.exit(1)
    except websockets.exceptions.InvalidMessage as e:
        print(f"ERROR: Invalid WebSocket response: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
