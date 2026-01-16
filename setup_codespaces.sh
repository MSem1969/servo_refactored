#!/bin/bash
# =============================================================================
# SERV.O - Setup iniziale Codespaces
# Eseguire SOLO la prima volta o dopo rebuild container
# =============================================================================

echo "=========================================="
echo "  SERV.O - Setup Codespaces"
echo "=========================================="

# 1. Installa PostgreSQL
echo "[1/6] Installazione PostgreSQL..."
sudo apt-get update -qq
sudo apt-get install -y -qq postgresql postgresql-contrib

# 2. Avvia PostgreSQL
echo "[2/6] Avvio PostgreSQL..."
sudo service postgresql start
sleep 3

# 3. Configura database
echo "[3/6] Configurazione database..."
sudo -u postgres psql -c "CREATE USER servo_user WITH PASSWORD 'servo_pwd';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE servo OWNER servo_user;" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE servo TO servo_user;" 2>/dev/null || true

# 4. Importa database
echo "[4/6] Import database..."
sudo -u postgres psql -d servo -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" 2>/dev/null
sudo -u postgres pg_restore -d servo /workspaces/servo_refactored/database_export.dump 2>/dev/null || true
sudo -u postgres psql -d servo -c "GRANT ALL ON SCHEMA public TO servo_user;" 2>/dev/null
sudo -u postgres psql -d servo -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO servo_user;" 2>/dev/null
sudo -u postgres psql -d servo -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO servo_user;" 2>/dev/null

# 5. Setup Backend
echo "[5/6] Setup Backend..."
cd /workspaces/servo_refactored/backend
python -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Crea .env
cat > .env << 'ENVEOF'
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=servo
PG_USER=servo_user
PG_PASSWORD=servo_pwd
SECRET_KEY=dev-secret-key-for-codespaces
DEBUG=true
ENVEOF

# 6. Setup Frontend
echo "[6/6] Setup Frontend..."
cd /workspaces/servo_refactored/frontend
npm install -q

# Reset password admin
echo ""
echo "[*] Reset password admin..."
cd /workspaces/servo_refactored/backend
source venv/bin/activate
python3 -c "
import bcrypt
import psycopg2
h = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode()
c = psycopg2.connect(host='127.0.0.1', database='servo', user='servo_user', password='servo_pwd')
cur = c.cursor()
cur.execute(\"UPDATE operatori SET password_hash=%s WHERE username='admin'\", (h,))
c.commit()
c.close()
print('  Password admin resettata a: admin123')
"

echo ""
echo "=========================================="
echo "  Setup completato!"
echo "=========================================="
echo ""
echo "  Ora esegui: ./start_codespaces.sh"
echo ""
echo "  Credenziali: admin / admin123"
echo "=========================================="
