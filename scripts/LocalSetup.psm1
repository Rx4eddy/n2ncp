Set-StrictMode -Version 2.0

function New-LocalSecret {
    param([int] $ByteCount = 32)
    $bytes = New-Object byte[] $ByteCount
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $random.GetBytes($bytes) } finally { $random.Dispose() }
    return ([BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
}

function Read-LocalSettings {
    param([Parameter(Mandatory = $true)][string] $Path)
    $settings = @{}
    foreach ($line in [System.IO.File]::ReadAllLines($Path)) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$') {
            $settings[$Matches[1]] = $Matches[2].Trim().Trim('"').Trim("'")
        }
    }
    return $settings
}

function Initialize-LocalEnvironment {
    param([Parameter(Mandatory = $true)][string] $ProjectRoot)
    $envPath = Join-Path $ProjectRoot '.env'
    $created = $false
    if (-not (Test-Path -LiteralPath $envPath)) {
        $template = [System.IO.File]::ReadAllText((Join-Path $ProjectRoot '.env.example'))
        $secret = New-LocalSecret
        $password = New-LocalSecret -ByteCount 24
        $template = $template.Replace('replace-with-a-random-64-character-secret-before-starting', $secret)
        $template = $template.Replace('replace-with-a-random-hex-database-password', $password)
        # UTF-8 without BOM works consistently with Compose and Windows PowerShell 5.1.
        $encoding = New-Object System.Text.UTF8Encoding($false)
        $bytes = $encoding.GetBytes($template)
        # CreateNew refuses to overwrite a file created by another launcher.
        $file = [System.IO.File]::Open($envPath, [System.IO.FileMode]::CreateNew)
        try { $file.Write($bytes, 0, $bytes.Length) } finally { $file.Dispose() }
        $created = $true
    }
    $settings = Read-LocalSettings -Path $envPath
    foreach ($key in @('SECRET_KEY', 'POSTGRES_PASSWORD', 'DEBUG', 'SITE_URL', 'ALLOWED_HOSTS')) {
        if (-not $settings.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($settings[$key]) -or $settings[$key] -like '*replace-with*') {
            throw "Your existing .env has an unset or placeholder $key. It was preserved. Follow docs/WINDOWS.md to repair an existing setup."
        }
    }
    if ($settings['DEBUG'] -ne '1') {
        throw 'This launcher is for local use only. Your existing .env is not in DEBUG=1 mode and was preserved. Use a separate folder for the local installation.'
    }
    if ($settings['SITE_URL'].TrimEnd('/') -notin @('http://localhost:8000', 'http://127.0.0.1:8000')) {
        throw 'Local startup expects SITE_URL=http://localhost:8000 or http://127.0.0.1:8000. Your .env was not changed.'
    }
    $hosts = @($settings['ALLOWED_HOSTS'].Split(',') | ForEach-Object { $_.Trim() })
    if ('localhost' -notin $hosts -or '127.0.0.1' -notin $hosts) {
        throw 'For local startup, include localhost and 127.0.0.1 in ALLOWED_HOSTS in .env.'
    }
    if ($settings['POSTGRES_PASSWORD'] -match '[:/@?#%\s]') {
        throw 'This local Compose configuration needs a URL-safe database password. Keep the existing database password intact and follow docs/WINDOWS.md for an existing installation.'
    }
    return [PSCustomObject]@{ Created = $created; SiteUrl = $settings['SITE_URL'].TrimEnd('/') }
}

function Invoke-N2ncpDocker {
    param([Parameter(Mandatory = $true)][string[]] $Arguments)
    $previous = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & docker @Arguments
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previous }
    if ($code -ne 0) { throw "Docker failed (exit code $code). Review the error above; startup has stopped." }
}

Export-ModuleMember -Function Initialize-LocalEnvironment, Invoke-N2ncpDocker
