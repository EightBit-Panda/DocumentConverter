
#define MyAppName "DocumentConverter"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "DocumentConverter"
#define MyAppExeName "DocumentConverter_v2.exe"

[Setup]
AppId={{aba8764f-6018-44f2-9ac5-9cb3b6979a1b}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\DocumentConverter
DefaultGroupName=DocumentConverter
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=DocumentConverter_Setup_{#MyAppVersion}
SetupIconFile=..\assets\icons\documentconverter.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
CloseApplications=yes
Uninstallable=yes

[Tasks]
Name: "desktopicon"; Description: "Opprett snarvei på skrivebordet"; GroupDescription: "Ekstra snarveier:"; Flags: unchecked

[Dirs]
Name: "{app}"; Flags: setntfscompression

[Files]
Source: "..\dist_v2\DocumentConverter_v2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\DocumentConverter"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\DocumentConverter"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Start DocumentConverter"; Flags: nowait postinstall skipifsilent
