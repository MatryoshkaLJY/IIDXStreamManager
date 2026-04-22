import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import websockets

logger = logging.getLogger(__name__)

BPL_URI = "ws://localhost:8080"
KNOCKOUT_URI = "ws://localhost:8081"


class ScoreboardPusher:
    def __init__(self) -> None:
        pass

    def push_team_score(self, round_number: int, left_score: int, right_score: int) -> bool:
        """Push a score update to the BPL scoreboard (port 8080)."""
        message = {
            "cmd": "score",
            "data": {
                "round": round_number,
                "leftScore": left_score,
                "rightScore": right_score,
            },
        }
        return self._send(BPL_URI, message)

    def push_individual_score(
        self,
        stage: str,
        group: str,
        round_number: int,
        scores: List[Dict[str, Any]],
    ) -> bool:
        """Push a score update to the knockout scoreboard (port 8081)."""
        message = {
            "cmd": "score",
            "data": {
                "stage": stage,
                "group": group,
                "round": round_number,
                "scores": scores,
            },
        }
        return self._send(KNOCKOUT_URI, message)

    def _send(self, uri: str, message: dict) -> bool:
        try:
            asyncio.run(self._send_async(uri, message))
            return True
        except Exception as exc:
            logger.warning("Scoreboard push to %s failed: %s", uri, exc)
            return False

    async def _send_async(self, uri: str, message: dict) -> None:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps(message, ensure_ascii=False))
