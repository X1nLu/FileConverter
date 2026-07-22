; FileConverter Installer Script
; Compile with Inno Setup 6.x
; Download: https://jrsoftware.org/isdl.php

#define MyAppName "FileConverter"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "X1nLu"
#define MyAppURL "https://github.com/X1nLu/FileConverter"
#define MyAppExeName "file_converter.exe"

[Setup]
AppId={{B8F4A3D2-1C5E-4A7F-9D6B-3E2F1C8A5D7E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=FileConverter_Setup_v{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
DisableProgramGroupPage=yes

; Setup icon (optional)
; SetupIconFile=..\flutter_app\windows\runner\resources\app_icon.ico

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: checkedonce

[Files]
; Flutter main executable
Source: "..\flutter_app\build\windows\runner\Release\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

; Python backend (PyInstaller output)
Source: "..\dist\backend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Run {#MyAppName}"; Flags: postinstall nowait skipifsilent

[UninstallRun]
; Ensure backend process is stopped on uninstall
Filename: "taskkill"; Parameters: "/f /im backend.exe"; Flags: runhidden
Filename: "taskkill"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden

[Code]
// Check if old version is running, prompt user to close it
function InitializeSetup: Boolean;
var
  ResultCode: Integer;
begin
  // Try to kill running old version
  Exec('taskkill', '/f /im backend.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill', '/f /im file_converter.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;