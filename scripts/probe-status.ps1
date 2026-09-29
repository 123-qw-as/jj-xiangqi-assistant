. (Join-Path $PSScriptRoot "probe-common.ps1")

$CertificateStatus = "未生成"
$Thumbprint = Get-ProbeCertificateThumbprint

if ($Thumbprint) {
    $Installed = Get-ChildItem Cert:\CurrentUser\Root | Where-Object Thumbprint -eq $Thumbprint
    $CertificateStatus = if ($Installed) { "已安装到当前用户 Root" } else { "已生成或已记录、未安装" }
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

