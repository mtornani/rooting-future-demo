# Prompt per Configurare n8n con Rooting Future

## Contesto Sistema

Ho già implementato l'infrastruttura lato Flask. Ecco gli endpoint disponibili:

### Endpoints n8n (Webhook receivers)
```
POST /api/n8n/questionnaire     - Riceve questionario compilato
POST /api/n8n/generate/{id}     - Triggera generazione piano
GET  /api/n8n/status/{id}       - Polling stato questionario
POST /api/n8n/callback          - Callback generico per notifiche
```

### Endpoints Auth
```
POST /api/auth/register         - Registra nuovo club + admin
POST /api/auth/login            - Login utente
POST /api/auth/refresh          - Refresh token JWT
GET  /api/auth/me               - Info utente corrente (richiede Bearer token)
```

### Endpoints Protetti
```
GET  /api/club/questionnaires   - Lista questionari del club (richiede auth)
GET  /api/admin/clubs           - Lista club (solo super_admin)
GET  /api/admin/users           - Lista utenti (solo super_admin)
GET  /api/questionnaire/schema  - Schema JSON del questionario
```

### Configurazione Sicurezza
- Header firma webhook: `X-N8N-Signature` (HMAC-SHA256)
- Secret: variabile ambiente `N8N_WEBHOOK_SECRET`
- JWT Secret: variabile ambiente `JWT_SECRET`
- In development mode, la firma webhook è opzionale

---

## PROMPT PER n8n / AI

```
Devo configurare n8n (localhost:5678) per integrarsi con un'app Flask (localhost:5000) che genera piani strategici per club calcistici.

L'INFRASTRUTTURA FLASK È GIÀ PRONTA. Devo solo creare i workflow n8n.

## ENDPOINTS FLASK DISPONIBILI

### Ricezione Questionario
POST http://localhost:5000/api/n8n/questionnaire
Headers: Content-Type: application/json
Body:
{
    "club_name": "AC Example",
    "category": "Serie B",
    "questionnaire_data": {
        "anagrafica": {
            "nome_ufficiale": "...",
            "anno_fondazione": 1920,
            ...
        },
        "sportiva": {...},
        "infrastrutture": {...},
        "finanze": {...},
        "marketing": {...},
        "obiettivi": {...}
    }
}

Response:
{
    "success": true,
    "questionnaire_id": "abc123",
    "club_id": "xyz789",
    "status": "submitted",
    "next_step": "/api/n8n/generate/abc123"
}

### Trigger Generazione
POST http://localhost:5000/api/n8n/generate/{questionnaire_id}
Response: parametri per chiamare /api/generate

### Polling Stato
GET http://localhost:5000/api/n8n/status/{questionnaire_id}
Response: {"status": "submitted|processing|completed"}

### Schema Questionario
GET http://localhost:5000/api/questionnaire/schema
Response: JSON schema con sezioni e campi del questionario

## WORKFLOW DA CREARE

### WORKFLOW 1: Raccolta Questionario
Trigger: Webhook (n8n espone URL per form esterno)
Steps:
1. Ricevi dati da form (Google Forms, Tally, Typeform, o form custom)
2. Valida e normalizza i dati
3. Invia a Flask: POST /api/n8n/questionnaire
4. Salva questionnaire_id per tracking
5. Invia email conferma al club
6. Notifica admin (Slack/Email)

### WORKFLOW 2: Generazione Piano
Trigger: Webhook o Schedule (dopo validazione manuale)
Steps:
1. Ricevi questionnaire_id
2. Chiama POST /api/n8n/generate/{id}
3. Usa i parametri per chiamare POST /api/generate
4. Attendi completamento (polling /api/n8n/status/{id})
5. Quando completed, invia notifica al club

### WORKFLOW 3: Registrazione Nuovo Club
Trigger: Webhook per form registrazione
Steps:
1. Ricevi dati registrazione
2. POST /api/auth/register con:
   - club_name, category, colors
   - admin_email, admin_password
3. Salva tokens
4. Email benvenuto con link dashboard

### WORKFLOW 4: Notifiche Stato
Trigger: Schedule (ogni 5 minuti) o Webhook interno
Steps:
1. Loop su questionari in stato "processing"
2. Per ogni uno, GET /api/n8n/status/{id}
3. Se status cambiato, invia notifica appropriata

## NODI n8n RICHIESTI

Per ogni workflow, specifica:
1. Tipo nodo (Webhook, HTTP Request, Gmail, IF, Set, etc.)
2. Configurazione completa
3. Connessioni tra nodi
4. Gestione errori

## OUTPUT RICHIESTO

1. JSON esportabile per ogni workflow (Import in n8n)
2. Istruzioni configurazione credenziali Gmail/Slack
3. Variabili ambiente da settare
4. Test cases per verificare funzionamento
```

---

## Schema Questionario (per Form Builder)

Disponibile su: `GET /api/questionnaire/schema`

```json
{
    "version": "1.0",
    "sections": [
        {
            "id": "anagrafica",
            "title": "Anagrafica Club",
            "fields": [
                {"id": "nome_ufficiale", "label": "Nome Ufficiale", "type": "text", "required": true},
                {"id": "anno_fondazione", "label": "Anno Fondazione", "type": "number"},
                {"id": "categoria", "label": "Categoria", "type": "select", "options": ["Serie A", "Serie B", "Serie C", "Serie D", "Eccellenza", "Promozione"]},
                {"id": "regione", "label": "Regione", "type": "text"},
                {"id": "citta", "label": "Città", "type": "text"},
                {"id": "colori_sociali", "label": "Colori Sociali", "type": "text"}
            ]
        },
        {
            "id": "sportiva",
            "title": "Area Sportiva",
            "fields": [
                {"id": "dimensione_rosa", "label": "Dimensione Rosa Prima Squadra", "type": "number"},
                {"id": "eta_media", "label": "Età Media Rosa", "type": "number"},
                {"id": "settore_giovanile", "label": "Settore Giovanile Attivo", "type": "boolean"},
                {"id": "categorie_giovanili", "label": "Categorie Giovanili", "type": "text"},
                {"id": "staff_tecnico", "label": "Numero Staff Tecnico", "type": "number"}
            ]
        },
        {
            "id": "infrastrutture",
            "title": "Infrastrutture",
            "fields": [
                {"id": "nome_stadio", "label": "Nome Stadio", "type": "text"},
                {"id": "capienza_stadio", "label": "Capienza Stadio", "type": "number"},
                {"id": "proprieta_stadio", "label": "Proprietà", "type": "select", "options": ["Proprietà", "Concessione", "Affitto"]},
                {"id": "centro_sportivo", "label": "Centro Sportivo Dedicato", "type": "boolean"},
                {"id": "numero_campi", "label": "Numero Campi Allenamento", "type": "number"}
            ]
        },
        {
            "id": "finanze",
            "title": "Dati Finanziari",
            "fields": [
                {"id": "fatturato_annuo", "label": "Fatturato Annuo (€)", "type": "number"},
                {"id": "monte_ingaggi", "label": "Monte Ingaggi (€)", "type": "number"},
                {"id": "debiti", "label": "Debiti Totali (€)", "type": "number"},
                {"id": "sponsor_principale", "label": "Sponsor Principale", "type": "text"},
                {"id": "ricavi_stadio", "label": "Ricavi da Stadio (€)", "type": "number"}
            ]
        },
        {
            "id": "marketing",
            "title": "Marketing e Tifoseria",
            "fields": [
                {"id": "abbonati", "label": "Numero Abbonati", "type": "number"},
                {"id": "media_spettatori", "label": "Media Spettatori Casa", "type": "number"},
                {"id": "follower_social", "label": "Follower Social Totali", "type": "number"},
                {"id": "merchandising", "label": "Ricavi Merchandising (€)", "type": "number"}
            ]
        },
        {
            "id": "obiettivi",
            "title": "Obiettivi Strategici",
            "fields": [
                {"id": "obiettivo_sportivo_1y", "label": "Obiettivo Sportivo Anno 1", "type": "text"},
                {"id": "obiettivo_sportivo_3y", "label": "Obiettivo Sportivo Anno 3", "type": "text"},
                {"id": "priorita_investimento", "label": "Priorità Investimento", "type": "select", "options": ["Stadio", "Settore Giovanile", "Prima Squadra", "Marketing", "Infrastrutture"]},
                {"id": "sfide_principali", "label": "Sfide Principali", "type": "textarea"}
            ]
        }
    ]
}
```

---

## Test Manuale Endpoints

```bash
# Test schema questionario
curl http://localhost:5000/api/questionnaire/schema

# Test invio questionario
curl -X POST http://localhost:5000/api/n8n/questionnaire \
  -H "Content-Type: application/json" \
  -d '{
    "club_name": "Test FC",
    "category": "Serie D",
    "questionnaire_data": {
        "anagrafica": {"nome_ufficiale": "Test FC", "citta": "Roma"},
        "sportiva": {"dimensione_rosa": 25},
        "infrastrutture": {"capienza_stadio": 5000},
        "finanze": {"fatturato_annuo": 500000},
        "marketing": {"abbonati": 1000},
        "obiettivi": {"obiettivo_sportivo_1y": "Playoff"}
    }
}'

# Test registrazione
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "club_name": "Test FC",
    "category": "Serie D",
    "admin_email": "admin@testfc.com",
    "admin_password": "password123"
}'

# Test login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@testfc.com",
    "password": "password123"
}'
```

---

## Prossimi Step

1. Apri n8n: http://localhost:5678
2. Crea nuovo workflow
3. Usa il prompt sopra per far generare i workflow da AI
4. Importa i JSON generati
5. Configura credenziali (Gmail, Slack se necessario)
6. Testa con curl o form di prova
