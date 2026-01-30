# =============================================================================
# SERV.O v11.5 - FTP SCHEDULER
# =============================================================================
# Scheduler per invio batch tracciati via FTP ogni 10 minuti
# =============================================================================

import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

from ...database_pg import get_db, log_operation

# Logger
logger = logging.getLogger('ftp_scheduler')
logger.setLevel(logging.INFO)

# Scheduler singleton
_scheduler: Optional[BackgroundScheduler] = None
_is_running = False


def _ftp_batch_job():
    """
    Job eseguito ogni 10 minuti per invio tracciati FTP.

    - Cerca esportazioni PENDING/RETRY
    - Invia coppie TO_T + TO_D
    - Gestisce retry e alert
    """
    from ..ftp.sender import invia_tracciati_batch

    try:
        logger.info(f"[{datetime.now()}] Avvio batch FTP...")

        result = invia_tracciati_batch()

        if result['sent'] > 0 or result['failed'] > 0:
            logger.info(
                f"Batch FTP completato: {result['sent']} inviati, "
                f"{result['failed']} falliti, {result['skipped']} skippati"
            )

        return result

    except Exception as e:
        logger.error(f"Errore batch FTP: {e}")
        log_operation('FTP_SCHEDULER_ERROR', 'scheduler', 0, str(e), operatore='SCHEDULER')
        raise


def _job_listener(event):
    """Listener per eventi job."""
    if event.exception:
        logger.error(f"Job FTP fallito: {event.exception}")
    else:
        logger.debug(f"Job FTP completato")


def start_ftp_scheduler():
    """
    Avvia lo scheduler FTP.

    Configura job ogni 10 minuti (configurabile da DB).
    """
    global _scheduler, _is_running

    if _is_running:
        logger.warning("FTP Scheduler gia in esecuzione")
        return

    try:
        # Verifica configurazione
        db = get_db()
        ftp_config = db.execute("""
            SELECT batch_enabled, batch_intervallo_minuti
            FROM ftp_config WHERE ftp_enabled = TRUE LIMIT 1
        """).fetchone()

        if not ftp_config or not ftp_config['batch_enabled']:
            logger.info("FTP batch non abilitato in configurazione")
            return

        intervallo = ftp_config['batch_intervallo_minuti'] or 10

        # Crea scheduler
        _scheduler = BackgroundScheduler(
            timezone='Europe/Rome',
            job_defaults={
                'coalesce': True,  # Unifica job persi
                'max_instances': 1,  # Max 1 istanza concorrente
                'misfire_grace_time': 60  # 1 minuto di tolleranza
            }
        )

        # Aggiungi listener
        _scheduler.add_listener(_job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

        # Aggiungi job batch FTP
        _scheduler.add_job(
            _ftp_batch_job,
            trigger=IntervalTrigger(minutes=intervallo),
            id='ftp_batch',
            name='FTP Batch Export',
            replace_existing=True
        )

        # Avvia scheduler
        _scheduler.start()
        _is_running = True

        logger.info(f"FTP Scheduler avviato (intervallo: {intervallo} minuti)")
        log_operation('FTP_SCHEDULER_START', 'scheduler', 0,
                     f'Scheduler avviato, intervallo {intervallo} min', operatore='SYSTEM')

    except Exception as e:
        logger.error(f"Errore avvio FTP Scheduler: {e}")
        raise


def stop_ftp_scheduler():
    """Ferma lo scheduler FTP."""
    global _scheduler, _is_running

    if _scheduler and _is_running:
        _scheduler.shutdown(wait=False)
        _is_running = False
        logger.info("FTP Scheduler fermato")
        log_operation('FTP_SCHEDULER_STOP', 'scheduler', 0,
                     'Scheduler fermato', operatore='SYSTEM')


def get_ftp_scheduler_status() -> dict:
    """Restituisce stato dello scheduler FTP."""
    global _scheduler, _is_running

    if not _scheduler or not _is_running:
        return {'running': False, 'jobs': []}

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None
        })

    return {
        'running': _is_running,
        'jobs': jobs
    }


def trigger_ftp_batch_now() -> dict:
    """
    Esegue il batch FTP immediatamente (manualmente).

    Returns:
        Risultato del batch
    """
    logger.info("Trigger manuale batch FTP")
    return _ftp_batch_job()
