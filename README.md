# JJ 象棋 AI 助手

这是面向 Windows 微信 `JJ象棋` 小程序的本地辅助工具。当前第一阶段提供一个 WebSocket 协议探针，用来确认当前 JJ 版本是否仍会发送结构化走棋消息，并把走棋事件转换为统一数据模型。

## 当前能力

- 解析 JJ 二进制消息的 8 字节帧头：消息类型和 JSON 负载长度均为小端整数。
- 识别 `0x03F3` 走棋消息并提取起点、终点、座位、局时、对局 ID。
- 定向记录残局闯关使用的 `POST /api/v1/chess/move` 请求和响应。
- 维护标准初始局面的 10×9 棋盘，按 JJ 坐标更新并输出 FEN。
- 以 JSONL 保存诊断帧与走棋事件，方便核对当前协议。
- 提供 mitmproxy 插件和 Windows 启动脚本。

## 安装开发环境

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install ".[dev,probe]"
```

## 离线验证

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m jj_assistant self-check
```

## 启动网络探针

经过用户确认后，在项目的 `data/mitmproxy` 中生成一套专用 CA，并安装到当前用户证书库：

```powershell
.\scripts\install-probe-ca.ps1
```

然后启动按进程捕获：

```powershell
.\scripts\start-probe.ps1
```

这里使用普通安装而不是 editable 安装，避免 Python 在部分中文 Windows 环境中按 GBK 读取含中文项目路径的 `.pth` 文件时启动失败。修改源码后需要重新执行安装命令。

启动脚本默认使用 mitmproxy 的 Windows local capture，只捕获名为 `WeChatAppEx.exe` 的进程，不修改 Windows 系统代理。事件写入 `data/jj-events.jsonl`。如果需要普通 HTTP 代理模式，可以运行 `start-probe.ps1 -Mode Regular -Port 8080`。

验证完成后移除当前用户证书库中的探针 CA：

```powershell
.\scripts\uninstall-probe-ca.ps1
```

安装和卸载脚本都按证书指纹操作，不会匹配或删除其他证书。

可以用下面的命令查看采集结果：

```powershell
.\.venv\Scripts\python.exe -m jj_assistant summarize data\jj-events.jsonl
```

另开一个 PowerShell 窗口运行置顶建议面板：

```powershell
.\.venv\Scripts\python.exe -m jj_assistant overlay data\jj-events.jsonl
```

面板只显示建议，不会向 JJ 窗口发送点击或键盘输入。
面板主行显示中文记谱（例如“将四进一”），下方保留原始坐标，便于核对。

## 设计边界

探针默认只处理 `wxminigame.srv.jjmatch.cn`，并只保存帧类型、方向、顶层字段和已经识别的走棋字段，不保存完整未知负载。每个有效走棋事件带有更新后的完整 FEN 和同步状态。使用 `--set jj_capture_unknown=true` 后才会保存未知 JSON 负载。残局关卡还需要从开始消息或视觉识别取得初始局面，不能直接套用标准初始 FEN。

详细的开源项目调研见 [docs/similar-projects-research.md](docs/similar-projects-research.md)。

本机接入步骤与判定标准见 [docs/probe-runbook.md](docs/probe-runbook.md)。

