from jj_assistant.overlay import SuggestionOverlay


def test_fen_side_mapping():
    assert SuggestionOverlay._fen_side("9/9/9/9/9/9/9/9/9/9 w - - 0 1") == "red"
    assert SuggestionOverlay._fen_side("9/9/9/9/9/9/9/9/9/9 b - - 0 1") == "black"
    assert SuggestionOverlay._fen_side("invalid") is None
