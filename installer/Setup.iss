#ifndef AppVersion
  #define AppVersion "1.0.1"
#endif
#define AppGuid "{507FE14E-2187-47CE-BC3F-052413B9B677}"

[Setup]
AppId={{#AppGuid}
AppName=yt-dlp Desktop
AppVersion={#AppVersion}
AppPublisher=raffaele-pet
AppPublisherURL=https://github.com/raffaele-pet/yt-dlp-Desktop
DefaultDirName={localappdata}\Programs\yt-dlp Desktop
DefaultGroupName=yt-dlp Desktop
UsePreviousAppDir=yes
DisableDirPage=auto
AlwaysShowDirOnReadyPage=yes
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
MinVersion=10.0
ChangesEnvironment=yes
SetupLogging=yes
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
const
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppGuid}_is1';
  DependencySteps = 5;

var
  InstalledDir, InstalledVersion: String;
  DependencyPage: TOutputProgressWizardPage;
  ShowDependencies: Boolean;
  DependencyStage: String;
  DependencyError: String;

procedure InitializeWizard;
begin
  RegQueryStringValue(HKCU, UninstallKey, 'InstallLocation', InstalledDir);
  RegQueryStringValue(HKCU, UninstallKey, 'DisplayVersion', InstalledVersion);
  DependencyPage := CreateOutputProgressPage(
    'Preparing dependencies', 'Setup is preparing the tools used by yt-dlp Desktop.');
end;

function UpdatingExistingInstallation: Boolean;
begin
  Result := (InstalledDir <> '') and FileExists(AddBackslash(InstalledDir) + 'app.py') and
    (CompareText(AddBackslash(WizardDirValue), AddBackslash(InstalledDir)) = 0);
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if (CurPageID = wpReady) and UpdatingExistingInstallation then
  begin
    WizardForm.PageNameLabel.Caption := 'Ready to update';
    WizardForm.PageDescriptionLabel.Caption :=
      'Setup will update yt-dlp Desktop in its current folder.';
    WizardForm.ReadyLabel.Caption := 'Click Update to continue, or click Back to review your settings.';
    WizardForm.NextButton.Caption := '&Update';
    if InstalledVersion <> '' then
      WizardForm.ReadyMemo.Lines.Insert(0,
        'Installed version: ' + InstalledVersion + '   |   Setup version: {#AppVersion}');
  end;
end;

procedure RegisterExtraCloseApplicationsResources;
var
  Launcher: String;
begin
  Launcher := AddBackslash(WizardDirValue) + '.venv\Scripts\pythonw.exe';
  if UpdatingExistingInstallation and FileExists(Launcher) then
    RegisterExtraCloseApplicationsResource(False, Launcher);
end;

procedure ShowDependencyOutput(const Line: String; const Error, FirstLine: Boolean);
var
  S: String;
  Step: Integer;
begin
  S := Trim(Line);
  if S = '' then
    exit;
  Log('Dependency setup: ' + S);

  if (Pos('[ERROR]', S) = 1) or (Pos('ERROR:', S) = 1) then
    DependencyError := S;
  if not ShowDependencies then
    exit;

  if (Copy(S, 1, 1) = '[') and (Copy(S, 3, 4) = '/6] ') then
  begin
    Step := StrToIntDef(Copy(S, 2, 1), 0);
    if (Step >= 1) and (Step <= DependencySteps) then
    begin
      DependencyStage := Format('Step %d of %d - %s', [Step, DependencySteps, Copy(S, 7, Length(S))]);
      DependencyPage.SetText(DependencyStage, '');
      DependencyPage.SetProgress(Step - 1, DependencySteps);
    end;
  end
  else if (Pos('[INSTALL]', S) = 1) or (Pos('[REPAIR]', S) = 1) then
    DependencyPage.SetText(DependencyStage, Copy(S, Pos(']', S) + 2, Length(S)))
  else if Pos('Collecting ', S) = 1 then
    DependencyPage.SetText(DependencyStage, 'Checking Python packages...')
  else if Pos('Downloading ', S) = 1 then
    DependencyPage.SetText(DependencyStage, 'Downloading packages...')
  else if Pos('Installing collected packages:', S) = 1 then
    DependencyPage.SetText(DependencyStage, 'Installing Python packages...');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ExitCode: Integer;
  Failure: String;
begin
  if CurStep <> ssPostInstall then
    exit;
  ShowDependencies := WizardForm.Visible;
  if ShowDependencies then
  begin
    DependencyPage.SetText('Checking prerequisites...', '');
    DependencyPage.SetProgress(0, DependencySteps);
    DependencyPage.Show;
  end;
  try
    if not ExecAndLogOutput(ExpandConstant('{cmd}'), '/D /C INSTALL.bat --setup', ExpandConstant('{app}'),
      SW_HIDE, ewWaitUntilTerminated, ExitCode, @ShowDependencyOutput) then
      Failure := 'Could not start dependency setup. Error code: ' + IntToStr(ExitCode)
    else if ExitCode <> 0 then
    begin
      Failure := 'Dependency setup failed. Error code: ' + IntToStr(ExitCode);
      if DependencyError <> '' then
        Failure := Failure + #13#10 + DependencyError;
    end;

    if Failure <> '' then
      RaiseException(Failure + #13#10#13#10 + 'Setup log: ' + ExpandConstant('{log}'));
    if ShowDependencies then
      DependencyPage.SetProgress(DependencySteps, DependencySteps);
  finally
    if ShowDependencies then
      DependencyPage.Hide;
  end;
end;
