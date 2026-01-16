# =============================================================================
# SERV.O v7.0 - UTILS/DB_HELPERS
# =============================================================================
# Helper per operazioni database
# =============================================================================

from typing import Any, Dict, List, Optional


def rows_to_dicts(rows) -> List[Dict[str, Any]]:
    """
    Convert SQLite/PostgreSQL rows to list of dicts.

    Args:
        rows: Cursor fetchall result

    Returns:
        List of dictionaries
    """
    if not rows:
        return []
    return [dict(row) for row in rows]


def row_to_dict(row) -> Optional[Dict[str, Any]]:
    """
    Convert single row to dict.

    Args:
        row: Row object

    Returns:
        Dictionary or None
    """
    return dict(row) if row else None
