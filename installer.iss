[Setup]
AppId=GoldenEmulator
AppName=GoldenEmulator
AppVersion=0.5.0
AppPublisher=IGN1TE
AppPublisherURL=https://github.com/IGN1TE/GoldenEmulator
DefaultDirName={localappdata}\Programs\GoldenEmulator
DefaultGroupName=GoldenEmulator
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=installer-dist
OutputBaseFilename=GoldenEmulator-Setup-0.5.0
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
Source: "dist\GoldenEmulator.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "START-HERE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\GoldenEmulator"; Filename: "{app}\GoldenEmulator.exe"
Name: "{group}\Stop GoldenEmulator"; Filename: "{app}\GoldenEmulator.exe"; Parameters: "--stop"
Name: "{autodesktop}\GoldenEmulator"; Filename: "{app}\GoldenEmulator.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\GoldenEmulator.exe"; Description: "Open GoldenEmulator"; Flags: nowait postinstall skipifsilent
