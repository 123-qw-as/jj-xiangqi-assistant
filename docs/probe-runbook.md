# JJ WebSocket 探针现场验证手册

## 目的

确认当前 Windows 微信、WMPF 25715 和 JJ 象棋版本是否仍发送可解析的结构化走棋消息。验证阶段只采集 JJ 小程序进程流量，不修改系统代理，不自动点击棋盘。

## 当前已确认的信息

- 微信小程序宿主进程：`WeChatAppEx.exe`。
- WMPF 运行时版本：`25715`。
- mitmproxy Windows local capture 可以截获该进程访问 `wxminigame.srv.jjmatch.cn` 和 `aetcollector.srv.jjmatch.cn` 的 TLS 连接。
- 未安装探针 CA 时，JJ 会以 `certificate unknown` 拒绝 TLS 握手；停止探针后连接恢复。

## 验证步骤

1. 执行 `scripts\probe-status.ps1`，确认没有遗留探针进程。
2. 经用户确认后执行 `scripts\install-probe-ca.ps1`。证书不存在时脚本先在隐藏的临时 mitmdump 进程中生成，然后只向 `Cert:\CurrentUser\Root` 导入该证书，并在项目根目录保存精确指纹供卸载使用。
3. 执行 `scripts\start-probe.ps1`。默认仅捕获 `WeChatAppEx.exe`。
4. 重新进入 JJ 象棋对局，至少完成十步，期间观察终端是否出现 `JJ MOVE`。
5. 按 `Ctrl+C` 停止探针。
6. 执行 `.\.venv\Scripts\python.exe -m jj_assistant summarize data\jj-events.jsonl`。
7. 执行 `scripts\uninstall-probe-ca.ps1` 移除 CA。

## 成功标准

- 日志出现消息类型 `0x03F3`，每步包含 `game_state.fen`。
- 至少十步的起终点坐标与画面全部一致。
- 重新开局后能区分新的 `match_id`，没有重复或漏步。
- 能确定每一步的 `seat` 和当前行棋方。

若只有二进制帧但无法按 8 字节头解析，开启 `-CaptureUnknown` 仅会额外保存已经成功解码的未知 JSON；原始二进制仍不落盘。若 TLS 成功但完全没有 WebSocket 帧，则转用 WMPFDebugger/CDP 探测运行时网络处理函数。

## 清理与恢复

`Ctrl+C` 会停止 Windows local capture。脚本从不修改系统代理。证书卸载脚本根据当前 mitmproxy CA 文件的 SHA-1 指纹精确删除对应证书，不使用主题名模糊匹配。

