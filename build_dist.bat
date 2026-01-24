@echo off
echo ===================================================
echo   ROOTING FUTURE STRATEGY ENGINE - BUILD DISTRIBUTION
echo ===================================================

echo [1/5] Cleaning previous builds...
rmdir /s /q build
rmdir /s /q dist

echo [2/5] Running PyInstaller (using venv)...
REM We use --onedir (folder) because it is more robust for web apps with templates
venv\Scripts\python.exe -m PyInstaller ^
    --noconfirm ^
    --onedir ^
    --name "RootingFuture" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --add-data "assets;assets" ^
    --hidden-import "engineio.async_drivers.threading" ^
    --hidden-import "flask_socketio" ^
    --hidden-import "docx" ^
    --hidden-import "google.generativeai" ^
    --collect-all "stripe" ^
    app.py

if %errorlevel% neq 0 (
    echo [ERROR] Build failed!
    pause
    exit /b %errorlevel%
)

echo [3/5] Copying configuration files...
if exist ".env" (
    copy ".env" "dist\RootingFuture\" >nul
    echo    - .env copied (API Keys)
)

echo [4/5] Creating instructions...
(
echo ===================================================
echo   ROOTING FUTURE STRATEGY ENGINE v5.4
echo ===================================================
echo.
echo ISTRUZIONI AVVIO:
echo 1. Apri la cartella 'RootingFuture'
echo 2. Fai doppio click su 'RootingFuture.exe'
echo 3. Si aprira una finestra nera ^(console^) - NON chiuderla
echo 4. Il browser si aprira automaticamente su http://127.0.0.1:5000
echo.
echo NOTA:
echo Se richiesto, inserisci la Chiave di Attivazione fornita.
) > "dist\ISTRUZIONI.txt"

echo [5/5] Done!
echo.
echo ===================================================
echo   BUILD COMPLETATA CON SUCCESSO
echo ===================================================
echo.
echo La cartella da inviare e:
echo   %CD%\dist\RootingFuture
echo.
echo Puoi zippare questa cartella e inviarla ai colleghi.
echo.
pause
