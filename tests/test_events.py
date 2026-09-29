import json
import struct

from jj_assistant.events import EventWriter
from jj_assistant.protocol import MSG_CHESS_MOVE


def frame(payload):
    body = json.dumps(payload).encode()
    return struct.pack("<II", MSG_CHESS_MOVE, len(body)) + body


def test_writer_records_minimal_move_event(tmp_path):
    output = tmp_path / "events.jsonl"
    writer = EventWriter(output)
    payload = {
        "matchid": "m1",
        "chessmove_ack_msg": {
            "beginposx": 0,
            "beginposy": 3,
            "endposx": 0,
            "endposy": 4,
            "seat": 1,
        },
    }

    events = writer.record_frame(frame(payload), from_client=False, host="example.test")

    assert events[0]["kind"] == "move"
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["move"]["match_id"] == "m1"
    assert saved["game_state"]["status"] == "applied"
    assert saved["game_state"]["fen"].endswith(" b - - 0 1")
    assert "payload" not in saved


def test_writer_does_not_store_unknown_payload_by_default(tmp_path):
    output = tmp_path / "events.jsonl"
    writer = EventWriter(output)
    writer.record_frame(frame({"token": "secret"}), from_client=True)
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["kind"] == "frame"
    assert saved["payload_keys"] == ["token"]
    assert "payload" not in saved


def test_writer_deduplicates_repeated_move(tmp_path):
    output = tmp_path / "events.jsonl"
    writer = EventWriter(output)
    payload = {
        "matchid": "m1",
        "chessmove_ack_msg": {
            "beginposx": 0,
            "beginposy": 3,
            "endposx": 0,
            "endposy": 4,
            "seat": 1,
        },
    }
    writer.record_frame(frame(payload), from_client=False)
    events = writer.record_frame(frame(payload), from_client=False)
    assert events[0]["game_state"]["status"] == "duplicate"
    assert events[0]["game_state"]["applied_moves"] == 1

