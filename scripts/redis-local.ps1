param(
    [ValidateSet("install", "start", "stop", "status")]
    [string]$Action = "status",
    [int]$Port = 6379
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$RedisRoot = Join-Path $Root ".tools\redis-8.10.3"
$Archive = Join-Path $RedisRoot "redis.zip"
$Version = "8.10.3"
$Url = "https://github.com/redis-windows/redis-windows/releases/download/$Version/Redis-$Version-Windows-x64-msys2.zip"
$ExpectedSha256 = "AF16DF340525B431E9EC8DABFD625D5E7A233F82805B5418819904EA909C447F"
$ExtractDir = Join-Path $RedisRoot "Redis-$Version-Windows-x64-msys2"
$Server = Join-Path $ExtractDir "redis-server.exe"
$Cli = Join-Path $ExtractDir "redis-cli.exe"
$Config = Join-Path $RedisRoot "redis-local.conf"
$PidFile = Join-Path $RedisRoot "redis.pid"

function Write-Info([string]$Message) {
    Write-Host "[redis] $Message"
}

function Install-Redis {
    New-Item -ItemType Directory -Force -Path $RedisRoot | Out-Null
    if (Test-Path $Server) {
        Write-Info "Redis $Version already installed: $ExtractDir"
        return
    }
    if (-not (Test-Path $Archive)) {
        Write-Info "Downloading Redis $Version..."
        Invoke-WebRequest -Uri $Url -OutFile $Archive
    }
    $hash = (Get-FileHash $Archive -Algorithm SHA256).Hash
    if ($hash -ne $ExpectedSha256) {
        throw "Redis archive checksum mismatch: $hash"
    }
    Write-Info "Extracting..."
    Expand-Archive -Path $Archive -DestinationPath $RedisRoot -Force
    if (-not (Test-Path $Server)) {
        throw "redis-server.exe not found after extraction"
    }
    Write-Info "Installed: $Server"
}

function Write-Config {
    $log = (Join-Path $RedisRoot "redis-local.log").Replace("\", "/")
    $dir = $RedisRoot.Replace("\", "/")
    @"
bind 127.0.0.1
port $Port
protected-mode yes
save ""
appendonly no
maxmemory 256mb
maxmemory-policy allkeys-lru
loglevel notice
logfile "$log"
dir "$dir"
"@ | Set-Content -Path $Config -Encoding ASCII
}

function Test-Redis {
    if (-not (Test-Path $Cli)) { return $false }
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    $output = & $Cli -h 127.0.0.1 -p $Port ping 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previous
    return ($code -eq 0) -and ($output -match "PONG")
}

function Start-Redis {
    if (-not (Test-Path $Server)) {
        throw "Redis is not installed. Run: .\scripts\redis-local.ps1 install"
    }
    if (Test-Redis) {
        Write-Info "Already running on 127.0.0.1:$Port"
        return
    }
    Write-Config
    $process = Start-Process -FilePath $Server `
        -ArgumentList "redis-local.conf" `
        -WorkingDirectory $RedisRoot `
        -WindowStyle Hidden `
        -PassThru
    Set-Content -Path $PidFile -Value $process.Id -Encoding ASCII
    Start-Sleep -Seconds 2
    if (-not (Test-Redis)) {
        throw "Redis did not start. See $RedisRoot\redis-local.log"
    }
    Write-Info "Started on 127.0.0.1:$Port (PID $($process.Id))"
    Write-Info "Use REDIS_URL=redis://127.0.0.1:$Port/0"
}

function Stop-Redis {
    if (Test-Redis) {
        $null = & $Cli -h 127.0.0.1 -p $Port shutdown nosave 2>&1
        Start-Sleep -Seconds 1
    }
    if (Test-Path $PidFile) {
        $processId = Get-Content $PidFile -ErrorAction SilentlyContinue
        if ($processId) {
            Stop-Process -Id ([int]$processId) -Force -ErrorAction SilentlyContinue
        }
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    }
    Write-Info "Stopped"
}

function Show-Status {
    if (Test-Redis) {
        $version = & $Cli -h 127.0.0.1 -p $Port info server |
            Select-String -Pattern "^redis_version:" |
            ForEach-Object { $_.Line.Split(":")[1].Trim() }
        Write-Info "Running on 127.0.0.1:$Port (Redis $version)"
        & $Cli -h 127.0.0.1 -p $Port info memory |
            Select-String -Pattern "used_memory_human|maxmemory_human|maxmemory_policy"
    } else {
        Write-Info "Not running on 127.0.0.1:$Port"
    }
}

switch ($Action) {
    "install" { Install-Redis }
    "start" { Start-Redis }
    "stop" { Stop-Redis }
    "status" { Show-Status }
}
