from __future__ import annotations

import queue
import subprocess
import threading
import time
from collections.abc import Sequence
from pathlib import Path


class EngineError(RuntimeError):
    """Pikafish 进程或 UCI 通信失败。"""


class PikafishEngine:
    """Pikafish 的最小 UCI 客户端。"""

    def __init__(
        self,
        command: str | Path | Sequence[str],
        *,
        startup_timeout: float = 8.0,
    ) -> None:
        self.command = self._normalize_command(command)
        self.startup_timeout = startup_timeout
        self._process: subprocess.Popen[str] | None = None
        self._lines: queue.Queue[str] = queue.Queue()
        self._reader: threading.Thread | None = None
        self._lock = threading.Lock()

    @staticmethod
    def _normalize_command(command: str | Path | Sequence[str]) -> list[str]:
        if isinstance(command, (str, Path)):
            return [str(command)]
        values = [str(value) for value in command]
        if not values:
            raise ValueError("Pikafish 命令不能为空")
        return values

    def start(self) -> None:
        if self._process is not None and self._process.poll() is None:
            return
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self._process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creationflags,
            )
        except OSError as exc:
            raise EngineError(f"无法启动 Pikafish：{exc}") from exc

        assert self._process.stdout is not None
        self._reader = threading.Thread(target=self._read_output, daemon=True)
        self._reader.start()
        try:
            self._send("uci")
            self._wait_for("uciok", self.startup_timeout)
            self._send("isready")
            self._wait_for("readyok", self.startup_timeout)
        except Exception:
            self.close()
            raise

    def best_move(self, fen: str, *, movetime_ms: int = 1000) -> str:
        if movetime_ms <= 0:
            raise ValueError("分析时间必须大于 0 毫秒")
        with self._lock:
            self.start()
            self._send(f"position fen {fen}")
            self._send(f"go movetime {movetime_ms}")
            line = self._wait_for("bestmove", max(self.startup_timeout, movetime_ms / 1000 + 5))
            parts = line.split()
            if len(parts) < 2 or parts[1] == "(none)":
                raise EngineError(f"Pikafish 没有返回可行走法：{line}")
            return parts[1]

    def close(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        try:
            if process.poll() is None and process.stdin is not None:
                process.stdin.write("quit\n")
                process.stdin.flush()
            process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            process.kill()
            process.wait(timeout=2)

    def __enter__(self) -> PikafishEngine:
        self.start()
        return self

    def __exit__(self, _exc_type: object, _exc_value: object, _traceback: object) -> None:
        self.close()

    def _send(self, command: str) -> None:
        process = self._process
        if process is None or process.stdin is None or process.poll() is not None:
            raise EngineError("Pikafish 进程未运行")
        try:
            process.stdin.write(command + "\n")
            process.stdin.flush()
        except OSError as exc:
            raise EngineError(f"写入 Pikafish 失败：{exc}") from exc

    def _wait_for(self, prefix: str, timeout: float) -> str:
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise EngineError(f"等待 Pikafish 返回 {prefix} 超时")
            try:
                line = self._lines.get(timeout=remaining)
            except queue.Empty as exc:
                raise EngineError(f"等待 Pikafish 返回 {prefix} 超时") from exc
            if line.startswith(prefix):
                return line

    def _read_output(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        for line in process.stdout:
            self._lines.put(line.strip())
