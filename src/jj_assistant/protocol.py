from __future__ import annotations

import json
import struct
from collections.abc import Iterator, Mapping
from typing import Any

from .models import JJMove, ParsedFrame

HEADER_SIZE = 8
MSG_CHESS_MOVE = 0x03F3
MSG_ACK = 0x0000
MSG_LOBBY = 0x14801


class ProtocolError(ValueError):
    """输入不符合已知 JJ 帧格式。"""


def parse_frame(data: bytes) -> ParsedFrame:
    """解析 ``<uint32 type><uint32 length><JSON>`` 格式的二进制帧。"""

    if len(data) < HEADER_SIZE:
        raise ProtocolError(f"帧长度 {len(data)} 小于 8 字节帧头")

    message_type, declared_length = struct.unpack_from("<II", data)
    available = len(data) - HEADER_SIZE
    if declared_length > available:
        raise ProtocolError(f"负载声明 {declared_length} 字节，实际只有 {available} 字节")

    payload_bytes = data[HEADER_SIZE : HEADER_SIZE + declared_length]
    try:
        payload_text = payload_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProtocolError(f"负载不是 UTF-8：{exc}") from exc

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"负载不是 JSON：{exc}") from exc

    return ParsedFrame(
        message_type=message_type,
        declared_length=declared_length,
        payload=payload,
        trailing_bytes=available - declared_length,
    )


def extract_moves(frame: ParsedFrame) -> list[JJMove]:
    """从帧的任意嵌套位置提取 ``chessmove_ack_msg``。"""

    if frame.message_type != MSG_CHESS_MOVE or not isinstance(frame.payload, Mapping):
        return []

    moves: list[JJMove] = []
    for candidate, match_id in _move_mappings(frame.payload):
        try:
            move = JJMove(
                from_x=_required_int(candidate, "beginposx"),
                from_y=_required_int(candidate, "beginposy"),
                to_x=_required_int(candidate, "endposx"),
                to_y=_required_int(candidate, "endposy"),
                seat=_optional_int(candidate.get("seat")),
                round_time=_optional_number(candidate.get("roundtime")),
                is_local=_optional_bool(candidate.get("islocal")),
                match_id=match_id,
            )
        except (TypeError, ValueError, KeyError):
            continue
        moves.append(move)
    return moves


def payload_keys(payload: Any) -> list[str]:
    if not isinstance(payload, Mapping):
        return []
    return sorted(str(key) for key in payload)


def _move_mappings(
    value: Any, inherited_match_id: str | int | None = None
) -> Iterator[tuple[Mapping[str, Any], str | int | None]]:
    if isinstance(value, Mapping):
        match_id = _direct_match_id(value)
        if match_id is None:
            match_id = inherited_match_id
        for key, child in value.items():
            if key == "chessmove_ack_msg":
                if isinstance(child, Mapping):
                    yield child, match_id
                elif isinstance(child, list):
                    yield from (
                        (item, match_id) for item in child if isinstance(item, Mapping)
                    )
                continue
            yield from _move_mappings(child, match_id)
    elif isinstance(value, list):
        for child in value:
            yield from _move_mappings(child, inherited_match_id)


def _direct_match_id(value: Mapping[str, Any]) -> str | int | None:
    for key in ("matchid", "match_id", "matchId"):
        candidate = value.get(key)
        if isinstance(candidate, (str, int)) and not isinstance(candidate, bool):
            return candidate
    return None


def _required_int(mapping: Mapping[str, Any], key: str) -> int:
    if key not in mapping:
        raise KeyError(key)
    value = _optional_int(mapping[key])
    if value is None:
        raise TypeError(f"{key} 不是整数")
    return value


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    return None


def _optional_number(value: Any) -> int | float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return float(value) if "." in value else int(value)
    return None


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if value in (0, "0"):
        return False
    if value in (1, "1"):
        return True
    return None

