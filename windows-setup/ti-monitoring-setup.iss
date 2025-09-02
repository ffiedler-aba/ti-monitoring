; TI-Monitoring Windows Setup Script für InnoSetup
; Lädt automatisch die neueste Release von GitHub und installiert sie

#define MyAppName "TI-Monitoring"
#define MyAppVersion "1.0"
#define MyAppPublisher "TI-Monitoring"
#define MyAppURL "https://github.com/elpatron68/ti-monitoring"
#define MyAppExeName "install-service.cmd"

[Setup]
; Hinweis: Der Wert von AppId identifiziert diese Anwendung eindeutig.
; Ändern Sie diesen Wert nicht, wenn Sie Updates für Ihre Anwendung veröffentlichen.
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\ti-monitor
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
OutputDir=dist
OutputBaseFilename=ti-monitoring-setup
SetupIconFile=
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; InnoSetup benötigt mindestens eine Datei - wir erstellen eine temporäre
Source: "install-service.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Automatische Installation nach dem Setup
Filename: "{app}\install-service.cmd"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  DownloadPage: TDownloadWizardPage;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  if Progress = ProgressMax then
    Log(Format('Successfully downloaded %s', [FileName]));
  Result := True;
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), @OnDownloadProgress);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  LatestReleaseUrl: String;
  DownloadUrl: String;
  ZipFileName: String;
  ExtractPath: String;
  ResultCode: Integer;
begin
  Result := True;
  
  if CurPageID = wpReady then
  begin
    DownloadPage.Clear;
    DownloadPage.Show;
    
    try
      // GitHub API aufrufen um die neueste Release zu finden
      if not DownloadTemporaryFile('https://api.github.com/repos/elpatron68/ti-monitoring/releases/latest', 'latest-release.json', '', @OnDownloadProgress) then
      begin
        MsgBox('Fehler beim Laden der Release-Informationen von GitHub.', mbError, MB_OK);
        Result := False;
        Exit;
      end;
      
      // JSON parsen um die Download-URL zu finden
      if not LoadStringFromFile(ExpandConstant('{tmp}\latest-release.json'), LatestReleaseUrl) then
      begin
        MsgBox('Fehler beim Lesen der Release-Informationen.', mbError, MB_OK);
        Result := False;
        Exit;
      end;
      
      // Einfache String-Suche nach der ZIP-Datei (ti-monitoring-portable-*.zip)
      if Pos('ti-monitoring-portable-', LatestReleaseUrl) > 0 then
      begin
        // Extrahiere die Download-URL aus dem JSON
        // Vereinfachte Implementierung - in der Praxis würde man ein JSON-Parser verwenden
        DownloadUrl := 'https://github.com/elpatron68/ti-monitoring/releases/latest/download/ti-monitoring-portable-latest.zip';
        ZipFileName := 'ti-monitoring-portable-latest.zip';
      end
      else
      begin
        MsgBox('Keine portable Release gefunden.', mbError, MB_OK);
        Result := False;
        Exit;
      end;
      
      // ZIP-Datei herunterladen
      DownloadPage.Add(DownloadUrl, ZipFileName, '');
      
      if not DownloadPage.Download then
      begin
        MsgBox('Fehler beim Herunterladen der Release.', mbError, MB_OK);
        Result := False;
        Exit;
      end;
      
      // ZIP-Datei in das Installationsverzeichnis extrahieren
      ExtractPath := ExpandConstant('{app}');
      if not DirExists(ExtractPath) then
        CreateDir(ExtractPath);
        
      if not ExtractTemporaryFile(ZipFileName) then
      begin
        MsgBox('Fehler beim Extrahieren der Dateien.', mbError, MB_OK);
        Result := False;
        Exit;
      end;
      
      // PowerShell verwenden um die ZIP-Datei zu extrahieren
      if not Exec('powershell.exe', '-Command "Expand-Archive -Path ''' + ExpandConstant('{tmp}\' + ZipFileName) + ''' -DestinationPath ''' + ExtractPath + ''' -Force"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      begin
        MsgBox('Fehler beim Extrahieren der ZIP-Datei.', mbError, MB_OK);
        Result := False;
        Exit;
      end;
      
      if ResultCode <> 0 then
      begin
        MsgBox('Fehler beim Extrahieren der ZIP-Datei. PowerShell Exit Code: ' + IntToStr(ResultCode), mbError, MB_OK);
        Result := False;
        Exit;
      end;
      
      DownloadPage.Hide;
      MsgBox('TI-Monitoring wurde erfolgreich heruntergeladen und extrahiert.', mbInformation, MB_OK);
      
    except
      MsgBox('Ein unerwarteter Fehler ist aufgetreten: ' + GetExceptionMessage, mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo, MemoComponentsInfo, MemoGroupInfo, MemoTaskInfo: String): String;
var
  S: String;
begin
  S := '';
  S := S + MemoUserInfoInfo + NewLine + NewLine;
  S := S + MemoDirInfo + NewLine + NewLine;
  S := S + MemoTypeInfo + NewLine + NewLine;
  S := S + MemoComponentsInfo + NewLine + NewLine;
  S := S + MemoGroupInfo + NewLine + NewLine;
  S := S + MemoTaskInfo + NewLine + NewLine;
  S := S + 'Das Setup wird:' + NewLine;
  S := S + '• Die neueste TI-Monitoring Release von GitHub herunterladen' + NewLine;
  S := S + '• Die Dateien in ' + ExpandConstant('{app}') + ' extrahieren' + NewLine;
  S := S += '• Den TI-Monitoring Service automatisch installieren' + NewLine;
  Result := S;
end;
