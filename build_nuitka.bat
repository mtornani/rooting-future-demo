@echo off
echo Building Rooting Future with Nuitka...
echo This will take several minutes, as it is a full C compilation.

REM Esegui Nuitka per compilare l'applicazione
py -m nuitka ^
    --standalone ^
    --output-dir=nuitka_dist ^
    --windows-console-mode=force ^
    --enable-plugin=flask ^
    --include-package-data=weasyprint ^
    --include-package-data=plotly ^
    --include-package=bs4 ^
    --include-package=lxml ^
    --include-package=requests ^
    --include-package=google ^
    --include-package=docx ^
    --include-package=waitress ^
    --include-data-dir=./templates=templates ^
    --include-data-dir=./static=static ^
    --include-data-dir=./assets=assets ^
    --include-data-dir=./knowledge_base=knowledge_base ^
    app.py

REM Controlla se la build ha avuto successo
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Nuitka build failed!
    pause
    exit /b %errorlevel%
)

echo.
echo Build successful.
echo.

REM Copia il file .env nella cartella di distribuzione
echo Copying .env file...
if exist ".env" (
    copy ".env" "nuitka_dist\app.dist"
    echo .env file copied.
) else (
    echo [WARNING] .env file not found. The application may not work without an API key.
)

echo.
echo ====================================================================
echo Build process complete.
echo To run the application, navigate to 'nuitka_dist\app.dist'
echo and run 'app.exe'.
echo ====================================================================
echo.

pause
