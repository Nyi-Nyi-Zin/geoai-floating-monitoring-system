$ErrorActionPreference = "Stop"

$mosquittoDir = "C:\Program Files\mosquitto"
$mosquittoExe = Join-Path $mosquittoDir "mosquitto.exe"
$passwordExe = Join-Path $mosquittoDir "mosquitto_passwd.exe"
$backendDir = Split-Path $PSScriptRoot -Parent
$envPath = Join-Path $backendDir ".env"
$runtimeDir = Join-Path $env:LOCALAPPDATA "FloodGuard\mosquitto"

foreach ($requiredPath in @($mosquittoExe, $passwordExe, $envPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required file is missing: $requiredPath"
    }
}

$environment = @{}
Get-Content -LiteralPath $envPath | ForEach-Object {
    if ($_ -match "^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$") {
        $environment[$matches[1]] = $matches[2]
    }
}

$username = $environment["MQTT_USERNAME"]
$password = $environment["MQTT_PASSWORD"]
$port = [int]$environment["MQTT_BROKER_PORT"]
if ($username -notmatch "^[A-Za-z0-9_-]+$") {
    throw "MQTT_USERNAME must use letters, numbers, underscore, or hyphen"
}
if ([string]::IsNullOrWhiteSpace($password)) {
    throw "MQTT_PASSWORD must be configured in backend/.env"
}
if ($port -lt 1 -or $port -gt 65535) {
    throw "MQTT_BROKER_PORT is invalid"
}

New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
$passwordFile = Join-Path $runtimeDir "passwords"
$aclFile = Join-Path $runtimeDir "acl"
$configFile = Join-Path $runtimeDir "mosquitto.conf"
$logFile = Join-Path $runtimeDir "broker.log"

& $passwordExe -c -b $passwordFile $username $password
if ($LASTEXITCODE -ne 0) {
    throw "Could not create Mosquitto password file"
}

@"
user $username
topic readwrite floodguard/stations/+/readings
"@ | Set-Content -LiteralPath $aclFile -Encoding ascii

$passwordConfigPath = $passwordFile.Replace("\", "/")
$aclConfigPath = $aclFile.Replace("\", "/")
$logConfigPath = $logFile.Replace("\", "/")
@"
listener $port 127.0.0.1
allow_anonymous false
password_file $passwordConfigPath
acl_file $aclConfigPath
persistence false
connection_messages true
log_dest file $logConfigPath
log_timestamp true
log_type error
log_type warning
log_type notice
"@ | Set-Content -LiteralPath $configFile -Encoding ascii

& $mosquittoExe --test-config -c $configFile
if ($LASTEXITCODE -ne 0) {
    throw "Mosquitto configuration validation failed"
}

Write-Output "Secured Mosquitto runtime configured at $runtimeDir"
