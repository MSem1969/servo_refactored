#!/usr/bin/env python3
"""
=============================================================================
TO_EXTRACTOR v6.2 - DATABASE REBUILD SCRIPT
=============================================================================
Ricostruisce il database PostgreSQL da zero.
NON inserisce dati di test - solo la struttura e i dati minimi necessari.

USO:
    python rebuild_database.py [--drop-existing]

    --drop-existing  Elimina tutte le tabelle esistenti prima di ricreare

PREREQUISITI:
    - PostgreSQL installato e in esecuzione
    - pip install psycopg2-binary bcrypt
    - Variabili ambiente configurate (vedi sotto)

VARIABILI AMBIENTE:
    PG_HOST      - Host PostgreSQL (default: localhost)
    PG_PORT      - Porta PostgreSQL (default: 5432)
    PG_DATABASE  - Nome database (default: to_extractor)
    PG_USER      - Utente PostgreSQL (default: to_extractor_user)
    PG_PASSWORD  - Password PostgreSQL (obbligatoria)

=============================================================================
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("ERRORE: psycopg2 non installato. Esegui: pip install psycopg2-binary")
    sys.exit(1)

try:
    import bcrypt
except ImportError:
    print("ERRORE: bcrypt non installato. Esegui: pip install bcrypt")
    sys.exit(1)


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
SQL_DIR = SCRIPT_DIR.parent / "sql"

# Configurazione database
DB_CONFIG = {
    "host": os.getenv("PG_HOST", "localhost"),
    "port": int(os.getenv("PG_PORT", "5432")),
    "database": os.getenv("PG_DATABASE", "to_extractor"),
    "user": os.getenv("PG_USER", "to_extractor_user"),
    "password": os.getenv("PG_PASSWORD", ""),
}

# Credenziali admin di default
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "Password1",
    "nome": "Amministratore",
    "cognome": "Sistema",
    "email": "admin@example.com",
}


# =============================================================================
# TABELLE DA ELIMINARE (ordine corretto per FK)
# =============================================================================

TABLES_TO_DROP = [
    "log_criteri_applicati",
    "tracciati_dettaglio",
    "esportazioni_dettaglio",
    "sessione_attivita",
    "supervisione_espositore",
    "anomalie",
    "ordini_dettaglio",
    "ordini_testata",
    "acquisizioni",
    "email_acquisizioni",
    "tracciati",
    "esportazioni",
    "log_operazioni",
    "criteri_ordinari_espositore",
    "user_sessions",
    "operatori",
    "vendor",
    "anagrafica_farmacie",
    "anagrafica_parafarmacie",
]

VIEWS_TO_DROP = [
    "v_ordini_completi",
    "v_dettagli_completi",
    "v_righe_esportabili",
    "v_supervisione_pending",
    "v_righe_confermabili",
    "v_righe_in_supervisione",
    "v_produttivita_operatore",
]


# =============================================================================
# FUNZIONI
# =============================================================================

def get_connection():
    """Crea connessione al database."""
    if not DB_CONFIG["password"]:
        print("ERRORE: PG_PASSWORD non impostata")
        print("Imposta la variabile ambiente: export PG_PASSWORD='password'")
        sys.exit(1)

    try:
        return psycopg2.connect(**DB_CONFIG)
    except psycopg2.OperationalError as e:
        print(f"ERRORE connessione database: {e}")
        sys.exit(1)


def drop_existing_objects(conn):
    """Elimina viste e tabelle esistenti."""
    print("\n=== FASE 0: Pulizia Database ===")

    with conn.cursor() as cur:
        # Elimina viste
        for view in VIEWS_TO_DROP:
            try:
                cur.execute(f"DROP VIEW IF EXISTS {view} CASCADE")
                print(f"  Vista {view} eliminata")
            except Exception as e:
                print(f"  Avviso: {view} - {e}")

        # Elimina tabelle
        for table in TABLES_TO_DROP:
            try:
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                print(f"  Tabella {table} eliminata")
            except Exception as e:
                print(f"  Avviso: {table} - {e}")

        conn.commit()

    print("  Pulizia completata")


def run_sql_file(conn, filepath: Path):
    """Esegue un file SQL."""
    print(f"  Esecuzione: {filepath.name}")

    if not filepath.exists():
        print(f"    ERRORE: File non trovato - {filepath}")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        sql = f.read()

    with conn.cursor() as cur:
        try:
            cur.execute(sql)
            conn.commit()
            print(f"    OK")
            return True
        except Exception as e:
            conn.rollback()
            print(f"    ERRORE: {e}")
            return False


def create_schema(conn):
    """Crea lo schema del database."""
    print("\n=== FASE 1: Creazione Schema ===")

    schema_file = SQL_DIR / "create_schema.sql"
    if not schema_file.exists():
        print(f"ERRORE CRITICO: {schema_file} non trovato!")
        print("Il file create_schema.sql deve essere presente nella cartella sql/")
        sys.exit(1)

    if not run_sql_file(conn, schema_file):
        print("ERRORE: Creazione schema fallita")
        sys.exit(1)


def create_admin_user(conn):
    """Crea utente admin con password di default."""
    print("\n=== FASE 2: Creazione Utente Admin ===")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Verifica se esiste già
        cur.execute("SELECT COUNT(*) as cnt FROM operatori WHERE username = %s",
                    (DEFAULT_ADMIN["username"],))

        if cur.fetchone()["cnt"] > 0:
            print(f"  Utente '{DEFAULT_ADMIN['username']}' già esistente")
            return

        # Genera hash password
        password_hash = bcrypt.hashpw(
            DEFAULT_ADMIN["password"].encode("utf-8"),
            bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

        # Inserisce utente
        cur.execute("""
            INSERT INTO operatori (
                username, password_hash, nome, cognome, email,
                ruolo, attivo, data_creazione
            ) VALUES (
                %s, %s, %s, %s, %s,
                'admin', TRUE, %s
            )
        """, (
            DEFAULT_ADMIN["username"],
            password_hash,
            DEFAULT_ADMIN["nome"],
            DEFAULT_ADMIN["cognome"],
            DEFAULT_ADMIN["email"],
            datetime.now(),
        ))

        conn.commit()
        print(f"  Utente admin creato: {DEFAULT_ADMIN['username']}")
        print(f"  Password: {DEFAULT_ADMIN['password']}")


def verify_installation(conn):
    """Verifica che l'installazione sia corretta."""
    print("\n=== FASE 3: Verifica Installazione ===")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Conta tabelle
        cur.execute("""
            SELECT COUNT(*) as cnt
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """)
        num_tables = cur.fetchone()["cnt"]
        print(f"  Tabelle create: {num_tables}")

        # Conta viste
        cur.execute("""
            SELECT COUNT(*) as cnt
            FROM information_schema.views
            WHERE table_schema = 'public'
        """)
        num_views = cur.fetchone()["cnt"]
        print(f"  Viste create: {num_views}")

        # Verifica vendor
        cur.execute("SELECT COUNT(*) as cnt FROM vendor")
        num_vendors = cur.fetchone()["cnt"]
        print(f"  Vendor configurati: {num_vendors}")

        # Verifica operatori
        cur.execute("SELECT COUNT(*) as cnt FROM operatori")
        num_operatori = cur.fetchone()["cnt"]
        print(f"  Operatori: {num_operatori}")

        # Lista operatori
        cur.execute("SELECT username, ruolo, attivo FROM operatori ORDER BY id_operatore")
        print("\n  Utenti nel database:")
        for row in cur.fetchall():
            status = "attivo" if row["attivo"] else "disabilitato"
            print(f"    - {row['username']} ({row['ruolo']}) [{status}]")


def print_summary():
    """Stampa riepilogo finale."""
    print("\n" + "=" * 50)
    print("RICOSTRUZIONE DATABASE COMPLETATA")
    print("=" * 50)
    print(f"\nDatabase: {DB_CONFIG['database']}")
    print(f"Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"\nCredenziali admin:")
    print(f"  Username: {DEFAULT_ADMIN['username']}")
    print(f"  Password: {DEFAULT_ADMIN['password']}")
    print("\nIMPORTANTE:")
    print("  1. Cambia la password admin dopo il primo login")
    print("  2. Importa le anagrafiche farmacie se necessario")
    print("  3. Configura i file .env per backend e frontend")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="TO_EXTRACTOR - Ricostruzione Database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python rebuild_database.py                    # Crea schema (se non esiste)
  python rebuild_database.py --drop-existing    # Elimina tutto e ricrea
        """
    )
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Elimina tabelle esistenti prima di ricreare"
    )
    args = parser.parse_args()

    print("=" * 50)
    print("TO_EXTRACTOR v6.2 - Ricostruzione Database")
    print("=" * 50)
    print(f"Host:     {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"Database: {DB_CONFIG['database']}")
    print(f"User:     {DB_CONFIG['user']}")
    print(f"Drop:     {'SI' if args.drop_existing else 'NO'}")
    print("=" * 50)

    # Conferma se drop
    if args.drop_existing:
        print("\nATTENZIONE: Verranno eliminate TUTTE le tabelle esistenti!")
        confirm = input("Continuare? (s/N): ").strip().lower()
        if confirm != "s":
            print("Operazione annullata.")
            sys.exit(0)

    conn = get_connection()

    try:
        if args.drop_existing:
            drop_existing_objects(conn)

        create_schema(conn)
        create_admin_user(conn)
        verify_installation(conn)
        print_summary()

    except Exception as e:
        print(f"\nERRORE: {e}")
        conn.rollback()
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
