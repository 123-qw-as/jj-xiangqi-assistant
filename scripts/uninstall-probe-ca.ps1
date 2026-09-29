$ErrorActionPreference = "Stop"

$CertificatePath = Join-Path $env:USERPROFILE ".mitmproxy\mitmproxy-ca-cert.cer"
if (-not (Test-Path -LiteralPath $CertificatePath)) {
    throw "未找到 $CertificatePath，无法确定要移除的证书指纹。"
}

$Certificate = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($CertificatePath)
$Existing = Get-ChildItem Cert:\CurrentUser\Root | Where-Object Thumbprint -eq $Certificate.Thumbprint
if (-not $Existing) {
    Write-Host "当前用户证书库中没有该探针 CA。"
    exit 0
}

certutil.exe -user -delstore Root $Certificate.Thumbprint | Out-Null
$Remaining = Get-ChildItem Cert:\CurrentUser\Root | Where-Object Thumbprint -eq $Certificate.Thumbprint
if ($Remaining) {
    throw "证书仍然存在，移除失败。"
}

Write-Host "已移除探针 CA。指纹：$($Certificate.Thumbprint)"

