from __future__ import annotations

import json
import tkinter as tk
from ctypes import wintypes
from pathlib import Path

from .board import XiangqiBoard
from .events import enrich_http_event
from .notation import format_chinese_move
from .protocol import parse_uci_move


class SuggestionOverlay:
    """显示最新的服务器建议；不向 JJ 窗口发送点击或键盘输入。"""

    def __init__(self, event_path: str | Path) -> None:
        self.event_path = Path(event_path)
        self.offset = 0
        self.challenge_board: XiangqiBoard | None = None
        self.root = tk.Tk()
        self.root.title("JJ 建议")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.92)
        self.root.configure(bg="#1f2937")
        self.frame = tk.Frame(self.root, bg="#1f2937", padx=12, pady=8)
        self.frame.pack(fill="both", expand=True)
        self.title_label = tk.Label(
            self.frame,
            text="JJ 象棋助手",
            font=("Microsoft YaHei UI", 10, "bold"),
            bg="#1f2937",
            fg="#f9fafb",
        )
        self.title_label.pack(anchor="w")
        self.value_label = tk.Label(
            self.frame,
            text="等待棋局消息…",
            font=("Consolas", 16, "bold"),
            bg="#1f2937",
            fg="#fbbf24",
        )
        self.value_label.pack(anchor="w", pady=(4, 0))
        self.detail_label = tk.Label(
            self.frame,
            text="",
            font=("Microsoft YaHei UI", 9),
            bg="#1f2937",
            fg="#d1d5db",
        )
        self.detail_label.pack(anchor="w")
        self._place_near_jj()

    def run(self) -> None:
        self._poll_events()
        self.root.mainloop()

    def _poll_events(self) -> None:
        if self.event_path.exists():
            with self.event_path.open("r", encoding="utf-8") as stream:
                stream.seek(self.offset)
                for line in stream:
                    self._handle_line(line)
                self.offset = stream.tell()
        self.root.after(200, self._poll_events)

    def _handle_line(self, line: str) -> None:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return
        if event.get("kind") in {"http_request", "http_response"}:
            enrich_http_event(event)
        if event.get("kind") == "http_request":
            self.challenge_board = self._board_from_request(event)
        suggestion = event.get("suggestion")
        if suggestion:
            uci = suggestion.get("uci", "未知走法")
            move = parse_uci_move(uci)
            chinese = (
                format_chinese_move(self.challenge_board, move)
                if move is not None and self.challenge_board is not None
                else uci
            )
            self.value_label.configure(text=chinese)
            body = event.get("body") or {}
            self.detail_label.configure(
                text=(
                    f"原始坐标：{uci} · 服务器建议 · "
                    f"{event.get('host', '')} · {body.get('message', '')}"
                )
            )
        elif event.get("kind") == "move":
            state = event.get("game_state") or {}
            self.value_label.configure(text="等待引擎分析…")
            self.detail_label.configure(text=f"局面状态：{state.get('status', 'unknown')}")

    @staticmethod
    def _board_from_request(event: dict) -> XiangqiBoard | None:
        state = event.get("challenge_state")
        if not isinstance(state, dict):
            return None
        fen = state.get("initial_fen")
        history = state.get("history_uci")
        if not isinstance(fen, str) or not isinstance(history, list):
            return None
        try:
            board = XiangqiBoard.from_fen(fen)
            for uci in history:
                move = parse_uci_move(uci)
                if move is None:
                    return None
                board.apply(move)
            return board
        except (TypeError, ValueError):
            return None

    def _place_near_jj(self) -> None:
        try:
            import ctypes

            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, "JJ象棋")
            rect = wintypes.RECT()
            if hwnd and user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                x = max(0, rect.right - 300)
                y = max(0, rect.top + 60)
                self.root.geometry(f"280x92+{x}+{y}")
                return
        except (AttributeError, OSError):
            pass
        self.root.geometry("280x92+20+80")


def run_overlay(event_path: str | Path) -> None:
    SuggestionOverlay(event_path).run()

