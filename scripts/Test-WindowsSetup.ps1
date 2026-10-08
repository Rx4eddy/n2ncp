# Run on Windows PowerShell 5.1 in CI; no Docker daemon or third-party test runner required.
#requires -Version 5.1
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
Import-Module (Join-Path $PSScriptRoot 'LocalSetup.psm1') -Force
$projectRoot = Split-Path -Parent $PSScriptRoot
$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('n2ncp setup test ' + [Guid]::NewGuid().ToString('N'))
$encoding = New-Object System.Text.UTF8Encoding($false)
$originalPath = $env:PATH
$passed = 0

function Assert-True {
    param([bool] $Condition, [string] $Message)
    if (-not $Condition) { throw $Message }
}
function Assert-Throws {
    param([scriptblock] $Work, [string] $Expected)
    $thrown = $false
    try { & $Work | Out-Null } catch {
        $thrown = $true
        if ($_.Exception.Message -notlike ('*' + $Expected + '*')) { throw }
    }
    Assert-True $thrown ('Expected failure: ' + $Expected)
}
function Write-Env {
    param([string] $Text)
    [System.IO.File]::WriteAllText((Join-Path $testRoot '.env'), $Text, $encoding)
}

try {
    New-Item -ItemType Directory -Path $testRoot | Out-Null
    Copy-Item -LiteralPath (Join-Path $projectRoot '.env.example') -Destination (Join-Path $testRoot '.env.example')
    foreach ($script in @('Start-Windows.ps1', 'LocalSetup.psm1', 'Test-WindowsSetup.ps1')) {
        $tokens = $null; $errors = $null
        [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $script), [ref] $tokens, [ref] $errors) | Out-Null
        Assert-True ($errors.Count -eq 0) ('PowerShell syntax error in ' + $script)
    }
    $passed++
    $initial = Initialize-LocalEnvironment -ProjectRoot $testRoot
    Assert-True $initial.Created 'First start must create .env'
    $envPath = Join-Path $testRoot '.env'
    $text = [System.IO.File]::ReadAllText($envPath)
    Assert-True ($text -notmatch 'replace-with') 'All secret placeholders must be replaced'
    Assert-True ($text -match '(?m)^SECRET_KEY=([a-f0-9]{64})\r?$') 'Secret must have 256 bits of randomness'
    $secret = $Matches[1]
    Assert-True ($text -match '(?m)^POSTGRES_PASSWORD=([a-f0-9]{48})\r?$') 'Database password must be URL-safe and random'
    $password = $Matches[1]
    Assert-True ($text.Contains('postgresql://n2ncp:' + $password + '@db:5432/n2ncp')) 'DATABASE_URL and PostgreSQL must use the same password'
    Assert-True (-not $text.Contains('SECRET_KEY=' + $password)) 'Application and database secrets must be independent'
    $bytes = [System.IO.File]::ReadAllBytes($envPath)
    Assert-True (-not ($bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191)) 'Compose .env must not start with a BOM'
    $passed++
    $again = Initialize-LocalEnvironment -ProjectRoot $testRoot
    Assert-True (-not $again.Created) 'Repeat startup must reuse existing .env'
    Assert-True ([System.IO.File]::ReadAllText($envPath) -ceq $text) 'Existing settings must be preserved byte for byte'
    $passed++
    $production = $text.Replace('DEBUG=1', 'DEBUG=0')
    Write-Env $production
    Assert-Throws { Initialize-LocalEnvironment -ProjectRoot $testRoot } 'local use only'
    Assert-True ([System.IO.File]::ReadAllText($envPath) -ceq $production) 'Production settings must not be modified'
    $passed++
    Write-Env ($text.Replace('SITE_URL=http://localhost:8000', 'SITE_URL=https://external.example'))
    Assert-Throws { Initialize-LocalEnvironment -ProjectRoot $testRoot } 'Local startup expects'
    $passed++
    Write-Env ($text.Replace('SECRET_KEY=' + $secret, 'SECRET_KEY=replace-with-a-secret'))
    Assert-Throws { Initialize-LocalEnvironment -ProjectRoot $testRoot } 'placeholder SECRET_KEY'
    $passed++
    Write-Env ($text.Replace('POSTGRES_PASSWORD=' + $password, 'POSTGRES_PASSWORD=unsafe@password'))
    Assert-Throws { Initialize-LocalEnvironment -ProjectRoot $testRoot } 'URL-safe database password'
    $passed++
    Write-Env ($text.Replace('ALLOWED_HOSTS=localhost,127.0.0.1', 'ALLOWED_HOSTS=localhost'))
    Assert-Throws { Initialize-LocalEnvironment -ProjectRoot $testRoot } 'include localhost and 127.0.0.1'
    $passed++
    # A real native-command failure must not be treated as a successful startup.
    [System.IO.File]::WriteAllText((Join-Path $testRoot 'docker.cmd'), "@echo off`r`nexit /b 17`r`n", $encoding)
    $env:PATH = $testRoot + [System.IO.Path]::PathSeparator + $originalPath
    Assert-Throws { Invoke-N2ncpDocker -Arguments @('compose', 'up') } 'exit code 17'
    [System.IO.File]::WriteAllText((Join-Path $testRoot 'docker.cmd'), "@echo off`r`nexit /b 0`r`n", $encoding)
    Invoke-N2ncpDocker -Arguments @('compose', 'version')
    $passed++
    Write-Host "$passed Windows setup checks passed (including paths with spaces)."
} finally {
    $env:PATH = $originalPath
    # Only the unique temporary directory created by this test is removed.
    Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction SilentlyContinue
}
