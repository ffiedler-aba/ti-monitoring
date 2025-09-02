$ErrorActionPreference = 'Stop'

# Basisverzeichnisse
$App = Split-Path -Parent $MyInvocation.MyCommand.Path
$App = Join-Path $App '..' | Resolve-Path
$App = $App.Path

# Executables
$Python = Join-Path $App '.venv\Scripts\python.exe'

function Resolve-NssmPath {
  param()
  try {
    $cmd = Get-Command nssm.exe -ErrorAction Stop
    return $cmd.Source
  } catch {}
  $candidates = @(
    Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\nssm.exe'),
    (Join-Path $env:ProgramFiles 'nssm\win64\nssm.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'nssm\win32\nssm.exe'),
    (Join-Path $env:SystemRoot 'System32\nssm.exe')
  foreach ($c in $candidates) {
    if ($c -and (Test-Path -LiteralPath $c)) { return $c }
  }
  throw 'nssm.exe wurde nicht gefunden. Bitte sicherstellen, dass NSSM per winget installiert ist und der Link unter %LOCALAPPDATA%\\Microsoft\\WinGet\\Links vorhanden ist.'
}

# NSSM
$nssm = Resolve-NssmPath

# Logs-Verzeichnis
$logDir = Join-Path $App 'data'
if (!(Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

# Service TIMon-UI
& $nssm install 'TIMon-UI' $Python 'app.py'
& $nssm set 'TIMon-UI' AppDirectory $App
& $nssm set 'TIMon-UI' AppStdout (Join-Path $logDir 'ui.out.log')
& $nssm set 'TIMon-UI' AppStderr (Join-Path $logDir 'ui.err.log')
& $nssm set 'TIMon-UI' Start SERVICE_AUTO_START

# Service TIMon-Cron
& $nssm install 'TIMon-Cron' $Python 'cron.py'
& $nssm set 'TIMon-Cron' AppDirectory $App
& $nssm set 'TIMon-Cron' AppStdout (Join-Path $logDir 'cron.out.log')
& $nssm set 'TIMon-Cron' AppStderr (Join-Path $logDir 'cron.err.log')
& $nssm set 'TIMon-Cron' Start SERVICE_AUTO_START

# Start services
& $nssm start 'TIMon-UI'
& $nssm start 'TIMon-Cron'
