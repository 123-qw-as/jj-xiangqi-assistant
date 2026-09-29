from __future__ import annotations

import json
import re
import struct
from collections.abc import Iterator, Mapping
from typing import Any

from .models import JJMove, ParsedFrame

HEADER_SIZE = 8
MSG_CHESS_MOVE = 0x03F3
MSG_ACK = 0x0000
MSG_LOBBY = 0x14801
UCI_MOVE_RE = re.compile(r"^[a-i][0-9][a-i][0-9](?:[a-i])?$")


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


def extract_player_side(frame: ParsedFrame) -> str | None:
    """从人机模式大厅请求的 ``isRed`` 推断本机执棋方。"""

    if frame.message_type != MSG_LOBBY:
        return None
    for mapping in _walk_mappings(frame.payload):
        bot_info = mapping.get("chessbotinfo_req_msg")
        if not isinstance(bot_info, Mapping):
            continue
        value = bot_info.get("isRed", bot_info.get("isred"))
        if isinstance(value, bool):
            return "red" if value else "black"
        if isinstance(value, int) and value in {0, 1}:
            return "red" if value == 1 else "black"
        if isinstance(value, str) and value in {"0", "1"}:
            return "red" if value == "1" else "black"
    return None


def extract_side_signals(frame: ParsedFrame) -> list[tuple[str | int | None, str, int]]:
    """提取 JJ 新版协议中的本机座位和红方座位信号。

    人机局有时不再发送 ``isRed``，但会先发送
    ``chesssetcolor_ack_msg.redseat``，随后由客户端发送
    ``chessappinfo_req_msg.seat``。两者结合即可得到本机执棋方。
    """

    if frame.message_type not in {MSG_LOBBY, MSG_CHESS_MOVE}:
        return []
    signals: list[tuple[str | int | None, str, int]] = []
    for mapping, match_id in _walk_mappings_with_match(frame.payload):
        app_info = mapping.get("chessappinfo_req_msg")
        if isinstance(app_info, Mapping):
            seat = _optional_int(app_info.get("seat"))
            if seat is not None:
                signals.append((match_id, "local_seat", seat))
        color_info = mapping.get("chesssetcolor_ack_msg")
        if isinstance(color_info, Mapping):
            red_seat = _optional_int(color_info.get("redseat"))
            if red_seat is not None:
                signals.append((match_id, "red_seat", red_seat))
    return signals


def extract_game_start(frame: ParsedFrame) -> str | int | None:
    """返回新棋局的 matchid；同一桌的多局可能复用该 ID。"""

    if frame.message_type != MSG_CHESS_MOVE:
        return None
    for mapping, match_id in _walk_mappings_with_match(frame.payload):
        if "chesslayoutbegin_ack_msg" in mapping:
            return match_id
    return None


def parse_uci_move(value: Any) -> JJMove | None:
    """把 Pikafish 的 ``a0a1`` 坐标转换为 JJ 坐标。"""

    if not isinstance(value, str) or not UCI_MOVE_RE.fullmatch(value):
        return None
    try:
        return JJMove(
            from_x=ord(value[0]) - ord("a"),
            from_y=int(value[1]),
            to_x=ord(value[2]) - ord("a"),
            to_y=int(value[3]),
        )
    except ValueError:
        return None


def parse_position_order(order: Any) -> tuple[str, list[JJMove]] | None:
    """解析 ``position fen ... moves ...`` 命令。"""

    if not isinstance(order, str) or not order.startswith("position fen "):
        return None
    tokens = order[len("position fen ") :].split()
    if len(tokens) < 6 or len(tokens[0].split("/")) != 10:
        return None
    fen = " ".join(tokens[:6])
    try:
        move_start = tokens.index("moves")
    except ValueError:
        move_tokens: list[str] = []
    else:
        move_tokens = tokens[move_start + 1 :]
    parsed_moves = [parse_uci_move(token) for token in move_tokens]
    if any(move is None for move in parsed_moves):
        return None
    return fen, [move for move in parsed_moves if move is not None]


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


def _walk_mappings(value: Any) -> Iterator[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_mappings(child)
    elif isinstance(value, str):
        # 部分微信版本把内层消息再次编码成 JSON 字符串。
        text = value.strip()
        if not text or text[0] not in "[{":
            return
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            return
        if decoded != value:
            yield from _walk_mappings(decoded)


def _walk_mappings_with_match(
    value: Any, inherited_match_id: str | int | None = None
) -> Iterator[tuple[Mapping[str, Any], str | int | None]]:
    if isinstance(value, Mapping):
        match_id = _direct_match_id(value)
        if match_id is None:
            match_id = inherited_match_id
        yield value, match_id
        for child in value.values():
            yield from _walk_mappings_with_match(child, match_id)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_mappings_with_match(child, inherited_match_id)
    elif isinstance(value, str):
        text = value.strip()
        if not text or text[0] not in "[{":
            return
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            return
        if decoded != value:
            yield from _walk_mappings_with_match(decoded, inherited_match_id)


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

