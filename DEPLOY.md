# 🚀 Rooting Future Strategy Engine - Guida al Deploy (AWS EC2)

Questa guida copre il deploy professionale su **Amazon EC2 (Elastic Compute Cloud)**.

## 1. Lanciare l'Istanza EC2
1. Accedi alla [Console AWS EC2](https://console.aws.amazon.com/ec2/).
2. Clicca su **Launch Instance** (Lancia istanza).
3. **Name:** Inserisci `RootingFuture-Prod`.
4. **OS Images (AMI):** Seleziona **Ubuntu** (versione 22.04 LTS o 24.04 LTS).
5. **Instance Type:**
   - *Minimo:* `t3.small` (2 vCPU, 2 GB RAM). È necessario per gestire la generazione PDF e l'AI.
   - *Risparmio:* Puoi provare `t2.micro` (Free Tier) ma potresti avere crash durante la generazione dei PDF pesanti per mancanza di RAM.
6. **Key Pair (Login):**
   - Clicca "Create new key pair".
   - Nome: `rooting-key`.
   - Tipo: `RSA`.
   - Formato: `.pem` (per OpenSSH).
   - **Scarica il file e salvalo in una cartella sicura.**

## 2. Network & Security (Il Firewall)
Nella sezione "Network settings", clicca su **Edit** o assicurati che sia selezionato "Create security group". Configura le regole **Inbound Security Group Rules**:

| Type | Protocol | Port Range | Source | Descrizione |
|------|----------|------------|--------|-------------|
| SSH | TCP | 22 | My IP (o 0.0.0.0/0) | Accesso Terminale |
| Custom TCP | TCP | **5000** | 0.0.0.0/0 (Anywhere) | Accesso Applicazione |

*Nota: Se decidi di usare un dominio in futuro, dovrai aprire anche 80 (HTTP) e 443 (HTTPS).*

## 3. Elastic IP (IP Statico)
Le istanze EC2 cambiano IP se vengono fermate. Per evitarlo:
1. Nel menu di sinistra vai su **Network & Security** -> **Elastic IPs**.
2. Clicca **Allocate Elastic IP address** -> **Allocate**.
3. Seleziona l'IP appena creato, clicca **Actions** -> **Associate Elastic IP address**.
4. Seleziona la tua istanza (`RootingFuture-Prod`) e conferma.
*Ora usa sempre questo IP per connetterti.*

## 4. Connessione al Server
Apri il terminale (o PowerShell/Putty) nella cartella dove hai scaricato la chiave `.pem`.

```bash
# Rendi la chiave privata (Solo su Mac/Linux, su Windows salta questo step)
chmod 400 rooting-key.pem

# Connettiti
ssh -i "rooting-key.pem" ubuntu@IL_TUO_IP_ELASTICO
```

## 5. Installazione (Automatizzata)
Una volta dentro il server, scarica il progetto e lancia lo script di setup.

```bash
# 1. Scarica il codice (Sostituisci con il tuo URL git reale)
git clone https://github.com/TUO_UTENTE/rooting_future.git
cd rooting_future

# 2. Lancia lo script di installazione
chmod +x setup_vps.sh
./setup_vps.sh
```

## 6. Configurazione Chiavi (.env)
Lo script ha creato un file `.env` di base. Ora devi inserire le tue chiavi reali:

```bash
nano .env
```

Modifica le righe necessarie:
```ini
GEMINI_API_KEY=AIzaSy...
SERPER_API_KEY=...
FLASK_SECRET_KEY=...
# Aggiungi altre configurazioni se necessario
```
*(Premi `CTRL+O` invio per salvare, `CTRL+X` per uscire)*

## 7. Avvio in Produzione (PM2)
Avvia l'applicazione in background in modo che resti accesa anche se chiudi il terminale.

```bash
# Avvia Rooting Future sulla porta 5000
pm2 start ecosystem.config.js

# Salva lo stato per il riavvio automatico del server
pm2 save
pm2 startup
```
*(Copia ed esegui il comando che `pm2 startup` ti mostrerà a video)*

## 8. Finito! 🚀
La tua applicazione è ora online su:
`http://IL_TUO_IP_ELASTICO:5000`

---

### Comandi Utili

**Aggiornare il sito:**
```bash
git pull
./venv/bin/pip install -r requirements.txt  # Solo se hai aggiunto nuove librerie
pm2 restart rooting-future
```

**Vedere i log (Errori/Info):**
```bash
pm2 logs rooting-future
```