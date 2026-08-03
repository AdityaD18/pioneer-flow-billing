; Inno Setup Script for Pioneer Connector Windows Service Installer
#define MyAppName "Pioneer Tally Connector"
#define MyAppVersion "2.0.1"
#define MyAppPublisher "Pioneer Automation Corp"
#define MyAppURL "https://pioneerautomation.com"
#define MyAppExeName "PioneerConnector.exe"

[Setup]
AppId={{D839210F-994A-4B2E-8E5A-3A1A2B3C4D5E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\Pioneer Automation\Pioneer Connector
DefaultGroupName={#MyAppName}
OutputDir=..\installer_output
OutputBaseFilename=PioneerConnectorSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\PioneerConnector\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Run]
; Register and start Windows Service automatically upon installation finish
Filename: "{app}\{#MyAppExeName}"; Parameters: "--install"; Flags: runhidden; Description: "Registering Pioneer Connector Service"
Filename: "net.exe"; Parameters: "start PioneerConnectorService"; Flags: runhidden; Description: "Starting Pioneer Connector Service"

[UninstallRun]
; Stop and remove Windows Service cleanly upon uninstallation
Filename: "net.exe"; Parameters: "stop PioneerConnectorService"; Flags: runhidden
Filename: "{app}\{#MyAppExeName}"; Parameters: "--remove"; Flags: runhidden
