import pytest

from src.match.scoring import judge_1v1, judge_2v2


def test_1v1_left_wins():
    assert judge_1v1(2000, 1500, 3) == (3, 0)


def test_1v1_right_wins():
    assert judge_1v1(1000, 1500, 2) == (0, 2)


def test_1v1_draw_no_points():
    assert judge_1v1(1500, 1500, 2) == (0, 0)


def test_2v2_rank_points_split():
    # 名次 1(左) 2(右) 3(左) 4(右) → 左 3+1=4，右 2+0=2
    result = judge_2v2([("left", 2000), ("right", 1900), ("left", 1800), ("right", 1700)])
    assert result == (4, 2)


def test_2v2_sweep():
    result = judge_2v2([("left", 2000), ("left", 1900), ("right", 1800), ("right", 1700)])
    assert result == (5, 1)


def test_2v2_requires_four_entries():
    with pytest.raises(ValueError):
        judge_2v2([("left", 1), ("right", 2)])


def test_2v2_rejects_unknown_side():
    with pytest.raises(ValueError, match="side"):
        judge_2v2([("left", 1), ("right", 2), ("middle", 3), ("left", 4)])
