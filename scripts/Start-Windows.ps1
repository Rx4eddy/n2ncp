#requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateSet('Start', 'Stop')][string] $Action = 'Start',
    [switch] $NoBrowser
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$projectRoot = Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $PSScriptRoot 'LocalSetup.psm1') -Force
$compose = @('compose', '--project-directory', $projectRoot, '-f', (Join-Path $projectRoot 'docker-compose.yml'))

try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker Desktop was not found. Install it from https://www.docker.com/products/docker-desktop/, then restart this launcher.'
    }
    Write-Host 'n2ncp - local Windows website' -ForegroundColor Cyan
    Write-Host 'Checking Docker Desktop...'
    $engine = ''
    $deadline = (Get-Date).AddSeconds(120)
    $triedDesktop = $false
    do {
        $previous = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $output = & docker info --format '{{.OSType}}' 2>&1
        $code = $LASTEXITCODE
        $ErrorActionPreference = $previous
        if ($code -eq 0) { $engine = ($output -join '').Trim(); break }
        if (-not $triedDesktop) {
            $desktop = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
            if (Test-Path -LiteralPath $desktop) {
                Write-Host 'Starting Docker Desktop; waiting for its engine...'
                Start-Process -FilePath $desktop
            }
            $triedDesktop = $true
        }
        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $deadline)
    if (-not $engine) { throw 'Docker Desktop did not become ready. Open Docker Desktop, resolve any WSL/virtualization message, and run start-windows.cmd again.' }
    if ($engine -ne 'linux') { throw 'Docker Desktop must use Linux containers. Switch to Linux containers in Docker Desktop and run this launcher again.' }
    Invoke-N2ncpDocker -Arguments @('compose', 'version')

    if ($Action -eq 'Stop') {
        Invoke-N2ncpDocker -Arguments ($compose + @('stop'))
        Write-Host 'n2ncp stopped. Your account, notes, and database are preserved.' -ForegroundColor Green
        exit 0
    }

    $local = Initialize-LocalEnvironment -ProjectRoot $projectRoot
    if ($local.Created) { Write-Host 'Created local settings with randomly generated secrets.' }
    else { Write-Host 'Using your existing settings and database.' }
    Invoke-N2ncpDocker -Arguments ($compose + @('config', '--quiet'))
    Write-Host 'Building and starting n2ncp. The first run can take several minutes.' -ForegroundColor Cyan
    Invoke-N2ncpDocker -Arguments ($compose + @('up', '-d', '--build'))

    $ready = $false
    $deadline = (Get-Date).AddSeconds(180)
    Write-Host 'Waiting for the website and database...'
    do {
        try {
            $response = Invoke-RestMethod -Uri ($local.SiteUrl + '/health/') -TimeoutSec 5
            $ready = $response.status -eq 'ok'
        } catch { $ready = $false }
        if (-not $ready) { Start-Sleep -Seconds 3 }
    } while (-not $ready -and (Get-Date) -lt $deadline)
    if (-not $ready) { throw 'The website did not become healthy. Run: docker compose logs --tail=80 init web worker beat. See docs/WINDOWS.md for port and Docker troubleshooting.' }

    $workerReady = $false
    for ($attempt = 0; $attempt -lt 6 -and -not $workerReady; $attempt++) {
        $previous = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $reply = & docker @compose exec -T worker celery -A config inspect ping --timeout=5 2>&1
        $code = $LASTEXITCODE
        $ErrorActionPreference = $previous
        $workerReady = $code -eq 0 -and ($reply -join ' ') -match 'pong'
        if (-not $workerReady) { Start-Sleep -Seconds 2 }
    }
    if (-not $workerReady) { throw 'The website is responding, but the email worker is not ready. Run: docker compose logs --tail=80 worker redis. Startup has not been declared successful.' }
    $running = @(& docker @compose ps --status running --services)
    if ($LASTEXITCODE -ne 0 -or 'beat' -notin $running -or 'mailpit' -notin $running) {
        throw 'The reminder scheduler or local inbox is not running. Run: docker compose ps and docker compose logs --tail=80 beat mailpit.'
    }
    Invoke-N2ncpDocker -Arguments ($compose + @('exec', '-T', 'web', 'python', 'manage.py', 'shell', '-c', "from apps.contests.tasks import sync_all_contests; sync_all_contests.delay(); print('Contest refresh queued')"))

    Write-Host ''
    Write-Host ('Website is running: ' + $local.SiteUrl) -ForegroundColor Green
    Write-Host 'Verification email inbox: http://localhost:8025'
    Write-Host 'Create an account on the website, open its verification email in the local inbox, then sign in.'
    Write-Host 'Emails stay on your computer. No SMTP account or external email delivery is needed.'
    Write-Host 'You can close this window. Double-click stop-windows.cmd to stop; start-windows.cmd to return.'
    if (-not $NoBrowser) {
        Start-Process $local.SiteUrl
        if ($local.Created) { Start-Process 'http://localhost:8025' }
    }
    exit 0
} catch {
    Write-Host ''
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host 'No database volumes were deleted. Read docs/WINDOWS.md for recovery steps.'
    exit 1
}
