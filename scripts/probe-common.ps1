$ProbeProjectRoot = Split-Path -Parent $PSScriptRoot
$ProbeMitmDump = Join-Path $ProbeProjectRoot ".venv\Scripts\mitmdump.exe"
$ProbeConfDir = Join-Path $ProbeProjectRoot "data\mitmproxy"
$ProbeCertificatePath = Join-Path $ProbeConfDir "mitmproxy-ca-cert.cer"
$ProbeThumbprintPath = Join-Path $ProbeProjectRoot ".probe-ca-thumbprint"

function Get-ProbeCertificateThumbprint {
    if (Test-Path -LiteralPath $ProbeThumbprintPath) {
        $Saved = (Get-Content -LiteralPath $ProbeThumbprintPath -Raw).Trim()
        if ($Saved -match "^[0-9A-Fa-f]{40}$") {
            return $Saved.ToUpperInvariant()
        }
    }
    if (Test-Path -LiteralPath $ProbeCertificatePath) {
        $Certificate = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new(
            $ProbeCertificatePath
        )
        return $Certificate.Thumbprint
    }
    return $null
}

function New-ProbeCertificateIfMissing {
    if (Test-Path -LiteralPath $ProbeCertificatePath) {
        return
    }
    if (-not (Test-Path -LiteralPath $ProbeMitmDump)) {
        throw "未找到 $ProbeMitmDump。请先安装项目依赖。"
    }

    $Process = Start-Process `
        -FilePath $ProbeMitmDump `
        -ArgumentList @(
            "--mode", "regular",
            "--listen-host", "127.0.0.1",
            "--listen-port", "0",
            "--set", "confdir=$ProbeConfDir"
        ) `
        -WorkingDirectory $ProbeProjectRoot `
        -WindowStyle Hidden `
        -PassThru
    try {
        for ($Attempt = 0; $Attempt -lt 50; $Attempt++) {
            if (Test-Path -LiteralPath $ProbeCertificatePath) {
                return
            }
            Start-Sleep -Milliseconds 100
        }
        throw "mitmproxy 未能在 5 秒内生成本机 CA。"
    } finally {
        if (-not $Process.HasExited) {
            Stop-Process -Id $Process.Id -Force
            $Process.WaitForExit()
        }
    }
}

