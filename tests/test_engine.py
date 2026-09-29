import sys

from jj_assistant.engine import PikafishEngine


def test_pikafish_engine_uses_uci_protocol(tmp_path):
    fake = tmp_path / "fake_engine.py"
    fake.write_text(
        """
import sys

for raw in sys.stdin:
    command = raw.strip()
    if command == 'uci':
        print('id name FakePikafish', flush=True)
        print('uciok', flush=True)
    elif command == 'isready':
        print('readyok', flush=True)
    elif command.startswith('go '):
        print('info depth 3 score cp 12', flush=True)
        print('bestmove d8d7', flush=True)
    elif command == 'quit':
        break
""",
        encoding="utf-8",
    )

    with PikafishEngine([sys.executable, "-u", str(fake)]) as engine:
        assert engine.best_move("4k4/9/9/9/9/9/9/9/9/4K4 b - - 0 1") == "d8d7"
