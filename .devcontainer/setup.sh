#!/bin/bash
# =============================================================================
# SERV.O - Codespaces Setup (Docker Compose)
# Questo script viene eseguito SOLO in Codespaces alla creazione
# PostgreSQL è già attivo come servizio Docker separato
# =============================================================================

set -e

echo "=========================================="
echo "SERV.O - Setup Codespaces"
echo "=========================================="

# 1. Verifica connessione PostgreSQL
echo "[1/5] Verifica PostgreSQL..."
until pg_isready -h localhost -U servo_user -d servo; do
  echo "    Attendo PostgreSQL..."
  sleep 2
done
echo "    PostgreSQL pronto!"

# 2. Copia .env se non esiste
echo "[2/5] Configurazione .env..."
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "    .env creato da .env.example"
else
  echo "    .env esistente, non sovrascritto"
fi

# 3. Installa dipendenze backend
echo "[3/5] Installazione dipendenze backend..."
cd backend
python -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt

# 4. Creazione schema database (Alembic)
echo "[4/5] Creazione schema database..."
alembic upgrade head
echo "    Schema creato!"
cd ..

# 5. Installa dipendenze frontend
echo "[5/5] Installazione dipendenze frontend..."
cd frontend
npm install --silent
cd ..

echo ""
echo "=========================================="
echo "Setup completato!"
echo ""
echo "PostgreSQL: localhost:5432"
echo "  Database: servo"
echo "  User:     servo_user"
echo "  Password: servo_pwd"
echo ""
echo "Per avviare l'applicazione:"
echo "  python run.py"
echo "=========================================="
