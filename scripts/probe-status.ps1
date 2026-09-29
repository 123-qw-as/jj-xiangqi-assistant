$CertificatePath = Join-Path $env:USERPROFILE ".mitmproxy\mitmproxy-ca-cert.cer"
$CertificateStatus = "未生成"
$Thumbprint = $null

if (Test-Path -LiteralPath $CertificatePath) {
    $Certificate = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($CertificatePath)
    $Thumbprint = $Certificate.Thumbprint
    $Installed = Get-ChildItem Cert:\CurrentUser\Root | Where-Object Thumbprint -eq $Thumbprint
    $CertificateStatus = if ($Installed) { "已安装到当前用户 Root" } else { "已生成、未安装" }
}

$ProbeProcesses = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "mitmdump.exe" -and $_.CommandLine -match "jj_assistant"
}

[PSCustomObject]@{
    CertificateStatus = $CertificateStatus
    CertificateThumbprint = $Thumbprint
    ProbeRunning = [bool]$ProbeProcesses
    ProbeProcessIds = @($ProbeProcesses.ProcessId) -join ","
} | Format-List

