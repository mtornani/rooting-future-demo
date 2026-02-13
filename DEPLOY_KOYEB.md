# Deploy Rooting Future su Koyeb (Gratis Permanente)

## Perché Koyeb?
- **Gratis permanente** (non trial!)
- Always-on (no cold start)
- PostgreSQL incluso
- 512MB RAM
- Deploy automatico da GitHub

## Prerequisiti
1. Account GitHub con il repository Rooting Future
2. Account Koyeb (gratuito): https://app.koyeb.com/auth/signup

## Step 1: Preparazione Repository

Assicurati che questi file siano nel repository:

```
Procfile                  # Configurazione Gunicorn
runtime.txt              # Versione Python
requirements-koyeb.txt   # Dipendenze
```

## Step 2: Crea Account Koyeb

1. Vai su https://app.koyeb.com/auth/signup
2. Registrati con GitHub (consigliato) o email
3. **NON serve carta di credito**

## Step 3: Crea Nuovo Servizio

1. Click su **"Create Service"**
2. Seleziona **"GitHub"** come source
3. Autorizza Koyeb ad accedere al tuo repository
4. Seleziona il repository `rooting-future`
5. Branch: `main` (o `master`)

## Step 4: Configura Build

- **Builder**: Buildpack
- **Run command**: lascia vuoto (usa Procfile)
- **Instance type**: Free (nano)

## Step 5: Configura Environment Variables

Clicca su "Environment variables" e aggiungi:

| Variable | Valore |
|----------|--------|
| `GEMINI_API_KEY` | La tua API key di Google AI Studio |
| `SERPER_API_KEY` | La tua API key di Serper.dev |
| `TAVILY_API_KEY` | (opzionale) API key Tavily |
| `SECRET_KEY` | Una stringa casuale lunga (es: `my-super-secret-key-12345`) |
| `FLASK_ENV` | `production` |
| `PORT` | `8000` |

### Come ottenere le API Keys:

**Gemini API Key (Gratis):**
1. Vai su https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copia la chiave

**Serper API Key (Gratis 2500 query/mese):**
1. Vai su https://serper.dev
2. Registrati
3. Copia la API key dalla dashboard

## Step 6: Deploy

1. Click **"Deploy"**
2. Attendi 2-5 minuti per il build
3. Una volta verde, clicca sul link pubblico

Il tuo URL sarà tipo: `https://rooting-future-tuonome.koyeb.app`

## Step 7: Verifica

1. Apri l'URL nel browser
2. Dovresti vedere la pagina di attivazione licenza
3. Genera una licenza admin e attiva

## Troubleshooting

### Build fallisce
- Controlla i log di build
- Verifica che `requirements-koyeb.txt` sia corretto

### App non si avvia
- Controlla i log runtime
- Verifica le environment variables

### Errore API Gemini
- Verifica che `GEMINI_API_KEY` sia corretta
- Controlla i limiti gratuiti di Gemini

## Aggiornamenti

Ogni push su GitHub triggera un nuovo deploy automatico!

```bash
git add .
git commit -m "Update"
git push
```

## Limiti Free Tier Koyeb

- 1 web service
- 512MB RAM
- 0.1 vCPU
- Sufficiente per uso normale (< 1000 utenti/giorno)

## Supporto

Per problemi:
- Koyeb Docs: https://www.koyeb.com/docs
- Koyeb Discord: https://discord.gg/koyeb
