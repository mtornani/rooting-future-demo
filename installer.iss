; Rooting Future Strategy Engine - Inno Setup Script
; Version: 6.0 Alpha
; Build with: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

#define MyAppName "Rooting Future Strategy Engine"
#define MyAppVersion "6.0.0-alpha"
#define MyAppPublisher "Rooting Future"
#define MyAppURL "https://rootingfuture.com"
#define MyAppExeName "RootingFuture_Alpha.exe"

[Setup]
; Basic info
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Install locations
DefaultDirName={autopf}\RootingFuture
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output
OutputDir=dist\installer
OutputBaseFilename=RootingFuture_Setup_v6.0.0_alpha
SetupIconFile=static\favicon.ico

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; UI
WizardStyle=modern
WizardImageFile=static\wizard_image.bmp
WizardSmallImageFile=static\wizard_small.bmp

; Privileges
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main executable and all dependencies
Source: "dist\RootingFuture_Alpha\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\RootingFuture_Alpha\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; Documentation
Source: "README_ALPHA.md"; DestDir: "{app}"; Flags: ignoreversion isreadme; Languages: english
Source: "LEGGIMI_ALPHA.md"; DestDir: "{app}"; Flags: ignoreversion isreadme; Languages: italian

; License
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\knowledge_base"
Type: filesandordirs; Name: "{app}\output"
Type: filesandordirs; Name: "{app}\logs"

[Code]
// Custom code for initialization
procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel2.Caption :=
    'Questo wizard ti guiderà nell''installazione di Rooting Future Strategy Engine.' + #13#10 + #13#10 +
    'Rooting Future genera piani strategici triennali per società calcistiche usando l''intelligenza artificiale.' + #13#10 + #13#10 +
    'Prima di procedere, assicurati di avere:' + #13#10 +
    '• Una connessione internet attiva' + #13#10 +
    '• Una API Key di Google Gemini (gratuita)' + #13#10 + #13#10 +
    'Clicca Avanti per continuare.';
end;
