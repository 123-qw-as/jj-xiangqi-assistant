# Windows 微信 JJ 象棋 AI 辅助项目调研

> 调研日期：2026-09-29  
> 范围：公开 GitHub 仓库、仓库源码、README、许可证和官方项目文档。维护时间以各仓库默认分支在本次调研时的最新提交为准。

## 结论

已经有一个与目标几乎完全相同的项目：[YoungerIOS/chess-helper-app](https://github.com/YoungerIOS/chess-helper-app)。它明确支持微信里的 JJ 象棋和天天象棋，实际源码走的是“窗口截图 → 霍夫圆定位棋盘 → JJ 专用 ONNX 棋子分类 → 稳定帧和局面连续性校验 → FEN → Pikafish → 侧边棋盘箭头”的路线。它是视觉方案最值得借鉴的代码库，但公开安装说明仍以 macOS 为主；源码虽然写了 Windows 窗口枚举分支，Windows 引擎路径、权限和打包流程仍需补齐。

Windows 上更成熟的通用底座是 [sojourners/public-Xiangqi](https://github.com/sojourners/public-Xiangqi)。它的“连线”功能已经实现 Windows 窗口选择、前台或 `PrintWindow` 后台截图、YOLOv11 ONNX 棋盘识别、连续局面差分、动画稳定确认、UCI/UCCI 引擎接入和观战分析模式。若接受 Java/JavaFX 与 GPLv3，它比从零写截图和状态同步更接近可运行产品。

网络方案也有直接先例：[JulyBear/chess-coach](https://github.com/JulyBear/chess-coach) 不是只有概念说明，源码确实用 mitmproxy 解析 JJ 象棋 WebSocket 二进制帧，从消息中读取 `matchid`、起终点坐标、座位和用时，再逐步生成 FEN。它说明“第 5 种：网络数据读取”在至少一个 JJ 版本上可行。这个仓库没有许可证，也没有协议样本或自动测试，解析器还固定从标准初始局面开始，因此更适合当协议探针和验证线索，不能直接复制进产品。

没有找到一个公开项目是通过 Windows `ReadProcessMemory` 直接扫描 JJ 棋盘结构。公开实现主要选择视觉或 WebSocket。若仍要读运行时对象，现成路线是 [WMPFDebugger](https://github.com/evi0s/WMPFDebugger) 暴露微信小程序的 CDP 调试通道，再用 [miniapp-cdp-mcp](https://github.com/zhizhuodemao/miniapp-cdp-mcp) 检查 AppService/WebView 的脚本、运行时变量、XHR、WebSocket 和作用域，而不是先猜原生内存地址。这个方案依赖具体 WMPF 版本和 Frida hook 偏移，适合作为限时可行性试验，不适合作为第一版产品的唯一数据源。

据此，当前项目的最短路线是：先用 `chess-coach` 给出的消息结构验证当前 JJ 版本的 WebSocket；普通标准开局若能稳定取得落子事件，就以网络事件为主数据源。残局关卡或任意初始局面还必须额外取得初始棋盘；可以继续研究开始消息中的局面字段，或仅在开局时做一次截图识别。网络验证失败时，直接采用 `chess-helper-app` 的 JJ 模型和 `public-Xiangqi` 的 Windows 连线结构。

## 项目对比

| 项目 | 与目标的关系 | 实际实现路线 | 最近提交 | 许可证与复用判断 |
|---|---|---|---|---|
| [YoungerIOS/chess-helper-app](https://github.com/YoungerIOS/chess-helper-app) | 最接近；README 明确写 JJ 象棋和天天象棋 | `mss` 截屏，窗口标题定位，霍夫圆找棋盘，平台专用 ONNX 分类，稳定帧/历史校验，Pikafish，PySide6 箭头 | [2026-04-28](https://github.com/YoungerIOS/chess-helper-app/commit/25a13b41a1566c109330b8af4958a7f962de25e0) | 根 [LICENSE](https://github.com/YoungerIOS/chess-helper-app/blob/25a13b41a1566c109330b8af4958a7f962de25e0/LICENSE) 是木兰宽松许可证 2.0，但 README 写 MIT 且附加“请勿商用”，三处表述不一致；复用前应请作者澄清 |
| [sojourners/public-Xiangqi](https://github.com/sojourners/public-Xiangqi) | Windows 通用连线、识别和引擎界面底座 | JNA 取窗口，Robot/`PrintWindow` 截图，YOLOv11 ONNX，局面差分和动画确认，UCI/UCCI，观战模式 | [2026-09-20](https://github.com/sojourners/public-Xiangqi/commit/11e42fdca495c58644959c1e50ef1b79f583f569) | 根 [LICENSE](https://github.com/sojourners/public-Xiangqi/blob/11e42fdca495c58644959c1e50ef1b79f583f569/LICENSE) 为 GPLv3；README 另写“未经授权不得商用”，与 GPLv3 的商业使用许可存在表述冲突，发布前需澄清 |
| [JulyBear/chess-coach](https://github.com/JulyBear/chess-coach) | 直接解析 JJ WebSocket，最能验证网络路线 | mitmproxy 解 TLS 后截取 WebSocket，解析 8 字节帧头和 JSON，提取落子坐标，生成 FEN，赛后调用 Pikafish | [2026-03-28](https://github.com/JulyBear/chess-coach/commit/b4bc3ee47d83526d092bbd9a60de1fb530aa23c2) | 仓库没有 LICENSE，默认不能直接复制代码；只适合参考协议行为并自行重新验证、实现 |
| [yingwang/xiangqi-bot](https://github.com/yingwang/xiangqi-bot) | 微信天天象棋的完整屏幕机器人参考 | macOS 窗口截图，15 类 CNN，低置信度双次采样，合法着法匹配，Pikafish，Quartz 点击 | [2026-09-16](https://github.com/yingwang/xiangqi-bot/commit/8eaeee634b052e12004c59e6fb57b67681b0cfaf) | 自有代码 [MIT](https://github.com/yingwang/xiangqi-bot/blob/8eaeee634b052e12004c59e6fb57b67681b0cfaf/LICENSE)；只支持 macOS，训练数据高度绑定天天象棋皮肤 |
| [evi0s/WMPFDebugger](https://github.com/evi0s/WMPFDebugger) | 为 Windows 微信第三方小程序暴露运行时 CDP | Frida 附加 `WeChatAppEx.exe`，按 WMPF 版本 hook `flue.dll`，代理私有调试协议到标准 CDP | [2026-09-21](https://github.com/evi0s/WMPFDebugger/commit/832b2bb0399d81eda8bad2cea776b68444505287) | [GPLv2](https://github.com/evi0s/WMPFDebugger/blob/832b2bb0399d81eda8bad2cea776b68444505287/LICENSE)；`src/third-party` 含从微信开发者工具提取的代码，仓库说明其版权属于腾讯，产品集成风险较高 |
| [zhizhuodemao/miniapp-cdp-mcp](https://github.com/zhizhuodemao/miniapp-cdp-mcp) | 在 CDP 已暴露后读取脚本、运行时和网络 | 切换 AppService/WebView target，列脚本和源码，运行表达式，检查断点作用域，捕获 XHR/WebSocket | [2026-04-22](https://github.com/zhizhuodemao/miniapp-cdp-mcp/commit/4373a1297dab2efae082ec014ea54122b843ff26) | [MIT](https://github.com/zhizhuodemao/miniapp-cdp-mcp/blob/4373a1297dab2efae082ec014ea54122b843ff26/LICENSE)；依赖 WMPFDebugger 一类工具先暴露端点 |
| [jiawei686/wechat-dev-mcp](https://github.com/jiawei686/wechat-dev-mcp) | Canvas、Runtime、Network 工具的实现参考 | 微信开发者工具项目注入，CDP 截图/触摸，包裹 `wx.request` 等 API 记录网络日志 | [2026-09-24](https://github.com/jiawei686/wechat-dev-mcp/commit/f357c6a01e156bdda418ca4f8726d5241ef42cc1) | [MIT](https://github.com/jiawei686/wechat-dev-mcp/blob/f357c6a01e156bdda418ca4f8726d5241ef42cc1/LICENSE)；主要面向自己能在微信开发者工具中加载的项目，不能仅凭第三方小程序分享链接直接使用 |
| [codertapsu/xiangqi-solver](https://github.com/codertapsu/xiangqi-solver) | 端到端分层架构参考，平台是 Android | MediaProjection 截图，视觉服务输出 10×9 棋盘，校验/归一化/FEN，Pikafish 池，悬浮层显示建议 | [2026-09-19](https://github.com/codertapsu/xiangqi-solver/commit/3e71c9e344051c5be60c66bd53434c79da7421bb) | 根目录没有通常意义上的代码 LICENSE；只有 [LICENSE-engine.md](https://github.com/codertapsu/xiangqi-solver/blob/3e71c9e344051c5be60c66bd53434c79da7421bb/LICENSE-engine.md)，直接复用项目前需确认授权 |

## 重点项目源码核实

### 1. chess-helper-app：与 JJ 目标最接近的视觉实现

仓库的公开说明明确列出 JJ 象棋和天天象棋，声称自动检测窗口、动态定位棋盘、跟随窗口移动并调用 Pikafish；这些核心能力在源码中确实存在，而不是只写在 README 中。[README](https://github.com/YoungerIOS/chess-helper-app/blob/25a13b41a1566c109330b8af4958a7f962de25e0/README.md)

实际链路如下：

1. [board_locator.py](https://github.com/YoungerIOS/chess-helper-app/blob/25a13b41a1566c109330b8af4958a7f962de25e0/app/chess/board_locator.py) 在 Windows 使用 `win32gui.EnumWindows` 和窗口标题寻找 `JJ象棋`/`天天象棋`，再用 `mss` 截取窗口区域。JJ 区域会先上下收缩，然后放大、模糊和闭运算，再用 `cv2.HoughCircles` 找棋子圆。源码用将/帅和兵/卒的关键组合推算整块棋盘。
2. [piece_recognizer.py](https://github.com/YoungerIOS/chess-helper-app/blob/25a13b41a1566c109330b8af4958a7f962de25e0/app/chess/piece_recognizer.py) 会按平台加载 `jj_piece_model.onnx` 或 `tt_piece_model.onnx`；每个交叉点裁图缩放到 80×80，通过 ONNX Runtime 批量分类。两个模型和类别映射已经提交在 `app/models/`。
3. [screenshot.py](https://github.com/YoungerIOS/chess-helper-app/blob/25a13b41a1566c109330b8af4958a7f962de25e0/app/chess/screenshot.py) 默认每 0.18 秒采集一次棋盘，并通过图像哈希稳定帧过滤后才送入识别队列；异常画面会延迟重试。
4. [checker.py](https://github.com/YoungerIOS/chess-helper-app/blob/25a13b41a1566c109330b8af4958a7f962de25e0/app/chess/checker.py) 与 [simulation.py](https://github.com/YoungerIOS/chess-helper-app/blob/25a13b41a1566c109330b8af4958a7f962de25e0/app/chess/simulation.py) 对比视觉局面和历史走子推演局面，防止单帧误识别破坏整局状态。
5. [engine.py](https://github.com/YoungerIOS/chess-helper-app/blob/25a13b41a1566c109330b8af4958a7f962de25e0/app/chess/engine.py) 通过子进程标准输入输出执行 `uci`、`isready`、`position fen`、`go depth/movetime`，读取 `bestmove`，并支持 MultiPV。
6. [board_display.py](https://github.com/YoungerIOS/chess-helper-app/blob/25a13b41a1566c109330b8af4958a7f962de25e0/app/ui/board_display.py) 在助手自己的 PySide6 棋盘中绘制推荐箭头、起点和终点标记。

Windows 复用局限也能从源码直接看出：README 的正式环境要求仍是 macOS 12+；默认 Pikafish 路径写成无 `.exe` 的 `Pikafish/src/pikafish`；部分权限提示仍调用 macOS 系统设置。它更像“已经加入 Windows 分支的 macOS 项目”，还不是经过 Windows 发布流程验证的成品。

最适合复用的部分是 JJ ONNX 模型和类别映射、棋盘定位算法、稳定帧过滤、局面连续性检查、UCI 封装和 PySide6 棋盘显示。窗口捕获和引擎路径应按 Windows 单独整理。

### 2. public-Xiangqi：Windows 连线结构最完整

[使用手册](https://github.com/sojourners/public-Xiangqi/blob/11e42fdca495c58644959c1e50ef1b79f583f569/MANUAL.md) 把“连线”定义为选择外部棋盘后持续识别，支持自动走棋和观战分析，并提供扫描间隔、识别线程数、动画确认及前后台模式。

源码对应关系很清楚：

- [WindowsGraphLinker.java](https://github.com/sojourners/public-Xiangqi/blob/11e42fdca495c58644959c1e50ef1b79f583f569/src/main/java/com/sojourners/chess/linker/WindowsGraphLinker.java) 用 JNA 获取窗口句柄和 DPI；前台模式调用 `java.awt.Robot`，后台模式调用 Win32 `PrintWindow` 抓取客户区，并可用 `PostMessage` 发送鼠标事件。
- [AbstractGraphLinker.java](https://github.com/sojourners/public-Xiangqi/blob/11e42fdca495c58644959c1e50ef1b79f583f569/src/main/java/com/sojourners/chess/linker/AbstractGraphLinker.java) 按设定间隔扫描，先定位棋盘，再识别 10×9 局面。它会比较外部棋盘和内部引擎棋盘，推断是对手已走、引擎已走、新棋局还是异常变化；动画模式会等连续两次识别一致。
- [OnnxModel.java](https://github.com/sojourners/public-Xiangqi/blob/11e42fdca495c58644959c1e50ef1b79f583f569/src/main/java/com/sojourners/chess/yolo/OnnxModel.java) 与 [Yolo11Model.java](https://github.com/sojourners/public-Xiangqi/blob/11e42fdca495c58644959c1e50ef1b79f583f569/src/main/java/com/sojourners/chess/yolo/Yolo11Model.java) 定义了 15 类（14 种棋子加棋盘）YOLOv11 ONNX 推理，模型文件也在仓库中。
- [Engine.java](https://github.com/sojourners/public-Xiangqi/blob/11e42fdca495c58644959c1e50ef1b79f583f569/src/main/java/com/sojourners/chess/enginee/Engine.java) 支持 UCI/UCCI，发送 `position fen` 与历史着法，可按时间、深度、节点或无限分析读取 `bestmove`。

这个项目最有价值的是 Windows 窗口捕获和“局面差分状态机”，而不是只拿识别模型。对微信小程序能否后台 `PrintWindow` 成功，需要在当前 `WeChatAppEx.exe` 上实测；手册也明确说明后台模式并非所有平台都支持。

### 3. chess-coach：JJ WebSocket 已有具体解析器

[jj_addon.py](https://github.com/JulyBear/chess-coach/blob/b4bc3ee47d83526d092bbd9a60de1fb530aa23c2/proxy/jj_addon.py) 的实现证明该仓库确实理解过一版 JJ 消息格式：

- 只处理 WebSocket 二进制消息。
- 前 4 字节按小端无符号整数读取消息类型，后 4 字节读取 JSON 负载长度，再解码 UTF-8 JSON。
- 用 `0x14801` 处理大厅/棋局请求，`0x0000` 处理服务端回应，`0x03F3` 处理走棋消息。
- 从 `chess_ack_msg.chessmove_ack_msg` 提取 `beginposx`、`beginposy`、`endposx`、`endposy`、`seat`、`roundtime` 和 `islocal`。
- 以 `matchid` 维护活动对局缓存，把每步坐标写入 SQLite，并调用 [xiangqi.py](https://github.com/JulyBear/chess-coach/blob/b4bc3ee47d83526d092bbd9a60de1fb530aa23c2/server/xiangqi.py) 从标准初始 FEN 逐步更新局面。
- [engine.py](https://github.com/JulyBear/chess-coach/blob/b4bc3ee47d83526d092bbd9a60de1fb530aa23c2/server/engine.py) 在复盘阶段调用 Pikafish，读取 `score cp`、`score mate`、PV 和 `bestmove`。

这条路线有四个现实限制：

1. 仓库只保留三个提交，最新提交在 2026-03-28，且没有协议录包、回归测试或版本标识，不能证明当前 JJ 版本仍保持相同消息结构。
2. 人人对战的己方座位识别在源码中被注释为不可靠，当前只在人机模式通过 `isRed` 确定座位。
3. 解析器总是以标准初始 FEN 建局。当前用户打开的“第 1 关”若是残局或非标准局面，必须另行从开始消息取得初始棋盘，或在开局时用视觉同步一次。
4. 仓库没有 LICENSE，不能直接复制实现。

尽管如此，它仍然把网络可行性从“猜测”提高到了“有具体源码先例”。如果当前版本抓到的 `0x03F3` 结构仍一致，实时助手无需每帧识别 90 个交叉点；只需在建立初始局面后消费落子事件。

### 4. xiangqi-bot：低置信度双采样值得移植

[xiangqi_bot.py](https://github.com/yingwang/xiangqi-bot/blob/8eaeee634b052e12004c59e6fb57b67681b0cfaf/xiangqi_bot.py) 在微信天天象棋窗口上执行自动校准、截图识别、局面跟踪、Pikafish 搜索和点击。它的主要价值是几个小而实用的策略：

- 首次用 CNN 在候选棋盘比例上做网格搜索，失败再要求两角人工标定。
- [xiangqi_cnn.py](https://github.com/yingwang/xiangqi-bot/blob/8eaeee634b052e12004c59e6fb57b67681b0cfaf/xiangqi_cnn.py) 使用“空位 + 红黑 14 类棋子”的分类模型，并按最大合法棋子数把低置信度的超额分类改为次优类别。
- 某些非空格置信度低于阈值时，延迟 0.3 秒再截图，对两次概率分布取平均，降低移动动画造成的瞬时误判。
- 对手走子不是只看两个像素变化，而是把视觉差异和 Pikafish 给出的合法着法集合匹配。

项目只支持 macOS，窗口截图使用 `screencapture`，点击使用 Quartz CGEvent；它的 CNN 训练数据也针对天天象棋皮肤，因此不能替代 JJ 专用模型。

### 5. WMPFDebugger + miniapp-cdp-mcp：运行时对象与网络的探测组合

[WMPFDebugger README](https://github.com/evi0s/WMPFDebugger/blob/832b2bb0399d81eda8bad2cea776b68444505287/README.zh.md) 说明它通过 Frida patch CDP 过滤器和条件判断，把微信小程序私有远程调试协议转换为标准 CDP。Windows 侧 [win32.ts](https://github.com/evi0s/WMPFDebugger/blob/832b2bb0399d81eda8bad2cea776b68444505287/src/platform/win32.ts) 查找 `WeChatAppEx.exe` 和 WMPF 版本；[index.ts](https://github.com/evi0s/WMPFDebugger/blob/832b2bb0399d81eda8bad2cea776b68444505287/src/index.ts) 启动调试服务与 CDP 代理并注入 hook。仓库在本次调研时列出的 Windows 最新适配版本为 25715，并提供仍属 Beta 的自动偏移检测；[ADAPTATION.md](https://github.com/evi0s/WMPFDebugger/blob/832b2bb0399d81eda8bad2cea776b68444505287/ADAPTATION.md) 明确说明新版本常需重新定位 `flue.dll` 中的偏移。

在端点暴露后，[miniapp-cdp-mcp README](https://github.com/zhizhuodemao/miniapp-cdp-mcp/blob/4373a1297dab2efae082ec014ea54122b843ff26/README.md) 所列工具可以：

- 区分并切换 AppService 与 WebView 调试目标；
- 列出、搜索和保存已加载 JavaScript 源码；
- 执行 JavaScript 表达式，在断点处检查调用栈和作用域；
- 捕获 XHR/Fetch、WebSocket 连接和消息；
- 提取 WASM 字节码。

对 JJ 象棋而言，实际探测顺序应是：先搜索源码中的 `chessmove_ack_msg`、`beginposx`、`matchid` 等已知协议字段；再在网络消息处理函数设置断点；落一步后检查作用域中是否出现棋盘数组、棋子列表或 from/to 坐标。如果局面保存在 JS AppService 中，就能直接取得结构化状态；如果主要逻辑在 WASM、原生模块或服务端，CDP 只能提供网络事件和外围对象。

这仍然比裸扫进程内存更有方向，但 WMPF 版本升级会让 hook 偏移失效，且运行时目标、压缩混淆和对象名都可能变化。

### 6. wechat-dev-mcp 与 xiangqi-solver：可拆用的工程模式

[wechat-dev-mcp 小游戏指南](https://github.com/jiawei686/wechat-dev-mcp/blob/f357c6a01e156bdda418ca4f8726d5241ef42cc1/docs/MINIGAME_GUIDE.md) 展示了如何通过 CDP 对 Canvas 发送触摸、截取画布，并记录 Runtime、Network、Performance 事件；它还通过包裹 `wx.request`、`wx.downloadFile`、`wx.uploadFile` 实现应用层网络日志。其默认工作流需要一个能在微信开发者工具中编译运行的项目，所以对只有分享链接的 JJ 第三方小程序不是现成答案，但 `cdp-client.js`、`game-runtime.js`、`board-vision.js` 的结构可以作为内部探针参考。

[xiangqi-solver README](https://github.com/codertapsu/xiangqi-solver/blob/3e71c9e344051c5be60c66bd53434c79da7421bb/README.md) 提供了另一套清楚的分层：Android MediaProjection 截屏，视觉模型输出紧凑的 10×9 棋盘，验证器归一化为合法局面并生成 FEN，Pikafish 使用常驻进程池分析，Flutter 悬浮层画出最佳着法。它的平台和识别方式与 Windows 不同，但“截图输入、棋盘契约、校验、引擎提供者、展示”之间的接口值得照搬。

## 对本项目的具体建议

### 数据源优先级

1. **先验证 WebSocket。** `chess-coach` 已给出当前最具体的 JJ 字段名和消息类型。若普通对局的每一步都能稳定获得 `matchid + from/to + seat`，网络事件应作为主数据源。
2. **用视觉解决初始同步和兜底。** 标准开局可以直接用默认 FEN；残局、关卡、观战中途接入需要初始棋盘。优先复用 `chess-helper-app` 的 JJ ONNX 模型，或采用 `public-Xiangqi` 的 YOLO 棋盘检测。
3. **把 CDP 当探测工具。** 若 mitmproxy 不能建立 TLS/WebSocket 或协议已经变化，用 WMPFDebugger + miniapp-cdp-mcp 定位 AppService 中的网络处理函数和运行时对象。验证成功后再决定是否长期依赖它。
4. **暂缓裸内存扫描。** 现有项目没有可复用的 JJ 内存偏移或棋盘结构；微信小程序运行时、渲染进程和版本变化会让固定偏移维护成本很高。

### 推荐的组合架构

```text
JJ WebSocket / CDP Runtime
        │ 落子事件
        ▼
棋局状态机 ──────── 视觉初始同步 / 异常重同步
        │
        ├─ 10×9 board
        ├─ side to move
        ├─ move history
        └─ FEN
        │
        ▼
常驻 Pikafish UCI 进程
        │ bestmove / score / pv
        ▼
PySide6 侧边窗或透明提示层
```

状态机应保留 `position_id`。新落子到达时先取消旧搜索；UI 只接收与当前 `position_id` 一致的结果。视觉同步必须经过连续帧稳定、合法走子和历史推演三重检查，这一点可以直接参考 `chess-helper-app` 与 `public-Xiangqi`。

### 一次可判定成败的网络验证

网络路线不需要先做完整应用。只要完成下面的最小探针，就能决定是否继续：

1. 记录当前微信/WMPF/JJ 小程序版本。
2. 启动本地代理并确认能看到 JJ 的 WebSocket 二进制帧。
3. 按 `chess-coach` 的 8 字节帧头尝试解析；检查是否仍存在 `0x03F3` 和 `chessmove_ack_msg`。
4. 连走 10 步，把网络坐标变化与画面逐步对照。
5. 退出、重连、重新开局各一次，确认 `matchid` 和起局同步可靠。
6. 再进入当前“第 1 关”，确认开始消息是否携带非标准初始棋盘；若没有，就确定必须增加一次视觉初始同步。

成功标准是：连续 10 步坐标全部正确，重连不重复或漏步，并能确定当前行棋方。满足后即可开始接 Pikafish；否则停止在协议探测阶段，转入视觉方案。

## Pikafish 集成与许可证

[Pikafish 官方仓库](https://github.com/official-pikafish/Pikafish) 将其定义为 UCI 中国象棋引擎；[UCI 命令文档](https://github.com/official-pikafish/Pikafish/wiki/UCI-&-Commands) 是接入时的权威参考。常驻子进程至少需要处理 `uci/uciok`、`isready/readyok`、`position fen` 或 `position startpos moves`、`go movetime/depth`、`stop` 与 `bestmove`。

Pikafish 本体采用 [GPLv3](https://github.com/official-pikafish/Pikafish/blob/master/Copying.txt)。官方 README 明确说明，分发二进制时必须随附许可证以及生成该二进制的完整对应源代码或其获取指引；修改过的引擎源码也必须以 GPLv3 提供。项目自己的 UI、识别模型和协议探针还要分别遵守各自上游许可证，不能因为通过子进程调用 Pikafish 就忽略随包分发时的义务。

## 未找到或仍需实测的部分

- 没有找到公开的 JJ 象棋 Windows 进程内存结构、稳定指针链或可直接复用的 `ReadProcessMemory` 实现。
- 没有一手资料证明当前用户机器上的 JJ 版本仍使用 `chess-coach` 的消息类型和 JSON 字段；必须抓取当前会话验证。
- 没有证据表明当前“第 1 关”的初始局面能从 `chess-coach` 已解析的开始消息中取得。
- `PrintWindow` 是否能在当前微信小程序窗口被遮挡时得到有效 Canvas 内容，必须在本机实测。
- `chess-helper-app` 的 Windows 分支没有公开的 Windows Release 或完整打包说明，不能按 README 直接视为 Windows 成品。
