import pytest

from src.config.models import KnockoutConfig, TeamMatchConfig
from src.match.session import MatchSession, SessionError, SessionPhase, parse_ex


def _team_session():
    cfg = TeamMatchConfig.model_validate(
        {
            "stageName": "S",
            "matchNumber": 1,
            "leftTeam": {"name": "L", "players": ["L1", "L2"]},
            "rightTeam": {"name": "R", "players": ["R1", "R2"]},
            "rounds": [
                {"type": "1v1", "theme": "T1", "leftPlayers": ["L1"], "rightPlayers": ["R1"], "points": 1},
                {
                    "type": "2v2",
                    "theme": "T2",
                    "leftPlayers": ["L1", "L2"],
                    "rightPlayers": ["R1", "R2"],
                    "points": 2,
                },
            ],
        }
    )
    return MatchSession("team", cfg)


def _knockout_session():
    cfg = KnockoutConfig.model_validate(
        {"tournamentName": "K", "groups": {g: [f"{g}{i}" for i in range(1, 5)] for g in "ABCD"}}
    )
    return MatchSession("knockout", cfg)


def _scores(machine_ex: dict):
    """{machine: {side: ex}} → 模拟分数服务返回。"""
    result = {}
    for m, sides in machine_ex.items():
        entry = {}
        for side, ex in sides.items():
            entry[f"{side}score"] = str(ex)
            entry[f"{side}_valid"] = True
        result[m] = entry
    return result


def _play_team_round(session, machine_ex):
    """PREP → 分配 → LIVE → 喂分 → REVIEW。"""
    info = session.current_round_info()
    machines = list(machine_ex)
    pairs = [(m, side) for m in machines for side in ("1p", "2p")]
    assignments = {
        player: {"machine": pairs[i][0], "side": pairs[i][1]}
        for i, player in enumerate(info["players"])
    }
    session.set_assignments(assignments)
    session.begin_round()
    for machine, sides in _scores(machine_ex).items():
        session.on_machine_scores(machine, sides)
    assert session.phase == SessionPhase.REVIEW


# ---- parse_ex ----

def test_parse_ex():
    assert parse_ex({"1pscore": "12345"}, "1p") == 12345
    assert parse_ex({"2pscore": "0"}, "2p") == 0
    assert parse_ex({"1pscore": ""}, "1p") is None
    assert parse_ex({}, "1p") is None
    assert parse_ex({"1pscore": "abc"}, "1p") is None


# ---- 团队赛 ----

def test_team_full_flow():
    s = _team_session()
    s.start()
    assert s.phase == SessionPhase.PREP
    info = s.current_round_info()
    assert info["round_no"] == 1 and info["total_rounds"] == 2 and info["type"] == "1v1"

    _play_team_round(s, {"IIDX#1": {"1p": 2000, "2p": 1500}})
    result = s.review_info()
    assert result["winner"] == "left" and result["left_points"] == 1

    payloads = s.confirm({"L1": 2000, "R1": 1500})
    assert payloads == [
        {"board": "bpl", "payload": {"cmd": "score", "data": {"round": 1, "leftScore": 1, "rightScore": 0}}}
    ]
    assert s.phase == SessionPhase.PUSHED

    s.advance()
    assert s.phase == SessionPhase.PREP
    assert s.current_round_info()["type"] == "2v2"

    _play_team_round(s, {"IIDX#1": {"1p": 2000, "2p": 1900}, "IIDX#2": {"1p": 1800, "2p": 1700}})
    # 2v2：L1(2000) L2(1900) R1(1800) R2(1700) → 左 3+2=5，右 1+0=1
    result = s.review_info()
    assert (result["left_points"], result["right_points"]) == (5, 1)
    s.confirm({"L1": 2000, "L2": 1900, "R1": 1800, "R2": 1700})
    s.advance()
    assert s.phase == SessionPhase.MATCH_END


def test_team_confirm_with_edited_scores():
    s = _team_session()
    s.start()
    _play_team_round(s, {"IIDX#1": {"1p": 2000, "2p": 1500}})
    # 导播改分：右边实际更高
    payloads = s.confirm({"L1": 1000, "R1": 1500})
    assert payloads[0]["payload"]["data"] == {"round": 1, "leftScore": 0, "rightScore": 1}


def test_assignment_validation():
    s = _team_session()
    s.start()
    with pytest.raises(SessionError, match="集合不符"):
        s.set_assignments({"L1": {"machine": "IIDX#1", "side": "1p"}})
    with pytest.raises(SessionError, match="重复分配"):
        s.set_assignments(
            {
                "L1": {"machine": "IIDX#1", "side": "1p"},
                "R1": {"machine": "IIDX#1", "side": "1p"},
            }
        )
    with pytest.raises(SessionError, match="无效"):
        s.set_assignments(
            {
                "L1": {"machine": "IIDX#1", "side": "3p"},
                "R1": {"machine": "IIDX#2", "side": "1p"},
            }
        )


def test_illegal_transitions():
    s = _team_session()
    with pytest.raises(SessionError):
        s.begin_round()
    with pytest.raises(SessionError):
        s.advance()
    s.start()
    with pytest.raises(SessionError, match="不能开始比赛"):
        s.start()
    with pytest.raises(SessionError, match="尚未完成机台分配"):
        s.begin_round()


def test_scores_ignored_outside_live():
    s = _team_session()
    s.start()
    assert s.on_machine_scores("IIDX#1", {"1pscore": "100"}) is False
    assert s.phase == SessionPhase.PREP


def test_partial_capture_stays_live():
    s = _team_session()
    s.start()
    s.set_assignments(
        {"L1": {"machine": "IIDX#1", "side": "1p"}, "R1": {"machine": "IIDX#2", "side": "2p"}}
    )
    s.begin_round()
    assert s.on_machine_scores("IIDX#1", {"1pscore": "2000"}) is False
    assert s.phase == SessionPhase.LIVE
    assert s.on_machine_scores("IIDX#2", {"2pscore": "1500"}) is True
    assert s.phase == SessionPhase.REVIEW


def test_abort():
    s = _team_session()
    s.start()
    s.abort()
    assert s.phase == SessionPhase.IDLE
    assert s.snapshot()["round"] is None


# ---- 淘汰赛 ----

def _play_knockout_round(session, winner_first=True):
    """打一局并确认。为避免 0 PT 并列触发平局决胜，4 人局的第 4 局交换中间两名。

    PT 分布：1-3 局按 players 顺序（2/1/0/0），第 4 局第 2、3 名互换
    → 总 PT 8/3/1/0，无并列。
    """
    info = session.current_round_info()
    players = info["players"]
    if len(players) == 4 and info["round_no"] == 4:
        ranked = [players[0], players[2], players[1], players[3]]
    else:
        ranked = list(players)
    assignments = {p: {"machine": f"IIDX#{i + 1}", "side": "1p"} for i, p in enumerate(players)}
    session.set_assignments(assignments)
    session.begin_round()
    ex = {p: 4000 - i * 100 for i, p in enumerate(ranked)}
    for i, p in enumerate(players):
        session.on_machine_scores(f"IIDX#{i + 1}", {"1pscore": str(ex[p])})
    assert session.phase == SessionPhase.REVIEW
    return session.confirm(ex)


def test_knockout_full_tournament():
    s = _knockout_session()
    s.start()
    groups = []
    while s.phase != SessionPhase.MATCH_END:
        info = s.current_round_info()
        groups.append(info["group"])
        payloads = _play_knockout_round(s)
        score_payload = payloads[0]["payload"]
        assert score_payload["cmd"] == "score"
        assert score_payload["data"]["group"] == info["group"]
        assert score_payload["data"]["round"] == info["round_no"]
        assert len(score_payload["data"]["scores"]) == len(info["players"])
        if info["group"] == "finals" and info["round_no"] == 4:
            assert payloads[-1]["payload"] == {
                "cmd": "settle",
                "data": {"stage": "final", "group": "finals"},
            }
        else:
            assert len(payloads) == 1
        s.advance()
    # A-D 各 4 局 + E、F 各 4 局 + 决赛 4 局 = 28 局
    assert len(groups) == 28
    assert groups.count("A") == 4 and groups.count("finals") == 4
    assert s.tournament is not None and s.tournament.finished


def test_knockout_stage_and_finals_group_payload():
    s = _knockout_session()
    s.start()
    # 快进到决赛
    while s.current_round_info()["group"] != "finals":
        _play_knockout_round(s)
        s.advance()
    info = s.current_round_info()
    assert info["stage"] == "final" and info["group"] == "finals"
    assert len(info["players"]) == 4
