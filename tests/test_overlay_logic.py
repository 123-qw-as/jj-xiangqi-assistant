import json
import queue

from jj_assistant.board import XiangqiBoard
from jj_assistant.overlay import SuggestionOverlay


class Label:
    def __init__(self):
        self.values = {}

    def configure(self, **kwargs):
        self.values.update(kwargs)


def test_fen_side_mapping():
    assert SuggestionOverlay._fen_side("9/9/9/9/9/9/9/9/9/9 w - - 0 1") == "red"
    assert SuggestionOverlay._fen_side("9/9/9/9/9/9/9/9/9/9 b - - 0 1") == "black"
    assert SuggestionOverlay._fen_side("invalid") is None


def test_overlay_replays_only_recent_log_tail(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_bytes(b"old event\n" * 10 + b"latest event\n")
    overlay = object.__new__(SuggestionOverlay)
    overlay.event_path = path
    overlay.MAX_REPLAY_BYTES = 20

    offset = overlay._initial_offset()

    assert path.read_bytes()[offset:] == b"latest event\n"


def test_server_opponent_move_is_applied_before_local_analysis():
    overlay = object.__new__(SuggestionOverlay)
    overlay.challenge_board = XiangqiBoard.initial()
    overlay.challenge_board.red_to_move = False
    overlay.my_side = "red"
    overlay.engine_path = "fake-pikafish.exe"
    overlay.value_label = Label()
    overlay.detail_label = Label()
    scheduled = []
    overlay._schedule_engine = lambda fen: scheduled.append(fen)

    overlay._handle_server_suggestion({}, {"uci": "g6g5"})

    assert overlay.challenge_board.red_to_move is True
    assert scheduled == [overlay.challenge_board.to_fen()]
    assert overlay.value_label.values["text"] == "正在分析我方…"


def test_auto_side_is_inferred_from_server_suggestion():
    overlay = object.__new__(SuggestionOverlay)
    overlay.challenge_board = XiangqiBoard.initial()
    overlay.challenge_board.red_to_move = False
    overlay.my_side = None
    overlay.auto_side = True
    overlay.engine_path = "fake-pikafish.exe"
    overlay.value_label = Label()
    overlay.detail_label = Label()
    scheduled = []
    overlay._schedule_engine = lambda fen: scheduled.append(fen)

    overlay._handle_server_suggestion({}, {"uci": "g6g5"})

    assert overlay.my_side == "red"
    assert scheduled == [overlay.challenge_board.to_fen()]


def test_overlay_skips_desynced_position():
    overlay = object.__new__(SuggestionOverlay)
    overlay.my_side = "red"
    overlay.auto_side = True
    overlay.engine_path = "fake-pikafish.exe"
    overlay.value_label = Label()
    overlay.detail_label = Label()
    overlay.requested_fen = "old"
    scheduled = []
    overlay._schedule_engine = lambda fen: scheduled.append(fen)
    overlay._handle_line(json.dumps({
        "kind": "move",
        "game_state": {"status": "desynced", "fen": XiangqiBoard.initial().to_fen()},
    }))
    assert scheduled == []
    assert overlay.requested_fen is None


def test_overlay_discards_result_after_turn_changed():
    overlay = object.__new__(SuggestionOverlay)
    overlay.my_side = "red"
    overlay.value_label = Label()
    overlay.detail_label = Label()
    fen = XiangqiBoard.initial().to_fen()
    overlay.requested_fen = None
    overlay.engine_busy = True
    overlay.engine_results = queue.Queue()
    overlay.engine_results.put((fen, "a3a4", None))
    overlay._drain_engine_results()
    assert "text" not in overlay.value_label.values
