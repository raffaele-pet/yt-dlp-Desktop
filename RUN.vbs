Option Explicit

Dim shell, fso, projectFolder, pythonw, appFile, command, userPath, processEnvironment
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

projectFolder = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = projectFolder & "\.venv\Scripts\pythonw.exe"
appFile = projectFolder & "\app.py"

If Not fso.FileExists(pythonw) Then
    MsgBox "yt-dlp Desktop is not installed yet." & vbCrLf & _
           "Run INSTALL.bat first to create the local .venv environment.", 16, "yt-dlp Desktop"
    WScript.Quit 1
End If

If Not fso.FileExists(appFile) Then
    MsgBox "The app.py file was not found.", 16, "yt-dlp Desktop"
    WScript.Quit 1
End If

shell.CurrentDirectory = projectFolder
Set processEnvironment = shell.Environment("Process")
On Error Resume Next
userPath = shell.RegRead("HKCU\Environment\Path")
On Error GoTo 0
If Len(userPath) > 0 Then
    processEnvironment("Path") = shell.ExpandEnvironmentStrings(userPath) & ";" & processEnvironment("Path")
End If
command = Chr(34) & pythonw & Chr(34) & " " & Chr(34) & appFile & Chr(34)
shell.Run command, 0, False
