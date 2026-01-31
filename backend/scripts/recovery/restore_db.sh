#!/bin/bash
# =============================================================================
# SERV.O v11.6 - DATABASE RESTORE
# =============================================================================
# Ripristina database da backup (schema, seed, o full)
# ATTENZIONE: Operazione distruttiva - richiede conferma
# =============================================================================

set -e

# Configurazione
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/../../backups"

# Carica variabili ambiente
if [ -f "${SCRIPT_DIR}/../../.env" ]; then
    export $(grep -v '^#' "${SCRIPT_DIR}/../../.env" | xargs)
fi

# Parametri database
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-servo}"
DB_USER="${DB_USER:-servo}"

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Help
show_help() {
    echo "Uso: $0 [opzioni]"
    echo ""
    echo "Opzioni:"
    echo "  -i, --input FILE      File di backup da ripristinare (obbligatorio)"
    echo "  -h, --host HOST       Host database"
    echo "  -p, --port PORT       Porta database"
    echo "  -d, --database DB     Nome database"
    echo "  -U, --user USER       Utente database"
    echo "  --docker CONTAINER    Esegui in container Docker"
    echo "  --schema-only         Ripristina solo schema (no dati)"
    echo "  --no-confirm          Salta conferma (PERICOLOSO)"
    echo "  --create-db           Crea database se non esiste"
    echo ""
    echo "Esempi:"
    echo "  $0 -i full/servo_full_latest.sql"
    echo "  $0 -i schema/schema_latest.sql --schema-only"
    echo "  $0 -i seed/seed_latest.sql"
    echo ""
    echo "Directory backup disponibili:"
    ls -la "$BACKUP_DIR" 2>/dev/null | grep "^d" | awk '{print "  " $NF}'
    exit 0
}

# Parse argomenti
INPUT_FILE=""
DOCKER_CONTAINER=""
SCHEMA_ONLY=false
NO_CONFIRM=false
CREATE_DB=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--input) INPUT_FILE="$2"; shift 2 ;;
        -h|--host) DB_HOST="$2"; shift 2 ;;
        -p|--port) DB_PORT="$2"; shift 2 ;;
        -d|--database) DB_NAME="$2"; shift 2 ;;
        -U|--user) DB_USER="$2"; shift 2 ;;
        --docker) DOCKER_CONTAINER="$2"; shift 2 ;;
        --schema-only) SCHEMA_ONLY=true; shift ;;
        --no-confirm) NO_CONFIRM=true; shift ;;
        --create-db) CREATE_DB=true; shift ;;
        --help) show_help ;;
        *) shift ;;
    esac
done

# Validazione input
if [ -z "$INPUT_FILE" ]; then
    print_error "File di input non specificato!"
    echo ""
    show_help
fi

# Trova file backup
if [ -f "$INPUT_FILE" ]; then
    BACKUP_FILE="$INPUT_FILE"
elif [ -f "$BACKUP_DIR/$INPUT_FILE" ]; then
    BACKUP_FILE="$BACKUP_DIR/$INPUT_FILE"
else
    print_error "File non trovato: $INPUT_FILE"
    exit 1
fi

# Decompressione se necessario
TEMP_FILE=""
if [[ "$BACKUP_FILE" == *.gz ]]; then
    print_step "Decompressione file..."
    TEMP_FILE="/tmp/servo_restore_$$.sql"
    gunzip -c "$BACKUP_FILE" > "$TEMP_FILE"
    BACKUP_FILE="$TEMP_FILE"
fi

# Info backup
SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
LINES=$(wc -l < "$BACKUP_FILE")

echo ""
print_warn "========================================"
print_warn "  ATTENZIONE: OPERAZIONE DISTRUTTIVA"
print_warn "========================================"
echo ""
print_info "File: $BACKUP_FILE"
print_info "Dimensione: $SIZE ($LINES righe)"
print_info "Database target: $DB_NAME@$DB_HOST:$DB_PORT"
echo ""

# Verifica contenuto
if grep -q "CREATE TABLE" "$BACKUP_FILE"; then
    print_info "Tipo: Schema + Dati (o solo schema)"
else
    print_info "Tipo: Solo dati (INSERT)"
fi

# Conferma
if [ "$NO_CONFIRM" = false ]; then
    echo ""
    print_warn "Questa operazione SOVRASCRIVERA' il database esistente!"
    read -p "Continuare? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Operazione annullata."
        [ -n "$TEMP_FILE" ] && rm -f "$TEMP_FILE"
        exit 0
    fi
fi

# Crea database se richiesto
if [ "$CREATE_DB" = true ]; then
    print_step "Creazione database (se non esiste)..."
    if [ -n "$DOCKER_CONTAINER" ]; then
        docker exec "$DOCKER_CONTAINER" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
            -c "CREATE DATABASE $DB_NAME;" postgres 2>/dev/null || true
    else
        PGPASSWORD="${DB_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
            -c "CREATE DATABASE $DB_NAME;" postgres 2>/dev/null || true
    fi
fi

# Esegui restore
print_step "Ripristino database..."
START_TIME=$(date +%s)

if [ -n "$DOCKER_CONTAINER" ]; then
    # Docker
    if [ "$SCHEMA_ONLY" = true ]; then
        docker exec -i "$DOCKER_CONTAINER" psql -h "$DB_HOST" -p "$DB_PORT" \
            -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE"
    else
        docker exec -i "$DOCKER_CONTAINER" psql -h "$DB_HOST" -p "$DB_PORT" \
            -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE"
    fi
else
    # Locale
    PGPASSWORD="${DB_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" \
        -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE"
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Cleanup
[ -n "$TEMP_FILE" ] && rm -f "$TEMP_FILE"

# Verifica
print_step "Verifica restore..."
if [ -n "$DOCKER_CONTAINER" ]; then
    TABLE_COUNT=$(docker exec "$DOCKER_CONTAINER" psql -h "$DB_HOST" -p "$DB_PORT" \
        -U "$DB_USER" -d "$DB_NAME" -t \
        -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
else
    TABLE_COUNT=$(PGPASSWORD="${DB_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" \
        -U "$DB_USER" -d "$DB_NAME" -t \
        -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
fi

echo ""
print_info "========================================"
print_info "Restore completato!"
print_info "========================================"
print_info "Durata: ${DURATION}s"
print_info "Tabelle nel database: $TABLE_COUNT"
echo ""
print_info "Verificare il funzionamento dell'applicazione."
