#!/bin/bash
# =============================================================================
# SERV.O v8.1 - Avvio Codespaces
# =============================================================================

echo "=========================================="
echo "  SERV.O v8.1 - Avvio Codespaces"
echo "=========================================="

# Rileva directory base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Avvia PostgreSQL
echo "[1/4] Avvio PostgreSQL..."
sudo service postgresql start
sleep 2

# 2. Verifica database
echo "[2/4] Verifica database..."
PGPASSWORD=servo_pwd psql -h 127.0.0.1 -U servo_user -d servo -c "SELECT COUNT(*) FROM operatori;" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "  ⚠ Database non configurato. Esegui prima setup_codespaces.sh"
    exit 1
fi
echo "  ✓ Database OK"

# 3. Avvia Backend in background
echo "[3/4] Avvio Backend..."
cd "$SCRIPT_DIR/backend"
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 &
BACKEND_PID=$!
sleep 3

# 4. Avvia Frontend
echo "[4/4] Avvio Frontend..."
cd "$SCRIPT_DIR/frontend"
npm run dev -- --host &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo "  SERV.O v8.1 Avviato!"
echo "=========================================="
echo ""
echo "  Backend PID:  $BACKEND_PID"
echo "  Frontend PID: $FRONTEND_PID"
echo ""
echo "  Per fermare: kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "  Credenziali: admin / admin123"
echo "=========================================="

# Attendi
wait
