# 🎬 Rooting Future - Video Demo Guide

## Obiettivo
Creare un video che mostra il sistema Rooting Future **in azione reale**, evidenziando le performance OPT-001 + OPT-002.

---

## 📋 Preparazione (5 minuti)

### 1. Installa Screen Recorder (Gratis)

**Windows - OBS Studio (Consigliato)**
```powershell
# Download da: https://obsproject.com/
# Oppure con winget:
winget install OBSProject.OBSStudio
```

**Alternativa Semplice: Windows Game Bar**
- Premi `Win + G` → Già integrato in Windows 10/11
- Click su "Capture" → Record

### 2. Setup Registrazione

**Impostazioni OBS** (se usi OBS):
1. Sources → Add → Display Capture (cattura tutto lo schermo)
2. Settings → Output → Recording Quality → "High Quality, Medium File Size"
3. Settings → Video → Output Resolution → 1920x1080
4. Settings → Audio → Desktop Audio → Attivo

**Impostazioni Windows Game Bar**:
- Win + G → Settings → Capture → Quality → High

### 3. Prepara Terminale

```powershell
# Apri PowerShell nella cartella progetto
cd C:\Users\Mirko\Desktop\rooting_future
.\venv\Scripts\Activate.ps1

# Aumenta font del terminale per leggibilità
# Right-click su barra titolo → Properties → Font → Size 16
```

---

## 🎥 Registrazione (2-3 minuti di video)

### STEP 1: Intro (10 secondi)

Apri un editor di testo e scrivi:

```
ROOTING FUTURE v6.0
Performance Demo

Optimizations:
- OPT-001: SQLite Indexing (+98% query speed)
- OPT-002: Real Async Execution (-66% generation time)

Live Demo: Generating strategic plan for AC DEMO UNITED
```

Lascia visibile 5 secondi, poi chiudi.

### STEP 2: Avvia Registrazione

**OBS**: Click su "Start Recording"
**Game Bar**: Win + Alt + R

### STEP 3: Esegui Demo (90-120 secondi)

```powershell
# Nel terminale PowerShell:
python create_live_demo.py
```

**Cosa mostrare mentre gira**:
1. I log che scorrono (mostra "AsyncGeminiClient initialized")
2. La sezione "TRUE PARALLEL EXECUTION"
3. I tempi di esecuzione degli agenti (dovrebbero essere ~15-20s totali)
4. Il summary finale con i tempi

### STEP 4: Mostra Output (20 secondi)

Mentre lo script finisce:
```powershell
# Apri cartella output
explorer output
```

- Mostra i file PDF e HTML generati
- Apri il PDF brevemente (scroll veloce per mostrare qualità)
- Apri l'HTML nel browser (mostra il design)

### STEP 5: Stop Registrazione

**OBS**: Click su "Stop Recording"
**Game Bar**: Win + Alt + R

---

## 🎬 Post-Produzione (Opzionale - 10 minuti)

### Aggiungi Testo Overlay (se vuoi)

Usa **Windows Video Editor** (gratis, già installato):
1. Apri "Video Editor" (cerca in Start Menu)
2. New Project → Add video
3. Add Text → Aggiungi titoli:
   - "OPT-001: +98% Query Speed" (al secondo 5)
   - "OPT-002: -66% Generation Time" (al secondo 10)
   - "Total: ~15-20 seconds" (quando appare il timing)

### Taglia Parti Inutili
- Taglia l'intro se troppo lento
- Taglia pause lunghe
- Mantieni il video sotto 3 minuti

---

## 📤 Export e Condivisione

### Export Settings (Windows Video Editor)
- Quality: High (1080p)
- Format: MP4
- Hardware acceleration: ON

### Condivisione Opzioni

**1. Google Drive**
- Upload su Google Drive
- Share link con colleghi
- Pro: Facile, streaming diretto

**2. YouTube (Unlisted)**
- Carica su YouTube come "Unlisted"
- Solo chi ha il link può vedere
- Pro: Streaming perfetto, nessun download

**3. File diretto**
- Comprimi con 7zip se troppo grande
- Invia via email/Teams
- Pro: Offline, nessuna dipendenza

---

## 📊 Metriche da Evidenziare nel Video

Quando mostri i risultati, evidenzia:

### Prima (Sistema Vecchio)
- ❌ Query DB: 50-100ms
- ❌ Generation time: 60s
- ❌ Esecuzione sequenziale

### Dopo (OPT-001 + OPT-002)
- ✅ Query DB: <1ms (+98%)
- ✅ Generation time: 15-20s (-66%)
- ✅ 6 agenti paralleli reali

---

## 🎯 Script Voce Over (Opzionale)

Se vuoi aggiungere narrazione audio:

```
"Rooting Future versione 6.0.

Abbiamo implementato due ottimizzazioni critiche:

OPT-001: Indicizzazione SQLite che migliora le query del 98%.
OPT-002: Esecuzione parallela reale che riduce il tempo di generazione del 66%.

Guardiamo il sistema in azione.
[pausa mentre gira]

Come vedete, il sistema genera un piano strategico completo in circa 15-20 secondi,
con 6 agenti AI che lavorano in parallelo.

Il vecchio sistema impiegava 60 secondi.

Ecco i file generati: PDF professionale e HTML interattivo.

Questo è Rooting Future v6.0 - performance enterprise, semplicità startup."
```

---

## ✅ Checklist Pre-Registrazione

- [ ] OBS/Game Bar configurato e testato
- [ ] Font terminale leggibile (Size 16+)
- [ ] Virtual environment attivato
- [ ] `create_live_demo.py` testato almeno una volta
- [ ] Cartella output vuota (per mostrare generazione fresh)
- [ ] Browser aperto per mostrare HTML
- [ ] Nessuna notifica distraente attiva (Do Not Disturb)

---

## 🐛 Troubleshooting

### "Python not found"
```powershell
.\venv\Scripts\python.exe create_live_demo.py
```

### "API Error"
Assicurati che GEMINI_API_KEY sia configurata:
```powershell
$env:GEMINI_API_KEY
# Se vuoto, aggiungi al .env
```

### Video troppo grande
- Comprimi con HandBrake (gratis): https://handbrake.fr/
- Target: ~100MB per 3 minuti
- Preset: "Fast 1080p30"

### Audio non registrato
- OBS: Settings → Audio → Desktop Audio Device → Seleziona giusto
- Game Bar: Settings → Audio → System Audio → ON

---

## 📝 Template Email per Colleghi

```
Ciao team,

Vi condivido il video demo di Rooting Future v6.0 con le ultime ottimizzazioni.

Link video: [inserisci link]

Highlights:
- Query DB: +98% più veloci (OPT-001)
- Generazione piani: -66% di tempo (OPT-002)
- Demo live: sistema reale in azione

Durata: 2-3 minuti

Feedback benvenuti!
```

---

**Pronto? Vai con la registrazione! 🎬**
