#!/usr/bin/env python3
"""
=============================================================================
TO_EXTRACTOR v6.2 - DATABASE RESTORE SCRIPT (Python)
=============================================================================
Ripristina il database PostgreSQL alla configurazione corrente.

USO:
    python restore_database.py [--full|--schema-only|--seed-only|--reset-passwords]

PREREQUISITI:
    - PostgreSQL installato e in esecuzione
    - pip install psycopg2-binary bcrypt
    - Variabili ambiente: PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD
=============================================================================
"""

import os
import sys
import argparse
from pathlib import Path

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

# Password di default per reset
DEFAULT_PASSWORDS = {
    "admin": "Password1",
    "SYSTEM": "System123",
}


# =============================================================================
# FUNZIONI
# =============================================================================

def get_connection():
    """Crea connessione al database."""
    if not DB_CONFIG["password"]:
        print("ERRORE: PG_PASSWORD non impostata")
        sys.exit(1)

    return psycopg2.connect(**DB_CONFIG)


def run_sql_file(conn, filepath: Path):
    """Esegue un file SQL."""
    print(f"  Esecuzione: {filepath.name}")

    with open(filepath, "r") as f:
        sql = f.read()

    with conn.cursor() as cur:
        cur.execute(sql)

    conn.commit()
    print(f"  OK")


def restore_schema(conn):
    """Ripristina lo schema del database."""
    print("\n=== FASE 1: Creazione Schema ===")

    schema_file = SQL_DIR / "create_schema.sql"
    if not schema_file.exists():
        print(f"ERRORE: {schema_file} non trovato")
        sys.exit(1)

    run_sql_file(conn, schema_file)


def apply_migrations(conn):
    """Applica le migrazioni."""
    print("\n=== FASE 2: Applicazione Migrazioni ===")

    migrations_dir = SQL_DIR / "migrations"
    if not migrations_dir.exists():
        print("  Nessuna directory migrations trovata")
        return

    migrations = sorted(migrations_dir.glob("*.sql"))
    if not migrations:
        print("  Nessuna migrazione trovata")
        return

    for migration in migrations:
        run_sql_file(conn, migration)


def restore_seed_data(conn):
    """Ripristina i dati seed."""
    print("\n=== FASE 3: Inserimento Seed Data ===")

    seed_file = SQL_DIR / "seed_data.sql"
    if not seed_file.exists():
        print(f"  AVVISO: {seed_file} non trovato")
        return

    run_sql_file(conn, seed_file)


def reset_passwords(conn):
    """Reset password utenti a valori di default."""
    print("\n=== Reset Password Utenti ===")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        for username, password in DEFAULT_PASSWORDS.items():
            # Genera hash bcrypt
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt(rounds=12)
            ).decode("utf-8")

            cur.execute(
                "UPDATE operatori SET password_hash = %s WHERE username = %s",
                (password_hash, username)
            )

            if cur.rowcount > 0:
                print(f"  {username}: password resettata a '{password}'")
            else:
                print(f"  {username}: utente non trovato")

        conn.commit()

        # Mostra utenti
        cur.execute("SELECT username, ruolo, attivo FROM operatori ORDER BY id_operatore")
        print("\n  Utenti nel database:")
        for row in cur.fetchall():
            status = "attivo" if row["attivo"] else "disabilitato"
            print(f"    - {row['username']} ({row['ruolo']}) [{status}]")


def create_admin_user(conn):
    """Crea utente admin se non esiste."""
    print("\n=== Verifica Utente Admin ===")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM operatori WHERE username = 'admin'")
        if cur.fetchone()["cnt"] == 0:
            password_hash = bcrypt.hashpw(
                "Password1".encode("utf-8"),
                bcrypt.gensalt(rounds=12)
            ).decode("utf-8")

            cur.execute("""
                INSERT INTO operatori (username, password_hash, nome, cognome, email, ruolo, attivo)
                VALUES ('admin', %s, 'Admin', 'Sistema', 'admin@example.com', 'admin', TRUE)
            """, (password_hash,))

            conn.commit()
            print("  Utente admin creato con password 'Password1'")
        else:
            print("  Utente admin esistente")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="TO_EXTRACTOR Database Restore")
    parser.add_argument(
        "--mode",
        choices=["full", "schema-only", "seed-only", "reset-passwords"],
        default="full",
        help="Modalita di ripristino"
    )
    args = parser.parse_args()

    print("==============================================")
    print("TO_EXTRACTOR - Database Restore (Python)")
    print("==============================================")
    print(f"Host:     {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"Database: {DB_CONFIG['database']}")
    print(f"User:     {DB_CONFIG['user']}")
    print(f"Mode:     {args.mode}")
    print("==============================================")

    conn = get_connection()

    try:
        if args.mode in ["full", "schema-only"]:
            restore_schema(conn)
            apply_migrations(conn)

        if args.mode in ["full", "seed-only"]:
            restore_seed_data(conn)

        if args.mode in ["full", "reset-passwords"]:
            reset_passwords(conn)
            create_admin_user(conn)

        print("\n" + "=" * 46)
        print("RIPRISTINO COMPLETATO")
        print("=" * 46)
        print("\nCredenziali di default:")
        for user, pwd in DEFAULT_PASSWORDS.items():
            print(f"  {user} / {pwd}")
        print("\nIMPORTANTE: Cambiare le password dopo il login!")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
