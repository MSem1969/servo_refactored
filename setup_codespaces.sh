#!/bin/bash
# =============================================================================
# TO_EXTRACTOR - Setup iniziale Codespaces
# Eseguire SOLO la prima volta o dopo rebuild container
# =============================================================================

echo "=========================================="
echo "  TO_EXTRACTOR - Setup Codespaces"
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
sudo -u postgres psql -c "CREATE USER to_extractor_user WITH PASSWORD 'to_extractor_pwd';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE to_extractor OWNER to_extractor_user;" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE to_extractor TO to_extractor_user;" 2>/dev/null || true

# 4. Importa database
echo "[4/6] Import database..."
sudo -u postgres psql -d to_extractor -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" 2>/dev/null
sudo -u postgres pg_restore -d to_extractor /workspaces/extractor_v2/database_export.dump 2>/dev/null || true
sudo -u postgres psql -d to_extractor -c "GRANT ALL ON SCHEMA public TO to_extractor_user;" 2>/dev/null
sudo -u postgres psql -d to_extractor -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO to_extractor_user;" 2>/dev/null
sudo -u postgres psql -d to_extractor -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO to_extractor_user;" 2>/dev/null

# 5. Setup Backend
echo "[5/6] Setup Backend..."
cd /workspaces/extractor_v2/backend
python -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Crea .env
cat > .env << 'ENVEOF'
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=to_extractor
PG_USER=to_extractor_user
PG_PASSWORD=to_extractor_pwd
SECRET_KEY=dev-secret-key-for-codespaces
DEBUG=true
ENVEOF

# 6. Setup Frontend
echo "[6/6] Setup Frontend..."
cd /workspaces/extractor_v2/frontend
npm install -q

# Reset password admin
echo ""
echo "[*] Reset password admin..."
cd /workspaces/extractor_v2/backend
source venv/bin/activate
python3 -c "
import bcrypt
import psycopg2
h = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode()
c = psycopg2.connect(host='127.0.0.1', database='to_extractor', user='to_extractor_user', password='to_extractor_pwd')
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
