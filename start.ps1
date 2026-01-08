# Rooting Future Strategy Engine - PowerShell Launcher
Write-Host "========================================"
Write-Host "  Rooting Future Strategy Engine v5.4"
Write-Host "  Gemini File Search Enabled"
Write-Host "========================================"
Write-Host ""

Set-Location $PSScriptRoot

# Attiva virtual environment
& .\venv\Scripts\Activate.ps1

Write-Host "Avvio server web..."
Write-Host ""
Write-Host "L'applicazione sara disponibile su:"
Write-Host "  http://localhost:5000"
Write-Host ""
Write-Host "Premi Ctrl+C per fermare il server"
Write-Host "========================================"
Write-Host ""

python app.py
