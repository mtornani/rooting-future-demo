# Script per creare collegamento desktop per Rooting Future

$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = "$DesktopPath\Rooting Future.lnk"
$TargetPath = "$PSScriptRoot\start.bat"
$WorkingDir = $PSScriptRoot
$IconPath = "$env:SystemRoot\System32\shell32.dll,77"  # Icona verde predefinita

# Crea il collegamento
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $WorkingDir
$Shortcut.IconLocation = $IconPath
$Shortcut.Description = "Rooting Future Strategy Engine - Gemini AI"
$Shortcut.WindowStyle = 1  # Normal window
$Shortcut.Save()

Write-Host "Collegamento creato sul desktop: $ShortcutPath"
Write-Host ""
Write-Host "Puoi avviare Rooting Future facendo doppio click sull'icona sul desktop!"
