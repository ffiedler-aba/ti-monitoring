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
; Keine App-Dateien, das Repo wird zur Laufzeit geklont
Source: "scripts\\install-services.ps1"; DestDir: "{app}\\scripts"; Flags: ignoreversion
Source: "scripts\\uninstall-services.ps1"; DestDir: "{app}\\scripts"; Flags: ignoreversion
; PortableGit wird mitgeliefert und nach {app}\tools\PortableGit entpackt
Source: "PortableGit\\*"; DestDir: "{app}\\tools\\PortableGit"; Flags: recursesubdirs ignoreversion

[Run]
; 1) winget Vorprüfung und Installationen (silent)
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command if(-not (Get-Command winget -ErrorAction SilentlyContinue)) {{ Write-Error 'winget nicht gefunden. Bitte App-Installer installieren.'; exit 1 }}"; StatusMsg: "Prüfe winget..."; Flags: runhidden
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command winget install -e --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements"; StatusMsg: "Installiere Python..."; Flags: runhidden
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command winget install -e --id Git.Git --silent --accept-source-agreements --accept-package-agreements"; StatusMsg: "Installiere Git..."; Flags: runhidden
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command winget install -e --id NSSM.NSSM --silent --accept-source-agreements --accept-package-agreements"; StatusMsg: "Installiere NSSM..."; Flags: runhidden

; 2) Repo & venv werden vollständig im folgenden Skript erledigt

; 4) Dienste und Firewall einrichten
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File '{app}\\scripts\\install-services.ps1'"; StatusMsg: "Richte Dienste ein..."; Flags: runhidden
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command if(-not (Get-NetFirewallRule -DisplayName 'TI Monitoring UI' -ErrorAction SilentlyContinue)) {{ New-NetFirewallRule -DisplayName 'TI Monitoring UI' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8050 }}"; StatusMsg: "Öffne Firewall-Port 8050..."; Flags: runhidden skipifsilent

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File '{app}\\scripts\\uninstall-services.ps1'"; RunOnceId: "svc_cleanup"; Flags: runhidden
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command if(Get-NetFirewallRule -DisplayName 'TI Monitoring UI' -ErrorAction SilentlyContinue){{ Remove-NetFirewallRule -DisplayName 'TI Monitoring UI' }}"; RunOnceId: "fw_cleanup"; Flags: runhidden

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
