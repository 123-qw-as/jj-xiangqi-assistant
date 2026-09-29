"""mitmproxy 插件：``mitmdump -s src/jj_assistant/mitm_addon.py``。"""

from __future__ import annotations

from pathlib import Path

try:
    from mitmproxy import ctx, http
except ImportError:  # 允许在未安装 probe 依赖时导入核心包
    ctx = None  # type: ignore[assignment]
    http = None  # type: ignore[assignment]

from jj_assistant.events import EventWriter

CHALLENGE_MOVE_PATH = "/api/v1/chess/move"


class JJWebSocketProbe:
    def __init__(self) -> None:
        self.writer: EventWriter | None = None

    def load(self, loader) -> None:  # pragma: no cover - 由 mitmproxy 调用
        loader.add_option("jj_output", str, "data/jj-events.jsonl", "JJ 事件 JSONL 输出路径")
        loader.add_option("jj_capture_unknown", bool, False, "保存未知 JSON 负载")
        loader.add_option(
            "jj_hosts",
            str,
            "wxminigame.srv.jjmatch.cn",
            "逗号分隔的 JJ 游戏 WebSocket 域名",
        )

    def running(self) -> None:  # pragma: no cover - 由 mitmproxy 调用
        output = Path(ctx.options.jj_output).resolve()
        self.writer = EventWriter(output, capture_unknown=ctx.options.jj_capture_unknown)
        ctx.log.info(f"JJ 协议探针已启动，事件输出：{output}")

    def websocket_message(self, flow) -> None:  # pragma: no cover - 由 mitmproxy 调用
        if self.writer is None or flow.websocket is None or not flow.websocket.messages:
            return
        message = flow.websocket.messages[-1]
        if message.is_text:
            return
        host = flow.request.pretty_host if flow.request else None
        allowed_hosts = {
            item.strip().lower() for item in ctx.options.jj_hosts.split(",") if item.strip()
        }
        if host is None or host.lower() not in allowed_hosts:
            return
        events = self.writer.record_frame(
            bytes(message.content), from_client=message.from_client, host=host
        )
        for event in events:
            if event["kind"] == "move":
                move = event["move"]
                ctx.log.alert(
                    "JJ MOVE "
                    f"({move['from_x']},{move['from_y']}) -> ({move['to_x']},{move['to_y']}) "
                    f"seat={move['seat']} match={move['match_id']}"
                )

    def request(self, flow) -> None:  # pragma: no cover - 由 mitmproxy 调用
        if self.writer is None or not _is_challenge_move(flow):
            return
        event = self.writer.record_http(
            kind="http_request",
            method=flow.request.method,
            host=flow.request.pretty_host,
            path=CHALLENGE_MOVE_PATH,
            data=flow.request.raw_content or b"",
        )
        ctx.log.alert(f"JJ CHALLENGE REQUEST {event['body']}")

    def response(self, flow) -> None:  # pragma: no cover - 由 mitmproxy 调用
        if self.writer is None or flow.response is None or not _is_challenge_move(flow):
            return
        event = self.writer.record_http(
            kind="http_response",
            method=flow.request.method,
            host=flow.request.pretty_host,
            path=CHALLENGE_MOVE_PATH,
            data=flow.response.raw_content or b"",
            status_code=flow.response.status_code,
        )
        ctx.log.alert(f"JJ CHALLENGE RESPONSE {event['body']}")


def _is_challenge_move(flow) -> bool:
    if flow.request is None or flow.request.method.upper() != "POST":
        return False
    return flow.request.path.split("?", 1)[0] == CHALLENGE_MOVE_PATH


addons = [JJWebSocketProbe()]

