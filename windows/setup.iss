; SPDX-License-Identifier: GPL-3.0-only
#define AppVersion "1.1.0-preview.1"
#ifndef SourceRoot
  #define SourceRoot ".."
#endif
#ifndef OutputRoot
  #define OutputRoot "..\windows-artifacts"
#endif
[Setup]
AppId={{3ED8A651-E762-49AC-A01B-7F6B45EC54B5}
AppName=ProjectScope
AppVersion={#AppVersion}
AppVerName=ProjectScope {#AppVersion}
AppPublisher=ProjectScope contributors
DefaultDirName={localappdata}\Programs\ProjectScope
DefaultGroupName=ProjectScope
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
DisableProgramGroupPage=yes
LicenseFile={#SourceRoot}\LICENSE
SetupIconFile={#SourceRoot}\build\windows\projectscope.ico
UninstallDisplayIcon={app}\ProjectScope.exe
OutputDir={#OutputRoot}
OutputBaseFilename=ProjectScope-Windows-{#AppVersion}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "{#SourceRoot}\dist\windows\ProjectScope\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\ProjectScope"; Filename: "{app}\ProjectScope.exe"; WorkingDir: "{app}"; AppUserModelID: "io.projectscope.Crosshair.Windows"
Name: "{userdesktop}\ProjectScope"; Filename: "{app}\ProjectScope.exe"; WorkingDir: "{app}"; AppUserModelID: "io.projectscope.Crosshair.Windows"; Tasks: desktopicon

[Run]
Filename: "{app}\ProjectScope.exe"; Description: "Open ProjectScope"; Flags: nowait postinstall skipifsilent

; Deliberately no UninstallDelete rule: %LOCALAPPDATA%\ProjectScope stores user data.
