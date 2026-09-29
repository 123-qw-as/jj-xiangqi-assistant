from __future__ import annotations

import argparse
import json
import struct
import sys
from collections import Counter
from pathlib import Path

from .board import XiangqiBoard
from .protocol import MSG_CHESS_MOVE, extract_moves, parse_frame


def _sample_frame() -> bytes:
    payload = {
        "matchid": "self-check",
        "chess_ack_msg": {
            "chessmove_ack_msg": {
                "beginposx": 0,
                "beginposy": 3,
                "endposx": 0,
                "endposy": 4,
                "seat": 1,
                "roundtime": 2,
                "islocal": 0,
            }
        },
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return struct.pack("<II", MSG_CHESS_MOVE, len(body)) + body


def self_check() -> int:
    frame = parse_frame(_sample_frame())
    moves = extract_moves(frame)
    if len(moves) != 1:
        print("自检失败：没有提取到唯一走棋", file=sys.stderr)
        return 1
    board = XiangqiBoard.initial()
    board.apply(moves[0])
    print(f"协议解析正常：{frame.message_type_hex}")
    print(f"示例走棋：{moves[0].from_x},{moves[0].from_y} -> {moves[0].to_x},{moves[0].to_y}")
    print(f"更新后 FEN：{board.to_fen()}")
    return 0


def summarize(path: Path) -> int:
    if not path.exists():
        print(f"找不到日志：{path}", file=sys.stderr)
        return 2
    counts: Counter[str] = Counter()
    types: Counter[str] = Counter()
    moves = []
    suggestions = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                print(f"忽略第 {line_number} 行：不是 JSON", file=sys.stderr)
                continue
            counts[event.get("kind", "unknown")] += 1
            if "message_type_hex" in event:
                types[event["message_type_hex"]] += 1
            if event.get("kind") == "move":
                moves.append(event)
            if event.get("suggestion"):
                suggestions.append(event["suggestion"])
    print("事件统计：", dict(counts))
    print("消息类型：", dict(types))
    print(f"已识别走棋：{len(moves)} 步")
    challenge_requests = counts["http_request"]
    challenge_responses = counts["http_response"]
    if challenge_requests or challenge_responses:
        print(f"残局接口：{challenge_requests} 个请求 / {challenge_responses} 个响应")
        print(f"残局推荐走法：{len(suggestions)} 个")
        for suggestion in suggestions[-5:]:
            print(f"  suggestion: {suggestion['uci']}")
    for index, event in enumerate(moves[-10:], start=max(1, len(moves) - 9)):
        move = event["move"]
        game_state = event.get("game_state", {})
        print(
            f"  {index}. ({move['from_x']},{move['from_y']}) -> "
            f"({move['to_x']},{move['to_y']}) seat={move.get('seat')} "
            f"state={game_state.get('status')}"
        )
        if game_state.get("fen"):
            print(f"     FEN: {game_state['fen']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="JJ 象棋 AI 助手")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("self-check", help="运行离线协议与 FEN 自检")
    summary_parser = subparsers.add_parser("summarize", help="汇总探针 JSONL 日志")
    summary_parser.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    if args.command == "self-check":
        return self_check()
    if args.command == "summarize":
        return summarize(args.path)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

