@echo off
echo Building Rooting Future executable...
echo This may take a few minutes.

py -m PyInstaller ^
    --noconfirm ^
    --onedir ^
    --name RootingFuture ^
    -p "C:\Users\Mirko\AppData\Roaming\Python\Python312\site-packages" ^
    --hidden-import requests ^
    --hidden-import sqlite3 ^
    --hidden-import lxml ^
    --hidden-import pyphen ^
    --hidden-import PIL ^
    --hidden-import google.api_core.exceptions ^
    --hidden-import google.generativeai ^
    --hidden-import loguru ^
    --hidden-import docx ^
    --hidden-import docx.shared ^
    --hidden-import html5lib ^
    --hidden-import tinycss2 ^
    --hidden-import cssselect2 ^
    --hidden-import svglib ^
    --hidden-import weasyprint ^
    --hidden-import weasyprint.fonts ^
    --hidden-import pyphen ^
    --hidden-import plotly ^
    --hidden-import kaleido ^
    --hidden-import reportlab ^
    --hidden-import reportlab.lib.fonts ^
    --hidden-import reportlab.graphics.barcode.code128 ^
    --hidden-import reportlab.graphics.barcode.code93 ^
    --hidden-import reportlab.graphics.barcode.code39 ^
    --hidden-import reportlab.graphics.barcode.usps ^
    --hidden-import reportlab.graphics.barcode.usps4s ^
    --hidden-import reportlab.graphics.barcode.postnet ^
    --hidden-import reportlab.graphics.barcode.ecc200datamatrix ^
    --hidden-import reportlab.graphics.barcode.pdf417 ^
    --hidden-import reportlab.graphics.barcode.qr ^
    --hidden-import reportlab.graphics.barcode.ean ^
    --add-data ".;." ^
    app.py

REM Controlla se la build ha avuto successo
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] PyInstaller build failed!
    pause
    exit /b %errorlevel%
)

echo.
echo Build successful.
echo.

REM Copia il file .env nella cartella di distribuzione
echo Copying .env file...
if exist ".env" (
    copy ".env" "dist\RootingFuture"
    echo .env file copied.
) else (
    echo [WARNING] .env file not found. The application may not work without an API key.
)

echo.
echo ====================================================================
echo Build process complete.
echo To run the application, navigate to the 'dist\RootingFuture' folder
echo and run 'RootingFuture.exe'.
echo ====================================================================
echo.

pause
