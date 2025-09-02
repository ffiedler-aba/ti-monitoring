$ErrorActionPreference = 'Stop'

# Basisverzeichnisse
$App = Split-Path -Parent $MyInvocation.MyCommand.Path
$App = Join-Path $App '..' | Resolve-Path
$App = $App.Path
 $ToolsDir = Join-Path $App 'tools'

# Konfiguration (kein Git mehr im Skript)

# Executables / Pfade
$Python     = Join-Path $App '.venv\Scripts\python.exe'
$Pip        = Join-Path $App '.venv\Scripts\pip.exe'
$AppScript  = Join-Path $App 'app.py'
$CronScript = Join-Path $App 'cron.py'

 # Keine Git-Funktionen mehr erforderlich

function Resolve-NssmPath {
  $bundled = Join-Path $ToolsDir 'nssm\nssm.exe'
  if (Test-Path -LiteralPath $bundled) { return $bundled }
  throw "Bundled NSSM nicht gefunden: $bundled"
}

function Ensure-Repo { if (!(Test-Path -LiteralPath $AppScript)) { throw "Repository fehlt oder ungültig im Pfad: $App" } }

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
