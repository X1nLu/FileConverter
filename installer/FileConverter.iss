; FileConverter 安装脚本
; 使用 Inno Setup 6.x 编译
; 下载: https://jrsoftware.org/isdl.php

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

; 安装包图标（可选）
; SetupIconFile=..\flutter_app\windows\runner\resources\app_icon.ico

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："; Flags: checkedonce

[Files]
; Flutter 主程序
Source: "..\flutter_app\build\windows\runner\Release\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

; Python 后端（PyInstaller 打包输出）
Source: "..\dist\backend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "运行 {#MyAppName}"; Flags: postinstall nowait skipifsilent

[UninstallRun]
; 卸载时确保后端进程已停止
Filename: "taskkill"; Parameters: "/f /im backend.exe"; Flags: runhidden
Filename: "taskkill"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden

[Code]
// 安装前检查是否已安装旧版本，提示用户关闭
function InitializeSetup: Boolean;
var
  ResultCode: Integer;
begin
  // 尝试关闭正在运行的旧版本
  Exec('taskkill', '/f /im backend.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill', '/f /im file_converter.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;