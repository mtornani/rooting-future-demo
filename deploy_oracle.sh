#!/bin/bash
# Deploy Rooting Future su Oracle Cloud Free Tier (ARM Ampere A1)
# Always-on, genuinely free, 4 OCPU + 24GB RAM disponibili
#
# Pre-requisiti:
# 1. Account Oracle Cloud (sempre gratuito)
# 2. Istanza ARM Ampere A1 creata (1 OCPU, 6GB RAM sufficiente)
# 3. SSH key configurata
#
# Uso: ssh opc@<IP> 'bash -s' < deploy_oracle.sh

set -e

echo "=== Rooting Future Deploy - Oracle Free Tier ==="

# System setup
sudo dnf install -y python3.11 python3.11-pip git nginx certbot python3-certbot-nginx

# Clone/update repo
if [ -d "/opt/rooting-future" ]; then
    cd /opt/rooting-future && git pull
else
    sudo git clone https://github.com/mtornani/rooting-future-demo.git /opt/rooting-future
    cd /opt/rooting-future
fi

# Python env
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# Env file (edit manually after first deploy)
if [ ! -f .env ]; then
    cat > .env << 'ENVEOF'
GEMINI_API_KEY=your-key-here
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_API_KEY=your-ollama-key
OLLAMA_MODEL=gemma3:27b
SECRET_KEY=$(python3.11 -c "import secrets; print(secrets.token_hex(32))")
ENVEOF
    echo "[!] Edit .env with your API keys: nano /opt/rooting-future/.env"
fi

# Systemd service (always-on)
sudo tee /etc/systemd/system/rooting-future.service << 'SVCEOF'
[Unit]
Description=Rooting Future Strategy Engine
After=network.target

[Service]
Type=simple
User=opc
WorkingDirectory=/opt/rooting-future
Environment=PYTHONUTF8=1
ExecStart=/opt/rooting-future/venv/bin/gunicorn app:app \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    --threads 4 \
    --timeout 300 \
    --access-logfile /var/log/rooting-future-access.log \
    --error-logfile /var/log/rooting-future-error.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

sudo systemctl daemon-reload
sudo systemctl enable rooting-future
sudo systemctl restart rooting-future

# Nginx reverse proxy
sudo tee /etc/nginx/conf.d/rooting-future.conf << 'NGXEOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        client_max_body_size 50M;
    }
}
NGXEOF

sudo systemctl enable nginx
sudo systemctl restart nginx

# Firewall
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload

echo ""
echo "=== Deploy completato ==="
echo "  HTTP:  http://$(curl -s ifconfig.me)"
echo "  Logs:  sudo journalctl -u rooting-future -f"
echo ""
echo "Prossimi passi:"
echo "  1. Configura .env: nano /opt/rooting-future/.env"
echo "  2. Configura dominio DNS"
echo "  3. SSL: sudo certbot --nginx -d tuodominio.com"
echo "  4. Apri porte 80/443 nella Security List Oracle Cloud Console"
