# =============================================================================
# SERV.O v8.2 - SCHEDULER SERVICE
# =============================================================================
# Gestione schedulazione automatica job (mail monitor, sync, etc.)
# =============================================================================

from .mail_scheduler import init_mail_scheduler, shutdown_scheduler, get_scheduler_status

__all__ = ['init_mail_scheduler', 'shutdown_scheduler', 'get_scheduler_status']
