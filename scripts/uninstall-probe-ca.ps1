$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "probe-common.ps1")

$Thumbprint = Get-ProbeCertificateThumbprint
if (-not $Thumbprint) {
    throw "没有已保存的证书指纹，也找不到当前 mitmproxy CA。"
}

$Existing = Get-ChildItem Cert:\CurrentUser\Root | Where-Object Thumbprint -eq $Thumbprint
if (-not $Existing) {
    Write-Host "当前用户证书库中没有该探针 CA。"
    if (Test-Path -LiteralPath $ProbeThumbprintPath) {
        Remove-Item -LiteralPath $ProbeThumbprintPath -Force
    }
    exit 0
}

certutil.exe -user -delstore Root $Thumbprint | Out-Null
$Remaining = Get-ChildItem Cert:\CurrentUser\Root | Where-Object Thumbprint -eq $Thumbprint
if ($Remaining) {
    throw "证书仍然存在，移除失败。"
}

if (Test-Path -LiteralPath $ProbeThumbprintPath) {
    Remove-Item -LiteralPath $ProbeThumbprintPath -Force
}
Write-Host "已移除探针 CA。指纹：$Thumbprint"

