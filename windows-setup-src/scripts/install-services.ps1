$ErrorActionPreference = 'Stop'

# Basisverzeichnisse
$App = Split-Path -Parent $MyInvocation.MyCommand.Path
$App = Join-Path $App '..' | Resolve-Path
$App = $App.Path

# Executables
$Python = Join-Path $App '.venv\Scripts\python.exe'

# NSSM
$nssm = (Get-Command nssm.exe -ErrorAction Stop).Source

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
