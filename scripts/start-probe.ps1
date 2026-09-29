param(
    [ValidateSet("Local", "Regular")]
    [string]$Mode = "Local",
    [int]$Port = 8080,
    [string]$Output = "data/jj-events.jsonl",
    [switch]$CaptureUnknown
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$MitmDump = Join-Path $ProjectRoot ".venv\Scripts\mitmdump.exe"
$Addon = Join-Path $ProjectRoot "src\jj_assistant\mitm_addon.py"
$OutputPath = Join-Path $ProjectRoot $Output

if (-not (Test-Path -LiteralPath $MitmDump)) {
    throw "未找到 $MitmDump。请先安装开发环境：.\.venv\Scripts\python.exe -m pip install `".[dev,probe]`""
}

$arguments = @(
    "-s", $Addon,
    "--set", "jj_output=$OutputPath"
)

if ($Mode -eq "Local") {
    $arguments += @("--mode", "local:WeChatAppEx.exe")
} else {
    $arguments += @(
        "--mode", "regular",
        "--listen-host", "127.0.0.1",
        "--listen-port", $Port
    )
}

if ($CaptureUnknown) {
    $arguments += @("--set", "jj_capture_unknown=true")
}

if ($Mode -eq "Local") {
    Write-Host "JJ 协议探针按进程捕获：WeChatAppEx.exe"
} else {
    Write-Host "JJ 协议探针监听 127.0.0.1:$Port"
}
Write-Host "事件输出：$OutputPath"
Write-Host "此脚本不会修改 Windows 系统代理，也不会安装证书。按 Ctrl+C 停止。"
& $MitmDump @arguments


