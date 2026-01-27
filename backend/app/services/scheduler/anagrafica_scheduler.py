# =============================================================================
# SERV.O v11.2 - ANAGRAFICA SCHEDULER
# =============================================================================
# Schedulazione automatica sincronizzazione anagrafica farmacie/parafarmacie
# Orario: ogni giorno alle 06:30, esclusi sabato e domenica
# =============================================================================

import os
from datetime import datetime
from typing import Dict, Any, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ..anagrafica.sync_ministero import sync_all, SyncAllResult
from ..email.sender import EmailSender
from ...database_pg import get_db

# Scheduler globale
_scheduler: Optional[BackgroundScheduler] = None
_last_run: Optional[datetime] = None
_last_result: Optional[Dict[str, Any]] = None


def _format_sync_email(result: SyncAllResult) -> tuple:
    """
    Formatta il risultato della sync per l'email.

    Returns:
        (subject, body_html)
    """
    now = datetime.now()

    # Determina se ci sono novità significative
    has_changes = False
    if result.farmacie:
        has_changes = has_changes or (
            result.farmacie.nuove > 0 or
            result.farmacie.aggiornate > 0 or
            result.farmacie.subentri > 0 or
            result.farmacie.chiuse > 0
        )
    if result.parafarmacie:
        has_changes = has_changes or (
            result.parafarmacie.nuove > 0 or
            result.parafarmacie.aggiornate > 0 or
            result.parafarmacie.subentri > 0 or
            result.parafarmacie.chiuse > 0
        )

    # Subject
    if not result.success:
        subject = f"[SERVO] Sync Anagrafica FALLITA - {now.strftime('%d/%m/%Y')}"
    elif has_changes:
        subject = f"[SERVO] Sync Anagrafica - Aggiornamenti del {now.strftime('%d/%m/%Y')}"
    else:
        subject = f"[SERVO] Sync Anagrafica - Nessun aggiornamento {now.strftime('%d/%m/%Y')}"

    # Body HTML
    body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h2 {{ color: #1e40af; }}
            table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            th {{ background-color: #f3f4f6; }}
            .success {{ color: #059669; }}
            .warning {{ color: #d97706; }}
            .error {{ color: #dc2626; }}
            .highlight {{ background-color: #fef3c7; }}
            .footer {{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 12px; color: #6b7280; }}
        </style>
    </head>
    <body>
        <h2>Sincronizzazione Anagrafica Ministeriale</h2>
        <p><strong>Data:</strong> {now.strftime('%d/%m/%Y %H:%M')}</p>
        <p><strong>Stato:</strong> <span class="{'success' if result.success else 'error'}">
            {'Completata' if result.success else 'FALLITA'}</span></p>
    """

    # Tabella Farmacie
    if result.farmacie:
        f = result.farmacie
        download_status = "Scaricato" if f.downloaded else "Non modificato (304)"
        body += f"""
        <h3>Farmacie</h3>
        <table>
            <tr>
                <th>Metrica</th>
                <th>Valore</th>
            </tr>
            <tr><td>Nuove</td><td class="{'highlight' if f.nuove > 0 else ''}">{f.nuove}</td></tr>
            <tr><td>Aggiornate</td><td class="{'highlight' if f.aggiornate > 0 else ''}">{f.aggiornate}</td></tr>
            <tr><td>Subentri (cambio P.IVA)</td><td class="{'warning highlight' if f.subentri > 0 else ''}">{f.subentri}</td></tr>
            <tr><td>Chiuse</td><td class="{'warning highlight' if f.chiuse > 0 else ''}">{f.chiuse}</td></tr>
            <tr><td>Invariate</td><td>{f.invariate}</td></tr>
            <tr><td>Errori</td><td class="{'error' if f.errori > 0 else ''}">{f.errori}</td></tr>
            <tr><td>Totale JSON</td><td>{f.totale_json}</td></tr>
            <tr><td>Totale DB</td><td><strong>{f.totale_db}</strong></td></tr>
            <tr><td>Durata</td><td>{f.durata_secondi:.1f} sec</td></tr>
        </table>
        <p><small>Fonte: {f.url or 'N/A'} ({download_status})</small></p>
        """

    # Tabella Parafarmacie
    if result.parafarmacie:
        p = result.parafarmacie
        download_status = "Scaricato" if p.downloaded else "Non modificato (304)"
        body += f"""
        <h3>Parafarmacie</h3>
        <table>
            <tr>
                <th>Metrica</th>
                <th>Valore</th>
            </tr>
            <tr><td>Nuove</td><td class="{'highlight' if p.nuove > 0 else ''}">{p.nuove}</td></tr>
            <tr><td>Aggiornate</td><td class="{'highlight' if p.aggiornate > 0 else ''}">{p.aggiornate}</td></tr>
            <tr><td>Subentri (cambio P.IVA)</td><td class="{'warning highlight' if p.subentri > 0 else ''}">{p.subentri}</td></tr>
            <tr><td>Chiuse</td><td class="{'warning highlight' if p.chiuse > 0 else ''}">{p.chiuse}</td></tr>
            <tr><td>Invariate</td><td>{p.invariate}</td></tr>
            <tr><td>Errori</td><td class="{'error' if p.errori > 0 else ''}">{p.errori}</td></tr>
            <tr><td>Totale JSON</td><td>{p.totale_json}</td></tr>
            <tr><td>Totale DB</td><td><strong>{p.totale_db}</strong></td></tr>
            <tr><td>Durata</td><td>{p.durata_secondi:.1f} sec</td></tr>
        </table>
        <p><small>Fonte: {p.url or 'N/A'} ({download_status})</small></p>
        """

    # Note su subentri
    if result.farmacie and result.farmacie.subentri > 0:
        body += f"""
        <div style="background-color: #fef3c7; padding: 15px; border-radius: 5px; margin: 15px 0;">
            <strong>Attenzione:</strong> Rilevati {result.farmacie.subentri} subentri (cambi P.IVA).
            Verificare eventuali anomalie LKP-A04 sugli ordini in corso.
        </div>
        """

    # Avviso errori
    total_errors = (result.farmacie.errori if result.farmacie else 0) + (result.parafarmacie.errori if result.parafarmacie else 0)
    if total_errors > 0:
        body += f"""
        <div style="background-color: #fee2e2; padding: 15px; border-radius: 5px; margin: 15px 0;">
            <strong style="color: #dc2626;">Errori rilevati:</strong> {total_errors} record non processati.
            Verificare i log per dettagli (possibili duplicati o constraint violation).
        </div>
        """

    body += f"""
        <div class="footer">
            <p>Durata totale: {result.durata_totale_secondi:.1f} secondi</p>
            <p>Email generata automaticamente da SERV.O</p>
        </div>
    </body>
    </html>
    """

    return subject, body


def _run_anagrafica_sync():
    """
    Esegue la sincronizzazione anagrafica e invia email di report.
    Chiamato dallo scheduler all'orario configurato.
    """
    global _last_run, _last_result

    _last_run = datetime.now()
    print(f"🏥 [{_last_run.strftime('%Y-%m-%d %H:%M:%S')}] Anagrafica Sync - Avvio schedulato...")

    try:
        # Esegui sync
        result = sync_all(force_download=False)

        _last_result = {
            "success": result.success,
            "message": result.message,
            "timestamp": _last_run.isoformat(),
            "farmacie": {
                "nuove": result.farmacie.nuove if result.farmacie else 0,
                "aggiornate": result.farmacie.aggiornate if result.farmacie else 0,
                "subentri": result.farmacie.subentri if result.farmacie else 0,
                "chiuse": result.farmacie.chiuse if result.farmacie else 0,
            },
            "parafarmacie": {
                "nuove": result.parafarmacie.nuove if result.parafarmacie else 0,
                "aggiornate": result.parafarmacie.aggiornate if result.parafarmacie else 0,
                "subentri": result.parafarmacie.subentri if result.parafarmacie else 0,
                "chiuse": result.parafarmacie.chiuse if result.parafarmacie else 0,
            }
        }

        if result.success:
            print(f"✅ Anagrafica Sync completata: {result.message}")
        else:
            print(f"⚠️ Anagrafica Sync con problemi: {result.message}")

        # Invia email di report
        _send_sync_report_email(result)

    except Exception as e:
        _last_result = {
            "success": False,
            "error": str(e),
            "timestamp": _last_run.isoformat()
        }
        print(f"❌ Errore Anagrafica Sync: {e}")

        # Invia email di errore
        _send_error_email(str(e))


def _send_sync_report_email(result: SyncAllResult):
    """Invia email con il report della sync."""
    # Recupera destinatari da env o config
    # Priorità: SYNC_REPORT_EMAIL > ADMIN_EMAIL > SMTP_USER (email configurata)
    recipients = os.getenv('SYNC_REPORT_EMAIL') or os.getenv('ADMIN_EMAIL') or os.getenv('SMTP_USER', '')

    if not recipients:
        print("⏭️ Nessun destinatario configurato per report sync")
        return

    try:
        db = get_db()
        sender = EmailSender(db)

        if not sender.is_configured(db):
            print("⏭️ Email non configurata, skip invio report")
            return

        subject, body = _format_sync_email(result)

        # Invia a tutti i destinatari (separati da virgola)
        for recipient in recipients.split(','):
            recipient = recipient.strip()
            if recipient:
                email_result = sender.send(
                    to=recipient,
                    subject=subject,
                    body_html=body,
                    email_type='sync_anagrafica_report'
                )
                if email_result['success']:
                    print(f"📧 Report sync inviato a {recipient}")
                else:
                    print(f"⚠️ Errore invio report a {recipient}: {email_result.get('error')}")

        db.commit()

    except Exception as e:
        print(f"⚠️ Errore invio email report: {e}")


def _send_error_email(error_message: str):
    """Invia email in caso di errore critico."""
    recipients = os.getenv('SYNC_REPORT_EMAIL') or os.getenv('ADMIN_EMAIL') or os.getenv('SMTP_USER', '')

    if not recipients:
        return

    try:
        db = get_db()
        sender = EmailSender(db)

        if not sender.is_configured(db):
            return

        now = datetime.now()
        subject = f"[SERVO] ERRORE Sync Anagrafica - {now.strftime('%d/%m/%Y')}"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #dc2626;">Errore Sincronizzazione Anagrafica</h2>
            <p><strong>Data:</strong> {now.strftime('%d/%m/%Y %H:%M')}</p>
            <p><strong>Errore:</strong></p>
            <pre style="background: #fee2e2; padding: 15px; border-radius: 5px;">{error_message}</pre>
            <p>Verificare i log del sistema per maggiori dettagli.</p>
        </body>
        </html>
        """

        for recipient in recipients.split(','):
            recipient = recipient.strip()
            if recipient:
                sender.send(to=recipient, subject=subject, body_html=body, email_type='sync_anagrafica_error')

        db.commit()

    except Exception as e:
        print(f"⚠️ Errore invio email errore: {e}")


def init_anagrafica_scheduler(hour: int = 6, minute: int = 30) -> bool:
    """
    Inizializza lo scheduler per la sync anagrafica.

    Args:
        hour: Ora di esecuzione (default: 6 = 06:00)
        minute: Minuto di esecuzione (default: 30)

    Schedulazione default: ogni giorno alle 06:30, Lun-Ven (esclusi Sab-Dom)

    Returns:
        True se inizializzato con successo
    """
    global _scheduler

    # Verifica se la sync è abilitata
    sync_enabled = os.getenv('ANAGRAFICA_SYNC_ENABLED', 'true').lower() == 'true'
    if not sync_enabled:
        print("⏭️ Anagrafica Scheduler: disabilitato da configurazione (ANAGRAFICA_SYNC_ENABLED=false)")
        return False

    try:
        _scheduler = BackgroundScheduler(
            timezone='Europe/Rome',
            job_defaults={
                'coalesce': True,
                'max_instances': 1
            }
        )

        # Schedulazione: Lun-Ven alle 06:30 (esclusi Sab-Dom)
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            day_of_week='mon-fri',
            timezone='Europe/Rome'
        )

        _scheduler.add_job(
            _run_anagrafica_sync,
            trigger=trigger,
            id='anagrafica_sync',
            name='Anagrafica Ministero Sync',
            replace_existing=True
        )

        _scheduler.start()

        # Calcola prossima esecuzione
        next_run = _scheduler.get_job('anagrafica_sync').next_run_time
        print(f"🏥 Anagrafica Scheduler attivato")
        print(f"   Orario: Lun-Ven alle {hour:02d}:{minute:02d}")
        print(f"   Prossima esecuzione: {next_run.strftime('%Y-%m-%d %H:%M') if next_run else 'N/A'}")

        return True

    except Exception as e:
        print(f"❌ Errore inizializzazione Anagrafica Scheduler: {e}")
        return False


def shutdown_anagrafica_scheduler():
    """Arresta lo scheduler in modo pulito."""
    global _scheduler

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("🏥 Anagrafica Scheduler arrestato")


def get_anagrafica_scheduler_status() -> Dict[str, Any]:
    """
    Ritorna lo stato dello scheduler per l'API.

    Returns:
        Dict con stato scheduler, prossima esecuzione, ultimo risultato
    """
    global _scheduler, _last_run, _last_result

    if not _scheduler:
        return {
            "enabled": False,
            "running": False,
            "reason": "Scheduler non inizializzato"
        }

    job = _scheduler.get_job('anagrafica_sync')

    return {
        "enabled": True,
        "running": _scheduler.running,
        "schedule": "Lun-Ven alle 06:30",
        "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None,
        "last_run": _last_run.isoformat() if _last_run else None,
        "last_result": _last_result
    }


def run_sync_now() -> Dict[str, Any]:
    """
    Esegue la sync immediatamente (per uso manuale/API).

    Returns:
        Dict con risultato della sync
    """
    _run_anagrafica_sync()
    return _last_result or {"success": False, "error": "Nessun risultato"}
