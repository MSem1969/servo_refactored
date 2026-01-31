#!/bin/bash
# =============================================================================
# SERV.O v11.6 - BACKUP COMPLETO
# =============================================================================
# Genera backup completo del database (schema + dati)
# Utilizzare per disaster recovery completo
# =============================================================================

set -e

# Configurazione
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/../../backups/full"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="servo_full_${TIMESTAMP}.sql"

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
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    echo "Uso: $0 [opzioni]"
    echo ""
    echo "Opzioni:"
    echo "  -o, --output FILE     File di output"
    echo "  -h, --host HOST       Host database"
    echo "  -p, --port PORT       Porta database"
    echo "  -d, --database DB     Nome database"
    echo "  -U, --user USER       Utente database"
    echo "  --docker CONTAINER    Esegui in container Docker"
    echo "  --compress            Comprimi con gzip"
    echo "  --exclude-logs        Escludi tabelle di log (più veloce)"
    echo ""
    exit 0
fi

# Parse argomenti
DOCKER_CONTAINER=""
COMPRESS=false
EXCLUDE_LOGS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output) BACKUP_FILE="$2"; shift 2 ;;
        -h|--host) DB_HOST="$2"; shift 2 ;;
        -p|--port) DB_PORT="$2"; shift 2 ;;
        -d|--database) DB_NAME="$2"; shift 2 ;;
        -U|--user) DB_USER="$2"; shift 2 ;;
        --docker) DOCKER_CONTAINER="$2"; shift 2 ;;
        --compress) COMPRESS=true; shift ;;
        --exclude-logs) EXCLUDE_LOGS=true; shift ;;
        *) shift ;;
    esac
done

# Crea directory
mkdir -p "$BACKUP_DIR"

print_info "========================================"
print_info "SERV.O Full Database Backup"
print_info "========================================"
print_info "Host: $DB_HOST:$DB_PORT"
print_info "Database: $DB_NAME"
print_info "Timestamp: $TIMESTAMP"
echo ""

# Opzioni pg_dump
PG_DUMP_CMD="pg_dump"
PG_DUMP_OPTS="--no-owner --no-privileges --if-exists --clean"

# Escludi tabelle di log se richiesto
if [ "$EXCLUDE_LOGS" = true ]; then
    print_warn "Escludendo tabelle di log..."
    PG_DUMP_OPTS="$PG_DUMP_OPTS --exclude-table=operatore_azioni_log"
    PG_DUMP_OPTS="$PG_DUMP_OPTS --exclude-table=log_operazioni"
    PG_DUMP_OPTS="$PG_DUMP_OPTS --exclude-table=audit_modifiche"
    PG_DUMP_OPTS="$PG_DUMP_OPTS --exclude-table=ftp_log"
    PG_DUMP_OPTS="$PG_DUMP_OPTS --exclude-table=email_log"
    PG_DUMP_OPTS="$PG_DUMP_OPTS --exclude-table=otp_audit_log"
    PG_DUMP_OPTS="$PG_DUMP_OPTS --exclude-table=backup_operations_log"
fi

# Esegui dump
print_step "Esecuzione pg_dump..."
START_TIME=$(date +%s)

if [ -n "$DOCKER_CONTAINER" ]; then
    docker exec "$DOCKER_CONTAINER" $PG_DUMP_CMD $PG_DUMP_OPTS \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" \
        > "$BACKUP_DIR/$BACKUP_FILE"
else
    PGPASSWORD="${DB_PASSWORD}" $PG_DUMP_CMD $PG_DUMP_OPTS \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" \
        > "$BACKUP_DIR/$BACKUP_FILE"
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Comprimi se richiesto
if [ "$COMPRESS" = true ]; then
    print_step "Compressione con gzip..."
    gzip -f "$BACKUP_DIR/$BACKUP_FILE"
    BACKUP_FILE="${BACKUP_FILE}.gz"
fi

# Verifica e statistiche
if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)

    print_info ""
    print_info "========================================"
    print_info "Backup completato!"
    print_info "========================================"
    print_info "File: $BACKUP_DIR/$BACKUP_FILE"
    print_info "Dimensione: $SIZE"
    print_info "Durata: ${DURATION}s"

    # Checksum
    CHECKSUM=$(sha256sum "$BACKUP_DIR/$BACKUP_FILE" | cut -d' ' -f1)
    echo "$CHECKSUM  $BACKUP_FILE" > "$BACKUP_DIR/${BACKUP_FILE}.sha256"
    print_info "Checksum: ${CHECKSUM:0:16}..."

    # Link simbolico
    ln -sf "$BACKUP_FILE" "$BACKUP_DIR/servo_full_latest.sql$([ "$COMPRESS" = true ] && echo '.gz')"

    # Cleanup vecchi backup (mantieni ultimi 5)
    print_step "Cleanup backup vecchi (mantieni ultimi 5)..."
    ls -t "$BACKUP_DIR"/servo_full_*.sql* 2>/dev/null | tail -n +11 | xargs -r rm -f

    echo ""
    print_info "Per restore: ./restore_db.sh --input $BACKUP_FILE"
else
    print_error "Backup fallito!"
    exit 1
fi
