from __future__ import annotations

from .board import XiangqiBoard
from .models import JJMove
from .protocol import parse_uci_move

_CHINESE_NUMBERS = "一二三四五六七八九"
_RED_PIECE_NAMES = {
    "k": "帅",
    "a": "仕",
    "b": "相",
    "n": "马",
    "r": "车",
    "c": "炮",
    "p": "兵",
}
_BLACK_PIECE_NAMES = {
    "k": "将",
    "a": "士",
    "b": "象",
    "n": "马",
    "r": "车",
    "c": "炮",
    "p": "卒",
}


def format_chinese_move(board: XiangqiBoard, move: JJMove) -> str:
    """把 JJ/UCI 坐标转换成常用的中国象棋记谱。"""

    piece = board.piece_at(move.from_x, move.from_y)
    if piece is None:
        return format_coordinate_move(move)

    is_red = piece.isupper()
    piece_name = (_RED_PIECE_NAMES if is_red else _BLACK_PIECE_NAMES)[piece.lower()]
    from_file = _file_number(move.from_x, is_red)
    to_file = _file_number(move.to_x, is_red)

    if move.from_y == move.to_y:
        action = "平"
        action_number = to_file
    else:
        is_forward = move.to_y > move.from_y if is_red else move.to_y < move.from_y
        action = "进" if is_forward else "退"
        # 马、象、士的斜线落点用目标纵线；其余棋子用移动格数。
        action_number = (
            to_file if piece.lower() in {"n", "b", "a"} else abs(move.to_y - move.from_y)
        )

    return (
        f"{piece_name}{_CHINESE_NUMBERS[from_file - 1]}"
        f"{action}{_CHINESE_NUMBERS[action_number - 1]}"
    )


def format_uci_move(board: XiangqiBoard, uci: str) -> str:
    move = parse_uci_move(uci)
    if move is None:
        return uci
    return format_chinese_move(board, move)


def format_coordinate_move(move: JJMove) -> str:
    """未知局面时的中文坐标后备显示。"""

    return (
        f"第{move.from_x + 1}列第{move.from_y}行"
        f"→第{move.to_x + 1}列第{move.to_y}行"
    )


def _file_number(x: int, is_red: bool) -> int:
    if not 0 <= x < 9:
        raise ValueError(f"棋盘列超出范围：{x}")
    return 9 - x if is_red else x + 1
