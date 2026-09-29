from __future__ import annotations

import json
import threading
from base64 import b64encode
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .protocol import (
    extract_moves,
    extract_player_side,
    extract_side_signals,
    parse_frame,
    parse_position_order,
    parse_uci_move,
    payload_keys,
)
from .state import GameState


class EventWriter:
    def __init__(self, output_path: str | Path, *, capture_unknown: bool = False) -> None:
        self.output_path = Path(output_path)
        self.capture_unknown = capture_unknown
        self._lock = threading.Lock()
        self._games: dict[str, GameState] = {}
        self._red_seats: dict[str, int] = {}
        self._local_seats: dict[str, int] = {}

    def record_frame(
        self,
        data: bytes,
        *,
        from_client: bool,
        host: str | None = None,
    ) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc).astimezone().isoformat()
        try:
            frame = parse_frame(data)
        except ValueError as exc:
            event = {
                "timestamp": now,
                "kind": "unparsed_binary",
                "direction": "client_to_server" if from_client else "server_to_client",
                "host": host,
                "size": len(data),
                "error": str(exc),
            }
            self._append(event)
            return [event]

        base = {
            "timestamp": now,
            "direction": "client_to_server" if from_client else "server_to_client",
            "host": host,
            "message_type": frame.message_type,
            "message_type_hex": frame.message_type_hex,
            "declared_length": frame.declared_length,
            "trailing_bytes": frame.trailing_bytes,
            "payload_keys": payload_keys(frame.payload),
        }
        player_side = extract_player_side(frame)
        for match_id, signal, seat in extract_side_signals(frame):
            state_key = str(match_id) if match_id is not None else f"unknown@{host}"
            if signal == "red_seat":
                self._red_seats[state_key] = seat
            else:
                self._local_seats[state_key] = seat
            if player_side is None:
                red_seat = self._red_seats.get(state_key)
                local_seat = self._local_seats.get(state_key)
                if red_seat is not None and local_seat is not None:
                    player_side = "red" if local_seat == red_seat else "black"
        if player_side is not None:
            base["player_side"] = player_side
        moves = extract_moves(frame)
        events: list[dict[str, Any]] = []
        if moves:
            for move in moves:
                state_key = str(move.match_id) if move.match_id is not None else f"unknown@{host}"
                game = self._games.setdefault(state_key, GameState())
                events.append(
                    {
                        **base,
                        "kind": "move",
                        "move": move.as_dict(),
                        "game_state": game.apply(move),
                    }
                )
        else:
            event = {**base, "kind": "frame"}
            if self.capture_unknown:
                event["payload"] = frame.payload
            events.append(event)

        for event in events:
            self._append(event)
        return events

    def record_http(
        self,
        *,
        kind: str,
        method: str,
        host: str,
        path: str,
        data: bytes,
        status_code: int | None = None,
    ) -> dict[str, Any]:
        """记录定向棋局 HTTP 接口，不包含查询参数和请求头。"""

        if kind not in {"http_request", "http_response"}:
            raise ValueError(f"不支持的 HTTP 事件类型：{kind}")
        event: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
            "kind": kind,
            "method": method,
            "host": host,
            "path": path,
            "status_code": status_code,
            "body_size": len(data),
        }
        limited = data[:262_144]
        event["truncated"] = len(limited) != len(data)
        try:
            text = limited.decode("utf-8")
        except UnicodeDecodeError:
            event["body_encoding"] = "base64"
            event["body"] = b64encode(limited).decode("ascii")
        else:
            event["body_encoding"] = "json"
            try:
                event["body"] = json.loads(text)
            except json.JSONDecodeError:
                event["body_encoding"] = "utf-8"
                event["body"] = text
        enrich_http_event(event)
        self._append(event)
        return event

    def _append(self, event: dict[str, Any]) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        with self._lock, self.output_path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")


def enrich_http_event(event: dict[str, Any]) -> None:
    body = event.get("body")
    if not isinstance(body, dict) or event["path"] != "/api/v1/chess/move":
        return
    if event["kind"] == "http_request":
        parsed = parse_position_order(body.get("order"))
        if parsed is None:
            return
        fen, moves = parsed
        event["challenge_state"] = {
            "initial_fen": fen,
            "history": [move.as_dict() for move in moves],
            "history_uci": body["order"].split(" moves ", 1)[1].split()
            if " moves " in body["order"]
            else [],
            "level": body.get("level"),
            "type": body.get("type"),
        }
    elif event["kind"] == "http_response":
        move = parse_uci_move(body.get("move"))
        if move is not None:
            event["suggestion"] = {"uci": body["move"], "move": move.as_dict()}

