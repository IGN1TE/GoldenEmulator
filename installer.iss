[Setup]
AppId=GoldenEmulator
AppName=GoldenEmulator
AppVersion=0.8.1
AppPublisher=IGN1TE
SetupIconFile=GoldenEmulator.ico
VersionInfoCompany=IGN1TE
VersionInfoDescription=GoldenEmulator Setup
AppPublisherURL=https://github.com/IGN1TE/GoldenEmulator
DefaultDirName={localappdata}\Programs\GoldenEmulator
DefaultGroupName=GoldenEmulator
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=installer-dist
OutputBaseFilename=GoldenEmulator-Setup-0.8.1
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\GoldenEmulator.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: checkedonce

[Files]
Source: "MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "dist\GoldenEmulator.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "START-HERE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\GoldenEmulator"; Filename: "{app}\GoldenEmulator.exe"
Name: "{group}\Stop GoldenEmulator"; Filename: "{app}\GoldenEmulator.exe"; Parameters: "--stop"
Name: "{autodesktop}\GoldenEmulator"; Filename: "{app}\GoldenEmulator.exe"; Tasks: desktopicon

[Run]
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Installing Microsoft WebView2 Runtime..."; Flags: runhidden waituntilterminated; Check: WebViewMissing
Filename: "{app}\GoldenEmulator.exe"; Description: "Open GoldenEmulator"; Flags: nowait postinstall skipifsilent

Filename: "{app}\GoldenEmulator.exe"; Flags: nowait; Check: RestartAfterUpdate

[Code]
function RestartAfterUpdate: Boolean;
begin
  Result := ExpandConstant('{param:RESTARTAPP|0}') <> '0';
end;

function WebViewMissing: Boolean;
var
  Version: String;
  Key: String;
begin
  Key := 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  Result := not ((RegQueryStringValue(HKLM32, Key, 'pv', Version) or
    RegQueryStringValue(HKCU, Key, 'pv', Version)) and (Version <> '') and (Version <> '0.0.0.0'));
end;
