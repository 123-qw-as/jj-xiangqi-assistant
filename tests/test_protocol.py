import json
import struct

import pytest

from jj_assistant.protocol import (
    MSG_CHESS_MOVE,
    MSG_LOBBY,
    ProtocolError,
    extract_moves,
    extract_player_side,
    extract_side_signals,
    parse_frame,
    parse_position_order,
    parse_uci_move,
)


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


def test_extracts_human_side_from_bot_info():
    payload = {
        "lobby_req_msg": {
            "chessbotinfo_req_msg": {"matchid": 7, "isRed": 0},
        }
    }

    frame = parse_frame(make_frame(payload, message_type=MSG_LOBBY))

    assert extract_player_side(frame) == "black"


def test_extracts_human_side_from_json_encoded_bot_info():
    payload = {
        "lobby_req_msg": {},
        "param": json.dumps({"chessbotinfo_req_msg": {"isRed": 1}}),
    }

    frame = parse_frame(make_frame(payload, message_type=MSG_LOBBY))

    assert extract_player_side(frame) == "red"


def test_extracts_new_protocol_side_signals():
    color = {
        "chess_ack_msg": {
            "matchid": 7,
            "chesssetcolor_ack_msg": {"redseat": 0},
        }
    }
    app = {
        "chess_req_msg": {
            "matchid": 7,
            "chessappinfo_req_msg": {"seat": 1},
        }
    }

    assert extract_side_signals(parse_frame(make_frame(color, MSG_CHESS_MOVE))) == [
        (7, "red_seat", 0)
    ]
    assert extract_side_signals(parse_frame(make_frame(app, MSG_LOBBY))) == [
        (7, "local_seat", 1)
    ]


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


def test_parses_uci_move_and_position_order():
    move = parse_uci_move("e9g8")
    assert move is not None
    assert (move.from_x, move.from_y, move.to_x, move.to_y) == (4, 9, 6, 8)

    parsed = parse_position_order(
        "position fen 3kn3C/2P1a4/5a2N/9/9/9/9/7RC/1crp1p3/4K4 b - - 0 10 moves e9g8 h2h9"
    )
    assert parsed is not None
    fen, history = parsed
    assert fen.endswith(" b - - 0 10")
    assert [(item.from_x, item.to_y) for item in history] == [(4, 8), (7, 9)]

