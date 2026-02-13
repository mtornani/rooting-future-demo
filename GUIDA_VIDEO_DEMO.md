# 📹 GUIDA CREAZIONE VIDEO DEMO - Rooting Future

## 🎯 Obiettivo

Creare un video demo **mobile-friendly** (verticale/quadrato) del sistema Rooting Future per presentarlo ai colleghi via WhatsApp, email o durante meeting.

---

## 🚀 METODO 1: Automatico con Selenium (Raccomandato)

### Prerequisiti

```bash
# Installa dipendenze
pip install selenium webdriver-manager opencv-python pillow
```

### Esecuzione

```bash
# 1. Avvia l'applicazione
python app.py

# 2. In un altro terminale, esegui lo script di demo
python create_demo_video.py --mobile

# Output:
#   📁 demo_output/screenshots/      → Screenshot catturati
#   📹 demo_output/rooting_future_demo_TIMESTAMP.mp4  → Video finale
```

### Personalizzazione

Modifica `create_demo_video.py`:

```python
# Cambia dati del club demo
self.demo_club = {
    "club_name": "Tuo Club",
    "category": "Serie D",
    "primary_color": "#ff0000"
}

# Cambia viewport (default: iPhone 12 Pro 390x844)
chrome_options.add_argument('--window-size=414,896')  # iPhone Pro Max
```

### Vantaggi
- ✅ Completamente automatizzato
- ✅ Consistente e ripetibile
- ✅ Output mobile-ottimizzato

### Svantaggi
- ⚠️ Richiede Chrome/Chromium installato
- ⚠️ Dipendenze Python pesanti (~200MB)

---

## 🎨 METODO 2: Manuale Guidato (Più Semplice)

### Prerequisiti

Nessuno! Solo il tuo browser e uno screenshot tool.

### Esecuzione

```bash
# Esegui script guida
python create_simple_demo.py

# Lo script ti guiderà passo-passo:
# STEP 1/12: 🏠 Dashboard Home
# URL: http://127.0.0.1:5000/
# AZIONE: Mostra la dashboard principale con i progetti attivi
# 📸 Cattura screenshot → Premi INVIO
```

### Strumenti Screenshot Consigliati

**Windows:**
- `Win + Shift + S` → Snipping Tool nativo
- ShareX (gratuito): https://getsharex.com/

**macOS:**
- `Cmd + Shift + 4` → Screenshot area
- CleanShot X: https://cleanshot.com/

**Linux:**
- `gnome-screenshot -a`
- Flameshot: https://flameshot.org/

### Creazione Video dagli Screenshots

#### Opzione A: App Mobile (MIGLIORE per mobile-friendly)

1. **InShot** (iOS/Android - Gratuito)
   - Scarica dall'App Store/Play Store
   - Nuovo Progetto → Video
   - Importa screenshots da `demo_manual/`
   - Imposta durata 2-3s per immagine
   - Aggiungi transizioni "Dissolve"
   - Aggiungi testo overlay (titoli scene)
   - Esporta 720p o 1080p

2. **CapCut** (iOS/Android - Gratuito)
   - Più professionale di InShot
   - Template predefiniti per presentations
   - Animazioni fluide integrate

#### Opzione B: Desktop

**Windows/Mac - PowerPoint → Video**

```
1. Apri PowerPoint
2. Inserisci ogni screenshot come slide (Inserisci → Immagine)
3. Seleziona tutte le slide → Transizioni → Dissolve → Durata 2s
4. File → Esporta → Crea Video
5. Scegli qualità "Full HD (1080p)"
6. Durata slide: 3 secondi
7. Salva come MP4
```

**Windows - Movie Maker (legacy) o Clipchamp**

- Importa screenshots
- Trascina in timeline
- Imposta durata 2-3s
- Aggiungi transizioni
- Esporta MP4

**macOS - iMovie**

```
1. Nuovo Progetto → Filmato
2. Importa screenshots da demo_manual/
3. Trascina in timeline
4. Durata clip: 3s (doppio click su clip)
5. Transizioni → Dissolve tra clip
6. Esporta → File → Risoluzione 1080p
```

**Linux - OpenShot / Kdenlive**

```bash
# Installa OpenShot
sudo apt install openshot-qt

# Importa screenshots, imposta durata, esporta
```

### Vantaggi
- ✅ Massimo controllo sul risultato finale
- ✅ Nessuna dipendenza Python pesante
- ✅ Puoi aggiungere narrazione audio
- ✅ Editing più professionale

### Svantaggi
- ⏱️ Richiede più tempo manuale
- 🎨 Richiede tool di video editing

---

## 📱 METODO 3: Screen Recording Diretto (Più Veloce)

### Windows

**Xbox Game Bar** (integrato in Windows 10/11):

```
1. Apri app Rooting Future nel browser
2. Ridimensiona finestra Chrome a 400px larghezza (mobile-like)
3. Premi Win + G
4. Click "Registra" (o Win + Alt + R)
5. Esegui il flusso demo:
   - Login
   - Genera piano
   - Mostra risultati
   - Export
6. Win + Alt + R per fermare
7. Video salvato in: C:\Users\USERNAME\Videos\Captures\
```

**OBS Studio** (Professionale - Gratuito):

```bash
# Download: https://obsproject.com/

1. Installa OBS Studio
2. Sorgenti → Cattura Finestra → Seleziona Chrome
3. Trasforma → Ritaglio → Imposta 400x800px (mobile ratio)
4. Avvia Registrazione
5. Esegui demo
6. Stop Registrazione
```

### macOS

**QuickTime Player** (integrato):

```
1. Apri QuickTime Player
2. File → Nuova Registrazione Schermo
3. Click freccia giù → Seleziona Microfono (opzionale)
4. Click Registra → Seleziona finestra Chrome
5. Esegui demo
6. Stop dalla barra menu
7. File → Salva
```

**ScreenFlow** (Professionale - €149):
- https://www.telestream.net/screenflow/

### Linux

```bash
# SimpleScreenRecorder
sudo apt install simplescreenrecorder

# Kazam
sudo apt install kazam
```

### Post-Produzione Video Recording

1. **Taglia parti inutili** (pause, errori)
2. **Accelera sezioni lente** (generazione piano: 2x speed)
3. **Aggiungi titoli scene** (overlay text)
4. **Musica sottofondo** (opzionale - cerca "royalty free background music")

Tool consigliati:
- **DaVinci Resolve** (gratuito, professionale): https://www.blackmagicdesign.com/products/davinciresolve
- **Shotcut** (gratuito, open-source): https://shotcut.org/

---

## 🎬 STORYBOARD DEMO CONSIGLIATO

### Scene 1: Intro (5s)
- Schermata iniziale con logo/nome
- Testo: "Rooting Future - Piano Strategico AI per Club Calcistici"

### Scene 2: Dashboard (3s)
- Mostra dashboard pulita
- Testo: "Dashboard Intuitiva"

### Scene 3: Form Generazione (8s)
- Compila rapidamente form (accelera video se troppo lento)
- Testo: "Inserisci Dati Club in 2 Minuti"

### Scene 4: Generazione in Corso (6s)
- Progress bar con agenti STW
- Testo: "6 Agenti AI Specializzati al Lavoro"
- Accelera video 2-3x

### Scene 5: Piano Completo (15s)
- Scroll attraverso sezioni principali
- Testo overlay per ogni sezione:
  - "Executive Summary"
  - "Obiettivi Sportivi (8 MACRO)"
  - "Obiettivi Strutturali"
  - "Marketing & Commerciale"
  - "Piano Economico"

### Scene 6: Export (5s)
- Click export
- Mostra formati disponibili
- Testo: "Export Multi-Formato: PDF, DOCX, Excel, ZIP"

### Scene 7: Risultato Finale (5s)
- Anteprima PDF aperto
- Testo: "Piano Professionale Pronto in 60 Secondi"

### Scene 8: Outro (3s)
- Logo + contatti
- CTA: "Contattaci per Demo Personalizzata"

**Durata totale**: ~50 secondi (perfetta per attention span mobile)

---

## 🎵 Musica di Sottofondo Consigliata

**Siti Royalty-Free**:

1. **YouTube Audio Library** (gratuito)
   - https://studio.youtube.com/channel/UC_AUDIO_LIBRARY
   - Cerca: "Corporate", "Upbeat", "Technology"

2. **Bensound** (gratuito con attribution)
   - https://www.bensound.com/
   - Consigliati: "Creative Minds", "Going Higher"

3. **Uppbeat** (gratuito per social media)
   - https://uppbeat.io/
   - Categoria: Tech/Corporate

**Tip**: Mantieni volume musica a ~20-30% del totale, deve essere sottofondo discreto.

---

## 📐 Specifiche Tecniche Ottimali

### Per WhatsApp/Instagram/Social
- **Risoluzione**: 720p (1280x720) o 1080p verticale (1080x1920)
- **Aspect Ratio**: 9:16 (verticale) o 1:1 (quadrato)
- **FPS**: 24 o 30
- **Bitrate**: 5-8 Mbps
- **Formato**: MP4 (H.264 + AAC)
- **Durata**: 30-60 secondi (max 90s)

### Per Email/Presentazioni
- **Risoluzione**: 1080p (1920x1080)
- **Aspect Ratio**: 16:9
- **FPS**: 30
- **Bitrate**: 8-12 Mbps
- **Formato**: MP4
- **Durata**: 60-120 secondi

### Compressione File Size

Se video troppo grande per WhatsApp (max 16MB):

```bash
# Con ffmpeg (gratuito)
ffmpeg -i input.mp4 -vcodec h264 -b:v 3000k -acodec aac -b:a 128k output_compressed.mp4

# Online tool
# https://www.freeconvert.com/video-compressor
```

---

## ✅ CHECKLIST PRE-REGISTRAZIONE

- [ ] App Rooting Future running su `http://127.0.0.1:5000`
- [ ] Browser ridimensionato a viewport mobile (~400px width)
- [ ] Demo club preparato con dati realistici
- [ ] Screenshot tool / screen recorder pronto
- [ ] Output folder creata
- [ ] Storyboard stampato/aperto come riferimento
- [ ] (Opzionale) Microfono per narrazione vocale
- [ ] (Opzionale) Script narrazione scritto

---

## 🎤 SCRIPT NARRAZIONE VOCALE (Opzionale)

```
[Scene 1 - Intro]
"Benvenuti in Rooting Future, il sistema AI che genera piani strategici professionali per società calcistiche in meno di 60 secondi."

[Scene 2 - Dashboard]
"Dalla dashboard intuitiva, è possibile gestire tutti i progetti strategici del club."

[Scene 3 - Form]
"Per generare un nuovo piano, basta inserire i dati essenziali del club: nome, categoria, colori istituzionali."

[Scene 4 - Generazione]
"Il sistema utilizza 6 agenti AI specializzati, allineati alla metodologia consulenziale Sport To Win."

[Scene 5 - Risultato]
"In pochi secondi, otteniamo un piano strategico completo: Executive Summary, Obiettivi Sportivi, Strutturali, Marketing, e Piano Economico-Finanziario."

[Scene 6 - Export]
"Il piano può essere esportato in PDF, Word, Excel, o scaricato come pacchetto completo."

[Scene 7 - Outro]
"Rooting Future: strategia professionale, velocità AI. Contattaci per una demo personalizzata."
```

**Durata narrazione**: ~45 secondi

---

## 🐛 TROUBLESHOOTING

### Video troppo lungo
- Accelera sezioni ripetitive (generazione, scroll)
- Taglia pause e momenti morti
- Usa transizioni veloci (0.3-0.5s)

### Video pixelato/sgranato
- Verifica risoluzione source (browser a dimensioni corrette)
- Esporta a bitrate più alto (8-12 Mbps)
- Non scalare video in up (mantieni risoluzione nativa)

### File troppo grande
- Comprimi con ffmpeg (vedi sopra)
- Riduci bitrate a 4-5 Mbps
- Riduci risoluzione a 720p

### Audio fuori sinc
- Esporta video a frame rate fisso (30fps)
- Non mixare sorgenti a FPS diversi
- Usa tool professionale (DaVinci Resolve)

### WhatsApp non accetta video
- Max 16MB per WhatsApp
- Comprimi video (vedi sezione compressione)
- Alternativa: carica su YouTube/Google Drive e condividi link

---

## 📤 CONDIVISIONE FINALE

### Opzione 1: WhatsApp/Telegram
- Comprimi video a <16MB
- Invia direttamente in chat

### Opzione 2: Email
- Se <25MB: allega direttamente
- Se >25MB: usa WeTransfer / Google Drive link

### Opzione 3: Cloud Storage
- **Google Drive**: Carica → Imposta permessi "Chiunque con link"
- **Dropbox**: Carica → Crea link condivisibile
- **OneDrive**: Carica → Condividi

### Opzione 4: YouTube (Privato/Unlisted)
- Carica video come "Non in elenco"
- Condividi link diretto
- Vantaggio: qualità preservata, no limiti dimensioni

---

## 🎓 RISORSE EXTRA

### Tutorial Video Editing
- **DaVinci Resolve Basics**: https://www.youtube.com/watch?v=52vK5mzl1jQ
- **iMovie Tutorial**: https://www.youtube.com/watch?v=vLx2rEFnjsQ
- **PowerPoint to Video**: https://www.youtube.com/watch?v=y8MaNSXZiHk

### Template Video
- **Envato Elements**: template after effects/premiere
- **Canva**: template video presentazioni online

---

## 💬 SUPPORTO

Problemi? Contatta il team:

- Email: support@rootingfuture.com
- GitHub Issues: (se disponibile)
- Documentazione: `README.md`

---

**Buona Creazione! 🎬🚀**
