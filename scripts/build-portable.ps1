# Requires -Version 5.1
param(
    [string]$StageDir = "portable-build",
    [string]$PythonExe = "python",
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Info([string]$msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn([string]$msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err([string]$msg) { Write-Host "[ERR ] $msg" -ForegroundColor Red }

function Test-CommandExists([string]$name) {
    $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

function New-CleanDirectory([string]$Path, [switch]$ForceDelete) {
    if (Test-Path -LiteralPath $Path) {
        if (-not $ForceDelete) { Write-Warn "'$Path' existiert bereits. Verwende -Force um zu überschreiben."; exit 1 }
        Write-Info "Lösche bestehenden Ordner '$Path'"
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
    Write-Info "Erstelle Ordner '$Path'"
    New-Item -ItemType Directory -Path $Path | Out-Null
}

function Copy-RepositoryToStage([string]$StagePath) {
    Write-Info "Kopiere Repository-Inhalt nach '$StagePath'"

    $excludeDirs = @(
        '.git','node_modules','.venv','portable-build','dist','build','out',
        '.mypy_cache','.pytest_cache','.ruff_cache','__pycache__'
    )
    $excludeFiles = @('.DS_Store')

    # Robocopy ist robust und schnell; /MIR spiegelt, aber wir kopieren in leeres Ziel
    $src = (Get-Location).Path
    $dst = (Resolve-Path -LiteralPath $StagePath).Path

    $excludeDirsArgs = @()
    foreach ($d in $excludeDirs) { $excludeDirsArgs += @('/XD', (Join-Path $src $d)) }
    $excludeFilesArgs = @()
    foreach ($f in $excludeFiles) { $excludeFilesArgs += @('/XF', (Join-Path $src $f)) }

    $args = @($src, $dst, '/E') + $excludeDirsArgs + $excludeFilesArgs
    $rc = Start-Process -FilePath robocopy -ArgumentList $args -NoNewWindow -PassThru -Wait
    # Robocopy erfolgreiche Exitcodes: 0-7
    if ($rc.ExitCode -gt 7) { throw "Robocopy fehlgeschlagen (ExitCode=$($rc.ExitCode))" }
}

function Ensure-ExampleFiles([string]$StagePath) {
    Push-Location -LiteralPath $StagePath
    try {
        Write-Info "Übernehme Beispielkonfigurationen falls nötig"
        if ((Test-Path 'config.yaml.example' -PathType Leaf) -and -not (Test-Path 'config.yaml')) {
            Copy-Item 'config.yaml.example' 'config.yaml'
        }
        if ((Test-Path 'notifications.json.example' -PathType Leaf) -and -not (Test-Path 'notifications.json')) {
            Copy-Item 'notifications.json.example' 'notifications.json'
        }
        if ((Test-Path '.env.example' -PathType Leaf) -and -not (Test-Path '.env')) {
            Copy-Item '.env.example' '.env'
        }
    }
    finally { Pop-Location }
}

function Ensure-DataFolder([string]$StagePath) {
    $dataStage = Join-Path $StagePath 'data'
    if (-not (Test-Path -LiteralPath $dataStage)) {
        Write-Info "Erstelle '$dataStage'"
        New-Item -ItemType Directory -Path $dataStage | Out-Null
    }

    if (Test-Path -LiteralPath 'data' -PathType Container) {
        Write-Info "Übernehme bestehende Daten nach '$dataStage'"
        $rc = Start-Process -FilePath robocopy -ArgumentList @('data', $dataStage, '/E') -NoNewWindow -PassThru -Wait
        if ($rc.ExitCode -gt 7) { throw "Robocopy (data) fehlgeschlagen (ExitCode=$($rc.ExitCode))" }
    }
    else {
        $keep = Join-Path $dataStage '.keep'
        if (-not (Test-Path -LiteralPath $keep)) { New-Item -ItemType File -Path $keep | Out-Null }
    }
}

function Ensure-ToolsFolder([string]$StagePath) {
    $toolsStage = Join-Path $StagePath 'tools'
    if (-not (Test-Path -LiteralPath $toolsStage)) {
        Write-Info "Erstelle '$toolsStage'"
        New-Item -ItemType Directory -Path $toolsStage | Out-Null
    }

    if (Test-Path -LiteralPath 'tools' -PathType Container) {
        Write-Info "Übernehme tools nach '$toolsStage'"
        $rc = Start-Process -FilePath robocopy -ArgumentList @('tools', $toolsStage, '/E') -NoNewWindow -PassThru -Wait
        if ($rc.ExitCode -gt 7) { throw "Robocopy (tools) fehlgeschlagen (ExitCode=$($rc.ExitCode))" }
    }
    else {
        Write-Info "Kein tools-Verzeichnis gefunden – überspringe"
    }
}

function New-WindowsVenv([string]$StagePath, [string]$Python) {
    Write-Info "Erzeuge venv im Staging"
    $venvPath = Join-Path $StagePath '.venv'
    & $Python -m venv $venvPath

    $pip = Join-Path $venvPath 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pip)) { throw "Venv wurde nicht korrekt erstellt: $venvPath" }

    $req = Join-Path $StagePath 'requirements.txt'
    if (Test-Path -LiteralPath $req -PathType Leaf) {
        Write-Info "Installiere Requirements in venv"
        & $pip -m pip install --upgrade pip
        & $pip -m pip install -r $req --no-cache-dir
        Write-Info "Requirements-Installation abgeschlossen"
        
        # Validiere wichtige Pakete
        Write-Info "Validiere Installation wichtiger Pakete..."
        $criticalPackages = @('dash', 'plotly', 'requests', 'apprise')
        foreach ($pkg in $criticalPackages) {
            try {
                & $pip show $pkg | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    Write-Info "✓ $pkg installiert"
                } else {
                    Write-Warn "✗ $pkg nicht gefunden"
                }
            } catch {
                Write-Warn "✗ $pkg Validierung fehlgeschlagen"
            }
        }
    }
    else {
        Write-Warn "requirements.txt nicht gefunden – überspringe Paketinstallation"
    }
}

function New-PortableZip([string]$StagePath) {
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $zipName = "ti-monitoring-portable-$timestamp.zip"
    $zipPath = Join-Path (Get-Location) $zipName
    Write-Info "Erzeuge ZIP: $zipPath"
    if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
    Compress-Archive -Path $StagePath -DestinationPath $zipPath -Force
    return $zipPath
}

# Vorbedingungen prüfen
if (-not (Test-CommandExists 'robocopy')) { Write-Err "'robocopy' wird benötigt (Windows Bordmittel)."; exit 1 }
if (-not (Test-CommandExists $PythonExe)) { Write-Err "Python nicht gefunden: '$PythonExe'"; exit 1 }

# 1) Staging vorbereiten
New-CleanDirectory -Path $StageDir -ForceDelete:$Force

# 2) Dateien kopieren (ohne .git/.venv/etc.)
Copy-RepositoryToStage -StagePath $StageDir

# 3) Beispielkonfigurationen übernehmen
Ensure-ExampleFiles -StagePath $StageDir

# 4) data/ sicherstellen und befüllen
Ensure-DataFolder -StagePath $StageDir

# 5) tools/ sicherstellen und befüllen
Ensure-ToolsFolder -StagePath $StageDir

# 6) venv erstellen und Requirements installieren
New-WindowsVenv -StagePath $StageDir -Python $PythonExe

# 7) ZIP erzeugen
$zip = New-PortableZip -StagePath $StageDir

Write-Host ""; Write-Info "Fertig. ZIP erstellt: $zip"

