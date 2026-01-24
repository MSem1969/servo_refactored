#!/bin/bash
# =============================================================================
# TO_EXTRACTOR v6.2 - ENVIRONMENT SETUP SCRIPT
# =============================================================================
# Questo script configura l'intero ambiente da zero.
#
# USO:
#   ./setup_environment.sh
#
# PREREQUISITI:
#   - Ubuntu/Debian con sudo
#   - Accesso a internet
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=============================================="
echo "TO_EXTRACTOR v6.2 - Environment Setup"
echo "=============================================="

# =============================================================================
# 1. INSTALLAZIONE DIPENDENZE SISTEMA
# =============================================================================

echo -e "\n${YELLOW}=== 1. Installazione dipendenze sistema ===${NC}"

# Verifica se siamo root
if [ "$EUID" -eq 0 ]; then
    APT_CMD="apt-get"
else
    APT_CMD="sudo apt-get"
fi

$APT_CMD update
$APT_CMD install -y python3 python3-pip python3-venv postgresql postgresql-contrib nodejs npm

echo -e "${GREEN}Dipendenze sistema installate${NC}"

# =============================================================================
# 2. CONFIGURAZIONE POSTGRESQL
# =============================================================================

echo -e "\n${YELLOW}=== 2. Configurazione PostgreSQL ===${NC}"

# Genera password random
PG_PASSWORD=$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9' | head -c 16)

# Crea utente e database
sudo -u postgres psql << EOF
-- Crea utente se non esiste
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'to_extractor_user') THEN
        CREATE USER to_extractor_user WITH PASSWORD '${PG_PASSWORD}';
    END IF;
END
\$\$;

-- Crea database se non esiste
SELECT 'CREATE DATABASE to_extractor OWNER to_extractor_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'to_extractor')\gexec

-- Permessi
GRANT ALL PRIVILEGES ON DATABASE to_extractor TO to_extractor_user;
EOF

echo -e "${GREEN}PostgreSQL configurato${NC}"
echo "Password generata: $PG_PASSWORD"

# Salva credenziali in .env
ENV_FILE="$(dirname "$0")/../../backend/.env"
cat > "$ENV_FILE" << EOF
# TO_EXTRACTOR PostgreSQL Configuration
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=to_extractor
PG_USER=to_extractor_user
PG_PASSWORD=${PG_PASSWORD}

# Application
DB_TYPE=postgresql
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
EOF

echo -e "${GREEN}File .env creato${NC}"

# =============================================================================
# 3. SETUP BACKEND
# =============================================================================

echo -e "\n${YELLOW}=== 3. Setup Backend ===${NC}"

BACKEND_DIR="$(dirname "$0")/../../backend"

cd "$BACKEND_DIR"

# Crea virtual environment
python3 -m venv venv
source venv/bin/activate

# Installa dipendenze
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}Backend configurato${NC}"

# =============================================================================
# 4. INIZIALIZZA DATABASE
# =============================================================================

echo -e "\n${YELLOW}=== 4. Inizializzazione Database ===${NC}"

# Esporta variabili
export PG_HOST=localhost
export PG_PORT=5432
export PG_DATABASE=to_extractor
export PG_USER=to_extractor_user
export PG_PASSWORD=${PG_PASSWORD}

# Esegui script restore
SCRIPT_DIR="$(dirname "$0")"
python "$SCRIPT_DIR/restore_database.py" --mode full

echo -e "${GREEN}Database inizializzato${NC}"

# =============================================================================
# 5. SETUP FRONTEND
# =============================================================================

echo -e "\n${YELLOW}=== 5. Setup Frontend ===${NC}"

FRONTEND_DIR="$(dirname "$0")/../../frontend"

cd "$FRONTEND_DIR"

npm install

echo -e "${GREEN}Frontend configurato${NC}"

# =============================================================================
# COMPLETATO
# =============================================================================

echo ""
echo -e "${GREEN}=============================================="
echo "SETUP COMPLETATO"
echo "==============================================${NC}"
echo ""
echo "Credenziali PostgreSQL:"
echo "  Host:     localhost:5432"
echo "  Database: to_extractor"
echo "  User:     to_extractor_user"
echo "  Password: $PG_PASSWORD"
echo ""
echo "Credenziali Applicazione:"
echo "  admin / Password1"
echo ""
echo "Per avviare l'applicazione:"
echo ""
echo "  # Terminal 1 - Backend"
echo "  cd backend && source venv/bin/activate"
echo "  uvicorn app.main:app --reload --port 8000"
echo ""
echo "  # Terminal 2 - Frontend"
echo "  cd frontend && npm run dev"
echo ""
echo "Accedi a: http://localhost:5173"
