param(
    [switch]$Clean,
    [int]$ApiPort = 8000,
    [switch]$LegacyStreamlit,
    [int]$StreamlitPort = 8501
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Stop-PortOwner {
    param([int]$Port)
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($connection in $connections) {
        if ($connection.OwningProcess -and $connection.OwningProcess -ne 0) {
            Stop-Process -Id $connection.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}

$apiCommand = "Set-Location '$ProjectRoot'; python -m uvicorn api.main:app --host 127.0.0.1 --port $ApiPort"
$streamlitCommand = "Set-Location '$ProjectRoot'; python -m streamlit run web/app.py --server.address 127.0.0.1 --server.port $StreamlitPort --server.headless true"

function Start-HiddenPowerShell {
    param([string]$Command)
    Start-Process -FilePath powershell.exe `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $Command) `
        -WindowStyle Hidden `
        -PassThru
}

function Test-Http {
    param([string]$Url)
    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Wait-Http {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 45
    )
    for ($i = 0; $i -lt $TimeoutSeconds; $i++) {
        if (Test-Http -Url $Url) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

if ($Clean) {
    Stop-PortOwner -Port $ApiPort
    Stop-PortOwner -Port $StreamlitPort
    Start-Sleep -Seconds 1
}

$api = Start-HiddenPowerShell -Command $apiCommand
$apiHealthy = Wait-Http -Url "http://127.0.0.1:$ApiPort/health" -TimeoutSeconds 45

if (-not $apiHealthy) {
    $api = Start-HiddenPowerShell -Command $apiCommand
    $apiHealthy = Wait-Http -Url "http://127.0.0.1:$ApiPort/health" -TimeoutSeconds 45
}

$streamlit = $null
if ($LegacyStreamlit) {
    $streamlit = Start-HiddenPowerShell -Command $streamlitCommand
    Start-Sleep -Seconds 4
    if (-not (Test-Http -Url "http://127.0.0.1:$StreamlitPort")) {
        $streamlit = Start-HiddenPowerShell -Command $streamlitCommand
        Start-Sleep -Seconds 4
    }
}

Write-Host "FastAPI PID: $($api.Id) -> http://127.0.0.1:$ApiPort/"
Write-Host "HTML UI: http://127.0.0.1:$ApiPort/"
Write-Host "FastAPI healthy: $apiHealthy"
if ($LegacyStreamlit -and $streamlit) {
    Write-Host "Legacy Streamlit PID: $($streamlit.Id) -> http://127.0.0.1:$StreamlitPort"
    Write-Host "Legacy Streamlit reachable: $(Test-Http -Url "http://127.0.0.1:$StreamlitPort")"
}
Write-Host "Use .\run_app.ps1 -Clean to stop stale listeners before starting."
