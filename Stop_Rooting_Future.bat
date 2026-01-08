@echo off
title ROOTING FUTURE - Service Stopper
color 0C

:: =============================================================================
:: ROOTING FUTURE - Ferma tutti i servizi
:: =============================================================================

echo.
echo  ===============================================================
echo  ^|                                                             ^|
echo  ^|     ROOTING FUTURE - STOP ALL SERVICES                      ^|
echo  ^|                                                             ^|
echo  ===============================================================
echo.

echo  [1/3] Terminazione processi Ngrok...
taskkill /f /im ngrok.exe 2>nul
if %errorlevel%==0 (echo        [OK] Ngrok terminato) else (echo        [--] Ngrok non in esecuzione)

echo.
echo  [2/3] Terminazione processi Node.js (n8n)...
taskkill /f /im node.exe 2>nul
if %errorlevel%==0 (echo        [OK] Node.js/n8n terminato) else (echo        [--] Node.js non in esecuzione)

echo.
echo  [3/3] Terminazione processi Python...
taskkill /f /im python.exe 2>nul
if %errorlevel%==0 (echo        [OK] Python terminato) else (echo        [--] Python non in esecuzione)

echo.
echo  ===============================================================
echo  ^|     Tutti i servizi sono stati fermati                      ^|
echo  ===============================================================
echo.

timeout /t 3
