[Setup]
AppName=TI Monitoring
AppVersion=1.0.0
DefaultDirName={commonpf}\ti-monitoring
DefaultGroupName=TI Monitoring
PrivilegesRequired=admin
OutputDir=.
OutputBaseFilename=TI-Monitoring-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Files]
; NSSM (mitliefern)
Source: "nssm-2.24\\win64\\nssm.exe"; DestDir: "{app}\\tools\\nssm"; Flags: ignoreversion

[Run]
; 1) winget Vorprüfung und Installationen (silent)
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command if(-not (Get-Command winget -ErrorAction SilentlyContinue)) {{ Write-Error 'winget nicht gefunden. Bitte App-Installer installieren.'; exit 1 }}"; StatusMsg: "Prüfe winget..."; Flags: runhidden
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command winget install -e --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements"; StatusMsg: "Installiere Python..."; Flags: runhidden
; keine winget-Installation von NSSM nötig; wird mitgeliefert

; 2) Zielordner anlegen
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command if(!(Test-Path -LiteralPath '{app}')){{ New-Item -ItemType Directory -Path '{app}' | Out-Null }}"; StatusMsg: "Lege Installationsordner an..."; Flags: runhidden

; 3) Venv anlegen
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command python -m venv '{app}\\.venv'"; StatusMsg: "Erzeuge virtuelles Umfeld..."; Flags: runhidden

; 4) Code laden (ZIP) und entpacken
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command $tmp=Join-Path $env:TEMP 'ti-mon.zip'; Invoke-WebRequest -Uri 'https://github.com/elpatron68/ti-monitoring/archive/refs/heads/main.zip' -OutFile $tmp -UseBasicParsing; $dir=Join-Path $env:TEMP ('ti-mon-' + [guid]::NewGuid()); New-Item -ItemType Directory -Path $dir | Out-Null; Expand-Archive -Path $tmp -DestinationPath $dir -Force; $src=Get-ChildItem -Path $dir -Directory | Select-Object -First 1; Copy-Item -Path (Join-Path $src.FullName '*') -Destination '{app}' -Recurse -Force"; StatusMsg: "Lade und entpacke Anwendung..."; Flags: runhidden

; 4b) Beispiel-Konfigurationen übernehmen (nur wenn noch nicht vorhanden)
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command if(!(Test-Path -LiteralPath '{app}\\config.yaml') -and (Test-Path -LiteralPath '{app}\\config.yaml.example')){{ Copy-Item -Path '{app}\\config.yaml.example' -Destination '{app}\\config.yaml' }}; if(!(Test-Path -LiteralPath '{app}\\notifications.json') -and (Test-Path -LiteralPath '{app}\\notifications.json.example')){{ Copy-Item -Path '{app}\\notifications.json.example' -Destination '{app}\\notifications.json' }}; if(!(Test-Path -LiteralPath '{app}\\.env') -and (Test-Path -LiteralPath '{app}\\.env.example')){{ Copy-Item -Path '{app}\\.env.example' -Destination '{app}\\.env' }}"; StatusMsg: "Übernehme Beispiel-Konfigurationen..."; Flags: runhidden

; 5) Requirements installieren
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command '{app}\\.venv\\Scripts\\python.exe' -m pip install --upgrade pip"; StatusMsg: "Aktualisiere pip..."; Flags: runhidden
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command '{app}\\.venv\\Scripts\\pip.exe' install -r '{app}\\requirements.txt'"; StatusMsg: "Installiere Abhängigkeiten..."; Flags: runhidden

; 6) Dienste mit gebundletem NSSM anlegen und starten
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command if(!(Test-Path -LiteralPath '{app}\\data')){{ New-Item -ItemType Directory -Path '{app}\\data' | Out-Null }}; $n='{app}\\tools\\nssm\\nssm.exe'; $py='{app}\\.venv\\Scripts\\python.exe'; $app='{app}'; & $n install TIMon-UI $py; & $n set TIMon-UI AppParameters '""{app}\\app.py""'; & $n set TIMon-UI AppDirectory $app; & $n set TIMon-UI AppStdout '""{app}\\data\\ui.out.log""'; & $n set TIMon-UI AppStderr '""{app}\\data\\ui.err.log""'; & $n set TIMon-UI AppEnvironmentExtra 'PYTHONIOENCODING=UTF-8' 'PYTHONUNBUFFERED=1' 'PYTHONPATH={app}'; & $n set TIMon-UI Start SERVICE_AUTO_START; & $n install TIMon-Cron $py; & $n set TIMon-Cron AppParameters '""{app}\\cron.py""'; & $n set TIMon-Cron AppDirectory $app; & $n set TIMon-Cron AppStdout '""{app}\\data\\cron.out.log""'; & $n set TIMon-Cron AppStderr '""{app}\\data\\cron.err.log""'; & $n set TIMon-Cron AppEnvironmentExtra 'PYTHONIOENCODING=UTF-8' 'PYTHONUNBUFFERED=1' 'PYTHONPATH={app}'; & $n set TIMon-Cron Start SERVICE_AUTO_START; & $n start TIMon-UI; & $n start TIMon-Cron"; StatusMsg: "Richte Dienste ein..."; Flags: runhidden

; 4) Dienste und Firewall einrichten
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File '{app}\\scripts\\install-services.ps1'"; StatusMsg: "Richte Dienste ein..."; Flags: runhidden
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command if(-not (Get-NetFirewallRule -DisplayName 'TI Monitoring UI' -ErrorAction SilentlyContinue)) {{ New-NetFirewallRule -DisplayName 'TI Monitoring UI' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8050 }}"; StatusMsg: "Öffne Firewall-Port 8050..."; Flags: runhidden skipifsilent

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command if(Get-Service TIMon-UI -ErrorAction SilentlyContinue){{ sc.exe stop TIMon-UI; '{app}\\tools\\nssm\\nssm.exe' remove TIMon-UI confirm }}"; RunOnceId: "svc_ui_cleanup"; Flags: runhidden
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command if(Get-Service TIMon-Cron -ErrorAction SilentlyContinue){{ sc.exe stop TIMon-Cron; '{app}\\tools\\nssm\\nssm.exe' remove TIMon-Cron confirm }}"; RunOnceId: "svc_cron_cleanup"; Flags: runhidden

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
