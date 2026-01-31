#!/bin/bash
# =============================================================================
# SERV.O v11.6 - DATABASE VERIFICATION
# =============================================================================
# Verifica integrità e completezza del database
# Utilizzare dopo restore per validare il ripristino
# =============================================================================

set -e

# Configurazione
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
NC='\033[0m'

print_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_fail() { echo -e "${RED}[FAIL]${NC} $1"; }
print_info() { echo -e "     $1"; }

ERRORS=0
WARNINGS=0

# Funzione per eseguire query
run_query() {
    PGPASSWORD="${DB_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" \
        -U "$DB_USER" -d "$DB_NAME" -t -A -c "$1" 2>/dev/null
}

echo ""
echo "========================================"
echo "SERV.O Database Verification"
echo "========================================"
echo "Database: $DB_NAME@$DB_HOST:$DB_PORT"
echo "========================================"
echo ""

# 1. Connessione
echo "1. CONNESSIONE"
echo "----------------------------------------"
if run_query "SELECT 1" > /dev/null 2>&1; then
    print_ok "Connessione al database OK"
else
    print_fail "Impossibile connettersi al database"
    exit 1
fi

# 2. Tabelle core
echo ""
echo "2. TABELLE CORE"
echo "----------------------------------------"

CORE_TABLES=(
    "acquisizioni"
    "ordini_testata"
    "ordini_dettaglio"
    "vendor"
    "anomalie"
    "anagrafica_farmacie"
    "anagrafica_parafarmacie"
    "operatori"
)

for table in "${CORE_TABLES[@]}"; do
    if run_query "SELECT 1 FROM $table LIMIT 1" > /dev/null 2>&1; then
        count=$(run_query "SELECT COUNT(*) FROM $table")
        print_ok "$table ($count righe)"
    else
        print_fail "$table - TABELLA MANCANTE!"
        ((ERRORS++))
    fi
done

# 3. Tabelle supervisione
echo ""
echo "3. TABELLE SUPERVISIONE"
echo "----------------------------------------"

SUP_TABLES=(
    "supervisione_unificata"
    "supervisione_aic"
    "supervisione_lookup"
    "supervisione_espositore"
    "supervisione_listino"
    "supervisione_prezzo"
    "supervisione_anagrafica"
)

for table in "${SUP_TABLES[@]}"; do
    if run_query "SELECT 1 FROM $table LIMIT 1" > /dev/null 2>&1; then
        count=$(run_query "SELECT COUNT(*) FROM $table")
        print_ok "$table ($count righe)"
    else
        print_fail "$table - TABELLA MANCANTE!"
        ((ERRORS++))
    fi
done

# 4. Tabelle criteri ML
echo ""
echo "4. TABELLE CRITERI ML"
echo "----------------------------------------"

ML_TABLES=(
    "criteri_ordinari_aic"
    "criteri_ordinari_lookup"
    "criteri_ordinari_espositore"
    "criteri_ordinari_listino"
)

for table in "${ML_TABLES[@]}"; do
    if run_query "SELECT 1 FROM $table LIMIT 1" > /dev/null 2>&1; then
        count=$(run_query "SELECT COUNT(*) FROM $table")
        print_ok "$table ($count pattern)"
    else
        print_fail "$table - TABELLA MANCANTE!"
        ((ERRORS++))
    fi
done

# 5. Viste
echo ""
echo "5. VISTE PRINCIPALI"
echo "----------------------------------------"

VIEWS=(
    "v_ordini_completi"
    "v_supervisione_pending"
    "v_sync_status"
)

for view in "${VIEWS[@]}"; do
    if run_query "SELECT 1 FROM $view LIMIT 1" > /dev/null 2>&1; then
        print_ok "$view"
    else
        print_fail "$view - VISTA MANCANTE!"
        ((ERRORS++))
    fi
done

# 6. Sequenze
echo ""
echo "6. SEQUENZE (campione)"
echo "----------------------------------------"

SEQ_COUNT=$(run_query "SELECT COUNT(*) FROM pg_sequences WHERE schemaname='public'")
print_ok "$SEQ_COUNT sequenze trovate"

# 7. Indici
echo ""
echo "7. INDICI"
echo "----------------------------------------"

IDX_COUNT=$(run_query "SELECT COUNT(*) FROM pg_indexes WHERE schemaname='public'")
print_ok "$IDX_COUNT indici trovati"

# Verifica indici critici
CRITICAL_INDEXES=(
    "ordini_testata_pkey"
    "ordini_dettaglio_pkey"
    "anomalie_pkey"
)

for idx in "${CRITICAL_INDEXES[@]}"; do
    if run_query "SELECT 1 FROM pg_indexes WHERE indexname='$idx'" | grep -q 1; then
        print_ok "$idx"
    else
        print_warn "$idx - indice mancante"
        ((WARNINGS++))
    fi
done

# 8. Foreign Keys
echo ""
echo "8. FOREIGN KEYS"
echo "----------------------------------------"

FK_COUNT=$(run_query "SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_type='FOREIGN KEY' AND table_schema='public'")
print_ok "$FK_COUNT foreign keys trovate"

# 9. Dati seed
echo ""
echo "9. DATI CONFIGURAZIONE"
echo "----------------------------------------"

# Vendor
VENDOR_COUNT=$(run_query "SELECT COUNT(*) FROM vendor" 2>/dev/null || echo 0)
if [ "$VENDOR_COUNT" -gt 0 ]; then
    print_ok "vendor: $VENDOR_COUNT vendor configurati"
else
    print_warn "vendor: nessun vendor configurato"
    ((WARNINGS++))
fi

# Operatori
OP_COUNT=$(run_query "SELECT COUNT(*) FROM operatori WHERE attivo=true" 2>/dev/null || echo 0)
if [ "$OP_COUNT" -gt 0 ]; then
    print_ok "operatori: $OP_COUNT operatori attivi"
else
    print_fail "operatori: nessun operatore attivo!"
    ((ERRORS++))
fi

# Admin
ADMIN_COUNT=$(run_query "SELECT COUNT(*) FROM operatori WHERE ruolo='admin' AND attivo=true" 2>/dev/null || echo 0)
if [ "$ADMIN_COUNT" -gt 0 ]; then
    print_ok "admin: $ADMIN_COUNT admin attivi"
else
    print_warn "admin: nessun admin attivo"
    ((WARNINGS++))
fi

# Email config
EMAIL_CFG=$(run_query "SELECT COUNT(*) FROM email_config" 2>/dev/null || echo 0)
if [ "$EMAIL_CFG" -gt 0 ]; then
    print_ok "email_config: configurazione presente"
else
    print_warn "email_config: configurazione mancante"
    ((WARNINGS++))
fi

# 10. Integrità dati
echo ""
echo "10. INTEGRITÀ DATI"
echo "----------------------------------------"

# Ordini senza dettaglio
ORPHAN_ORDERS=$(run_query "SELECT COUNT(*) FROM ordini_testata ot WHERE NOT EXISTS (SELECT 1 FROM ordini_dettaglio od WHERE od.id_testata = ot.id_testata)")
if [ "$ORPHAN_ORDERS" -eq 0 ]; then
    print_ok "Nessun ordine senza dettaglio"
else
    print_warn "$ORPHAN_ORDERS ordini senza righe dettaglio"
    ((WARNINGS++))
fi

# Dettagli orfani
ORPHAN_DETAILS=$(run_query "SELECT COUNT(*) FROM ordini_dettaglio od WHERE NOT EXISTS (SELECT 1 FROM ordini_testata ot WHERE ot.id_testata = od.id_testata)")
if [ "$ORPHAN_DETAILS" -eq 0 ]; then
    print_ok "Nessun dettaglio orfano"
else
    print_warn "$ORPHAN_DETAILS dettagli senza testata"
    ((WARNINGS++))
fi

# Riepilogo
echo ""
echo "========================================"
echo "RIEPILOGO"
echo "========================================"

TOTAL_TABLES=$(run_query "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
TOTAL_VIEWS=$(run_query "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='VIEW'")

echo "Tabelle: $TOTAL_TABLES"
echo "Viste: $TOTAL_VIEWS"
echo "Indici: $IDX_COUNT"
echo "Sequenze: $SEQ_COUNT"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}Database OK - Nessun problema rilevato${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}Database OK con $WARNINGS avvisi${NC}"
    exit 0
else
    echo -e "${RED}ERRORI: $ERRORS | AVVISI: $WARNINGS${NC}"
    exit 1
fi
