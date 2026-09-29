import json
import struct

from jj_assistant.events import EventWriter
from jj_assistant.protocol import MSG_CHESS_MOVE, MSG_LOBBY


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


def test_writer_infers_side_from_new_protocol_seat_signals(tmp_path):
    output = tmp_path / "events.jsonl"
    writer = EventWriter(output)
    body = json.dumps(
        {
            "chess_req_msg": {
                "matchid": 7,
                "chessappinfo_req_msg": {"seat": 1},
            }
        }
    ).encode()
    writer.record_frame(struct.pack("<II", MSG_LOBBY, len(body)) + body, from_client=True)

    body = json.dumps(
        {
            "chess_ack_msg": {
                "matchid": 7,
                "chesssetcolor_ack_msg": {"redseat": 0},
            }
        }
    ).encode()
    events = writer.record_frame(
        struct.pack("<II", MSG_CHESS_MOVE, len(body)) + body,
        from_client=False,
    )

    assert events[0]["player_side"] == "black"
    move_body = json.dumps({
        "chess_ack_msg": {
            "matchid": 7,
            "chessmove_ack_msg": {
                "beginposx": 0, "beginposy": 3,
                "endposx": 0, "endposy": 4,
            },
        }
    }).encode()
    move = writer.record_frame(
        struct.pack("<II", MSG_CHESS_MOVE, len(move_body)) + move_body,
        from_client=False,
    )[0]
    assert move["player_side"] == "black"


def test_new_game_resets_board_and_old_seat(tmp_path):
    writer = EventWriter(tmp_path / "events.jsonl")

    def send(payload, *, client=False, message_type=MSG_CHESS_MOVE):
        body = json.dumps(payload).encode()
        return writer.record_frame(
            struct.pack("<II", message_type, len(body)) + body,
            from_client=client,
        )[0]

    send({"chess_req_msg": {"matchid": 7, "chessappinfo_req_msg": {"seat": 1}}},
         client=True, message_type=MSG_LOBBY)
    send({"chess_ack_msg": {"matchid": 7, "chesssetcolor_ack_msg": {"redseat": 0}}})
    send({"chess_ack_msg": {"matchid": 7, "chessmove_ack_msg": {
        "beginposx": 0, "beginposy": 3, "endposx": 0, "endposy": 4,
    }}})

    send({"chess_ack_msg": {"matchid": 7, "chesslayoutbegin_ack_msg": {}}})
    color = send({"chess_ack_msg": {
        "matchid": 7, "chesssetcolor_ack_msg": {"redseat": 1},
    }})
    side = send({"chess_req_msg": {
        "matchid": 7, "chessappinfo_req_msg": {"seat": 1},
    }}, client=True, message_type=MSG_LOBBY)
    first_move = send({"chess_ack_msg": {"matchid": 7, "chessmove_ack_msg": {
        "beginposx": 0, "beginposy": 3, "endposx": 0, "endposy": 4,
    }}})

    assert "player_side" not in color
    assert side["player_side"] == "red"
    assert first_move["game_state"]["status"] == "applied"
    assert first_move["game_state"]["applied_moves"] == 1


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


def test_writer_does_not_resume_analysis_after_a_lost_move(tmp_path):
    writer = EventWriter(tmp_path / "events.jsonl")

    def send(move):
        payload = {"matchid": "m1", "chessmove_ack_msg": move}
        return writer.record_frame(frame(payload), from_client=False)[0]
    first = send({"beginposx": 0, "beginposy": 3, "endposx": 0, "endposy": 4})
    missed = send({"beginposx": 0, "beginposy": 3, "endposx": 0, "endposy": 5})
    later = send({"beginposx": 2, "beginposy": 3, "endposx": 2, "endposy": 4})

    assert first["game_state"]["status"] == "applied"
    assert missed["game_state"]["status"] == "desynced"
    assert later["game_state"]["status"] == "desynced"


def test_writer_rejects_move_from_wrong_color(tmp_path):
    writer = EventWriter(tmp_path / "events.jsonl")
    event = writer.record_frame(frame({"chessmove_ack_msg": {
        "beginposx": 0, "beginposy": 6, "endposx": 0, "endposy": 5,
    }}), from_client=False)[0]
    assert event["game_state"]["status"] == "desynced"


def test_writer_records_challenge_http_json_without_query_or_headers(tmp_path):
    output = tmp_path / "events.jsonl"
    writer = EventWriter(output)

    event = writer.record_http(
        kind="http_request",
        method="POST",
        host="120.133.38.51",
        path="/api/v1/chess/move",
        data=b'{"fen":"test-position","depth":8}',
    )

    assert event["body_encoding"] == "json"
    assert event["body"] == {"fen": "test-position", "depth": 8}
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert set(saved) == {
        "timestamp",
        "kind",
        "method",
        "host",
        "path",
        "status_code",
        "body_size",
        "truncated",
        "body_encoding",
        "body",
    }


def test_writer_base64_encodes_binary_http_body(tmp_path):
    writer = EventWriter(tmp_path / "events.jsonl")
    event = writer.record_http(
        kind="http_response",
        method="POST",
        host="example.test",
        path="/api/v1/chess/move",
        data=b"\xff\x00",
        status_code=200,
    )
    assert event["body_encoding"] == "base64"
    assert event["body"] == "/wA="


def test_writer_extracts_challenge_state_and_suggestion(tmp_path):
    output = tmp_path / "events.jsonl"
    writer = EventWriter(output)
    request = writer.record_http(
        kind="http_request",
        method="POST",
        host="arena.srv.jj.cn",
        path="/api/v1/chess/move",
        data=json.dumps(
            {
                "order": (
                    "position fen 3kn3C/2P1a4/5a2N/9/9/9/9/7RC/1crp1p3/4K4 "
                    "b - - 0 10 moves e9g8"
                ),
                "level": 8,
                "type": 1,
            }
        ).encode(),
    )
    response = writer.record_http(
        kind="http_response",
        method="POST",
        host="arena.srv.jj.cn",
        path="/api/v1/chess/move",
        data=b'{"status":200,"move":"g8e9"}',
        status_code=200,
    )

    assert request["challenge_state"]["initial_fen"].endswith(" b - - 0 10")
    assert request["challenge_state"]["history_uci"] == ["e9g8"]
    assert response["suggestion"]["uci"] == "g8e9"

