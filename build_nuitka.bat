@echo off
echo ========================================================
echo   ROOTING FUTURE - COMMERCIAL BUILD SYSTEM (NUITKA)
echo ========================================================
echo.
echo Questo script compilera' l'intero progetto in un singolo file .EXE.
echo Il codice sorgente sara' protetto e inaccessibile.
echo.
echo Requisiti:
echo - Python 3.11+
echo - Nuitka (pip install nuitka)
echo - Compilatore C (Nuitka scarichera' MinGW64 se manca)
echo.

call venv\Scripts\activate.bat

echo [1/4] Installazione Nuitka e zstandard (per compressione)...
pip install nuitka zstandard ordered-set

echo.
echo [2/4] Pulizia vecchie build...
rmdir /s /q dist
rmdir /s /q build
rmdir /s /q app.dist
rmdir /s /q app.build

echo.
echo [3/4] Compilazione in corso (potrebbe richiedere 10-20 minuti)...
echo ATTENZIONE: Se Nuitka chiede di scaricare il compilatore C, rispondi YES.
echo.

python -m nuitka --standalone ^
    --onefile ^
    --enable-plugin=flask ^
    --include-data-dir=templates=templates ^
    --include-data-dir=static=static ^
    --include-data-dir=assets=assets ^
    --include-package=engineio ^
    --include-package=socketio ^
    --include-package=flask_socketio ^
    --output-dir=dist ^
    --output-filename=RootingFuture_v5.4.exe ^
    --windows-icon-from-ico=assets/icon.ico ^
    --company-name="Rooting Future" ^
    --product-name="Strategy Engine" ^
    --file-version=5.4.0.0 ^
    --copyright="Copyright (c) 2026 Rooting Future" ^
    app.py

echo.
if exist "dist\RootingFuture_v5.4.exe" (
    echo [4/4] BUILD COMPLETATA CON SUCCESSO!
    echo Il file eseguibile si trova in: dist\RootingFuture_v5.4.exe
    echo.
    echo Ora puoi distribuire questo file .exe SENZA il codice sorgente.
) else (
    echo [ERRORE] La compilazione e' fallita. Controlla i log sopra.
)
pause