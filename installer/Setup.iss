#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{507FE14E-2187-47CE-BC3F-052413B9B677}
AppName=yt-dlp Desktop
AppVersion={#AppVersion}
AppPublisher=raffaele-pet
AppPublisherURL=https://github.com/raffaele-pet/yt-dlp-Desktop
DefaultDirName={localappdata}\Programs\yt-dlp Desktop
DefaultGroupName=yt-dlp Desktop
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
MinVersion=10.0
ChangesEnvironment=yes
SetupIconFile=..\assets\desktop.ico
UninstallDisplayIcon={app}\assets\desktop.ico
OutputDir=..\dist
OutputBaseFilename=yt-dlp-Desktop-Setup
WizardStyle=modern
Compression=lzma2
SolidCompression=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"

[Files]
Source: "..\app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\INSTALL.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\RUN.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\RUN_DEBUG.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\desktop.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\desktop.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\plugins\vidxgo\yt_dlp_plugins\extractor\vidxgo.py"; DestDir: "{app}\plugins\vidxgo\yt_dlp_plugins\extractor"; Flags: ignoreversion
Source: "..\plugins\desktop\yt_dlp_plugins\postprocessor\desktop.py"; DestDir: "{app}\plugins\desktop\yt_dlp_plugins\postprocessor"; Flags: ignoreversion

[Icons]
Name: "{group}\yt-dlp Desktop"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\RUN.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\desktop.ico"
Name: "{userdesktop}\yt-dlp Desktop"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\RUN.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\desktop.ico"; Tasks: desktopicon

[Run]
Filename: "{sys}\wscript.exe"; Parameters: """{app}\RUN.vbs"""; WorkingDir: "{app}"; Description: "Launch yt-dlp Desktop"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\plugins\vidxgo\yt_dlp_plugins\extractor\__pycache__"
Type: filesandordirs; Name: "{app}\plugins\desktop\yt_dlp_plugins\postprocessor\__pycache__"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ExitCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    WizardForm.StatusLabel.Caption := 'Preparing Python, yt-dlp, FFmpeg and Deno…';
    if not Exec(ExpandConstant('{cmd}'), '/D /C INSTALL.bat --setup', ExpandConstant('{app}'),
      SW_SHOW, ewWaitUntilTerminated, ExitCode) then
      RaiseException('Could not start dependency setup. Run INSTALL.bat from the installation folder for details.');
    if ExitCode <> 0 then
      RaiseException('Dependency setup failed. Run INSTALL.bat from the installation folder for details.');
  end;
end;
