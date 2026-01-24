"""
Router per operazioni amministrative del sistema.
Gestisce backup, reset, pulizia dati, impostazioni e sincronizzazioni.
"""

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from typing import Dict, Any, Optional
import shutil
import os
from datetime import datetime, date

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
    Reset completo del sistema per fase di test (v10.5).

    PRESERVA:
    - operatori (utenti)
    - anagrafica_farmacie
    - anagrafica_parafarmacie
    - anagrafica_clienti
    - listini_vendor (listini prezzi)
    - vendor (configurazione vendor)
    - permessi_ruolo, app_sezioni (configurazione)
    - backup_* (configurazione backup)
    - sync_state (stato sincronizzazione)

    ELIMINA tutto il resto:
    - Ordini e dettagli
    - Anomalie e supervisioni
    - Criteri ML (pattern appresi)
    - Tracciati e esportazioni
    - CRM (tickets, messaggi, allegati)
    - Log operazioni e audit
    - Sessioni attive

    Richiede conferma esplicita.
    """
    if confirm != "RESET_COMPLETO":
        raise HTTPException(400, "Conferma non valida. Usa ?confirm=RESET_COMPLETO")

    try:
        from ..database_pg import get_db

        db = get_db()

        # v10.5: Tabelle da svuotare (ordine per foreign key - prima le dipendenti)
        # PRESERVATE: operatori, anagrafica_*, listini_vendor, vendor, permessi_ruolo,
        #             app_sezioni, backup_*, sync_state, alembic_version
        tables_to_clear = [
            # 1. Log e audit (prima perché possono avere FK verso altre tabelle)
            "log_operazioni",
            "log_criteri_applicati",
            "audit_modifiche",
            # 2. Esportazioni e tracciati
            "esportazioni_dettaglio",
            "esportazioni",
            "tracciati_dettaglio",
            "tracciati",
            # 3. CRM
            "crm_allegati",
            "crm_messaggi",
            "crm_tickets",
            # 4. Supervisione (tutte le tipologie)
            "supervisione_espositore",
            "supervisione_listino",
            "supervisione_lookup",
            "supervisione_aic",
            "supervisione_prezzo",
            # 5. Criteri ML (pattern appresi)
            "criteri_ordinari_espositore",
            "criteri_ordinari_listino",
            "criteri_ordinari_lookup",
            "criteri_ordinari_aic",
            # 6. Anomalie
            "anomalie",
            # 7. Ordini
            "ordini_dettaglio",
            "ordini_testata",
            # 8. Acquisizioni
            "email_acquisizioni",
            "acquisizioni",
            # 9. Sessioni
            "sessione_attivita",
            "user_sessions",
        ]

        deleted_counts = {}

        # Prima conta tutti i record
        for table in tables_to_clear:
            try:
                cursor = db.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                deleted_counts[table] = count
            except Exception as e:
                deleted_counts[table] = f"tabella non trovata"
                db._conn.rollback()

        # Usa DELETE invece di TRUNCATE (non richiede ownership delle sequenze)
        # L'ordine è importante per le foreign key
        try:
            for table in tables_to_clear:
                try:
                    db.execute(f"DELETE FROM {table}")
                    print(f"✅ Tabella {table} svuotata")
                except Exception as e:
                    print(f"⚠️ Tabella {table} non svuotata: {e}")
                    db._conn.rollback()
            db.commit()
            print(f"✅ Reset completato: {deleted_counts}")
        except Exception as e:
            db._conn.rollback()
            print(f"❌ Errore DELETE: {e}")
            raise HTTPException(500, f"Errore DELETE: {str(e)}")

        # v10.5: Reset sequenze (ID ripartono da 1)
        sequences_to_reset = [
            "anomalie_id_anomalia_seq",
            "ordini_testata_id_testata_seq",
            "ordini_dettaglio_id_dettaglio_seq",
            "acquisizioni_id_acquisizione_seq",
            "tracciati_id_tracciato_seq",
            "esportazioni_id_esportazione_seq",
            "crm_tickets_id_ticket_seq",
            "crm_messaggi_id_messaggio_seq",
            "supervisione_espositore_id_supervisione_seq",
            "supervisione_listino_id_supervisione_seq",
            "supervisione_lookup_id_supervisione_seq",
            "supervisione_aic_id_supervisione_seq",
        ]

        for seq in sequences_to_reset:
            try:
                db.execute(f"ALTER SEQUENCE IF EXISTS {seq} RESTART WITH 1")
            except Exception:
                pass  # Ignora se sequenza non esiste

        db.commit()
        db.close()

        return {
            "success": True,
            "message": "Reset completato. Preservati: utenti, anagrafiche (farmacie, parafarmacie, clienti), listini, vendor, configurazioni. Sequenze resettate.",
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


# =============================================================================
# SINCRONIZZAZIONE ANAGRAFICA MINISTERO (v8.2)
# =============================================================================

def _format_sync_result(result) -> Dict[str, Any]:
    """Formatta risultato sync per response API."""
    return {
        "tipo": result.tipo,
        "downloaded": result.downloaded,
        "nuove": result.nuove,
        "aggiornate": result.aggiornate,
        "subentri": result.subentri,
        "chiuse": result.chiuse,
        "invariate": result.invariate,
        "errori": result.errori,
        "totale_json": result.totale_json,
        "totale_db": result.totale_db,
        "url": result.url,
        "durata_secondi": round(result.durata_secondi, 2)
    }


@router.get("/sync/status")
async def get_sync_status() -> Dict[str, Any]:
    """
    Verifica stato sincronizzazione anagrafica farmacie e parafarmacie.

    Ritorna per ciascuna:
    - Data ultima sincronizzazione
    - URL utilizzato
    - Se è disponibile un aggiornamento
    - Numero record nel DB
    """
    try:
        from ..services.anagrafica import check_sync_status
        status = check_sync_status()
        return {"success": True, "data": status}
    except Exception as e:
        raise HTTPException(500, f"Errore verifica stato: {str(e)}")


@router.post("/sync/farmacie")
async def sync_anagrafica_farmacie(
    force: bool = Query(False, description="Forza download anche se non modificato"),
    target_date: Optional[str] = Query(None, description="Data specifica YYYY-MM-DD (default: oggi)"),
    dry_run: bool = Query(False, description="Simula senza modificare il DB")
) -> Dict[str, Any]:
    """
    Sincronizza anagrafica FARMACIE dal Ministero della Salute.

    URL: https://www.dati.salute.gov.it/.../FRM_FARMA_5_YYYYMMDD.json

    Il sistema:
    1. Verifica se il file è cambiato (HTTP ETag)
    2. Scarica solo se necessario (~36 MB)
    3. Applica modifiche incrementali
    """
    try:
        from ..services.anagrafica import sync_farmacie

        parsed_date = None
        if target_date:
            try:
                parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(400, "Formato data non valido. Usa YYYY-MM-DD")

        result = sync_farmacie(
            force_download=force,
            target_date=parsed_date,
            dry_run=dry_run
        )

        return {
            "success": result.success,
            "message": result.message,
            "data": _format_sync_result(result)
        }
    except Exception as e:
        raise HTTPException(500, f"Errore sincronizzazione: {str(e)}")


@router.post("/sync/parafarmacie")
async def sync_anagrafica_parafarmacie(
    force: bool = Query(False, description="Forza download anche se non modificato"),
    target_date: Optional[str] = Query(None, description="Data specifica YYYY-MM-DD (default: oggi)"),
    dry_run: bool = Query(False, description="Simula senza modificare il DB")
) -> Dict[str, Any]:
    """
    Sincronizza anagrafica PARAFARMACIE dal Ministero della Salute.

    URL: https://www.dati.salute.gov.it/.../FRM_PFARMA_7_YYYYMMDD.json

    Il sistema:
    1. Verifica se il file è cambiato (HTTP ETag)
    2. Scarica solo se necessario
    3. Applica modifiche incrementali
    """
    try:
        from ..services.anagrafica import sync_parafarmacie

        parsed_date = None
        if target_date:
            try:
                parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(400, "Formato data non valido. Usa YYYY-MM-DD")

        result = sync_parafarmacie(
            force_download=force,
            target_date=parsed_date,
            dry_run=dry_run
        )

        return {
            "success": result.success,
            "message": result.message,
            "data": _format_sync_result(result)
        }
    except Exception as e:
        raise HTTPException(500, f"Errore sincronizzazione: {str(e)}")


@router.post("/sync/all")
async def sync_anagrafica_all(
    force: bool = Query(False, description="Forza download anche se non modificato"),
    target_date: Optional[str] = Query(None, description="Data specifica YYYY-MM-DD (default: oggi)"),
    dry_run: bool = Query(False, description="Simula senza modificare il DB")
) -> Dict[str, Any]:
    """
    Sincronizza ENTRAMBE le anagrafiche (farmacie + parafarmacie).

    Esegue in sequenza:
    1. Sync farmacie
    2. Sync parafarmacie

    Ritorna risultati aggregati.
    """
    try:
        from ..services.anagrafica import sync_all

        parsed_date = None
        if target_date:
            try:
                parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(400, "Formato data non valido. Usa YYYY-MM-DD")

        result = sync_all(
            force_download=force,
            target_date=parsed_date,
            dry_run=dry_run
        )

        return {
            "success": result.success,
            "message": result.message,
            "data": {
                "farmacie": _format_sync_result(result.farmacie) if result.farmacie else None,
                "parafarmacie": _format_sync_result(result.parafarmacie) if result.parafarmacie else None,
                "durata_totale_secondi": round(result.durata_totale_secondi, 2)
            }
        }
    except Exception as e:
        raise HTTPException(500, f"Errore sincronizzazione: {str(e)}")


@router.get("/sync/subentri")
async def get_subentri(
    days: int = Query(30, description="Giorni da considerare", ge=1, le=365)
) -> Dict[str, Any]:
    """
    Recupera elenco subentri (cambi P.IVA) recenti.

    Utile per:
    - Verificare farmacie/parafarmacie con cambio proprietario
    - Identificare ordini con lookup obsoleto (LKP-A04)
    - Audit trail modifiche anagrafica
    """
    try:
        from ..services.anagrafica import get_subentri_recenti
        subentri = get_subentri_recenti(days)
        return {
            "success": True,
            "data": {
                "count": len(subentri),
                "days": days,
                "subentri": subentri
            }
        }
    except Exception as e:
        raise HTTPException(500, f"Errore recupero subentri: {str(e)}")
