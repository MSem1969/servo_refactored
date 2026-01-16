#!/bin/bash
set -e

echo "=========================================="
echo "  SERV.O - Codespaces Setup"
echo "=========================================="

# Install PostgreSQL
echo "[1/6] Installing PostgreSQL..."
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib

# Start PostgreSQL
echo "[2/6] Starting PostgreSQL..."
sudo service postgresql start
sleep 3

# Create database and user
echo "[3/6] Setting up database..."
sudo -u postgres psql -c "CREATE USER servo_user WITH PASSWORD 'servo_pwd';" 2>/dev/null || echo "User already exists"
sudo -u postgres psql -c "CREATE DATABASE servo OWNER servo_user;" 2>/dev/null || echo "Database already exists"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE servo TO servo_user;" 2>/dev/null || true

# Import database dump if exists
echo "[4/6] Importing database..."
if [ -f "database_export.dump" ]; then
    sudo -u postgres pg_restore -d servo --clean --if-exists database_export.dump 2>/dev/null || \
    sudo -u postgres pg_restore -d servo database_export.dump 2>/dev/null || \
    echo "Warning: Could not restore dump (may be empty or incompatible)"
    echo "Database import attempted"
else
    echo "Warning: database_export.dump not found"
fi

# Grant permissions
sudo -u postgres psql -d servo -c "GRANT ALL ON SCHEMA public TO servo_user;" 2>/dev/null || true
sudo -u postgres psql -d servo -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO servo_user;" 2>/dev/null || true
sudo -u postgres psql -d servo -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO servo_user;" 2>/dev/null || true

# Setup Backend
echo "[5/6] Setting up backend..."
cd backend
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create .env for Codespaces
cat > .env << 'EOF'
DATABASE_URL=postgresql://servo_user:servo_pwd@localhost:5432/servo
SECRET_KEY=dev-secret-key-for-codespaces
DEBUG=true
CORS_ORIGINS=["http://localhost:5173","https://*.github.dev"]
EOF

cd ..

# Setup mail_monitor
echo "[5b/6] Setting up mail_monitor..."
cd mail_monitor
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cd ..

# Setup Frontend
echo "[6/6] Setting up frontend..."
cd frontend
npm install
cd ..

echo ""
echo "=========================================="
echo "  SERV.O Setup Complete!"
echo "=========================================="
echo ""
echo "To start the application:"
echo "  ./start_codespaces.sh"
echo ""
echo "Or manually:"
echo "  Backend:      cd backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0"
echo "  Frontend:     cd frontend && npm run dev -- --host"
echo "  Mail Monitor: cd mail_monitor && source venv/bin/activate && python mail_monitor.py"
echo ""
echo "Default credentials: admin / admin123"
echo "=========================================="
