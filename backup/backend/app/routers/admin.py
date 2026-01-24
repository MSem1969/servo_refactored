"""
Router per operazioni amministrative del sistema.
Gestisce backup, reset, pulizia dati e impostazioni.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any
import shutil
import os
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["Admin"])

# Path del database
DB_PATH = "extractor_to.db"
BACKUP_DIR = "backups"


@router.post("/backup")
async def backup_database() -> Dict[str, Any]:
    """
    Crea un backup del database SQLite.
    Il backup viene salvato nella cartella 'backups' con timestamp.
    """
    try:
        # Crea directory backup se non esiste
        os.makedirs(BACKUP_DIR, exist_ok=True)

        # Nome file con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.db"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)

        # Copia il database
        shutil.copy2(DB_PATH, backup_path)

        # Calcola dimensione
        size_bytes = os.path.getsize(backup_path)
        size_mb = round(size_bytes / (1024 * 1024), 2)

        return {
            "success": True,
            "message": f"Backup creato: {backup_filename}",
            "filename": backup_filename,
            "size_mb": size_mb,
            "timestamp": timestamp
        }
    except Exception as e:
        raise HTTPException(500, f"Errore backup: {str(e)}")


@router.delete("/ordini/all")
async def clear_all_ordini(
    confirm: str = Query(..., description="Deve essere 'CONFERMA' per procedere")
) -> Dict[str, Any]:
    """
    Elimina tutti gli ordini dal database.
    Richiede conferma esplicita come parametro query.
    """
    if confirm != "CONFERMA":
        raise HTTPException(400, "Conferma non valida. Usa ?confirm=CONFERMA")

    try:
        from ..database_pg import get_db

        conn = get_db()
        cursor = conn.cursor()

        # Conta ordini prima della cancellazione
        cursor.execute("SELECT COUNT(*) FROM ordini")
        count_ordini = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM ordini_righe")
        count_righe = cursor.fetchone()[0]

        # Elimina righe e ordini
        cursor.execute("DELETE FROM ordini_righe")
        cursor.execute("DELETE FROM ordini")

        # Pulisci anche tabelle correlate
        cursor.execute("DELETE FROM anomalie")
        cursor.execute("DELETE FROM supervisione_log")

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": "Tutti gli ordini eliminati",
            "deleted": {
                "ordini": count_ordini,
                "righe": count_righe
            }
        }
    except Exception as e:
        raise HTTPException(500, f"Errore pulizia: {str(e)}")


@router.post("/reset")
async def reset_sistema(
    confirm: str = Query(..., description="Deve essere 'RESET_COMPLETO' per procedere")
) -> Dict[str, Any]:
    """
    Reset completo del sistema.
    Elimina tutti i dati TRANNE le anagrafiche (farmacie/parafarmacie).
    Richiede conferma esplicita.
    """
    if confirm != "RESET_COMPLETO":
        raise HTTPException(400, "Conferma non valida. Usa ?confirm=RESET_COMPLETO")

    try:
        from ..database_pg import get_db

        db = get_db()

        # Tabelle da svuotare (ordine per foreign key - prima le dipendenti)
        # NOTA: PostgreSQL usa nomi lowercase
        tables_to_clear = [
            # Prima le tabelle con FK
            "log_operazioni",
            "log_criteri_applicati",
            "esportazioni_dettaglio",
            "esportazioni",
            "tracciati_dettaglio",
            "tracciati",
            "supervisione_espositore",
            "criteri_ordinari_espositore",
            "anomalie",
            "ordini_dettaglio",
            "ordini_testata",
            "email_acquisizioni",
            "acquisizioni",
        ]

        deleted_counts = {}

        # Prima conta tutti i record
        for table in tables_to_clear:
            try:
                cursor = db.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                deleted_counts[table] = count
            except Exception as e:
                deleted_counts[table] = f"errore: {e}"
                db._conn.rollback()

        # Usa DELETE invece di TRUNCATE (non richiede ownership delle sequenze)
        # L'ordine è importante per le foreign key
        try:
            for table in tables_to_clear:
                db.execute(f"DELETE FROM {table}")
                print(f"✅ Tabella {table} svuotata")
            db.commit()
            print(f"✅ Reset completato: {deleted_counts}")
        except Exception as e:
            db._conn.rollback()
            print(f"❌ Errore DELETE: {e}")
            raise HTTPException(500, f"Errore DELETE: {str(e)}")

        db.close()

        return {
            "success": True,
            "message": "Reset completato. Anagrafiche preservate.",
            "deleted": deleted_counts
        }
    except Exception as e:
        raise HTTPException(500, f"Errore reset: {str(e)}")


@router.get("/settings")
async def get_settings() -> Dict[str, Any]:
    """
    Recupera le impostazioni di sistema dal database.
    """
    try:
        from ..database_pg import get_db

        conn = get_db()
        cursor = conn.cursor()

        # Verifica se esiste la tabella settings
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='system_settings'
        """)

        if not cursor.fetchone():
            # Ritorna default se tabella non esiste
            conn.close()
            return {
                "success": True,
                "data": get_default_settings()
            }

        cursor.execute("SELECT key, value FROM system_settings")
        rows = cursor.fetchall()
        conn.close()

        settings = get_default_settings()
        for key, value in rows:
            if key in settings:
                # Converti stringhe in tipi appropriati
                if value.lower() in ('true', 'false'):
                    settings[key] = value.lower() == 'true'
                elif value.isdigit():
                    settings[key] = int(value)
                else:
                    try:
                        settings[key] = float(value)
                    except:
                        settings[key] = value

        return {"success": True, "data": settings}
    except Exception as e:
        return {"success": True, "data": get_default_settings()}


@router.put("/settings")
async def save_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Salva le impostazioni di sistema nel database.
    """
    try:
        from ..database_pg import get_db

        conn = get_db()
        cursor = conn.cursor()

        # Crea tabella se non esiste
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Salva ogni impostazione
        for key, value in settings.items():
            cursor.execute("""
                INSERT OR REPLACE INTO system_settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, str(value)))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": "Impostazioni salvate",
            "saved_keys": list(settings.keys())
        }
    except Exception as e:
        raise HTTPException(500, f"Errore salvataggio: {str(e)}")


def get_default_settings() -> Dict[str, Any]:
    """Ritorna le impostazioni di default del sistema."""
    return {
        "autoValidate": False,
        "mlAutoApprove": False,
        "mlMinConfidence": 0.85,
        "emailNotifications": False,
        "autoBackup": True,
        "backupFrequency": "daily",
        "debugMode": False,
        "logLevel": "INFO",
        "maxUploadSize": 10,
        "defaultVendor": ""
    }
