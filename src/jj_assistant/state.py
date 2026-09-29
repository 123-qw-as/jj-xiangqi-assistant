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

    def apply(self, move: JJMove) -> dict[str, Any]:
        signature = (move.from_x, move.from_y, move.to_x, move.to_y, move.seat)
        if signature == self.last_signature:
            return {
                "status": "duplicate",
                "fen": self.board.to_fen(),
                "applied_moves": self.applied_moves,
            }

        try:
            captured = self.board.apply(move)
        except ValueError as exc:
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

