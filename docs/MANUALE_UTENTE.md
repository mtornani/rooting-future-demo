# Rooting Future Strategy Engine
## Manuale Utente v6.0.0-alpha

---

## Indice

1. [Introduzione](#1-introduzione)
2. [Requisiti di Sistema](#2-requisiti-di-sistema)
3. [Installazione](#3-installazione)
4. [Attivazione della Licenza](#4-attivazione-della-licenza)
5. [Configurazione AI](#5-configurazione-ai)
6. [Generare un Piano Strategico](#6-generare-un-piano-strategico)
7. [Visualizzare il Piano (WebApp)](#7-visualizzare-il-piano-webapp)
8. [Esportare il Piano](#8-esportare-il-piano)
9. [Condividere il Piano](#9-condividere-il-piano)
10. [Impostazioni](#10-impostazioni)
11. [Risoluzione Problemi](#11-risoluzione-problemi)
12. [FAQ](#12-faq)
13. [Supporto](#13-supporto)

---

## 1. Introduzione

**Rooting Future Strategy Engine** è un software di intelligenza artificiale progettato per generare piani strategici professionali per società sportive calcistiche.

### Cosa fa il software

- Analizza i dati del club (nome, categoria, città, competitor)
- Genera automaticamente un piano strategico completo usando 6 agenti AI specializzati
- Produce contenuti scientifici con benchmark di settore
- Esporta in formati professionali (PDF, DOCX, HTML)
- Permette la condivisione sicura con stakeholder esterni

### I 6 Agenti AI

| Agente | Specializzazione |
|--------|------------------|
| Sportivo | Settore tecnico, prima squadra, metodologie |
| Strutturale | Infrastrutture, impianti, logistica |
| Marketing | Comunicazione, brand, sponsorizzazioni |
| Sociale | Community, responsabilità sociale, territorio |
| Finanziario | Budget, sostenibilità economica, investimenti |
| Coordinatore | Sintesi strategica e coerenza complessiva |

---

## 2. Requisiti di Sistema

### Requisiti Minimi

| Componente | Requisito |
|------------|-----------|
| Sistema Operativo | Windows 10/11 (64-bit) |
| RAM | 4 GB |
| Spazio Disco | 500 MB |
| Connessione | Internet richiesta |
| Browser | Chrome, Firefox, Edge (versione recente) |

### Requisiti Consigliati

| Componente | Consigliato |
|------------|-------------|
| RAM | 8 GB |
| Connessione | Fibra o 4G stabile |
| Schermo | 1920x1080 o superiore |

---

## 3. Installazione

### Passo 1: Estrai i file

1. Scarica il file `RootingFuture_v6.0.0-alpha.zip`
2. Fai clic destro sul file ZIP
3. Seleziona **"Estrai tutto..."**
4. Scegli una cartella di destinazione (es. `C:\RootingFuture`)
5. Clicca **"Estrai"**

### Passo 2: Avvia l'applicazione

1. Apri la cartella estratta
2. Fai doppio clic su `RootingFuture_Alpha.exe`
3. Se Windows mostra un avviso di sicurezza:
   - Clicca **"Ulteriori informazioni"**
   - Clicca **"Esegui comunque"**

### Passo 3: Attendi l'avvio

- L'applicazione impiega 5-10 secondi per avviarsi
- Il browser si aprirà automaticamente su `http://localhost:5000`
- Vedrai la pagina di **Attivazione**

> **Nota**: Non chiudere la finestra del terminale nero che appare. È il server dell'applicazione.

---

## 4. Attivazione della Licenza

Al primo avvio, devi attivare la licenza per utilizzare il software.

### Passo 1: Copia il Codice Macchina

Nella pagina di attivazione vedrai un **Codice Macchina (HWID)** nel formato:
```
XXXX-XXXX-XXXX-XXXX
```

1. Clicca sul codice per copiarlo
2. Invialo al tuo referente Rooting Future

### Passo 2: Ricevi la Chiave di Licenza

Il tuo referente ti invierà:
- Una **chiave di licenza** nel formato `XXXXXX-XXXXXX-XXXXXX-XXXXXX`
- La **durata** della licenza (es. 365 giorni)

### Passo 3: Attiva

1. Inserisci la tua **email**
2. Inserisci la **chiave di licenza** ricevuta
3. (Opzionale) Inserisci la **durata in giorni**
4. Clicca **"Attiva Licenza"**

Se i dati sono corretti, verrai reindirizzato alla Dashboard.

### Cosa succede dopo l'attivazione

- Viene creato automaticamente un account con la tua email
- Ricevi **10 crediti** per generare piani
- La licenza viene salvata localmente

---

## 5. Configurazione AI

Prima di generare piani, devi configurare il provider AI.

### Accedi alle Impostazioni

1. Dalla Dashboard, clicca sull'icona **ingranaggio** (⚙️) in alto a destra
2. Oppure vai direttamente a `http://localhost:5000/settings`

### Opzione A: Google Gemini (Consigliato)

1. Vai su https://aistudio.google.com/apikey
2. Accedi con il tuo account Google
3. Clicca **"Create API Key"**
4. Copia la chiave generata (inizia con `AIza...`)
5. Nelle Impostazioni di Rooting Future:
   - Seleziona **"Google Gemini"** come provider
   - Incolla la API Key nel campo
   - Clicca **"Testa Connessione"**
   - Se verde, clicca **"Salva Impostazioni"**

### Opzione B: OpenRouter (Alternativa Gratuita)

1. Vai su https://openrouter.ai/keys
2. Crea un account gratuito
3. Genera una API Key (inizia con `sk-or-v1-...`)
4. Nelle Impostazioni di Rooting Future:
   - Seleziona **"OpenRouter"** come provider
   - Incolla la API Key
   - Seleziona un **modello gratuito**:
     - Gemini 2.0 Flash (free) - consigliato
     - DeepSeek V3 (free)
     - Llama 4 Maverick (free)
     - Qwen3 235B (free)
   - Clicca **"Testa Connessione"**
   - Se verde, clicca **"Salva Impostazioni"**

---

## 6. Generare un Piano Strategico

### Passo 1: Avvia la generazione

1. Dalla Dashboard, clicca **"Nuovo Piano"**
2. Oppure vai a `http://localhost:5000/new-plan`

### Passo 2: Compila i dati del club

| Campo | Descrizione | Esempio |
|-------|-------------|---------|
| Nome Club | Nome ufficiale della società | A.S.D. Virtus Roma |
| Città | Sede principale | Roma |
| Categoria | Livello competitivo | Serie D |
| Competitor | Club rivali (max 10) | Lazio, Roma, Frosinone |

### Passo 3: Avvia la generazione

1. Clicca **"Genera Piano Strategico"**
2. Attendi il completamento (1-2 minuti)
3. Vedrai una barra di progresso con gli step:
   - Analisi dati
   - Generazione sezioni (6 agenti)
   - Sintesi finale
   - Salvataggio

### Passo 4: Visualizza il risultato

Al termine, verrai reindirizzato alla **WebApp del Piano** con:
- Tutte le sezioni navigate dal menu laterale
- Pulsanti per esportare in vari formati
- Opzione di condivisione

---

## 7. Visualizzare il Piano (WebApp)

La WebApp è l'interfaccia interattiva per consultare il piano generato.

### Navigazione

- **Menu laterale sinistro**: lista delle sezioni
- **Barra di ricerca**: cerca parole chiave nel piano
- **Sezione centrale**: contenuto della sezione selezionata

### Sezioni del Piano

1. **Executive Summary** - Panoramica strategica
2. **Analisi Situazionale** - Stato attuale del club
3. **Area Tecnico-Sportiva** - Prima squadra e metodologie
4. **Settore Giovanile** - Academy e formazione
5. **Infrastrutture** - Impianti e strutture
6. **Marketing e Comunicazione** - Brand e sponsor
7. **Area Sociale** - Community e territorio
8. **Sostenibilità Finanziaria** - Budget e investimenti
9. **Piano Operativo** - Timeline e milestone
10. **KPI e Metriche** - Indicatori di successo
11. **Risk Management** - Analisi rischi
12. **Conclusioni** - Sintesi e next steps

### Dati Scientifici

Ogni sezione include **Data Points** con:
- 📊 **Valore**: dato numerico o qualitativo
- 📈 **Benchmark**: confronto con media di categoria
- 🎯 **Affidabilità**: livello di confidenza (High/Medium/Low)
- 📚 **Fonte**: riferimento bibliografico

> **Tooltip Affidabilità**: passa il mouse sulla "?" per capire cosa significano i livelli.

---

## 8. Esportare il Piano

### Formati Disponibili

| Formato | Descrizione | Uso Consigliato |
|---------|-------------|-----------------|
| **PDF** | Documento formattato professionale | Presentazioni, stampa |
| **DOCX** | Microsoft Word editabile | Modifiche successive |
| **HTML** | Pagina web standalone | Archivio digitale |
| **One-Pager** | Sintesi 1 pagina | Pitch rapido |

### Come Esportare

1. Dalla WebApp del piano, clicca il pulsante del formato desiderato
2. Attendi la generazione (PDF richiede 5-10 secondi)
3. Il file verrà scaricato automaticamente

### Note sui Formati

- **PDF**: Richiede connessione internet (usa Chromium per il rendering)
- **DOCX**: Editabile, mantiene la formattazione base
- **HTML**: Include tutti gli stili, visualizzabile offline
- **One-Pager**: Ideale per executive summary rapido

---

## 9. Condividere il Piano

Puoi condividere il piano con stakeholder esterni (presidenti, sponsor, investitori) senza che abbiano un account.

### Creare un Link di Condivisione

1. Dalla WebApp del piano, clicca **"Condividi Piano"**
2. Configura le opzioni:

| Opzione | Descrizione |
|---------|-------------|
| Scadenza | 7, 30, 90, o 365 giorni |
| Password | (Opzionale) Protezione con password |
| Permessi Download | Abilita/disabilita download file |

3. Clicca **"Genera Link"**
4. Copia il link generato e invialo

### Gestire le Condivisioni

- Dalla WebApp, sezione **"Link Attivi"**
- Puoi vedere: visualizzazioni, data creazione, scadenza
- Puoi **revocare** un link in qualsiasi momento

### Sicurezza

- I link sono UUID casuali (non indovinabili)
- La password viene hashata (SHA-256)
- La revoca è immediata e irreversibile
- I link scaduti non sono più accessibili

---

## 10. Impostazioni

Accedi alle impostazioni cliccando l'ingranaggio (⚙️) dalla Dashboard.

### Configurazione AI

| Campo | Descrizione |
|-------|-------------|
| Provider AI | Gemini o OpenRouter |
| API Key | La tua chiave personale |
| Modello | (Solo OpenRouter) Modello da usare |

### Stato Licenza

Visualizza:
- Email associata
- Data attivazione
- Scadenza licenza
- Giorni rimanenti

### Salvataggio

Clicca **"Salva Impostazioni"** dopo ogni modifica.

---

## 11. Risoluzione Problemi

### L'applicazione non si avvia

**Causa**: Windows Defender o antivirus bloccano l'exe.

**Soluzione**:
1. Apri Windows Defender
2. Vai su "Protezione da virus e minacce"
3. Clicca "Cronologia protezione"
4. Trova RootingFuture e clicca "Consenti"

### Errore "API Key mancante"

**Causa**: Non hai configurato il provider AI.

**Soluzione**:
1. Vai su Impostazioni
2. Inserisci la tua API Key (Gemini o OpenRouter)
3. Clicca "Testa Connessione"
4. Salva

### Errore "Licenza scaduta"

**Causa**: La licenza ha superato la data di scadenza.

**Soluzione**:
1. Contatta il tuo referente per il rinnovo
2. Riceverai una nuova chiave di licenza
3. Reinstalla o contatta il supporto

### Generazione lenta (>3 minuti)

**Causa**: Connessione lenta o provider AI sovraccarico.

**Soluzione**:
1. Verifica la connessione internet
2. Prova un provider diverso (Gemini ↔ OpenRouter)
3. Riprova in un momento diverso

### PDF non si genera

**Causa**: Playwright/Chromium non installato.

**Soluzione**:
1. Assicurati di avere connessione internet
2. Usa l'export DOCX come alternativa
3. Riavvia l'applicazione

### Pagina bianca nel browser

**Causa**: Il server non è ancora avviato.

**Soluzione**:
1. Attendi 10 secondi
2. Ricarica la pagina (F5)
3. Verifica che la finestra del terminale sia aperta

---

## 12. FAQ

### Quanti piani posso generare?

Dipende dai crediti disponibili. Ogni piano costa 1 credito. Parti con 10 crediti e puoi richiederne altri al tuo referente.

### Posso modificare i piani generati?

Sì, esportando in formato DOCX puoi modificare tutto con Microsoft Word o software compatibili.

### I dati del club sono salvati online?

No. Tutti i dati sono salvati **localmente** sul tuo computer nel file `rooting_future.db`. Nessun dato viene inviato a server esterni oltre alle API AI per la generazione.

### Posso usare il software offline?

No. È necessaria una connessione internet per:
- Generare piani (richiede API AI)
- Generare PDF (richiede Chromium)

### La licenza è trasferibile?

No. La licenza è vincolata all'hardware del computer (HWID). Se cambi PC, dovrai richiedere una nuova licenza.

### Cosa succede se la licenza scade?

Puoi continuare a visualizzare e esportare i piani già generati. Non puoi generare nuovi piani finché non rinnovi.

### Posso installare su più computer?

Ogni computer richiede una licenza separata perché l'HWID è unico.

### I competitor vengono analizzati online?

No. I competitor inseriti servono solo come contesto per l'AI. Non viene effettuata ricerca web automatica nella versione alpha.

---

## 13. Supporto

### Contatti

- **Email**: support@rootingfuture.com
- **Referente Licenze**: Il tuo contatto commerciale

### Segnalare un Bug

Quando segnali un problema, includi:
1. Descrizione del problema
2. Passaggi per riprodurlo
3. Screenshot (se possibile)
4. Contenuto della cartella `logs/` (se presente)

### Richiedere Funzionalità

Invia suggerimenti a support@rootingfuture.com con oggetto "Feature Request".

---

## Appendice: Scorciatoie da Tastiera

| Scorciatoia | Azione |
|-------------|--------|
| `Ctrl + F` | Cerca nel piano |
| `Esc` | Chiudi finestre modali |
| `↑ / ↓` | Naviga tra sezioni |

---

## Cronologia Versioni

| Versione | Data | Note |
|----------|------|------|
| 6.0.0-alpha | Feb 2026 | Prima release alpha pubblica |

---

*Manuale aggiornato: 7 Febbraio 2026*
*Rooting Future Strategy Engine - Tutti i diritti riservati*
