# =============================================================================
# SERV.O v8.1 - ROUTERS PACKAGE
# =============================================================================

from . import upload
from . import ordini
from . import anagrafica
from . import tracciati
from . import anomalie
from . import dashboard
from . import lookup
from . import supervisione
from . import admin
from . import mail
from . import produttivita
from . import listini
from . import backup
from . import email  # v8.1
from . import crm    # v8.1

__all__ = [
    'upload',
    'ordini',
    'anagrafica',
    'tracciati',
    'anomalie',
    'dashboard',
    'lookup',
    'supervisione',
    'admin',
    'mail',
    'produttivita',
    'listini',
    'backup',
    'email',
    'crm',
]
