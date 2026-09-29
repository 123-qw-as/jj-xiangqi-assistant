from jj_assistant.board import XiangqiBoard
from jj_assistant.models import JJMove
from jj_assistant.notation import format_chinese_move


def test_formats_black_general_move():
    board = XiangqiBoard.from_fen("3k5/9/9/9/9/9/9/9/9/4K4 b - - 0 1")

    assert format_chinese_move(board, JJMove(3, 9, 3, 8)) == "将四进一"


def test_formats_red_cannon_horizontal_move():
    board = XiangqiBoard.from_fen("9/9/9/9/9/9/9/9/9/2C6 w - - 0 1")

    assert format_chinese_move(board, JJMove(2, 0, 5, 0)) == "炮七平四"


def test_uses_red_piece_names():
    board = XiangqiBoard.from_fen("9/9/9/9/9/9/9/9/9/4K4 w - - 0 1")

    assert format_chinese_move(board, JJMove(4, 0, 4, 1)) == "帅五进一"


def test_unknown_piece_uses_coordinate_fallback():
    board = XiangqiBoard.from_fen("9/9/9/9/9/9/9/9/9/9 w - - 0 1")

    assert format_chinese_move(board, JJMove(3, 8, 3, 7)) == "第4列第8行→第4列第7行"
