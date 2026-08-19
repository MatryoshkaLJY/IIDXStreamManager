"""个人淘汰赛机制集成测试（一次性脚本）：通过 MatchSession 走完整场 16 人淘汰赛。

覆盖：
- 每组 4 局的完整会话流转（PREP→LIVE→REVIEW→PUSHED→下一局 PREP）；
- 单局并列积分（竞争排名）；
- A-F 组：无并列直接晋级 / PT 并列按总 EX 晋级 / 第 2/3 名跨线并列加赛一首决出 /
  次席三人并列加赛一次（末两位平分不再加赛）/ 末位并列与头名并列均不触发加赛；
- 决赛：三人 PT 并列，多次加赛直到全部决出，final_ranking 正确；
- 每局 confirm 后 should_show_scoreboard 的取值序列（局间不切、4 局结束切、
  进入加赛前切、加赛未决不切、加赛决出切）；
- 推送载荷结构：score 载荷的 group/round 递增、settle 载荷仅决赛出现；
- 8 人 EF 赛制（knockout_ef）：E→F→决赛推进、跨线加赛、init 载荷 startGroup 标记；
- 4 人决赛赛制（knockout_final）：直接决赛、多组 PT 并列一次加赛全部决出。
"""
import sys

sys.path.insert(0, "iidx_director")

from src.config.models import KnockoutConfig, KnockoutEFConfig, KnockoutFinalConfig
from src.match.knockout import KnockoutTournament
from src.match.session import MatchSession, SessionPhase
from src.push.scoreboard import knockout_init_payload

FAILED = []


def check(name, cond, detail=""):
    if cond:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name} {detail}")
        FAILED.append(name)


MACHINES = [("m1", "1p"), ("m1", "2p"), ("m2", "1p"), ("m2", "2p")]


def play_song(session, scores):
    """打一局：分配机台（如需要）→ 开始 → 录分 → 确认。返回 (payloads, show_scoreboard)。"""
    players = session.players_to_assign()
    assert set(players) == set(scores), f"选手集合不符: {players} vs {list(scores)}"
    assert session.phase == SessionPhase.PREP, session.phase
    if set(session.assignments) != set(players):
        session.set_assignments(
            {p: {"machine": m, "side": s} for p, (m, s) in zip(players, MACHINES)}
        )
    session.begin_round()
    assert session.phase == SessionPhase.LIVE
    session.force_review(scores)
    assert session.phase == SessionPhase.REVIEW
    payloads = session.confirm(scores)
    assert session.phase == SessionPhase.PUSHED
    show = session.tournament.should_show_scoreboard(session.group)
    return payloads, show


def play_songs(session, group, songs):
    """在当前组依次打若干局，每局后 advance。返回每局 (payloads, show) 列表。"""
    out = []
    for scores in songs:
        assert session.group == group, f"当前组 {session.group} != 预期 {group}"
        out.append(play_song(session, scores))
        session.advance()
    return out


def shows(results):
    return [show for _, show in results]


def score_rounds(results):
    """提取每局 score 载荷的 (group, round)。"""
    rounds = []
    for payloads, _ in results:
        score = next(p for p in payloads if p["payload"]["cmd"] == "score")
        data = score["payload"]["data"]
        rounds.append((data["group"], data["round"]))
    return rounds


def settle_count(results):
    return sum(
        1 for payloads, _ in results for p in payloads if p["payload"]["cmd"] == "settle"
    )


cfg = KnockoutConfig(groups={
    "A": ["A1", "A2", "A3", "A4"],
    "B": ["B1", "B2", "B3", "B4"],
    "C": ["C1", "C2", "C3", "C4"],
    "D": ["D1", "D2", "D3", "D4"],
})
s = MatchSession("knockout", cfg)
s.start()
check("开始后进 PREP", s.phase == SessionPhase.PREP)

# ---- A 组：无并列，干净晋级 ----
r = play_songs(s, "A", [
    {"A1": 100, "A2": 90, "A3": 80, "A4": 70},
    {"A1": 100, "A2": 90, "A3": 80, "A4": 70},
    {"A1": 100, "A2": 90, "A3": 80, "A4": 70},
    {"A1": 100, "A2": 90, "A3": 80, "A4": 70},
])
check("A组 局间不切计分板、第4局切", shows(r) == [False, False, False, True], shows(r))
check("A组 score 载荷局号", score_rounds(r) == [("A", 1), ("A", 2), ("A", 3), ("A", 4)],
      score_rounds(r))
check("A组 无 settle 载荷", settle_count(r) == 0)
check("A组晋级 A1->E0 A2->F0",
      s.tournament.groups["E"][0].name == "A1" and s.tournament.groups["F"][0].name == "A2")

# ---- D 组：次席三人并列 → 加赛一次决出次席，末两位平分不再加赛 ----
r = play_songs(s, "D", [
    {"D1": 100, "D2": 90, "D3": 90, "D4": 90},
    {"D1": 100, "D2": 90, "D3": 90, "D4": 90},
    {"D1": 100, "D2": 90, "D3": 90, "D4": 90},
    {"D1": 100, "D2": 90, "D3": 90, "D4": 90},
])
check("D组 第4局后进入加赛", shows(r)[-1] and s.tournament.in_tiebreaker)
check("D组 加赛三人上机", s.players_to_assign() == ["D2", "D3", "D4"], s.players_to_assign())
r1 = play_songs(s, "D", [{"D2": 150, "D3": 140, "D4": 140}])
check("D组 次席决出后末两位平分不再加赛、展示计分板",
      shows(r1) == [True] and not s.tournament.in_tiebreaker)
check("D组 加赛局号为 5", score_rounds(r1) == [("D", 5)], score_rounds(r1))
check("D组晋级 D1->E3 D2->F3",
      s.tournament.groups["E"][3].name == "D1" and s.tournament.groups["F"][3].name == "D2")

# ---- B 组：PT 并列、总 EX 不同 → 不加赛 ----
r = play_songs(s, "B", [
    {"B1": 100, "B2": 90, "B3": 80, "B4": 70},
    {"B1": 100, "B2": 90, "B3": 80, "B4": 70},
    {"B2": 100, "B3": 90, "B1": 80, "B4": 70},
    {"B3": 100, "B4": 90, "B1": 80, "B2": 79},
])
check("B组 无加赛", shows(r) == [False, False, False, True] and not s.tournament.in_tiebreaker)
check("B组晋级 B1->F1 B2->E1",
      s.tournament.groups["F"][1].name == "B1" and s.tournament.groups["E"][1].name == "B2")

# ---- C 组：第 2/3 名跨出线线并列 → 加赛一首决出次席 ----
r = play_songs(s, "C", [
    {"C1": 100, "C2": 90, "C3": 80, "C4": 70},
    {"C1": 100, "C3": 90, "C2": 80, "C4": 70},
    {"C1": 100, "C2": 90, "C3": 80, "C4": 70},
    {"C1": 100, "C3": 90, "C2": 80, "C4": 70},
])
check("C组 第4局后进入加赛且展示计分板",
      shows(r) == [False, False, False, True] and s.tournament.in_tiebreaker)
check("C组 加赛仅并列两人", s.players_to_assign() == ["C2", "C3"], s.players_to_assign())
r = play_songs(s, "C", [{"C2": 150, "C3": 140}])
check("C组 加赛决出后展示计分板", shows(r) == [True])
check("C组 加赛局号为 5", score_rounds(r) == [("C", 5)], score_rounds(r))
check("C组晋级 C1->F2 C2->E2",
      s.tournament.groups["F"][2].name == "C1" and s.tournament.groups["E"][2].name == "C2")

# ---- 末位并列（第 3/4 名）不触发加赛 ----
t2 = KnockoutTournament({"A": ["P1", "P2", "P3", "P4"]})
for scores in [
    {"P1": 100, "P2": 90, "P3": 80, "P4": 80},
    {"P1": 100, "P2": 90, "P3": 80, "P4": 80},
    {"P1": 100, "P2": 90, "P3": 80, "P4": 80},
    {"P1": 100, "P2": 90, "P3": 80, "P4": 80},
]:
    t2.record_round("A", scores)
t2.settle("A")
check("末位并列不进入加赛", not t2.in_tiebreaker and t2.group_settled("A"))
check("末位并列晋级不受影响",
      t2.groups["E"][0].name == "P1" and t2.groups["F"][0].name == "P2")

# ---- 头名并列（第 1/2 名都出线）不触发加赛，按当前排序落位 ----
t3 = KnockoutTournament({"A": ["Q1", "Q2", "Q3", "Q4"]})
for scores in [
    {"Q1": 100, "Q2": 100, "Q3": 80, "Q4": 70},
    {"Q1": 100, "Q2": 100, "Q3": 80, "Q4": 70},
    {"Q1": 100, "Q2": 100, "Q3": 80, "Q4": 70},
    {"Q1": 100, "Q2": 100, "Q3": 80, "Q4": 70},
]:
    t3.record_round("A", scores)
t3.settle("A")
check("头名并列不进入加赛", not t3.in_tiebreaker and t3.group_settled("A"))
check("头名并列按名单顺序晋级",
      t3.groups["E"][0].name == "Q1" and t3.groups["F"][0].name == "Q2")

# ---- 半决赛 E/F：干净晋级（D 组新晋级顺序：D1->E3、D2->F3） ----
r = play_songs(s, "E", [
    {"A1": 100, "B2": 90, "C2": 80, "D1": 70},
    {"A1": 100, "B2": 90, "C2": 80, "D1": 70},
    {"A1": 100, "B2": 90, "C2": 80, "D1": 70},
    {"A1": 100, "B2": 90, "C2": 80, "D1": 70},
])
check("E组晋级 A1->决赛0 B2->决赛1",
      s.tournament.groups["finals"][0].name == "A1"
      and s.tournament.groups["finals"][1].name == "B2")
r = play_songs(s, "F", [
    {"A2": 100, "B1": 90, "C1": 80, "D2": 70},
    {"A2": 100, "B1": 90, "C1": 80, "D2": 70},
    {"A2": 100, "B1": 90, "C1": 80, "D2": 70},
    {"A2": 100, "B1": 90, "C1": 80, "D2": 70},
])
check("F组晋级 A2->决赛2 B1->决赛3",
      s.tournament.groups["finals"][2].name == "A2"
      and s.tournament.groups["finals"][3].name == "B1")

# ---- 决赛：三人 PT 并列 → 多次加赛 ----
r = play_songs(s, "finals", [
    {"A1": 100, "B2": 90, "A2": 80, "B1": 70},
    {"B2": 100, "A2": 90, "A1": 80, "B1": 70},
    {"A2": 100, "A1": 90, "B2": 80, "B1": 70},
    {"B1": 100, "A1": 80, "B2": 80, "A2": 80},  # A1/B2/A2 并列第二各 +1
])
# PT: A1=4, B2=4, A2=4, B1=2
check("决赛 局间不切、第4局切", shows(r) == [False, False, False, True], shows(r))
check("决赛 4 局均带 settle 载荷", settle_count(r) == 1, settle_count(r))
check("决赛 三人并列进入加赛", s.tournament.in_tiebreaker and not s.tournament.finished)
check("决赛 加赛三人上机", s.players_to_assign() == ["A1", "B2", "A2"], s.players_to_assign())

r1 = play_songs(s, "finals", [{"A1": 150, "B2": 150, "A2": 140}])
check("决赛 tb1 一人决出、两人继续加赛、不切计分板",
      shows(r1) == [False] and s.tournament.in_tiebreaker)
check("决赛 tb1 后仅仍未决两人上机", s.players_to_assign() == ["A1", "B2"],
      s.players_to_assign())
r2 = play_songs(s, "finals", [{"A1": 150, "B2": 150}])
check("决赛 tb2 仍平分继续、不切计分板", shows(r2) == [False] and s.tournament.in_tiebreaker)
r3 = play_songs(s, "finals", [{"B2": 160, "A1": 150}])
check("决赛 tb3 决出并展示计分板", shows(r3) == [True])
check("决赛 加赛局号 5/6/7",
      score_rounds(r1 + r2 + r3) == [("finals", 5), ("finals", 6), ("finals", 7)])
check("决赛 加赛每次都带 settle 载荷", settle_count(r1 + r2 + r3) == 3)
check("比赛结束", s.phase == SessionPhase.MATCH_END, s.phase)
check("决赛名次", s.tournament.final_ranking == ["B2", "A1", "A2", "B1"],
      s.tournament.final_ranking)
check("快照含 final_ranking", s.snapshot()["summary"]["final_ranking"] == ["B2", "A1", "A2", "B1"])

# ============================================================
# 8 人 EF 赛制（knockout_ef）：E/F 组起 → 决赛
# ============================================================
cfg_ef = KnockoutEFConfig(groups={
    "E": ["E1", "E2", "E3", "E4"],
    "F": ["F1", "F2", "F3", "F4"],
})
init_ef = knockout_init_payload(cfg_ef)
check("EF init 载荷只含 E/F 且带 startGroup",
      init_ef["data"]["groups"] == {"E": ["E1", "E2", "E3", "E4"], "F": ["F1", "F2", "F3", "F4"]}
      and init_ef["data"].get("startGroup") == "E", init_ef)

se = MatchSession("knockout_ef", cfg_ef)
se.start()
check("EF 赛制起始组为 E", se.group == "E")
check("EF 赛制 stage 为 semifinal", se.current_round_info()["stage"] == "semifinal")
check("EF 赛制上机选手为 E 组", se.players_to_assign() == ["E1", "E2", "E3", "E4"])

# ---- E 组：第 2/3 名跨线并列（PT 与总 EX 均相同）→ 加赛一局 ----
r = play_songs(se, "E", [
    {"E1": 100, "E2": 90, "E3": 80, "E4": 70},
    {"E1": 100, "E3": 90, "E2": 80, "E4": 70},
    {"E1": 100, "E2": 90, "E3": 80, "E4": 70},
    {"E1": 100, "E3": 90, "E2": 80, "E4": 70},
])
check("EF E组 第4局后进入加赛", shows(r)[-1] and se.tournament.in_tiebreaker)
check("EF E组 score 载荷 stage 为 semifinal",
      all(p["payload"]["data"]["stage"] == "semifinal"
          for payloads, _ in r for p in payloads if p["payload"]["cmd"] == "score"))
check("EF E组 加赛仅并列两人", se.players_to_assign() == ["E2", "E3"], se.players_to_assign())
r = play_songs(se, "E", [{"E2": 150, "E3": 140}])
check("EF E组晋级 E1->决赛0 E2->决赛1",
      se.tournament.groups["finals"][0].name == "E1"
      and se.tournament.groups["finals"][1].name == "E2")

# ---- F 组：干净晋级 ----
r = play_songs(se, "F", [
    {"F1": 100, "F2": 90, "F3": 80, "F4": 70},
    {"F1": 100, "F2": 90, "F3": 80, "F4": 70},
    {"F1": 100, "F2": 90, "F3": 80, "F4": 70},
    {"F1": 100, "F2": 90, "F3": 80, "F4": 70},
])
check("EF F组晋级 F1->决赛2 F2->决赛3",
      se.tournament.groups["finals"][2].name == "F1"
      and se.tournament.groups["finals"][3].name == "F2")
check("EF 赛制无 A-D 组", se.tournament.group_sequence == ("E", "F", "finals"))

# ---- 决赛：PT 全部不同，4 局直接定名次 ----
r = play_songs(se, "finals", [
    {"E1": 100, "F1": 90, "E2": 80, "F2": 70},
    {"E1": 100, "F1": 90, "F2": 80, "E2": 70},
    {"E1": 100, "E2": 90, "F1": 80, "F2": 70},
    {"F1": 100, "E1": 90, "E2": 80, "F2": 70},
])
# PT: E1=7, F1=4, E2=2, F2=1
check("EF 决赛无加赛直接结束", not se.tournament.in_tiebreaker and se.tournament.finished)
check("EF 决赛 score 载荷 stage 为 final",
      all(p["payload"]["data"]["stage"] == "final"
          for payloads, _ in r for p in payloads if p["payload"]["cmd"] == "score"))
check("EF 决赛仅第4局带 settle 载荷", settle_count(r) == 1, settle_count(r))
check("EF 比赛结束", se.phase == SessionPhase.MATCH_END, se.phase)
check("EF 决赛名次", se.tournament.final_ranking == ["E1", "F1", "E2", "F2"],
      se.tournament.final_ranking)

# ============================================================
# 4 人决赛赛制（knockout_final）：直接决赛
# ============================================================
cfg_fin = KnockoutFinalConfig(groups={"finals": ["W", "X", "Y", "Z"]})
init_fin = knockout_init_payload(cfg_fin)
check("决赛赛制 init 载荷只含 finals 且带 startGroup",
      init_fin["data"]["groups"] == {"finals": ["W", "X", "Y", "Z"]}
      and init_fin["data"].get("startGroup") == "finals", init_fin)

sf = MatchSession("knockout_final", cfg_fin)
sf.start()
check("决赛赛制起始组为 finals", sf.group == "finals")
check("决赛赛制 stage 为 final", sf.current_round_info()["stage"] == "final")
check("决赛赛制组序列仅 finals", sf.tournament.group_sequence == ("finals",))

# 头名与末位各两人 PT 并列 → 两组都加赛，一局全部决出
r = play_songs(sf, "finals", [
    {"W": 100, "X": 90, "Y": 80, "Z": 70},
    {"W": 100, "X": 90, "Y": 80, "Z": 70},
    {"X": 100, "W": 90, "Y": 80, "Z": 70},
    {"X": 100, "W": 90, "Y": 80, "Z": 70},
])
# PT: W=6, X=6, Y=0, Z=0
check("决赛赛制 第4局后两组并列进入加赛",
      shows(r) == [False, False, False, True] and sf.tournament.in_tiebreaker)
check("决赛赛制 加赛四人全部上机",
      sf.players_to_assign() == ["W", "X", "Y", "Z"], sf.players_to_assign())
r = play_songs(sf, "finals", [{"W": 150, "X": 140, "Y": 130, "Z": 120}])
check("决赛赛制 加赛一局全部决出", shows(r) == [True] and sf.tournament.finished)
check("决赛赛制 score 载荷 stage 为 final",
      all(p["payload"]["data"]["stage"] == "final"
          for payloads, _ in r for p in payloads if p["payload"]["cmd"] == "score"))
check("决赛赛制 比赛结束", sf.phase == SessionPhase.MATCH_END, sf.phase)
check("决赛赛制 名次", sf.tournament.final_ranking == ["W", "X", "Y", "Z"],
      sf.tournament.final_ranking)

print()
if FAILED:
    print(f"{len(FAILED)} 项失败: {FAILED}")
    sys.exit(1)
print("全部通过")
