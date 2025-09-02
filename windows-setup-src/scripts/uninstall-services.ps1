$ErrorActionPreference = 'SilentlyContinue'
try {
  $nssm = (Get-Command nssm.exe -ErrorAction Stop).Source
} catch {
  exit 0
}

& $nssm stop  'TIMon-UI'
& $nssm stop  'TIMon-Cron'
& $nssm remove 'TIMon-UI'   confirm
& $nssm remove 'TIMon-Cron' confirm
