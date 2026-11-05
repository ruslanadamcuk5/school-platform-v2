param(
    [switch]$SkipFrontend
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$nodeDir = Join-Path $root '.tools\node-v22.14.0-win-x64'
$npm = Join-Path $nodeDir 'npm.cmd'
$failed = @()
$started = Get-Date

function Show-Tail {
    param(
        [object[]]$Lines,
        [int]$Count = 20
    )
    $Lines | Select-Object -Last $Count | ForEach-Object { Write-Host $_ }
}

if (-not (Test-Path $python)) {
    Write-Host "Python venv not found: $python" -ForegroundColor Red
    exit 2
}

Write-Host '== ruff =='
Push-Location (Join-Path $root 'backend')
$out = & $python -m ruff check . 2>&1
$code = $LASTEXITCODE
Pop-Location
Show-Tail $out 20
if ($code -ne 0) { $failed += 'ruff' }

Write-Host '== pytest =='
Push-Location (Join-Path $root 'backend')
$out = & $python -m pytest -o addopts="" -q --tb=line -p no:warnings 2>&1
$code = $LASTEXITCODE
Pop-Location
Show-Tail $out 20
if ($code -ne 0) { $failed += 'pytest' }

if (-not $SkipFrontend) {
    Write-Host '== typecheck =='
    if (Test-Path $npm) {
        $env:Path = "$nodeDir;$env:Path"
        Push-Location (Join-Path $root 'frontend')
        $out = & $npm run typecheck 2>&1
        $code = $LASTEXITCODE
        Pop-Location
        Show-Tail $out 20
        if ($code -ne 0) { $failed += 'typecheck' }
    }
    else {
        Write-Host "npm not found: $npm (skipped)" -ForegroundColor Yellow
    }
}

$elapsed = [math]::Round(((Get-Date) - $started).TotalSeconds, 1)
if ($failed.Count -gt 0) {
    Write-Host ("FAILED ({0}s): {1}" -f $elapsed, ($failed -join ', ')) -ForegroundColor Red
    exit 1
}
$checks = if ($SkipFrontend) { 'ruff, pytest' } else { 'ruff, pytest, typecheck' }
Write-Host ("OK ({0}s): {1}" -f $elapsed, $checks) -ForegroundColor Green
