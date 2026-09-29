from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class JJMove:
    """JJ 坐标系中的一步棋。y=0 是红方底线，y=9 是黑方底线。"""

    from_x: int
    from_y: int
    to_x: int
    to_y: int
    seat: int | None = None
    round_time: int | float | None = None
    is_local: bool | None = None
    match_id: str | int | None = None

    def __post_init__(self) -> None:
        for name, value, upper in (
            ("from_x", self.from_x, 8),
            ("to_x", self.to_x, 8),
            ("from_y", self.from_y, 9),
            ("to_y", self.to_y, 9),
        ):
            if not 0 <= value <= upper:
                raise ValueError(f"{name}={value} 超出 JJ 棋盘坐标范围")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ParsedFrame:
    message_type: int
    declared_length: int
    payload: Any
    trailing_bytes: int = 0

    @property
    def message_type_hex(self) -> str:
        return f"0x{self.message_type:04X}"

