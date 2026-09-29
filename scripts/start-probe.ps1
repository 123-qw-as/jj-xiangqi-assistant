param(
    [ValidateSet("Local", "Regular")]
    [string]$Mode = "Local",
    [int]$Port = 8080,
    [string]$Output = "data/jj-events.jsonl",
    [switch]$CaptureUnknown
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "probe-common.ps1")

$Addon = Join-Path $ProbeProjectRoot "src\jj_assistant\mitm_addon.py"
$OutputPath = Join-Path $ProbeProjectRoot $Output

if (-not (Test-Path -LiteralPath $ProbeMitmDump)) {
    throw "未找到 $ProbeMitmDump。请先安装开发环境：.\.venv\Scripts\python.exe -m pip install `".[dev,probe]`""
}

$arguments = @(
    "-s", $Addon,
    "--set", "jj_output=$OutputPath",
    "--set", "confdir=$ProbeConfDir"
)

$ModeDescription = if ($Mode -eq "Local") {
    $arguments += @("--mode", "local:WeChatAppEx.exe")
    "按进程捕获：WeChatAppEx.exe"
} else {
    $arguments += @(
        "--mode", "regular",
        "--listen-host", "127.0.0.1",
        "--listen-port", $Port
    )
    "监听 127.0.0.1:$Port"
}

if ($CaptureUnknown) {
    $arguments += @("--set", "jj_capture_unknown=true")
}

Write-Host "JJ 协议探针$ModeDescription"
Write-Host "事件输出：$OutputPath"
Write-Host "此脚本不会修改 Windows 系统代理，也不会安装证书。按 Ctrl+C 停止。"
& $ProbeMitmDump @arguments


