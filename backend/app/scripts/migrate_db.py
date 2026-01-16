#!/usr/bin/env python3
# =============================================================================
# SERV.O v6.2 - DATABASE MIGRATION SCRIPT
# =============================================================================
# Script per migrare il database da v6.1 a v6.2
# Aggiunge: colonne OPERATORI, colonne LOG_OPERAZIONI, tabella USER_SESSIONS
#
# USO:
#   python -m app.scripts.migrate_db
#   python -m app.scripts.migrate_db --check  (solo verifica, non applica)
# =============================================================================

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))


# =============================================================================
# DEFINIZIONE MIGRAZIONI
# =============================================================================

MIGRATIONS = [
    # -------------------------------------------------------------------------
    # STEP 1: Nuove colonne per OPERATORI
    # -------------------------------------------------------------------------
    {
        "name": "OPERATORI.created_by_operatore",
        "check": "SELECT 1 FROM pragma_table_info('OPERATORI') WHERE name='created_by_operatore'",
        "sql": "ALTER TABLE OPERATORI ADD COLUMN created_by_operatore INTEGER REFERENCES OPERATORI(id_operatore)"
    },
    {
        "name": "OPERATORI.disabled_at",
        "check": "SELECT 1 FROM pragma_table_info('OPERATORI') WHERE name='disabled_at'",
        "sql": "ALTER TABLE OPERATORI ADD COLUMN disabled_at TEXT"
    },
    {
        "name": "OPERATORI.disabled_by_operatore",
        "check": "SELECT 1 FROM pragma_table_info('OPERATORI') WHERE name='disabled_by_operatore'",
        "sql": "ALTER TABLE OPERATORI ADD COLUMN disabled_by_operatore INTEGER REFERENCES OPERATORI(id_operatore)"
    },
    {
        "name": "OPERATORI.disable_reason",
        "check": "SELECT 1 FROM pragma_table_info('OPERATORI') WHERE name='disable_reason'",
        "sql": "ALTER TABLE OPERATORI ADD COLUMN disable_reason TEXT"
    },
    {
        "name": "OPERATORI.last_login_at",
        "check": "SELECT 1 FROM pragma_table_info('OPERATORI') WHERE name='last_login_at'",
        "sql": "ALTER TABLE OPERATORI ADD COLUMN last_login_at TEXT"
    },
    {
        "name": "OPERATORI.last_login_ip",
        "check": "SELECT 1 FROM pragma_table_info('OPERATORI') WHERE name='last_login_ip'",
        "sql": "ALTER TABLE OPERATORI ADD COLUMN last_login_ip TEXT"
    },
    {
        "name": "OPERATORI.updated_at",
        "check": "SELECT 1 FROM pragma_table_info('OPERATORI') WHERE name='updated_at'",
        "sql": "ALTER TABLE OPERATORI ADD COLUMN updated_at TEXT"
    },
    {
        "name": "OPERATORI.updated_at_init",
        "check": "SELECT 1 FROM OPERATORI WHERE updated_at IS NOT NULL LIMIT 1",
        "sql": "UPDATE OPERATORI SET updated_at = datetime('now') WHERE updated_at IS NULL"
    },

    # -------------------------------------------------------------------------
    # STEP 2: Indici per OPERATORI
    # -------------------------------------------------------------------------
    {
        "name": "idx_operatori_ruolo",
        "check": "SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_operatori_ruolo'",
        "sql": "CREATE INDEX IF NOT EXISTS idx_operatori_ruolo ON OPERATORI(ruolo)"
    },
    {
        "name": "idx_operatori_attivo",
        "check": "SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_operatori_attivo'",
        "sql": "CREATE INDEX IF NOT EXISTS idx_operatori_attivo ON OPERATORI(attivo)"
    },
    {
        "name": "idx_operatori_created_by",
        "check": "SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_operatori_created_by'",
        "sql": "CREATE INDEX IF NOT EXISTS idx_operatori_created_by ON OPERATORI(created_by_operatore)"
    },

    # -------------------------------------------------------------------------
    # STEP 3: Nuove colonne per LOG_OPERAZIONI
    # -------------------------------------------------------------------------
    {
        "name": "LOG_OPERAZIONI.username_snapshot",
        "check": "SELECT 1 FROM pragma_table_info('LOG_OPERAZIONI') WHERE name='username_snapshot'",
        "sql": "ALTER TABLE LOG_OPERAZIONI ADD COLUMN username_snapshot TEXT"
    },
    {
        "name": "LOG_OPERAZIONI.action_category",
        "check": "SELECT 1 FROM pragma_table_info('LOG_OPERAZIONI') WHERE name='action_category'",
        "sql": "ALTER TABLE LOG_OPERAZIONI ADD COLUMN action_category TEXT"
    },
    {
        "name": "LOG_OPERAZIONI.success",
        "check": "SELECT 1 FROM pragma_table_info('LOG_OPERAZIONI') WHERE name='success'",
        "sql": "ALTER TABLE LOG_OPERAZIONI ADD COLUMN success INTEGER DEFAULT 1"
    },
    {
        "name": "LOG_OPERAZIONI.error_message",
        "check": "SELECT 1 FROM pragma_table_info('LOG_OPERAZIONI') WHERE name='error_message'",
        "sql": "ALTER TABLE LOG_OPERAZIONI ADD COLUMN error_message TEXT"
    },
    {
        "name": "LOG_OPERAZIONI.ip_address",
        "check": "SELECT 1 FROM pragma_table_info('LOG_OPERAZIONI') WHERE name='ip_address'",
        "sql": "ALTER TABLE LOG_OPERAZIONI ADD COLUMN ip_address TEXT"
    },
    {
        "name": "LOG_OPERAZIONI.user_agent",
        "check": "SELECT 1 FROM pragma_table_info('LOG_OPERAZIONI') WHERE name='user_agent'",
        "sql": "ALTER TABLE LOG_OPERAZIONI ADD COLUMN user_agent TEXT"
    },
    {
        "name": "LOG_OPERAZIONI.session_id",
        "check": "SELECT 1 FROM pragma_table_info('LOG_OPERAZIONI') WHERE name='session_id'",
        "sql": "ALTER TABLE LOG_OPERAZIONI ADD COLUMN session_id INTEGER"
    },

    # -------------------------------------------------------------------------
    # STEP 4: Indici per LOG_OPERAZIONI
    # -------------------------------------------------------------------------
    {
        "name": "idx_log_category",
        "check": "SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_log_category'",
        "sql": "CREATE INDEX IF NOT EXISTS idx_log_category ON LOG_OPERAZIONI(action_category)"
    },
    {
        "name": "idx_log_success",
        "check": "SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_log_success'",
        "sql": "CREATE INDEX IF NOT EXISTS idx_log_success ON LOG_OPERAZIONI(success)"
    },
    {
        "name": "idx_log_timestamp",
        "check": "SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_log_timestamp'",
        "sql": "CREATE INDEX IF NOT EXISTS idx_log_timestamp ON LOG_OPERAZIONI(timestamp)"
    },

    # -------------------------------------------------------------------------
    # STEP 5: Nuova tabella USER_SESSIONS
    # -------------------------------------------------------------------------
    {
        "name": "TABLE USER_SESSIONS",
        "check": "SELECT 1 FROM sqlite_master WHERE type='table' AND name='USER_SESSIONS'",
        "sql": """
            CREATE TABLE IF NOT EXISTS USER_SESSIONS (
                id_session INTEGER PRIMARY KEY AUTOINCREMENT,
                id_operatore INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT (datetime('now')) NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                revoked_by_operatore INTEGER,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (id_operatore) REFERENCES OPERATORI(id_operatore),
                FOREIGN KEY (revoked_by_operatore) REFERENCES OPERATORI(id_operatore)
            )
        """
    },
    {
        "name": "idx_sessions_operatore",
        "check": "SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_sessions_operatore'",
        "sql": "CREATE INDEX IF NOT EXISTS idx_sessions_operatore ON USER_SESSIONS(id_operatore)"
    },
    {
        "name": "idx_sessions_token",
        "check": "SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_sessions_token'",
        "sql": "CREATE INDEX IF NOT EXISTS idx_sessions_token ON USER_SESSIONS(token_hash)"
    },
    {
        "name": "idx_sessions_expires",
        "check": "SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_sessions_expires'",
        "sql": "CREATE INDEX IF NOT EXISTS idx_sessions_expires ON USER_SESSIONS(expires_at)"
    },
]


# =============================================================================
# FUNZIONI MIGRAZIONE
# =============================================================================

def check_migration_needed(db, migration: dict) -> bool:
    """
    Verifica se una migrazione è già stata applicata.

    Returns:
        True se la migrazione è necessaria (non ancora applicata)
    """
    try:
        result = db.execute(migration["check"]).fetchone()
        return result is None  # Se None, la migrazione è necessaria
    except Exception:
        return True  # In caso di errore, assumiamo sia necessaria


def apply_migration(db, migration: dict) -> bool:
    """
    Applica una singola migrazione.

    Returns:
        True se applicata con successo
    """
    try:
        db.execute(migration["sql"])
        db.commit()
        return True
    except Exception as e:
        print(f"  ❌ Errore: {e}")
        return False


def run_migrations(check_only: bool = False) -> int:
    """
    Esegue tutte le migrazioni necessarie.

    Args:
        check_only: Se True, solo verifica senza applicare

    Returns:
        Numero di migrazioni applicate (o necessarie se check_only)
    """
    from app.database_pg import get_db

    db = get_db()

    print("=" * 60)
    print("SERV.O v6.2 - DATABASE MIGRATION")
    print("=" * 60)
    print("")

    needed = []
    already_applied = []

    # Fase 1: Verifica quali migrazioni sono necessarie
    print("📋 Verifica migrazioni...")
    print("")

    for migration in MIGRATIONS:
        if check_migration_needed(db, migration):
            needed.append(migration)
            print(f"  ⏳ {migration['name']} - DA APPLICARE")
        else:
            already_applied.append(migration)
            print(f"  ✅ {migration['name']} - già applicata")

    print("")
    print(
        f"Riepilogo: {len(already_applied)} già applicate, {len(needed)} da applicare")
    print("")

    if not needed:
        print("✅ Database già aggiornato, nessuna migrazione necessaria!")
        return 0

    if check_only:
        print(f"⚠️  Modalità check: {len(needed)} migrazioni da applicare")
        print("   Esegui senza --check per applicare le migrazioni")
        return len(needed)

    # Fase 2: Applica migrazioni
    print("🔄 Applicazione migrazioni...")
    print("")

    applied = 0
    failed = 0

    for migration in needed:
        print(f"  Applico: {migration['name']}...", end=" ")
        if apply_migration(db, migration):
            print("✅")
            applied += 1
        else:
            print("❌")
            failed += 1

    print("")
    print("=" * 60)

    if failed == 0:
        print(f"✅ MIGRAZIONE COMPLETATA: {applied} modifiche applicate")
    else:
        print(f"⚠️  MIGRAZIONE PARZIALE: {applied} OK, {failed} FALLITE")

    print("=" * 60)

    return applied


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Migra il database SERV.O a v6.2"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Solo verifica, non applica le migrazioni"
    )

    args = parser.parse_args()

    try:
        result = run_migrations(check_only=args.check)
        sys.exit(0 if result >= 0 else 1)
    except Exception as e:
        print(f"❌ Errore fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
