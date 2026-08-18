Option Explicit

Dim fso, shell, projectDir, pythonExe, command

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

projectDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonExe = fso.BuildPath(projectDir, ".venv\Scripts\pythonw.exe")

If Not fso.FileExists(pythonExe) Then
    MsgBox "Python virtual environment was not found:" & vbCrLf & pythonExe, 16, "Waterfall Media Viewer"
    WScript.Quit 1
End If

shell.CurrentDirectory = projectDir
command = Chr(34) & pythonExe & Chr(34) & " -m waterfall_viewer"
shell.Run command, 0, False
