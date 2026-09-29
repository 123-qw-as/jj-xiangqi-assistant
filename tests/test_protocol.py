import json
import struct

import pytest

from jj_assistant.protocol import MSG_CHESS_MOVE, ProtocolError, extract_moves, parse_frame


def make_frame(payload, message_type=MSG_CHESS_MOVE, trailing=b""):
    body = json.dumps(payload).encode()
    return struct.pack("<II", message_type, len(body)) + body + trailing


def test_parses_header_json_and_trailing_bytes():
    frame = parse_frame(make_frame({"ok": True}, message_type=7, trailing=b"xx"))

    assert frame.message_type == 7
    assert frame.payload == {"ok": True}
    assert frame.trailing_bytes == 2
    assert frame.message_type_hex == "0x0007"


def test_extracts_nested_move_and_match_id():
    payload = {
        "wrapper": {
            "matchid": 42,
            "chess_ack_msg": {
                "chessmove_ack_msg": {
                    "beginposx": "1",
                    "beginposy": 2,
                    "endposx": 3,
                    "endposy": 4,
                    "seat": "2",
                    "roundtime": "1.5",
                    "islocal": 0,
                }
            },
        }
    }

    moves = extract_moves(parse_frame(make_frame(payload)))

    assert len(moves) == 1
    assert moves[0].from_x == 1
    assert moves[0].to_y == 4
    assert moves[0].seat == 2
    assert moves[0].round_time == 1.5
    assert moves[0].is_local is False
    assert moves[0].match_id == 42


def test_rejects_short_or_truncated_frames():
    with pytest.raises(ProtocolError, match="小于 8"):
        parse_frame(b"123")
    with pytest.raises(ProtocolError, match="实际只有"):
        parse_frame(struct.pack("<II", 1, 10) + b"{}")


def test_ignores_invalid_move_coordinates():
    payload = {"chessmove_ack_msg": {"beginposx": 99, "beginposy": 0, "endposx": 0, "endposy": 1}}
    assert extract_moves(parse_frame(make_frame(payload))) == []


def test_ignores_move_shape_in_unrelated_message_type():
    payload = {
        "chessmove_ack_msg": {
            "beginposx": 0,
            "beginposy": 3,
            "endposx": 0,
            "endposy": 4,
        }
    }
    assert extract_moves(parse_frame(make_frame(payload, message_type=7))) == []


def test_uses_nearest_match_id_for_each_move_branch():
    payload = {
        "matchid": "outer",
        "games": [
            {
                "matchid": "first",
                "chessmove_ack_msg": {
                    "beginposx": 0,
                    "beginposy": 3,
                    "endposx": 0,
                    "endposy": 4,
                },
            },
            {
                "matchid": "second",
                "chessmove_ack_msg": {
                    "beginposx": 2,
                    "beginposy": 3,
                    "endposx": 2,
                    "endposy": 4,
                },
            },
        ],
    }
    moves = extract_moves(parse_frame(make_frame(payload)))
    assert [move.match_id for move in moves] == ["first", "second"]

