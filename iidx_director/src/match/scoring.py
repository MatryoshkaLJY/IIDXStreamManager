"""胜负判定与积分计算（纯函数）。"""

from __future__ import annotations

# 2v2 按 EX 分排名，名次得分
RANK_POINTS_2V2 = (3, 2, 1, 0)


def judge_1v1(left_ex: int, right_ex: int, points: int) -> tuple[int, int]:
    """1v1：EX 分高者得 `points` 分。平局双方均不得分（导播可手动改分后再确认）。"""
    if left_ex > right_ex:
        return points, 0
    if right_ex > left_ex:
        return 0, points
    return 0, 0


def judge_1v1_bp(left_bp: int, right_bp: int, points: int) -> tuple[int, int]:
    """1v1 BP 局：miss count（BP）少者得 `points` 分。BP 相同为平局，双方均不得分。"""
    if left_bp < right_bp:
        return points, 0
    if right_bp < left_bp:
        return 0, points
    return 0, 0


def judge_2v2(side_scores: list[tuple[str, int]]) -> tuple[int, int]:
    """2v2：4 人按 EX 分排名 3/2/1/0，按队求和。

    `side_scores` 为 `[(side, ex_score), ...]`，side ∈ {"left", "right"}，恰好 4 项。
    同分时按输入顺序稳定排序（先列出的排前），导播可在确认前改分。
    返回 (left_points, right_points)。
    """
    if len(side_scores) != 4:
        raise ValueError(f"2v2 需要 4 个成绩，实际 {len(side_scores)}")
    ranked = sorted(side_scores, key=lambda item: -item[1])  # 稳定排序，同分保持输入序
    left = right = 0
    for rank, (side, _ex) in enumerate(ranked):
        if side == "left":
            left += RANK_POINTS_2V2[rank]
        elif side == "right":
            right += RANK_POINTS_2V2[rank]
        else:
            raise ValueError(f"未知 side: {side!r}")
    return left, right
