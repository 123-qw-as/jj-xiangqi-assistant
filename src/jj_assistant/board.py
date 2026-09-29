from __future__ import annotations

from dataclasses import dataclass, field

from .models import JJMove

INITIAL_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w"


@dataclass(slots=True)
class XiangqiBoard:
    """最小棋局状态，用于验证网络坐标是否能连续生成 FEN。"""

    rows: list[list[str | None]] = field(default_factory=list)
    red_to_move: bool = True

    @classmethod
    def initial(cls) -> XiangqiBoard:
        return cls.from_fen(INITIAL_FEN)

    @classmethod
    def from_fen(cls, fen: str) -> XiangqiBoard:
        parts = fen.split()
        if not parts:
            raise ValueError("FEN 不能为空")
        row_tokens = parts[0].split("/")
        if len(row_tokens) != 10:
            raise ValueError("中国象棋 FEN 必须包含 10 行")

        rows: list[list[str | None]] = []
        for token in row_tokens:
            row: list[str | None] = []
            for char in token:
                if char.isdigit():
                    row.extend([None] * int(char))
                else:
                    row.append(char)
            if len(row) != 9:
                raise ValueError("每一行必须展开为 9 列")
            rows.append(row)
        return cls(rows=rows, red_to_move=len(parts) < 2 or parts[1] == "w")

    def apply(self, move: JJMove) -> str | None:
        source_row = 9 - move.from_y
        target_row = 9 - move.to_y
        piece = self.rows[source_row][move.from_x]
        if piece is None:
            raise ValueError(
                f"起点 ({move.from_x},{move.from_y}) 没有棋子，可能缺少初始局面或发生漏帧"
            )
        captured = self.rows[target_row][move.to_x]
        self.rows[target_row][move.to_x] = piece
        self.rows[source_row][move.from_x] = None
        self.red_to_move = not self.red_to_move
        return captured

    def to_fen(self) -> str:
        encoded_rows: list[str] = []
        for row in self.rows:
            parts: list[str] = []
            empty = 0
            for piece in row:
                if piece is None:
                    empty += 1
                else:
                    if empty:
                        parts.append(str(empty))
                        empty = 0
                    parts.append(piece)
            if empty:
                parts.append(str(empty))
            encoded_rows.append("".join(parts))
        return f"{'/'.join(encoded_rows)} {'w' if self.red_to_move else 'b'}"

