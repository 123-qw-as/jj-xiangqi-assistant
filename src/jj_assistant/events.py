from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .protocol import extract_moves, parse_frame, payload_keys


class EventWriter:
    def __init__(self, output_path: str | Path, *, capture_unknown: bool = False) -> None:
        self.output_path = Path(output_path)
        self.capture_unknown = capture_unknown
        self._lock = threading.Lock()

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
        moves = extract_moves(frame)
        events: list[dict[str, Any]] = []
        if moves:
            for move in moves:
                events.append({**base, "kind": "move", "move": move.as_dict()})
        else:
            event = {**base, "kind": "frame"}
            if self.capture_unknown:
                event["payload"] = frame.payload
            events.append(event)

        for event in events:
            self._append(event)
        return events

    def _append(self, event: dict[str, Any]) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        with self._lock, self.output_path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")

