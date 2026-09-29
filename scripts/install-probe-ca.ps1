$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "probe-common.ps1")

New-ProbeCertificateIfMissing

$Certificate = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new(
    $ProbeCertificatePath
)
$Existing = Get-ChildItem Cert:\CurrentUser\Root | Where-Object Thumbprint -eq $Certificate.Thumbprint
if ($Existing) {
    Set-Content -LiteralPath $ProbeThumbprintPath -Value $Certificate.Thumbprint -NoNewline
    Write-Host "探针 CA 已安装。指纹：$($Certificate.Thumbprint)"
    exit 0
}

Import-Certificate -FilePath $ProbeCertificatePath -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
$Installed = Get-ChildItem Cert:\CurrentUser\Root | Where-Object Thumbprint -eq $Certificate.Thumbprint
if (-not $Installed) {
    throw "证书导入后未在当前用户 Root 证书库中找到。"
}

Set-Content -LiteralPath $ProbeThumbprintPath -Value $Certificate.Thumbprint -NoNewline
Write-Host "已安装探针 CA 到当前用户证书库。"
Write-Host "指纹：$($Certificate.Thumbprint)"

