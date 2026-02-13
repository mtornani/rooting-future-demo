# Rooting Future Strategy Engine - Alpha v6.0.0

## Avvio Rapido

1. **Avvia l'applicazione:**
   - Doppio click su `RootingFuture_Alpha.exe`
   - Il browser si aprira su `http://localhost:5000`

2. **Attivazione (prima volta):**
   - Copia il **Codice Macchina (HWID)** mostrato a schermo
   - Invialo al tuo referente per ricevere la chiave di licenza
   - Inserisci email e chiave di licenza per attivare

3. **Configurazione AI (scegli una opzione):**

   **Opzione A - Google Gemini (consigliato):**
   - Vai su Impostazioni
   - Seleziona "Google Gemini" come provider
   - Inserisci la Gemini API Key (gratuita su https://aistudio.google.com/apikey)

   **Opzione B - OpenRouter (alternativa):**
   - Vai su Impostazioni
   - Seleziona "OpenRouter" come provider
   - Crea account gratuito su https://openrouter.ai/keys
   - Inserisci la OpenRouter API Key
   - Seleziona un modello gratuito (Gemini Flash, DeepSeek V3, Llama 4, ecc.)

4. **Genera il tuo primo piano:**
   - Clicca "Nuovo Piano"
   - Inserisci nome club, citta e categoria
   - Clicca "Genera Piano Strategico"
   - Attendi 1-2 minuti per la generazione AI
   - Visualizza la webapp interattiva o scarica PDF/DOCX

## Funzionalita

- Generazione piani strategici con AI multi-agente
- 6 agenti AI specializzati (Sportivo, Strutturale, Marketing, Sociale, Finanziario, Coordinatore)
- Supporto doppio provider AI: Google Gemini o OpenRouter
- Modelli AI gratuiti disponibili via OpenRouter
- Dati scientifici con benchmark di categoria
- Webapp interattiva con ricerca e navigazione
- Export in PDF, DOCX, HTML, OnePager
- Condivisione pubblica con password
- Tracciamento progressi in tempo reale
- Interfaccia responsive per mobile

## Requisiti di Sistema

- Windows 10/11 (64-bit)
- 4 GB RAM minimo
- Connessione internet richiesta
- API key AI (Gemini o OpenRouter - livello gratuito disponibile)

## Limitazioni Note (Alpha)

- Generazione PDF richiede Playwright/Chromium (installato automaticamente)
- Alcuni caratteri speciali potrebbero causare problemi
- Massimo 10 competitor per piano
- Upload file limitato a 10 MB

## Risoluzione Problemi

**L'app non si avvia:**
- Esegui dal Prompt dei Comandi per vedere messaggi di errore
- Verifica che Windows Defender non l'abbia bloccata

**Errore "API key mancante":**
- Vai su Impostazioni e configura il provider AI
- Per Gemini: Ottieni chiave gratuita su https://aistudio.google.com/apikey
- Per OpenRouter: Ottieni chiave gratuita su https://openrouter.ai/keys

**Generazione PDF fallisce:**
- Verifica connessione internet
- Prova export DOCX invece
- Controlla la cartella logs per dettagli

## Supporto

Segnala bug e feedback a: support@rootingfuture.com

## Licenza

Proprietary - Tutti i diritti riservati
