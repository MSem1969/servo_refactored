#!/bin/bash
# =============================================================================
# SERV.O v11.6 - BACKUP SCHEMA (DDL)
# =============================================================================
# Genera dump completo dello schema database (struttura senza dati)
# Include: tabelle, indici, viste, sequenze, constraints, funzioni
# =============================================================================

set -e

# Configurazione
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/../../backups/schema"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="schema_${TIMESTAMP}.sql"

# Carica variabili ambiente
if [ -f "${SCRIPT_DIR}/../../.env" ]; then
    export $(grep -v '^#' "${SCRIPT_DIR}/../../.env" | xargs)
fi

# Parametri database (default o da .env)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-servo}"
DB_USER="${DB_USER:-servo}"

# Colori output
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
    echo "  -o, --output FILE   File di output (default: schema_TIMESTAMP.sql)"
    echo "  -h, --host HOST     Host database (default: localhost)"
    echo "  -p, --port PORT     Porta database (default: 5432)"
    echo "  -d, --database DB   Nome database (default: servo)"
    echo "  -U, --user USER     Utente database (default: servo)"
    echo "  --docker CONTAINER  Esegui dentro container Docker"
    echo "  --stdout            Output su stdout invece che file"
    echo ""
    exit 0
fi

# Parse argomenti
DOCKER_CONTAINER=""
OUTPUT_STDOUT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output) BACKUP_FILE="$2"; shift 2 ;;
        -h|--host) DB_HOST="$2"; shift 2 ;;
        -p|--port) DB_PORT="$2"; shift 2 ;;
        -d|--database) DB_NAME="$2"; shift 2 ;;
        -U|--user) DB_USER="$2"; shift 2 ;;
        --docker) DOCKER_CONTAINER="$2"; shift 2 ;;
        --stdout) OUTPUT_STDOUT=true; shift ;;
        *) shift ;;
    esac
done

# Crea directory backup
mkdir -p "$BACKUP_DIR"

# Comando pg_dump
PG_DUMP_CMD="pg_dump"
PG_DUMP_OPTS="--schema-only --no-owner --no-privileges --if-exists --clean"

# Header
if [ "$OUTPUT_STDOUT" = false ]; then
    print_info "SERV.O Schema Backup"
    print_info "===================="
    print_info "Host: $DB_HOST:$DB_PORT"
    print_info "Database: $DB_NAME"
    print_info "Output: $BACKUP_DIR/$BACKUP_FILE"
    echo ""
fi

# Esegui dump
if [ -n "$DOCKER_CONTAINER" ]; then
    # Esecuzione in Docker
    if [ "$OUTPUT_STDOUT" = true ]; then
        docker exec "$DOCKER_CONTAINER" $PG_DUMP_CMD $PG_DUMP_OPTS \
            -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"
    else
        print_info "Esecuzione in container Docker: $DOCKER_CONTAINER"
        docker exec "$DOCKER_CONTAINER" $PG_DUMP_CMD $PG_DUMP_OPTS \
            -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" \
            > "$BACKUP_DIR/$BACKUP_FILE"
    fi
else
    # Esecuzione locale
    if [ "$OUTPUT_STDOUT" = true ]; then
        PGPASSWORD="${DB_PASSWORD}" $PG_DUMP_CMD $PG_DUMP_OPTS \
            -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"
    else
        PGPASSWORD="${DB_PASSWORD}" $PG_DUMP_CMD $PG_DUMP_OPTS \
            -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" \
            > "$BACKUP_DIR/$BACKUP_FILE"
    fi
fi

# Risultato
if [ "$OUTPUT_STDOUT" = false ]; then
    if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
        SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
        print_info "Backup completato: $SIZE"

        # Conta oggetti
        TABLES=$(grep -c "CREATE TABLE" "$BACKUP_DIR/$BACKUP_FILE" 2>/dev/null || echo 0)
        INDEXES=$(grep -c "CREATE INDEX\|CREATE UNIQUE INDEX" "$BACKUP_DIR/$BACKUP_FILE" 2>/dev/null || echo 0)
        VIEWS=$(grep -c "CREATE VIEW" "$BACKUP_DIR/$BACKUP_FILE" 2>/dev/null || echo 0)

        print_info "Oggetti: $TABLES tabelle, $INDEXES indici, $VIEWS viste"

        # Crea link simbolico all'ultimo backup
        ln -sf "$BACKUP_FILE" "$BACKUP_DIR/schema_latest.sql"
        print_info "Link simbolico: schema_latest.sql -> $BACKUP_FILE"
    else
        print_error "Backup fallito!"
        exit 1
    fi
fi
