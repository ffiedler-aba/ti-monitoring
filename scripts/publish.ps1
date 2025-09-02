# Requires -Version 5.1
param(
    [string]$Version = "",
    [string]$ZipPath = "",
    [switch]$Prerelease = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Info([string]$msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn([string]$msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err([string]$msg) { Write-Host "[ERR ] $msg" -ForegroundColor Red }

function Test-GitHubCLI() {
    $null -ne (Get-Command 'gh' -ErrorAction SilentlyContinue)
}

function Test-GitRepository() {
    $null -ne (Get-Command 'git' -ErrorAction SilentlyContinue) -and (Test-Path '.git')
}

function Get-CurrentVersion() {
    $gitTag = git describe --tags --abbrev=0 2>$null
    if ($gitTag) {
        return $gitTag.TrimStart('v')
    }
    return "1.0.0"
}

function Get-NextVersion([string]$CurrentVersion) {
    $parts = $CurrentVersion.Split('.')
    if ($parts.Length -eq 3) {
        $patch = [int]$parts[2] + 1
        return "$($parts[0]).$($parts[1]).$patch"
    }
    return "1.0.1"
}

function Find-LatestZip() {
    $zipFiles = Get-ChildItem -Path "." -Filter "ti-monitoring-portable-*.zip" | Sort-Object LastWriteTime -Descending
    if ($zipFiles.Count -gt 0) {
        return $zipFiles[0].FullName
    }
    return $null
}

function New-GitHubRelease([string]$Version, [string]$ZipPath, [bool]$IsPrerelease) {
    Write-Info "Erstelle GitHub Release für Version v$Version"
    
    # Prüfe GitHub CLI
    if (-not (Test-GitHubCLI)) {
        Write-Err "GitHub CLI (gh) nicht gefunden. Bitte installiere es von: https://cli.github.com/"
        return $false
    }
    
    # Prüfe Git Repository
    if (-not (Test-GitRepository)) {
        Write-Err "Kein Git Repository gefunden. Bitte führe das Skript aus dem Repository-Root aus."
        return $false
    }
    
    # Prüfe GitHub Authentication
    try {
        $null = gh auth status 2>$null
    } catch {
        Write-Err "GitHub CLI nicht authentifiziert. Führe 'gh auth login' aus."
        return $false
    }
    
    # Prüfe ob ZIP-Datei existiert
    if (-not (Test-Path -LiteralPath $ZipPath)) {
        Write-Err "ZIP-Datei nicht gefunden: $ZipPath"
        return $false
    }
    
    # Git Tag erstellen
    $tagName = "v$Version"
    Write-Info "Erstelle Git Tag: $tagName"
    try {
        git tag -a $tagName -m "Release version $Version"
        git push origin $tagName
        Write-Info "Tag $tagName erfolgreich erstellt und gepusht."
    } catch {
        Write-Err "Fehler beim Erstellen des Git Tags: $_"
        return $false
    }
    
    # Release Notes generieren
    $releaseType = if ($IsPrerelease) { "Pre-Release" } else { "Release" }
    $releaseNotes = @"
## TI-Monitoring Portable v$Version ($releaseType)

### Windows Portable Build
- Vollständig portable Windows-Anwendung
- Automatische Service-Installation mit NSSM
- Virtuelle Python-Umgebung enthalten
- Umfassende Installationsanleitung

### Installation
1. ZIP-Datei entpacken
2. `install-service.cmd` als Administrator ausführen
3. Web-Interface unter http://localhost:8050 aufrufen

### Features
- Automatische TI-Service-Überwachung
- Web-basierte Benutzeroberfläche
- Beliebige Benachrichtigungsmöglichkeiten über Apprise
- Detaillierte Statistiken und Logs

### Changelog
- Siehe [Commits](https://github.com/$(gh repo view --json owner,name -q '.owner.login + "/" + .name")/compare/$(git describe --tags --abbrev=0 2>$null || 'HEAD~1')...v$Version) für Details
"@
    
    # GitHub Release erstellen
    Write-Info "Erstelle GitHub Release..."
    try {
        $releaseArgs = @($tagName, $ZipPath, "--title", "TI-Monitoring Portable v$Version", "--notes", $releaseNotes)
        if ($IsPrerelease) {
            $releaseArgs += "--prerelease"
        }
        
        $releaseOutput = & gh release create @releaseArgs
        Write-Info "GitHub Release erfolgreich erstellt: $releaseOutput"
        return $true
    } catch {
        Write-Err "Fehler beim Erstellen des GitHub Releases: $_"
        return $false
    }
}

# Hauptlogik
Write-Host "========================================"
Write-Host "TI-Monitoring GitHub Release Publisher"
Write-Host "========================================"
Write-Host ""

# Version bestimmen
if (-not $Version) {
    $currentVersion = Get-CurrentVersion
    $nextVersion = Get-NextVersion $currentVersion
    Write-Info "Aktuelle Version: $currentVersion"
    Write-Info "Nächste Version: $nextVersion"
    $Version = Read-Host "Version eingeben (Enter für $nextVersion)"
    if (-not $Version) { $Version = $nextVersion }
}

# ZIP-Datei finden
if (-not $ZipPath) {
    $latestZip = Find-LatestZip
    if ($latestZip) {
        Write-Info "Gefundene ZIP-Datei: $latestZip"
        $useLatest = Read-Host "Diese ZIP-Datei verwenden? (j/n)"
        if ($useLatest -eq "j" -or $useLatest -eq "y") {
            $ZipPath = $latestZip
        } else {
            $ZipPath = Read-Host "Pfad zur ZIP-Datei eingeben"
        }
    } else {
        $ZipPath = Read-Host "Pfad zur ZIP-Datei eingeben"
    }
}

# Prerelease-Status
if ($Prerelease) {
    $makePrerelease = Read-Host "Als Pre-Release erstellen? (j/n, Standard: j)"
    if ($makePrerelease -eq "n") { $Prerelease = $false }
}

# Zusammenfassung anzeigen
Write-Host ""
Write-Info "========================================"
Write-Info "Release-Zusammenfassung"
Write-Info "========================================"
Write-Info "Version: v$Version"
Write-Info "ZIP-Datei: $ZipPath"
Write-Info "Pre-Release: $Prerelease"
Write-Host ""

$confirm = Read-Host "Release erstellen? (j/n)"
if ($confirm -ne "j" -and $confirm -ne "y") {
    Write-Info "Abgebrochen."
    exit 0
}

# Release erstellen
$success = New-GitHubRelease -Version $Version -ZipPath $ZipPath -IsPrerelease $Prerelease
if ($success) {
    Write-Host ""
    Write-Info "========================================"
    Write-Info "Release erfolgreich erstellt!"
    Write-Info "========================================"
    Write-Info "Release URL: https://github.com/$(gh repo view --json owner,name -q '.owner.login + "/" + .name")/releases/tag/v$Version"
    Write-Info "Tag: v$Version"
    Write-Info "ZIP: $ZipPath"
} else {
    Write-Err "Release konnte nicht erstellt werden!"
    exit 1
}
