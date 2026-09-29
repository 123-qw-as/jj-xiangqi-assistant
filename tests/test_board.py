import pytest

from jj_assistant.board import INITIAL_FEN, XiangqiBoard
from jj_assistant.models import JJMove


def test_initial_fen_round_trip():
    assert XiangqiBoard.initial().to_fen() == INITIAL_FEN


def test_applies_jj_coordinates_and_flips_side():
    board = XiangqiBoard.initial()

    captured = board.apply(JJMove(0, 3, 0, 4))

    assert captured is None
    assert board.to_fen() == (
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/P8/2P1P1P1P/1C5C1/9/RNBAKABNR b"
    )


def test_rejects_move_from_empty_square():
    board = XiangqiBoard.initial()
    with pytest.raises(ValueError, match="没有棋子"):
        board.apply(JJMove(0, 4, 0, 5))

