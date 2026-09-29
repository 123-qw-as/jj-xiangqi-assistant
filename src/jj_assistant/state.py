from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .board import XiangqiBoard
from .models import JJMove


@dataclass(slots=True)
class GameState:
    """把结构化落子事件连续应用到一个标准初始局面。"""

    board: XiangqiBoard = field(default_factory=XiangqiBoard.initial)
    last_signature: tuple[int, int, int, int, int | None] | None = None
    applied_moves: int = 0
    desynced: bool = False

    def apply(self, move: JJMove) -> dict[str, Any]:
        signature = (move.from_x, move.from_y, move.to_x, move.to_y, move.seat)
        if signature == self.last_signature:
            return {
                "status": "duplicate",
                "fen": self.board.to_fen(),
                "applied_moves": self.applied_moves,
            }

        if self.desynced:
            return {
                "status": "desynced",
                "fen": self.board.to_fen(),
                "applied_moves": self.applied_moves,
                "error": "棋局已失步，等待下一局重新同步",
            }

        try:
            piece = self.board.piece_at(move.from_x, move.from_y)
            if piece is not None and piece.isupper() != self.board.red_to_move:
                raise ValueError("走子方与棋盘回合不符，可能发生漏帧")
            captured = self.board.apply(move)
        except ValueError as exc:
            self.desynced = True
            return {
                "status": "desynced",
                "fen": self.board.to_fen(),
                "applied_moves": self.applied_moves,
                "error": str(exc),
            }

        self.last_signature = signature
        self.applied_moves += 1
        return {
            "status": "applied",
            "fen": self.board.to_fen(),
            "applied_moves": self.applied_moves,
            "captured": captured,
        }

