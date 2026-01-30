# =============================================================================
# SERV.O v11.5 - SCHEDULER SERVICE
# =============================================================================
# Gestione schedulazione automatica job (mail monitor, anagrafica sync, FTP export)
# =============================================================================

from .mail_scheduler import (
    init_mail_scheduler,
    shutdown_scheduler as shutdown_mail_scheduler,
    get_scheduler_status as get_mail_scheduler_status
)

from .anagrafica_scheduler import (
    init_anagrafica_scheduler,
    shutdown_anagrafica_scheduler,
    get_anagrafica_scheduler_status,
    run_sync_now as run_anagrafica_sync_now
)

from .ftp_scheduler import (
    start_ftp_scheduler as init_ftp_scheduler,
    stop_ftp_scheduler as shutdown_ftp_scheduler,
    get_ftp_scheduler_status,
    trigger_ftp_batch_now
)


# Funzione aggregata per shutdown di tutti gli scheduler
def shutdown_all_schedulers():
    """Arresta tutti gli scheduler attivi."""
    shutdown_mail_scheduler()
    shutdown_anagrafica_scheduler()
    shutdown_ftp_scheduler()


# Alias per retrocompatibilità
shutdown_scheduler = shutdown_all_schedulers
get_scheduler_status = get_mail_scheduler_status

__all__ = [
    # Mail Scheduler
    'init_mail_scheduler',
    'shutdown_mail_scheduler',
    'get_mail_scheduler_status',
    # Anagrafica Scheduler
    'init_anagrafica_scheduler',
    'shutdown_anagrafica_scheduler',
    'get_anagrafica_scheduler_status',
    'run_anagrafica_sync_now',
    # FTP Scheduler (v11.5)
    'init_ftp_scheduler',
    'shutdown_ftp_scheduler',
    'get_ftp_scheduler_status',
    'trigger_ftp_batch_now',
    # Aggregati
    'shutdown_all_schedulers',
    'shutdown_scheduler',
    'get_scheduler_status',
]
