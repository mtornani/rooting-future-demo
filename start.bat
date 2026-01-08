@echo off
title Rooting Future Strategy Engine
color 0A

echo.
echo  ========================================================
echo  ^|                                                      ^|
echo  ^|     ROOTING FUTURE STRATEGY ENGINE v5.4              ^|
echo  ^|     Powered by Gemini AI with File Search            ^|
echo  ^|                                                      ^|
echo  ========================================================
echo.

cd /d "%~dp0"

:: Attiva virtual environment
call venv\Scripts\activate.bat

:: Apri il browser dopo 3 secondi (in background)
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:5000"

echo  Server in avvio...
echo.
echo  L'applicazione si aprira automaticamente nel browser.
echo  URL: http://localhost:5000
echo.
echo  Premi Ctrl+C per fermare il server
echo  ========================================================
echo.

:: Avvia il server
python app.py

pause
