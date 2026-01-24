# =============================================================================
# SERV.O v8.2 - TRACKING SERVICE
# =============================================================================
# Sistema di tracking azioni operatore per analisi ML
# =============================================================================

from .tracker import (
    track_action,
    track_action_start,
    track_action_end,
    track_from_user,
    get_session_id,
    TrackingContext,
    Sezione,
    Azione,
)

__all__ = [
    'track_action',
    'track_action_start',
    'track_action_end',
    'track_from_user',
    'get_session_id',
    'TrackingContext',
    'Sezione',
    'Azione',
]
