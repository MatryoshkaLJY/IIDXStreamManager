#!/usr/bin/env python3
"""
BPL Scoreboard Testbench
A Python test tool for sending WebSocket commands to the scoreboard.
"""

import json
import random
import asyncio
import websockets
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple


@dataclass
class Team:
    """Team data structure"""
    id: str
    name: str
    logo: str
    colors: Dict[str, str]
    players: List[Dict]


@dataclass
class MatchRound:
    """Single round configuration"""
    round_num: int
    match_type: str  # "1v1" or "2v2"
    left_players: List[str]
    right_players: List[str]
    theme: str


@dataclass
class MatchConfig:
    """Complete match configuration"""
    stage_name: str
    match_number: int
    left_team: Team
    right_team: Team
    rounds: List[MatchRound]


class DataManager:
    """Manages loading and querying team/match data"""

    def __init__(self, data_path: str = "data.json"):
        self.data_path = Path(data_path)
        self.data = self._load_data()

    def _load_data(self) -> Dict:
        """Load data from JSON file"""
        with open(self.data_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_team(self, team_id: str) -> Team:
        """Get team by ID"""
        team_data = self.data['teams'].get(team_id)
        if not team_data:
            raise ValueError(f"Team '{team_id}' not found")
        return Team(**team_data)

    def list_teams(self) -> List[str]:
        """List all team IDs"""
        return list(self.data['teams'].keys())

    def get_template(self, template_id: str) -> Dict:
        """Get match template by ID"""
        template = self.data['match_templates'].get(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' not found")
        return template

    def list_templates(self) -> List[str]:
        """List all template IDs"""
        return list(self.data['match_templates'].keys())

    def get_stage(self, stage_id: str) -> Dict:
        """Get stage info by ID"""
        for stage in self.data['stages']:
            if stage['id'] == stage_id:
                return stage
        raise ValueError(f"Stage '{stage_id}' not found")

    def get_schedule(self, week: Optional[int] = None) -> List[Dict]:
        """Get season schedule"""
        if week is None:
            return self.data['season_schedule']['weeks']
        for w in self.data['season_schedule']['weeks']:
            if w['week'] == week:
                return w['matches']
        return []

    def select_players(self, team: Team, match_type: str,
                       excluded: Optional[List[str]] = None) -> List[str]:
        """Auto-select players based on match type and strategy"""
        excluded = excluded or []
        available = [p for p in team.players if p['id'] not in excluded]

        if match_type == "1v1":
            # Prioritize veterans for 1v1
            veterans = [p for p in available if p['role'] == 'veteran']
            if veterans:
                return [random.choice(veterans)['name']]
            return [random.choice(available)['name']] if available else ["???"]

        elif match_type == "2v2":
            # Try to get one veteran + one regular
            veterans = [p for p in available if p['role'] == 'veteran']
            regulars = [p for p in available if p['role'] == 'regular']

            selected = []
            if veterans:
                selected.append(random.choice(veterans))
            if regulars:
                selected.append(random.choice(regulars))

            # Fill remaining slots
            while len(selected) < 2 and available:
                remaining = [p for p in available if p not in selected]
                if remaining:
                    selected.append(random.choice(remaining))
                else:
                    break

            return [p['name'] for p in selected[:2]]

        return []


class MatchGenerator:
    """Generates match configurations"""

    def __init__(self, data_manager: DataManager):
        self.dm = data_manager

    def generate(self, left_team_id: str, right_team_id: str,
                 template_id: str = "standard_4round",
                 stage_id: str = "regular",
                 match_number: int = 1) -> MatchConfig:
        """Generate a complete match configuration"""

        left_team = self.dm.get_team(left_team_id)
        right_team = self.dm.get_team(right_team_id)
        template = self.dm.get_template(template_id)
        stage = self.dm.get_stage(stage_id)

        rounds = []
        left_used = []
        right_used = []

        for round_config in template['rounds']:
            match_type = round_config['type']
            theme_pool = round_config['theme_pool']

            # Select theme
            theme = random.choice(theme_pool) if theme_pool else "RANDOM"

            # Select players
            left_players = self.dm.select_players(left_team, match_type, left_used)
            right_players = self.dm.select_players(right_team, match_type, right_used)

            # Track used players (simple rotation)
            left_used.extend([p for p in left_players])
            right_used.extend([p for p in right_players])

            rounds.append(MatchRound(
                round_num=round_config['round'],
                match_type=match_type,
                left_players=left_players,
                right_players=right_players,
                theme=theme
            ))

        return MatchConfig(
            stage_name=stage['name'],
            match_number=match_number,
            left_team=left_team,
            right_team=right_team,
            rounds=rounds
        )

    def generate_from_schedule(self, week: int, match_index: int = 0) -> MatchConfig:
        """Generate match from season schedule"""
        matches = self.dm.get_schedule(week)
        if match_index >= len(matches):
            raise ValueError(f"Match index {match_index} not found in week {week}")

        match_data = matches[match_index]
        return self.generate(
            left_team_id=match_data['left_team'],
            right_team_id=match_data['right_team'],
            template_id=match_data['template'],
            stage_id=match_data['stage'],
            match_number=match_index + 1
        )


class ScoreboardClient:
    """WebSocket client for communicating with scoreboard"""

    def __init__(self, uri: str = "ws://localhost:8080"):
        self.uri = uri
        self.websocket = None

    async def connect(self):
        """Connect to WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.uri)
            print(f"✅ Connected to {self.uri}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.websocket:
            await self.websocket.close()
            print("🔌 Disconnected")

    async def send_init(self, match_config: MatchConfig):
        """Send init command"""
        cmd = {
            "cmd": "init",
            "data": {
                "stageName": match_config.stage_name,
                "matchNumber": match_config.match_number,
                "leftTeam": {
                    "name": match_config.left_team.name,
                    "logo": match_config.left_team.logo,
                    "colors": match_config.left_team.colors
                },
                "rightTeam": {
                    "name": match_config.right_team.name,
                    "logo": match_config.right_team.logo,
                    "colors": match_config.right_team.colors
                },
                "matches": [
                    {
                        "type": r.match_type,
                        "leftPlayers": r.left_players,
                        "rightPlayers": r.right_players,
                        "theme": r.theme
                    }
                    for r in match_config.rounds
                ]
            }
        }
        await self._send(cmd)
        print(f"📤 Sent: init - {match_config.left_team.name} vs {match_config.right_team.name}")

    async def send_score(self, round_num: int, left_score: int, right_score: int):
        """Send score update"""
        cmd = {
            "cmd": "score",
            "data": {
                "round": round_num,
                "leftScore": left_score,
                "rightScore": right_score
            }
        }
        await self._send(cmd)
        print(f"📤 Sent: score round {round_num} - {left_score}:{right_score}")

    async def send_reset(self):
        """Send reset command"""
        cmd = {"cmd": "reset"}
        await self._send(cmd)
        print("📤 Sent: reset")

    async def _send(self, data: Dict):
        """Send data to WebSocket"""
        if not self.websocket:
            raise RuntimeError("Not connected to WebSocket")
        await self.websocket.send(json.dumps(data))


class Testbench:
    """Main testbench interface"""

    def __init__(self, data_path: str = "data.json", ws_uri: str = "ws://localhost:8080"):
        self.dm = DataManager(data_path)
        self.generator = MatchGenerator(self.dm)
        self.client = ScoreboardClient(ws_uri)
        self.current_match: Optional[MatchConfig] = None

    async def interactive_mode(self):
        """Run interactive testbench"""
        print("\n" + "="*50)
        print("🎮 BPL Scoreboard Testbench")
        print("="*50 + "\n")

        # Connect to WebSocket
        if not await self.client.connect():
            print("\n⚠️  Running in offline mode (no WebSocket connection)")

        try:
            while True:
                print("\nCommands:")
                print("  1. init    - Initialize a new match")
                print("  2. score   - Update round score")
                print("  3. reset   - Reset all scores")
                print("  4. quick   - Quick start (random match)")
                print("  5. demo    - Run full demo sequence")
                print("  6. list    - List available teams/templates")
                print("  0. exit    - Exit testbench")

                choice = input("\n> ").strip().lower()

                if choice in ('0', 'exit', 'quit'):
                    break
                elif choice in ('1', 'init'):
                    await self._cmd_init()
                elif choice in ('2', 'score'):
                    await self._cmd_score()
                elif choice in ('3', 'reset'):
                    await self.client.send_reset()
                elif choice in ('4', 'quick'):
                    await self._cmd_quick()
                elif choice in ('5', 'demo'):
                    await self._cmd_demo()
                elif choice in ('6', 'list'):
                    self._cmd_list()
                else:
                    print("Unknown command")

        finally:
            await self.client.disconnect()

    async def _cmd_init(self):
        """Initialize match command"""
        print("\n--- Initialize Match ---")

        # List teams
        teams = self.dm.list_teams()
        print(f"\nAvailable teams: {', '.join(teams)}")

        left = input("Left team: ").strip()
        right = input("Right team: ").strip()

        if left not in teams or right not in teams:
            print("❌ Invalid team selection")
            return

        # Select template
        templates = self.dm.list_templates()
        print(f"\nTemplates: {', '.join(templates)}")
        template = input("Template [standard_4round]: ").strip() or "standard_4round"

        # Generate match
        self.current_match = self.generator.generate(left, right, template)

        # Display config
        print("\n--- Match Configuration ---")
        print(f"{self.current_match.left_team.name} vs {self.current_match.right_team.name}")
        for r in self.current_match.rounds:
            print(f"  Round {r.round_num} ({r.match_type}): "
                  f"{', '.join(r.left_players)} vs {', '.join(r.right_players)} "
                  f"| Theme: {r.theme}")

        # Send to scoreboard
        await self.client.send_init(self.current_match)

    async def _cmd_score(self):
        """Update score command"""
        if not self.current_match:
            print("❌ No active match. Use 'init' first.")
            return

        print("\n--- Update Score ---")
        print(f"Match has {len(self.current_match.rounds)} rounds")

        try:
            round_num = int(input("Round number: "))
            left = int(input("Left score: "))
            right = int(input("Right score: "))
            await self.client.send_score(round_num, left, right)
        except ValueError:
            print("❌ Invalid input")

    async def _cmd_quick(self):
        """Quick start with random match"""
        teams = self.dm.list_teams()
        left, right = random.sample(teams, 2)
        template = random.choice(self.dm.list_templates())

        self.current_match = self.generator.generate(left, right, template)
        await self.client.send_init(self.current_match)

        print(f"\n✅ Quick match started: {self.current_match.left_team.name} vs {self.current_match.right_team.name}")

    async def _cmd_demo(self):
        """Run full demo sequence"""
        print("\n--- Running Demo ---")

        # Generate match
        teams = self.dm.list_teams()
        left, right = random.sample(teams, 2)
        self.current_match = self.generator.generate(left, right, "standard_4round")

        # Send init
        await self.client.send_init(self.current_match)
        await asyncio.sleep(1)

        # Send scores for each round
        for i, round_config in enumerate(self.current_match.rounds, 1):
            left_score = random.randint(0, 5)
            right_score = random.randint(0, 5)
            await self.client.send_score(i, left_score, right_score)
            await asyncio.sleep(1.5)

        print("\n✅ Demo completed")

    def _cmd_list(self):
        """List available data"""
        print("\n--- Teams ---")
        for team_id in self.dm.list_teams():
            team = self.dm.get_team(team_id)
            print(f"  {team_id}: {team.name} ({len(team.players)} players)")

        print("\n--- Templates ---")
        for tid in self.dm.list_templates():
            template = self.dm.get_template(tid)
            print(f"  {tid}: {template['name']} ({len(template['rounds'])} rounds)")

        print("\n--- Stages ---")
        for stage in self.dm.data['stages']:
            print(f"  {stage['id']}: {stage['name']}")


async def main():
    parser = argparse.ArgumentParser(description='BPL Scoreboard Testbench')
    parser.add_argument('--data', '-d', default='data.json', help='Path to data.json')
    parser.add_argument('--ws', '-w', default='ws://localhost:8080', help='WebSocket URI')
    parser.add_argument('--demo', action='store_true', help='Run demo and exit')
    parser.add_argument('--init', help='Initialize match with team1,team2')
    parser.add_argument('--template', '-t', default='standard_4round', help='Match template')

    args = parser.parse_args()

    tb = Testbench(args.data, args.ws)

    if args.demo:
        await tb.client.connect()
        await tb._cmd_demo()
        await tb.client.disconnect()
    elif args.init:
        teams = args.init.split(',')
        if len(teams) != 2:
            print("Usage: --init team1,team2")
            return
        await tb.client.connect()
        tb.current_match = tb.generator.generate(teams[0], teams[1], args.template)
        await tb.client.send_init(tb.current_match)
        await tb.client.disconnect()
    else:
        await tb.interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())
