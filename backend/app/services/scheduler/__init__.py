# =============================================================================
# SERV.O v11.2 - SCHEDULER SERVICE
# =============================================================================
# Gestione schedulazione automatica job (mail monitor, anagrafica sync, etc.)
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

# Funzione aggregata per shutdown di tutti gli scheduler
def shutdown_all_schedulers():
    """Arresta tutti gli scheduler attivi."""
    shutdown_mail_scheduler()
    shutdown_anagrafica_scheduler()

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
    # Aggregati
    'shutdown_all_schedulers',
    'shutdown_scheduler',
    'get_scheduler_status',
]
