from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from ctypes import wintypes
from pathlib import Path

from .board import XiangqiBoard
from .engine import EngineError, PikafishEngine
from .events import enrich_http_event
from .notation import format_chinese_move
from .protocol import parse_uci_move


class SuggestionOverlay:
    """显示最新的服务器建议；不向 JJ 窗口发送点击或键盘输入。"""

    def __init__(
        self,
        event_path: str | Path,
        *,
        engine_path: str | Path | None = None,
        movetime_ms: int = 1000,
        my_side: str = "red",
    ) -> None:
        if my_side not in {"red", "black"}:
            raise ValueError("我方阵营必须是 red 或 black")
        self.event_path = Path(event_path)
        self.offset = 0
        self.challenge_board: XiangqiBoard | None = None
        self.engine_path = Path(engine_path) if engine_path else None
        self.movetime_ms = movetime_ms
        self.my_side = my_side
        self.engine: PikafishEngine | None = None
        self.engine_busy = False
        self.requested_fen: str | None = None
        self.engine_results: queue.Queue[tuple[str, str | None, str | None]] = queue.Queue()
        self.engine_lock = threading.Lock()
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
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._place_near_jj()

    def run(self) -> None:
        self._poll_events()
        self.root.mainloop()

    def _poll_events(self) -> None:
        self._drain_engine_results()
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
            if self.challenge_board is not None and self._side_to_move() != self.my_side:
                self.value_label.configure(text="等待我方回合…")
                self.detail_label.configure(text=f"已忽略对方建议 · 原始坐标：{uci}")
                return
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
            fen = state.get("fen")
            if isinstance(fen, str) and self._fen_side(fen) != self.my_side:
                self.value_label.configure(text="等待对方走子…")
                self.detail_label.configure(
                    text=f"当前不是我方回合，跳过这一步 · 状态：{state.get('status', 'unknown')}"
                )
            elif self.engine_path and isinstance(fen, str):
                self.value_label.configure(text="正在分析…")
                self.detail_label.configure(text="我方回合 · 正在调用 Pikafish")
                self._schedule_engine(fen)
            else:
                self.value_label.configure(text="等待引擎分析…")
                self.detail_label.configure(text=f"局面状态：{state.get('status', 'unknown')}")

    def _side_to_move(self) -> str | None:
        if self.challenge_board is None:
            return None
        return "red" if self.challenge_board.red_to_move else "black"

    @staticmethod
    def _fen_side(fen: str) -> str | None:
        parts = fen.split()
        if len(parts) < 2 or parts[1] not in {"w", "b"}:
            return None
        return "red" if parts[1] == "w" else "black"

    def _schedule_engine(self, fen: str) -> None:
        self.requested_fen = fen
        if self.engine_busy:
            return
        self.engine_busy = True
        threading.Thread(target=self._analyze_in_background, args=(fen,), daemon=True).start()

    def _analyze_in_background(self, fen: str) -> None:
        try:
            with self.engine_lock:
                if self.engine is None:
                    assert self.engine_path is not None
                    self.engine = PikafishEngine(self.engine_path)
                uci = self.engine.best_move(fen, movetime_ms=self.movetime_ms)
            self.engine_results.put((fen, uci, None))
        except (EngineError, ValueError) as exc:
            self.engine_results.put((fen, None, str(exc)))

    def _drain_engine_results(self) -> None:
        while True:
            try:
                fen, uci, error = self.engine_results.get_nowait()
            except queue.Empty:
                return
            self.engine_busy = False
            if fen == self.requested_fen:
                if error:
                    self.value_label.configure(text="引擎暂不可用")
                    self.detail_label.configure(text=error)
                elif uci:
                    board = XiangqiBoard.from_fen(fen)
                    move = parse_uci_move(uci)
                    chinese = format_chinese_move(board, move) if move else uci
                    self.value_label.configure(text=chinese)
                    self.detail_label.configure(text=f"本地引擎 · 原始坐标：{uci}")
            if self.requested_fen and self.requested_fen != fen:
                self._schedule_engine(self.requested_fen)

    def close(self) -> None:
        if self.engine is not None:
            self.engine.close()
            self.engine = None
        self.root.destroy()

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


def run_overlay(
    event_path: str | Path,
    *,
    engine_path: str | Path | None = None,
    movetime_ms: int = 1000,
    my_side: str = "red",
) -> None:
    SuggestionOverlay(
        event_path,
        engine_path=engine_path,
        movetime_ms=movetime_ms,
        my_side=my_side,
    ).run()

