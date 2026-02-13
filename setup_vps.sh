#!/bin/bash

# Stop on error
set -e

echo "🚀 Inizio Setup Rooting Future su VPS Ubuntu..."

# 1. Update System
echo "🔄 Aggiornamento pacchetti di sistema..."
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install System Dependencies (Python, Build Tools, WeasyPrint libs)
echo "📦 Installazione dipendenze di sistema..."
sudo apt-get install -y \
    software-properties-common \
    build-essential \
    python3-dev \
    python3-venv \
    python3-pip \
    git \
    nodejs \
    npm \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info

# 3. Install PM2 (Process Manager)
echo "⚙️ Installazione PM2..."
if ! command -v pm2 &> /dev/null
then
    sudo npm install -g pm2
else
    echo "PM2 già installato."
fi

# 4. Setup Python Environment
echo "🐍 Configurazione ambiente Python..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtualenv creato."
fi

source venv/bin/activate

echo "📥 Installazione dipendenze Python (potrebbe richiedere qualche minuto)..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. Create basic .env if not exists
if [ ! -f ".env" ]; then
    echo "⚠️ File .env non trovato. Creazione file di esempio..."
    echo "GEMINI_API_KEY=inserisci_qui" > .env
    echo "SERPER_API_KEY=inserisci_qui" >> .env
    echo "FLASK_SECRET_KEY=$(openssl rand -hex 16)" >> .env
    echo "Fai 'nano .env' per configurare le tue chiavi API!"
fi

echo "✅ Setup completato con successo!"
echo "👉 Prossimi passi:"
echo "   1. Modifica il file .env: nano .env"
echo "   2. Avvia il server: pm2 start ecosystem.config.js"
echo "   3. Salva la configurazione: pm2 save && pm2 startup"
