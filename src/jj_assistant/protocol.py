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

    if not isinstance(frame.payload, Mapping):
        return []

    match_id = _first_value(frame.payload, ("matchid", "match_id", "matchId"))
    moves: list[JJMove] = []
    for candidate in _named_mappings(frame.payload, "chessmove_ack_msg"):
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


def _named_mappings(value: Any, target: str) -> Iterator[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == target:
                if isinstance(child, Mapping):
                    yield child
                elif isinstance(child, list):
                    yield from (item for item in child if isinstance(item, Mapping))
            yield from _named_mappings(child, target)
    elif isinstance(value, list):
        for child in value:
            yield from _named_mappings(child, target)


def _first_value(value: Any, keys: tuple[str, ...]) -> str | int | None:
    if isinstance(value, Mapping):
        for key in keys:
            candidate = value.get(key)
            if isinstance(candidate, (str, int)) and not isinstance(candidate, bool):
                return candidate
        for child in value.values():
            found = _first_value(child, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _first_value(child, keys)
            if found is not None:
                return found
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

