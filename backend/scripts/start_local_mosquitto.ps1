$ErrorActionPreference = "Stop"

$mosquittoExe = "C:\Program Files\mosquitto\mosquitto.exe"
$backendDir = Split-Path $PSScriptRoot -Parent
$envPath = Join-Path $backendDir ".env"
$configPath = Join-Path $env:LOCALAPPDATA "FloodGuard\mosquitto\mosquitto.conf"

if (-not (Test-Path -LiteralPath $mosquittoExe)) {
    throw "Mosquitto is not installed at $mosquittoExe"
}
if (-not (Test-Path -LiteralPath $configPath)) {
    throw "Run scripts/setup_local_mosquitto.ps1 first"
}

$portLine = Get-Content -LiteralPath $envPath |
    Where-Object { $_ -match "^MQTT_BROKER_PORT=" } |
    Select-Object -First 1
$port = [int]($portLine -replace "^MQTT_BROKER_PORT=", "")

function Test-LocalTcpPort {
    param([int]$Port)

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connection = $client.ConnectAsync("127.0.0.1", $Port)
        if (-not $connection.Wait(500)) {
            return $false
        }
        return $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

if (Test-LocalTcpPort -Port $port) {
    Write-Output "A broker is already listening on 127.0.0.1:$port"
    exit 0
}

& $mosquittoExe --test-config -c $configPath
if ($LASTEXITCODE -ne 0) {
    throw "Mosquitto configuration validation failed"
}

$process = Start-Process `
    -FilePath $mosquittoExe `
    -ArgumentList @("-c", $configPath) `
    -WindowStyle Hidden `
    -PassThru

$deadline = [DateTime]::UtcNow.AddSeconds(10)
do {
    Start-Sleep -Milliseconds 250
    $isListening = Test-LocalTcpPort -Port $port
} until ($isListening -or [DateTime]::UtcNow -ge $deadline)

if (-not $isListening) {
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id
    }
    throw "Mosquitto did not begin listening on port $port"
}

Write-Output "Mosquitto listening on 127.0.0.1:$port (PID $($process.Id))"
