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
