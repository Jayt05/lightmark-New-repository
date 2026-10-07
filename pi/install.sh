#!/usr/bin/env bash
# Installs (or updates) Lightmark on a Raspberry Pi or any Debian-based Linux machine.
# Run from the folder that holds index.html:   sudo bash pi/install.sh
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Run this with sudo: sudo bash pi/install.sh"; exit 1; }
SRC="$(cd "$(dirname "$0")/.." && pwd)"
APP=/opt/lightmark
DATA=/var/lib/lightmark
PORT="${LIGHTMARK_PORT:-8080}"

command -v python3 >/dev/null || { apt-get update && apt-get install -y python3; }
id lightmark >/dev/null 2>&1 || useradd --system --home "$DATA" --shell /usr/sbin/nologin lightmark
mkdir -p "$APP" "$DATA/backups"
install -m 644 "$SRC/index.html" "$APP/index.html"
install -m 755 "$SRC/pi/server.py" "$APP/server.py"
chown -R lightmark:lightmark "$DATA"
chmod 700 "$DATA"

if [ ! -f "$DATA/password.json" ]; then
  echo "Choose the password people will type to open Lightmark (8+ characters)."
  sudo -u lightmark LIGHTMARK_DATA="$DATA" python3 "$APP/server.py" --set-password
fi

cat > /etc/systemd/system/lightmark.service <<UNIT
[Unit]
Description=Lightmark drawing server
After=network-online.target
Wants=network-online.target

[Service]
User=lightmark
Environment=LIGHTMARK_DATA=$DATA
Environment=LIGHTMARK_PORT=$PORT
ExecStart=/usr/bin/python3 $APP/server.py
Restart=always
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=$DATA
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT

# Daily backup of the drawings, keeping the last 14 days.
cat > /etc/cron.daily/lightmark-backup <<'CRON'
#!/bin/sh
cd /var/lib/lightmark || exit 0
sudo -u lightmark python3 -c "import sqlite3,datetime; s=sqlite3.connect('lightmark.db'); d=sqlite3.connect('backups/lightmark-'+datetime.date.today().isoformat()+'.db'); s.backup(d); d.close()"
find /var/lib/lightmark/backups -name 'lightmark-*.db' -mtime +14 -delete
CRON
chmod 755 /etc/cron.daily/lightmark-backup

systemctl daemon-reload
systemctl enable --now lightmark >/dev/null
systemctl restart lightmark

IP="$(hostname -I | awk '{print $1}')"
echo
echo "Lightmark is running. On a phone or laptop on the same Wi-Fi, open:"
echo "  http://$(hostname).local:$PORT"
echo "  or http://$IP:$PORT"
echo "Drawings are stored in $DATA, with daily backups in $DATA/backups."
