@echo off
setlocal EnableDelayedExpansion
title ROOTING FUTURE - Full Stack Launcher
color 0A

:: =============================================================================
:: ROOTING FUTURE STRATEGY ENGINE v5.4
:: Full Stack Launcher: Python API + n8n + Ngrok
::
:: ARCHITETTURA:
::   Tally -> Ngrok (porta 5678) -> n8n -> Python API (localhost:5000)
::
:: Ngrok espone n8n per ricevere webhook esterni (Tally, Google Forms, etc.)
:: n8n chiama Python API in locale per la generazione dei piani
:: =============================================================================

cd /d "%~dp0"

cls
echo.
echo  ===============================================================
echo  ^|                                                             ^|
echo  ^|     ROOTING FUTURE - STRATEGY ENGINE v5.4                   ^|
echo  ^|     Full Stack Automation Launcher                          ^|
echo  ^|                                                             ^|
echo  ^|     ARCHITETTURA:                                           ^|
echo  ^|       Tally/Forms -^> Ngrok -^> n8n -^> Python API            ^|
echo  ^|                                                             ^|
echo  ^|     Servizi in avvio:                                       ^|
echo  ^|       [0] Diagnostica Integrita                             ^|
echo  ^|       [1] Python Flask API (porta 5000)                     ^|
echo  ^|       [2] n8n Workflow Automation (porta 5678)              ^|
echo  ^|       [3] Ngrok Tunnel (espone n8n sulla 5678)              ^|
echo  ^|                                                             ^|
echo  ===============================================================
echo.

:: -----------------------------------------------------------------------------
:: STEP 0: Verifica integrità sistema
:: -----------------------------------------------------------------------------
echo  [0/4] Esecuzione diagnostica rapida...
call venv\Scripts\activate.bat
venv\Scripts\python.exe diagnostica_avvio.py --quiet
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [!] ERRORE: La diagnostica ha rilevato problemi.
    echo      Controlla gli errori sopra e premi un tasto per uscire.
    pause
    exit /b %ERRORLEVEL%
)
echo        [OK] Sistema integro.
echo.

:: -----------------------------------------------------------------------------
:: STEP 1: Chiudi eventuali processi Python sulla porta 5000
:: -----------------------------------------------------------------------------
echo  [1/4] Verifica porta 5000...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5000 " ^| findstr "LISTENING"') do (
    if not "%%a"=="" (
        echo        Terminazione processo PID %%a sulla porta 5000...
        taskkill /F /PID %%a >nul 2>&1
    )
)
timeout /t 3 /nobreak > nul
echo        [OK] Porta 5000 libera
echo.

:: -----------------------------------------------------------------------------
:: STEP 2: Avvio Python API (finestra visibile per debug)
:: -----------------------------------------------------------------------------
echo  [2/4] Avvio Python API Server (porta 5000)...
start "Python API Server" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && py avvia_server.py"
timeout /t 8 /nobreak > nul
echo        [OK] Python API avviato
echo        Endpoint: http://127.0.0.1:5000
echo.

:: -----------------------------------------------------------------------------
:: STEP 3: Avvio N8N (finestra minimizzata)
:: -----------------------------------------------------------------------------
echo  [3/4] Avvio n8n Workflow Engine (porta 5678)...
start /min "n8n Automation" cmd /c "npx n8n start"
timeout /t 8 /nobreak > nul
echo        [OK] n8n avviato in background
echo        Dashboard: http://localhost:5678
echo.

:: -----------------------------------------------------------------------------
:: STEP 4: Avvio NGROK -> porta 5678 (n8n)
:: -----------------------------------------------------------------------------
echo  [4/4] Avvio Ngrok Tunnel (espone n8n)...
echo        IMPORTANTE: Ngrok punta alla porta 5678 (n8n)
start /min "Ngrok Tunnel" cmd /c "ngrok http --domain=jakob-untalking-purringly.ngrok-free.dev 5678"
timeout /t 4 /nobreak > nul
echo        [OK] Ngrok avviato in background
echo        Dominio: jakob-untalking-purringly.ngrok-free.dev
echo.

:: -----------------------------------------------------------------------------
:: INFO BOX
:: -----------------------------------------------------------------------------
echo  ===============================================================
echo  ^|                                                             ^|
echo  ^|     TUTTI I SERVIZI AVVIATI CON SUCCESSO                    ^|
echo  ^|                                                             ^|
echo  ^|     LINK RAPIDI:                                            ^|
echo  ^|                                                             ^|
echo  ^|     [Python API]  http://localhost:5000                     ^|
echo  ^|     [n8n Local]   http://localhost:5678                     ^|
echo  ^|     [n8n Pubblico] https://jakob-untalking-purringly.ngrok-free.dev ^|
echo  ^|                                                             ^|
echo  ^|     FLUSSO WEBHOOK:                                         ^|
echo  ^|                                                             ^|
echo  ^|     1. Tally invia a:                                       ^|
echo  ^|        https://jakob-untalking-purringly.ngrok-free.dev/webhook/XXX ^|
echo  ^|                                                             ^|
echo  ^|     2. n8n riceve e processa, poi chiama:                   ^|
echo  ^|        http://localhost:5000/api/generate-from-webhook      ^|
echo  ^|                                                             ^|
echo  ^|     3. Python genera il piano e ritorna il risultato        ^|
echo  ^|                                                             ^|
echo  ===============================================================
echo.
echo  [INFO] Tutti i servizi sono in esecuzione.
echo.
echo  Per terminare: chiudi questa finestra o premi un tasto.
echo  Ricorda di chiudere anche le finestre minimizzate:
echo    - Python API Server
echo    - n8n Automation
echo    - Ngrok Tunnel
echo.
echo  Oppure usa Stop_Rooting_Future.bat per terminare tutto.
echo  ---------------------------------------------------------------
echo.

:: Apri browser dopo 10 secondi (tempo sufficiente per avvio server)
start /b cmd /c "timeout /t 10 /nobreak >nul && start http://127.0.0.1:5000"
start /b cmd /c "timeout /t 12 /nobreak >nul && start http://127.0.0.1:5678"

pause

:: Se l'utente preme un tasto, mostra messaggio finale
echo.
echo  ---------------------------------------------------------------
echo  [!] Script terminato.
echo  [!] Ricorda di chiudere le finestre minimizzate manualmente.
echo  [!] Oppure esegui Stop_Rooting_Future.bat
echo  ---------------------------------------------------------------
