# =============================================================================
# SERV.O v7.0 - UTILS/RESPONSE
# =============================================================================
# Builder per risposte API standardizzate
# =============================================================================

from typing import Any, Dict, List


def success_response(data: Any = None, message: str = None, **kwargs) -> Dict[str, Any]:
    """
    Build standard success response.

    Args:
        data: Response payload
        message: Optional message
        **kwargs: Additional fields (count, pagination, etc.)

    Returns:
        Standardized success response dict
    """
    response = {"success": True}
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    response.update(kwargs)
    return response


def error_response(message: str, code: str = None) -> Dict[str, Any]:
    """
    Build standard error response.

    Args:
        message: Error message
        code: Optional error code

    Returns:
        Standardized error response dict
    """
    response = {"success": False, "error": message}
    if code:
        response["code"] = code
    return response


def paginated_response(
    items: List[Any],
    total: int,
    limit: int,
    offset: int
) -> Dict[str, Any]:
    """
    Build paginated response.

    Args:
        items: List of items
        total: Total count
        limit: Page size
        offset: Current offset

    Returns:
        Response with pagination metadata
    """
    pages = (total + limit - 1) // limit if limit > 0 else 1
    return {
        "success": True,
        "data": items,
        "pagination": {
            "totale": total,
            "limit": limit,
            "offset": offset,
            "pages": pages
        }
    }


def batch_result(success_count: int, total: int, errors: List[str] = None) -> Dict[str, Any]:
    """
    Build batch operation result.

    Args:
        success_count: Number of successful operations
        total: Total attempted
        errors: List of error messages

    Returns:
        Batch operation result dict
    """
    result = {
        "success": True,
        "data": {
            "completati": success_count,
            "totale": total,
            "falliti": total - success_count
        }
    }
    if errors:
        result["data"]["errori"] = errors
    return result
