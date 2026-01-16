#!/bin/bash
# =============================================================================
# TO_EXTRACTOR v6.2 - DATABASE RESTORE SCRIPT
# =============================================================================
# Questo script ripristina il database PostgreSQL alla configurazione corrente.
#
# USO:
#   ./restore_database.sh [--full|--schema-only|--seed-only]
#
# OPZIONI:
#   --full         Ripristino completo (schema + seed data)
#   --schema-only  Solo schema (tabelle vuote)
#   --seed-only    Solo seed data (richiede schema esistente)
#
# PREREQUISITI:
#   - PostgreSQL installato e in esecuzione
#   - Database 'to_extractor' creato
#   - Utente 'to_extractor_user' con permessi
#   - Variabile d'ambiente PG_PASSWORD impostata
# =============================================================================

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directory dello script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="$SCRIPT_DIR/../sql"

# Configurazione database (da environment o default)
PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_DATABASE="${PG_DATABASE:-to_extractor}"
PG_USER="${PG_USER:-to_extractor_user}"

# Verifica password
if [ -z "$PG_PASSWORD" ]; then
    echo -e "${RED}ERRORE: Variabile PG_PASSWORD non impostata${NC}"
    echo "Esegui: export PG_PASSWORD='your_password'"
    exit 1
fi

# Parse argomenti
MODE="${1:---full}"

echo "=============================================="
echo "TO_EXTRACTOR - Database Restore"
echo "=============================================="
echo "Host:     $PG_HOST:$PG_PORT"
echo "Database: $PG_DATABASE"
echo "User:     $PG_USER"
echo "Mode:     $MODE"
echo "=============================================="

# Funzione per eseguire SQL
run_sql() {
    local file=$1
    echo -e "${YELLOW}Esecuzione: $file${NC}"
    PGPASSWORD=$PG_PASSWORD psql -h $PG_HOST -p $PG_PORT -U $PG_USER -d $PG_DATABASE -f "$file"
    echo -e "${GREEN}OK${NC}"
}

# Ripristino schema
if [ "$MODE" == "--full" ] || [ "$MODE" == "--schema-only" ]; then
    echo ""
    echo "=== FASE 1: Creazione Schema ==="

    if [ -f "$SQL_DIR/create_schema.sql" ]; then
        run_sql "$SQL_DIR/create_schema.sql"
    else
        echo -e "${RED}ERRORE: create_schema.sql non trovato${NC}"
        exit 1
    fi

    # Applica migrazioni
    echo ""
    echo "=== FASE 2: Applicazione Migrazioni ==="
    if [ -d "$SQL_DIR/migrations" ]; then
        for migration in $(ls "$SQL_DIR/migrations"/*.sql 2>/dev/null | sort); do
            run_sql "$migration"
        done
    else
        echo "Nessuna migrazione trovata"
    fi
fi

# Ripristino seed data
if [ "$MODE" == "--full" ] || [ "$MODE" == "--seed-only" ]; then
    echo ""
    echo "=== FASE 3: Inserimento Seed Data ==="

    if [ -f "$SQL_DIR/seed_data.sql" ]; then
        run_sql "$SQL_DIR/seed_data.sql"
    else
        echo -e "${YELLOW}AVVISO: seed_data.sql non trovato${NC}"
    fi
fi

# Reset password admin
echo ""
echo "=== FASE 4: Reset Password Admin ==="
echo "Impostazione password di default per utenti..."

PGPASSWORD=$PG_PASSWORD psql -h $PG_HOST -p $PG_PORT -U $PG_USER -d $PG_DATABASE << 'EOSQL'
-- Reset password per admin (Password1)
UPDATE operatori
SET password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.qLBDAGqPRQKmGy'
WHERE username = 'admin';

-- Reset password per SYSTEM (System123)
UPDATE operatori
SET password_hash = '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi'
WHERE username = 'SYSTEM';

SELECT username, ruolo, attivo FROM operatori ORDER BY id_operatore;
EOSQL

echo ""
echo -e "${GREEN}=============================================="
echo "RIPRISTINO COMPLETATO"
echo "==============================================${NC}"
echo ""
echo "Credenziali di default:"
echo "  admin / Password1"
echo "  SYSTEM / System123"
echo ""
echo "IMPORTANTE: Cambiare le password dopo il login!"
