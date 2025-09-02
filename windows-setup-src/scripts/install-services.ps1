$ErrorActionPreference = 'Stop'

# Basisverzeichnisse
$App = Split-Path -Parent $MyInvocation.MyCommand.Path
$App = Join-Path $App '..' | Resolve-Path
$App = $App.Path

# Konfiguration
$RepoUrl = 'https://github.com/elpatron68/ti-monitoring.git'

# Executables / Pfade
$Python     = Join-Path $App '.venv\Scripts\python.exe'
$Pip        = Join-Path $App '.venv\Scripts\pip.exe'
$AppScript  = Join-Path $App 'app.py'
$CronScript = Join-Path $App 'cron.py'

function Resolve-GitPath {
  try { return (Get-Command git.exe -ErrorAction Stop).Source } catch {}
  $candidates = @(
    (Join-Path $env:ProgramFiles 'Git\cmd\git.exe'),
    (Join-Path $env:ProgramFiles 'Git\bin\git.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Git\cmd\git.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Git\bin\git.exe'),
    (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\git.exe')
  )
  foreach ($c in $candidates) { if ($c -and (Test-Path -LiteralPath $c)) { return $c } }
  throw 'git.exe wurde nicht gefunden. Bitte stellen Sie sicher, dass Git installiert ist.'
}

function Resolve-NssmPath {
  param()
  try {
    $cmd = Get-Command nssm.exe -ErrorAction Stop
    return $cmd.Source
  } catch {}
  $candidates = @(
    (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\nssm.exe'),
    (Join-Path $env:ProgramFiles 'nssm\win64\nssm.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'nssm\win32\nssm.exe'),
    (Join-Path $env:SystemRoot 'System32\nssm.exe')
  )
  foreach ($c in $candidates) {
    if ($c -and (Test-Path -LiteralPath $c)) { return $c }
  }
  throw 'nssm.exe wurde nicht gefunden. Bitte sicherstellen, dass NSSM per winget installiert ist und der Link unter %LOCALAPPDATA%\Microsoft\WinGet\Links vorhanden ist.'
}

function Ensure-Repo {
  $git = Resolve-GitPath
  if (Test-Path -LiteralPath $AppScript -PathType Leaf -ErrorAction SilentlyContinue) { return }
  if (Test-Path -LiteralPath (Join-Path $App '.git')) {
    try { Push-Location $App; & $git pull --ff-only; Pop-Location } catch { }
  } else {
    if (!(Test-Path -LiteralPath $App)) { New-Item -ItemType Directory -Path $App | Out-Null }
    & $git -c http.sslBackend=schannel clone --depth 1 $RepoUrl $App
  }
  if (!(Test-Path -LiteralPath $AppScript)) { throw "Repository fehlt oder ungültig im Pfad: $App" }
}

function Ensure-Venv {
  if (!(Test-Path -LiteralPath $Python)) {
    & python -m venv (Join-Path $App '.venv')
  }
  if (!(Test-Path -LiteralPath $Python)) { throw "Venv konnte nicht erstellt werden: $($Python)" }
  & $Python -m pip install --upgrade pip
  & $Pip install -r (Join-Path $App 'requirements.txt')
}

# Vorbedingungen sicherstellen
Ensure-Repo
Ensure-Venv

# NSSM
$nssm = Resolve-NssmPath

# Logs-Verzeichnis
$logDir = Join-Path $App 'data'
if (!(Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

# Gemeinsame Einstellungen
$envExtra = "PYTHONIOENCODING=UTF-8;PYTHONUNBUFFERED=1;PYTHONPATH=$App"

# Service TIMon-UI
& $nssm install 'TIMon-UI' $Python $AppScript
& $nssm set 'TIMon-UI' AppDirectory $App
& $nssm set 'TIMon-UI' AppParameters $AppScript
& $nssm set 'TIMon-UI' AppStdout (Join-Path $logDir 'ui.out.log')
& $nssm set 'TIMon-UI' AppStderr (Join-Path $logDir 'ui.err.log')
& $nssm set 'TIMon-UI' AppEnvironmentExtra $envExtra
& $nssm set 'TIMon-UI' AppExit Default Restart
& $nssm set 'TIMon-UI' AppKillProcessTree 1
& $nssm set 'TIMon-UI' Start SERVICE_AUTO_START

# Service TIMon-Cron
& $nssm install 'TIMon-Cron' $Python $CronScript
& $nssm set 'TIMon-Cron' AppDirectory $App
& $nssm set 'TIMon-Cron' AppParameters $CronScript
& $nssm set 'TIMon-Cron' AppStdout (Join-Path $logDir 'cron.out.log')
& $nssm set 'TIMon-Cron' AppStderr (Join-Path $logDir 'cron.err.log')
& $nssm set 'TIMon-Cron' AppEnvironmentExtra $envExtra
& $nssm set 'TIMon-Cron' AppExit Default Restart
& $nssm set 'TIMon-Cron' AppKillProcessTree 1
& $nssm set 'TIMon-Cron' Start SERVICE_AUTO_START

# Start services
& $nssm start 'TIMon-UI'
& $nssm start 'TIMon-Cron'
