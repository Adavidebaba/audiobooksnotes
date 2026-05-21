#!/bin/bash
# Forza la directory di esecuzione a quella in cui si trova lo script
cd "$(dirname "$0")"

echo "=== Arresto del container esistente ==="
docker compose down

echo "=== Ricostruzione dell'immagine Docker ==="
docker compose build --no-cache

echo "=== Avvio del nuovo container in background ==="
docker compose up -d

echo "=== Stato dei container ==="
docker compose ps

echo ""
echo "=== Fatto! ==="
read -p "Premi [Invio] per chiudere questa finestra..."
