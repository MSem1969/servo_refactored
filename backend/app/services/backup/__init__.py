# =============================================================================
# SERV.O v9.0 - BACKUP SERVICES
# =============================================================================
# Sistema di backup modulare e configurabile.
# =============================================================================

from .manager import BackupManager, backup_manager

__all__ = [
    'BackupManager',
    'backup_manager',
]
