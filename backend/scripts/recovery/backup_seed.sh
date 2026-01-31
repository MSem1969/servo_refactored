#!/bin/bash
# =============================================================================
# SERV.O v11.6 - BACKUP SEED DATA
# =============================================================================
# Genera dump dei dati di configurazione essenziali per il sistema
# Tabelle: vendor, app_sezioni, permessi_ruolo, email_config, ftp_config,
#          ftp_endpoints, backup_modules, backup_storage, operatori (opzionale)
# =============================================================================

set -e

# Configurazione
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/../../backups/seed"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="seed_${TIMESTAMP}.sql"

# Carica variabili ambiente
if [ -f "${SCRIPT_DIR}/../../.env" ]; then
    export $(grep -v '^#' "${SCRIPT_DIR}/../../.env" | xargs)
fi

# Parametri database
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-servo}"
DB_USER="${DB_USER:-servo}"

# Tabelle seed (configurazione sistema)
SEED_TABLES=(
    "vendor"
    "app_sezioni"
    "permessi_ruolo"
    "email_config"
    "ftp_config"
    "ftp_endpoints"
    "ftp_vendor_mapping"
    "backup_modules"
    "backup_storage"
    "backup_schedules"
    "sync_state"
)

# Tabelle opzionali (dati sensibili)
OPTIONAL_TABLES=(
    "operatori"
    "listini_vendor"
    "anagrafica_clienti"
)

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Help
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    echo "Uso: $0 [opzioni]"
    echo ""
    echo "Opzioni:"
    echo "  -o, --output FILE     File di output (default: seed_TIMESTAMP.sql)"
    echo "  -h, --host HOST       Host database"
    echo "  -p, --port PORT       Porta database"
    echo "  -d, --database DB     Nome database"
    echo "  -U, --user USER       Utente database"
    echo "  --docker CONTAINER    Esegui in container Docker"
    echo "  --include-operators   Includi tabella operatori"
    echo "  --include-listini     Includi listini vendor"
    echo "  --include-clienti     Includi anagrafica clienti"
    echo "  --all                 Includi tutti i dati opzionali"
    echo ""
    echo "Tabelle seed incluse:"
    for t in "${SEED_TABLES[@]}"; do echo "  - $t"; done
    echo ""
    exit 0
fi

# Parse argomenti
DOCKER_CONTAINER=""
INCLUDE_OPERATORS=false
INCLUDE_LISTINI=false
INCLUDE_CLIENTI=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output) BACKUP_FILE="$2"; shift 2 ;;
        -h|--host) DB_HOST="$2"; shift 2 ;;
        -p|--port) DB_PORT="$2"; shift 2 ;;
        -d|--database) DB_NAME="$2"; shift 2 ;;
        -U|--user) DB_USER="$2"; shift 2 ;;
        --docker) DOCKER_CONTAINER="$2"; shift 2 ;;
        --include-operators) INCLUDE_OPERATORS=true; shift ;;
        --include-listini) INCLUDE_LISTINI=true; shift ;;
        --include-clienti) INCLUDE_CLIENTI=true; shift ;;
        --all) INCLUDE_OPERATORS=true; INCLUDE_LISTINI=true; INCLUDE_CLIENTI=true; shift ;;
        *) shift ;;
    esac
done

# Aggiungi tabelle opzionali
if [ "$INCLUDE_OPERATORS" = true ]; then
    SEED_TABLES+=("operatori")
fi
if [ "$INCLUDE_LISTINI" = true ]; then
    SEED_TABLES+=("listini_vendor")
fi
if [ "$INCLUDE_CLIENTI" = true ]; then
    SEED_TABLES+=("anagrafica_clienti")
fi

# Crea directory
mkdir -p "$BACKUP_DIR"

print_info "SERV.O Seed Data Backup"
print_info "======================="
print_info "Host: $DB_HOST:$DB_PORT"
print_info "Database: $DB_NAME"
print_info "Output: $BACKUP_DIR/$BACKUP_FILE"
print_info "Tabelle: ${#SEED_TABLES[@]}"
echo ""

# Costruisci opzioni tabelle per pg_dump
TABLE_OPTS=""
for table in "${SEED_TABLES[@]}"; do
    TABLE_OPTS="$TABLE_OPTS --table=$table"
done

# Comando pg_dump
PG_DUMP_CMD="pg_dump"
PG_DUMP_OPTS="--data-only --no-owner --no-privileges --disable-triggers --inserts"

# Header file
cat > "$BACKUP_DIR/$BACKUP_FILE" << 'EOF'
-- =============================================================================
-- SERV.O - SEED DATA BACKUP
-- =============================================================================
-- Questo file contiene i dati di configurazione essenziali per il sistema.
-- Eseguire DOPO il restore dello schema.
-- =============================================================================

SET session_replication_role = 'replica';  -- Disabilita FK temporaneamente

EOF

# Esegui dump
if [ -n "$DOCKER_CONTAINER" ]; then
    docker exec "$DOCKER_CONTAINER" $PG_DUMP_CMD $PG_DUMP_OPTS $TABLE_OPTS \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" \
        >> "$BACKUP_DIR/$BACKUP_FILE"
else
    PGPASSWORD="${DB_PASSWORD}" $PG_DUMP_CMD $PG_DUMP_OPTS $TABLE_OPTS \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" \
        >> "$BACKUP_DIR/$BACKUP_FILE"
fi

# Footer file
cat >> "$BACKUP_DIR/$BACKUP_FILE" << 'EOF'

SET session_replication_role = 'origin';  -- Riabilita FK

-- Reset sequenze (eseguire dopo insert)
-- SELECT setval('vendor_id_vendor_seq', COALESCE((SELECT MAX(id_vendor) FROM vendor), 1));
-- etc.

EOF

# Risultato
if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
    ROWS=$(grep -c "^INSERT" "$BACKUP_DIR/$BACKUP_FILE" 2>/dev/null || echo 0)

    print_info "Backup completato: $SIZE ($ROWS righe)"

    # Dettaglio per tabella
    echo ""
    print_info "Dettaglio tabelle:"
    for table in "${SEED_TABLES[@]}"; do
        count=$(grep -c "INSERT INTO.*$table" "$BACKUP_DIR/$BACKUP_FILE" 2>/dev/null || echo 0)
        printf "  %-25s %5d righe\n" "$table" "$count"
    done

    # Link simbolico
    ln -sf "$BACKUP_FILE" "$BACKUP_DIR/seed_latest.sql"
    print_info "Link: seed_latest.sql -> $BACKUP_FILE"
else
    print_error "Backup fallito!"
    exit 1
fi
