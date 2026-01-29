# =============================================================================
# SERV.O v11.4 - MAIL SCHEDULER
# =============================================================================
# Schedulazione automatica controllo email
# Orari: ogni ora dalle 8:00 alle 18:00, lunedì-venerdì
# v11.4: Notifica errori via ticket CRM
# =============================================================================

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Scheduler globale
_scheduler: Optional[BackgroundScheduler] = None
_last_run: Optional[datetime] = None
_last_result: Optional[Dict[str, Any]] = None
_consecutive_failures: int = 0  # v11.4: contatore errori consecutivi


def _get_mail_monitor_path() -> Path:
    """Ritorna il path al mail_monitor.py"""
    # In Docker: /mail_monitor/mail_monitor.py
    docker_path = Path("/mail_monitor/mail_monitor.py")
    if docker_path.exists():
        return docker_path

    # In locale: ../../../mail_monitor/mail_monitor.py
    local_path = Path(__file__).parent.parent.parent.parent.parent / "mail_monitor" / "mail_monitor.py"
    return local_path


def _parse_mail_monitor_output(stdout: str) -> Dict[str, int]:
    """
    v11.4: Estrae statistiche dall'output del mail_monitor.
    Cerca pattern: "RIEPILOGO: X processate, Y errori"
    """
    import re
    result = {'processate': 0, 'errori': 0}

    # Pattern: "RIEPILOGO: 3 processate, 0 errori"
    match = re.search(r'RIEPILOGO:\s*(\d+)\s*processate,\s*(\d+)\s*errori', stdout)
    if match:
        result['processate'] = int(match.group(1))
        result['errori'] = int(match.group(2))

    return result


def _notify_new_orders(processate: int, errori: int):
    """
    v11.4: Crea ticket CRM per notificare nuovi ordini arrivati via email.
    """
    try:
        from ...database_pg import get_db
        from ..crm.tickets.commands import crea_ticket_sistema

        db = get_db()

        # Determina priorità in base agli errori
        priorita = 'alta' if errori > 0 else 'normale'

        contenuto = f"""Il monitoraggio email ha scaricato nuovi ordini.

**Riepilogo:**
- PDF processati con successo: {processate}
- Errori: {errori}

Gli ordini sono ora visibili nella sezione Database."""

        if errori > 0:
            contenuto += f"""

**Attenzione:** Si sono verificati {errori} errori durante l'elaborazione.
Verificare i log per dettagli."""

        crea_ticket_sistema(
            db,
            tipo_alert='MONITORAGGIO',
            oggetto=f'Nuovi ordini da email ({processate} PDF)',
            contenuto=contenuto,
            priorita=priorita,
            contesto={
                'pagina_origine': 'scheduler',
                'dati_extra': {
                    'PDF processati': processate,
                    'Errori': errori,
                    'Data sync': _last_run.strftime('%d/%m/%Y %H:%M') if _last_run else 'N/A'
                }
            }
        )
        print(f"📬 Ticket creato: {processate} nuovi ordini da email")
    except Exception as e:
        print(f"⚠️ Impossibile creare ticket per nuovi ordini: {e}")


def _notify_mail_failure(error_msg: str):
    """
    v11.4: Crea ticket CRM per notificare errore mail monitor.
    Chiamato dopo 3 errori consecutivi.
    """
    try:
        from ...database_pg import get_db
        from ..crm.tickets.commands import crea_ticket_sistema

        db = get_db()
        crea_ticket_sistema(
            db,
            tipo_alert='MONITORAGGIO',
            oggetto='Errore sincronizzazione email',
            contenuto=f"""Il sistema di monitoraggio email ha riscontrato errori ripetuti.

**Ultimo errore:** {error_msg}

**Azione richiesta:**
Verificare la connessione al server email e le credenziali IMAP.""",
            priorita='alta',
            contesto={
                'pagina_origine': 'scheduler',
                'dati_extra': {
                    'Errori consecutivi': _consecutive_failures,
                    'Ultimo tentativo': _last_run.isoformat() if _last_run else 'N/A'
                }
            }
        )
    except Exception as e:
        print(f"⚠️ Impossibile creare ticket per errore mail: {e}")


def _run_mail_sync():
    """
    Esegue il mail_monitor.py per sincronizzare le email.
    Chiamato dallo scheduler agli orari configurati.
    """
    global _last_run, _last_result, _consecutive_failures

    _last_run = datetime.now()
    print(f"📧 [{_last_run.strftime('%Y-%m-%d %H:%M:%S')}] Mail Monitor - Avvio schedulato...")

    mail_monitor_path = _get_mail_monitor_path()

    if not mail_monitor_path.exists():
        _last_result = {
            "success": False,
            "error": f"mail_monitor.py non trovato: {mail_monitor_path}",
            "timestamp": _last_run.isoformat()
        }
        print(f"❌ {_last_result['error']}")
        _consecutive_failures += 1
        if _consecutive_failures >= 3:
            _notify_mail_failure(_last_result['error'])
        return

    try:
        result = subprocess.run(
            [sys.executable, str(mail_monitor_path)],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minuti timeout
            cwd=str(mail_monitor_path.parent)
        )

        _last_result = {
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
            "timestamp": _last_run.isoformat()
        }

        if result.returncode == 0:
            print(f"✅ Mail Monitor completato con successo")
            _consecutive_failures = 0  # Reset contatore

            # v11.4: Notifica nuovi ordini se ci sono PDF processati
            stats = _parse_mail_monitor_output(result.stdout or "")
            if stats['processate'] > 0:
                _notify_new_orders(stats['processate'], stats['errori'])
        else:
            print(f"⚠️ Mail Monitor terminato con codice {result.returncode}")
            if result.stderr:
                print(f"   Errore: {result.stderr[:200]}")
            _consecutive_failures += 1
            if _consecutive_failures >= 3:
                _notify_mail_failure(result.stderr[:500] if result.stderr else f"Exit code {result.returncode}")

    except subprocess.TimeoutExpired:
        _last_result = {
            "success": False,
            "error": "Timeout: esecuzione interrotta dopo 5 minuti",
            "timestamp": _last_run.isoformat()
        }
        print(f"❌ {_last_result['error']}")
        _consecutive_failures += 1
        if _consecutive_failures >= 3:
            _notify_mail_failure(_last_result['error'])

    except Exception as e:
        _last_result = {
            "success": False,
            "error": str(e),
            "timestamp": _last_run.isoformat()
        }
        print(f"❌ Errore Mail Monitor: {e}")
        _consecutive_failures += 1
        if _consecutive_failures >= 3:
            _notify_mail_failure(str(e))


def init_mail_scheduler() -> bool:
    """
    Inizializza lo scheduler per il mail monitor.

    Schedulazione: ogni ora dalle 8:00 alle 18:00, lunedì-venerdì

    Returns:
        True se inizializzato con successo
    """
    global _scheduler

    # Verifica se le credenziali email sono configurate
    smtp_user = os.getenv('SMTP_USER', '') or os.getenv('IMAP_USER', '')
    if not smtp_user:
        print("⏭️ Mail Scheduler: credenziali email non configurate, scheduler disabilitato")
        return False

    try:
        _scheduler = BackgroundScheduler(
            timezone='Europe/Rome',
            job_defaults={
                'coalesce': True,  # Se perde un job, ne esegue solo uno
                'max_instances': 1  # Max 1 istanza contemporanea
            }
        )

        # Schedulazione: ogni ora dalle 8 alle 18, lun-ven
        # hour='8-18' significa alle ore 8,9,10,11,12,13,14,15,16,17,18
        # day_of_week='mon-fri' significa lunedì-venerdì
        trigger = CronTrigger(
            hour='8-18',
            minute=0,
            day_of_week='mon-fri',
            timezone='Europe/Rome'
        )

        _scheduler.add_job(
            _run_mail_sync,
            trigger=trigger,
            id='mail_monitor',
            name='Mail Monitor Sync',
            replace_existing=True
        )

        _scheduler.start()

        # Calcola prossima esecuzione
        next_run = _scheduler.get_job('mail_monitor').next_run_time
        print(f"📧 Mail Scheduler attivato")
        print(f"   Orari: 08:00-18:00, Lun-Ven")
        print(f"   Prossima esecuzione: {next_run.strftime('%Y-%m-%d %H:%M') if next_run else 'N/A'}")

        return True

    except Exception as e:
        print(f"❌ Errore inizializzazione Mail Scheduler: {e}")
        return False


def shutdown_scheduler():
    """Arresta lo scheduler in modo pulito."""
    global _scheduler

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("📧 Mail Scheduler arrestato")


def get_scheduler_status() -> Dict[str, Any]:
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

    job = _scheduler.get_job('mail_monitor')

    return {
        "enabled": True,
        "running": _scheduler.running,
        "schedule": "Ogni ora 08:00-18:00, Lun-Ven",
        "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None,
        "last_run": _last_run.isoformat() if _last_run else None,
        "last_result": _last_result
    }
