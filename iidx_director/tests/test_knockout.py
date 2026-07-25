import pytest

from src.match.knockout import KnockoutTournament


def _tournament():
    return KnockoutTournament({g: [f"{g}{i}" for i in range(1, 5)] for g in "ABCD"})


def _play_group(t: KnockoutTournament, group: str, scores_by_round):
    for scores in scores_by_round:
        t.record_round(group, scores)
    t.settle(group)


def test_pt_accumulation_and_tiebreak_by_total_raw():
    t = _tournament()
    # A1 三胜一负 (2+2+2+0=6 PT)；A2/A3 各 5 PT 时按 totalRaw 区分
    rounds = [
        {"A1": 4000, "A2": 3000, "A3": 2000, "A4": 1000},
        {"A1": 4000, "A3": 3000, "A2": 2000, "A4": 1000},
        {"A1": 4000, "A2": 3000, "A3": 2000, "A4": 1000},
        {"A4": 4000, "A2": 3001, "A3": 3000, "A1": 1000},
    ]
    _play_group(t, "A", rounds)
    # A1: 2+2+2+0=6 PT 第一；A2: 1+0+1+1=3，A3: 0+1+0+0=1，A4: 0+0+0+2=2 → A2 第二
    assert t.lineup("E")[0] == "A1"  # A 组第一 → E[0]
    assert t.lineup("F")[0] == "A2"  # A 组第二 → F[0]


def test_advancement_mapping_all_quarterfinals():
    t = _tournament()
    # 每组让编号小的两人晋级（每局都按编号顺序给分）
    for group in "ABCD":
        rounds = [
            {f"{group}1": 4000, f"{group}2": 3000, f"{group}3": 2000, f"{group}4": 1000}
            for _ in range(4)
        ]
        _play_group(t, group, rounds)
    # A: 1st→E[0] 2nd→F[0]；B: 1st→F[1] 2nd→E[1]
    # C: 1st→F[2] 2nd→E[2]；D: 1st→E[3] 2nd→F[3]
    assert t.lineup("E") == ["A1", "B2", "C2", "D1"]
    assert t.lineup("F") == ["A2", "B1", "C1", "D2"]


def test_semifinal_to_finals():
    t = _tournament()
    for group in "ABCD":
        rounds = [
            {f"{group}1": 4000, f"{group}2": 3000, f"{group}3": 2000, f"{group}4": 1000}
            for _ in range(4)
        ]
        _play_group(t, group, rounds)
    # E 组让 E[1](B2) 第一、E[0](A1) 第二；F 组让 F[0](A2) 第一、F[1](B1) 第二
    e_rounds = [{"B2": 4000, "A1": 3000, "C2": 2000, "D1": 1000} for _ in range(4)]
    f_rounds = [{"A2": 4000, "B1": 3000, "C1": 2000, "D2": 1000} for _ in range(4)]
    _play_group(t, "E", e_rounds)
    _play_group(t, "F", f_rounds)
    # E: 1st→finals[0] 2nd→finals[1]；F: 1st→finals[2] 2nd→finals[3]
    assert t.lineup("finals") == ["B2", "A1", "A2", "B1"]


def test_finals_clean_finish():
    t = _tournament()
    for group in "ABCD":
        rounds = [
            {f"{group}1": 4000, f"{group}2": 3000, f"{group}3": 2000, f"{group}4": 1000}
            for _ in range(4)
        ]
        _play_group(t, group, rounds)
    for group in "EF":
        lineup = [n for n in t.lineup(group) if n]
        rounds = [{name: 4000 - i * 1000 for i, name in enumerate(lineup)} for _ in range(4)]
        _play_group(t, group, rounds)
    lineup = t.lineup("finals")
    # 前 3 局按 lineup 名次，第 4 局交换 2、3 名 → PT 8/3/1/0，无并列
    rounds = [{name: 4000 - i * 1000 for i, name in enumerate(lineup)} for _ in range(3)]
    swapped = [lineup[0], lineup[2], lineup[1], lineup[3]]
    rounds.append({name: 4000 - i * 1000 for i, name in enumerate(swapped)})
    for scores in rounds:
        t.record_round("finals", scores)
    t.settle("finals")
    assert t.finished
    assert not t.in_tiebreaker
    assert t.final_ranking == lineup  # PT 8/3/1/0 与 lineup 顺序一致


def test_finals_tiebreaker():
    t = _tournament()
    for group in "ABCD":
        rounds = [
            {f"{group}1": 4000, f"{group}2": 3000, f"{group}3": 2000, f"{group}4": 1000}
            for _ in range(4)
        ]
        _play_group(t, group, rounds)
    for group in "EF":
        lineup = [n for n in t.lineup(group) if n]
        rounds = [{name: 4000 - i * 1000 for i, name in enumerate(lineup)} for _ in range(4)]
        _play_group(t, group, rounds)
    f = t.lineup("finals")
    # 构造 PT 并列：f[0] 与 f[1] 各两胜两负 → 同 6 PT；f[2]/f[3] 必然同 0 PT（与 board 一致，
    # 两组并列都进入加赛）
    rounds = [
        {f[0]: 4000, f[1]: 3000, f[2]: 2000, f[3]: 1000},
        {f[0]: 4000, f[1]: 3000, f[2]: 2000, f[3]: 1000},
        {f[1]: 4000, f[0]: 3000, f[2]: 2000, f[3]: 1000},
        {f[1]: 4000, f[0]: 3000, f[2]: 2000, f[3]: 1000},
    ]
    for scores in rounds:
        t.record_round("finals", scores)
    t.settle("finals")
    assert not t.finished
    assert t.in_tiebreaker
    # 两组并列的选手都继续上机（board 端行为：所有并列组保持 active）
    assert t.active_players("finals") == f
    # 加赛一局：f[1] 胜 f[0]，f[3] 胜 f[2] → 名次 f1/f0/f3/f2
    t.record_round("finals", {f[1]: 4000, f[0]: 3000, f[3]: 2000, f[2]: 1000})
    t.settle("finals")
    assert t.finished
    assert t.final_ranking == [f[1], f[0], f[3], f[2]]


def test_settle_before_complete_rejected():
    t = _tournament()
    t.record_round("A", {"A1": 4, "A2": 3, "A3": 2, "A4": 1})
    with pytest.raises(ValueError, match="不能结算"):
        t.settle("A")


def test_record_unknown_player_rejected():
    t = _tournament()
    with pytest.raises(ValueError, match="没有这些选手"):
        t.record_round("A", {"ZZ": 100})
