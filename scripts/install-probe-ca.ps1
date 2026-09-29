$ErrorActionPreference = "Stop"

$CertificatePath = Join-Path $env:USERPROFILE ".mitmproxy\mitmproxy-ca-cert.cer"
if (-not (Test-Path -LiteralPath $CertificatePath)) {
    throw "未找到 $CertificatePath。请先启动一次探针，让 mitmproxy 生成本机 CA。"
}

$Certificate = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($CertificatePath)
$Existing = Get-ChildItem Cert:\CurrentUser\Root | Where-Object Thumbprint -eq $Certificate.Thumbprint
if ($Existing) {
    Write-Host "探针 CA 已安装。指纹：$($Certificate.Thumbprint)"
    exit 0
}

Import-Certificate -FilePath $CertificatePath -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
$Installed = Get-ChildItem Cert:\CurrentUser\Root | Where-Object Thumbprint -eq $Certificate.Thumbprint
if (-not $Installed) {
    throw "证书导入后未在当前用户 Root 证书库中找到。"
}

Write-Host "已安装探针 CA 到当前用户证书库。"
Write-Host "指纹：$($Certificate.Thumbprint)"

