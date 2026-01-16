# =============================================================================
# SERV.O v9.0 - BACKUP API ROUTER
# =============================================================================
# Endpoints per gestione sistema backup.
# Accessibili solo ad admin.
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from ..auth.dependencies import get_current_user, require_admin
from ..auth.models import UtenteResponse
from ..services.backup import backup_manager


# =============================================================================
# ROUTER
# =============================================================================

router = APIRouter(prefix="/backup", tags=["Backup"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ModuleConfigRequest(BaseModel):
    """Request configurazione modulo."""
    config: Dict[str, Any] = Field(..., description="Configurazione modulo")


class StorageRequest(BaseModel):
    """Request aggiunta storage."""
    name: str = Field(..., min_length=1, max_length=100)
    storage_type: str = Field(..., pattern="^(local|nas|s3|gcs|azure)$")
    path: str = Field(..., min_length=1)
    config: Optional[Dict[str, Any]] = None
    capacity_gb: Optional[int] = None


class BackupExecuteRequest(BaseModel):
    """Request esecuzione backup."""
    triggered_by: str = Field(default="manual", pattern="^(manual|scheduled|pre-migration)$")


class CleanupRequest(BaseModel):
    """Request cleanup."""
    retention_days: Optional[int] = Field(None, ge=1, le=365)


# =============================================================================
# ENDPOINTS - MODULI
# =============================================================================

@router.get("/modules")
async def get_modules(
    user: UtenteResponse = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Lista moduli backup disponibili.

    Returns:
        Lista moduli con stato configurazione
    """
    return backup_manager.get_available_modules()


@router.get("/modules/{module_name}")
async def get_module(
    module_name: str,
    user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Dettaglio singolo modulo.

    Args:
        module_name: Nome modulo (es: 'wal_archive')

    Returns:
        Info modulo con stato e configurazione
    """
    modules = backup_manager.get_available_modules()
    for m in modules:
        if m['name'] == module_name:
            return m

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Modulo '{module_name}' non trovato"
    )


@router.get("/modules/{module_name}/status")
async def get_module_status(
    module_name: str,
    user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Stato corrente modulo (health check dettagliato).

    Args:
        module_name: Nome modulo

    Returns:
        Stato con metriche e health
    """
    module = backup_manager.get_module(module_name)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Modulo '{module_name}' non trovato"
        )

    return module.get_status()


@router.post("/modules/{module_name}/configure")
async def configure_module(
    module_name: str,
    request: ModuleConfigRequest,
    user: UtenteResponse = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Configura modulo backup.

    Richiede ruolo admin.

    Args:
        module_name: Nome modulo
        request: Configurazione da applicare

    Returns:
        Esito configurazione con eventuali istruzioni manuali
    """
    result = backup_manager.configure_module(
        module_name,
        request.config,
        operator_id=user.id_operatore
    )

    if not result['success']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result
        )

    return result


@router.post("/modules/{module_name}/enable")
async def enable_module(
    module_name: str,
    user: UtenteResponse = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Abilita modulo backup (dopo configurazione e test).

    Richiede ruolo admin.

    Args:
        module_name: Nome modulo

    Returns:
        Esito abilitazione
    """
    result = backup_manager.enable_module(
        module_name,
        operator_id=user.id_operatore
    )

    if not result['success']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result['message']
        )

    return result


@router.post("/modules/{module_name}/disable")
async def disable_module(
    module_name: str,
    user: UtenteResponse = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Disabilita modulo backup.

    Richiede ruolo admin.

    Args:
        module_name: Nome modulo

    Returns:
        Esito disabilitazione
    """
    return backup_manager.disable_module(
        module_name,
        operator_id=user.id_operatore
    )


@router.post("/modules/{module_name}/test")
async def test_module(
    module_name: str,
    user: UtenteResponse = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Testa funzionamento modulo.

    Verifica configurazione senza eseguire backup completo.

    Richiede ruolo admin.

    Args:
        module_name: Nome modulo

    Returns:
        Risultato test con dettagli
    """
    return backup_manager.test_module(module_name)


# =============================================================================
# ENDPOINTS - ESECUZIONE BACKUP
# =============================================================================

@router.post("/modules/{module_name}/execute")
async def execute_backup(
    module_name: str,
    request: BackupExecuteRequest = BackupExecuteRequest(),
    user: UtenteResponse = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Esegue backup per modulo.

    Richiede ruolo admin.

    Args:
        module_name: Nome modulo
        request: Opzioni esecuzione

    Returns:
        Risultato backup con file path, dimensione, etc.
    """
    return backup_manager.execute_backup(
        module_name,
        operator_id=user.id_operatore,
        triggered_by=request.triggered_by
    )


@router.post("/modules/{module_name}/cleanup")
async def cleanup_module(
    module_name: str,
    request: CleanupRequest = CleanupRequest(),
    user: UtenteResponse = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Esegue cleanup backup vecchi per modulo.

    Richiede ruolo admin.

    Args:
        module_name: Nome modulo
        request: Override retention se necessario

    Returns:
        Risultato cleanup
    """
    return backup_manager.cleanup_module(
        module_name,
        retention_days=request.retention_days,
        operator_id=user.id_operatore
    )


# =============================================================================
# ENDPOINTS - DASHBOARD E STORICO
# =============================================================================

@router.get("/dashboard")
async def get_dashboard(
    user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Dashboard statistiche backup.

    Returns:
        Statistiche aggregate su moduli, backup, storage
    """
    return backup_manager.get_dashboard_stats()


@router.get("/history")
async def get_history(
    module_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user: UtenteResponse = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Storico backup eseguiti.

    Args:
        module_name: Filtra per modulo (opzionale)
        status: Filtra per stato (opzionale)
        limit: Numero risultati (default 50)
        offset: Offset paginazione

    Returns:
        Lista backup history
    """
    return backup_manager.get_backup_history(
        module_name=module_name,
        status=status,
        limit=limit,
        offset=offset
    )


# =============================================================================
# ENDPOINTS - STORAGE
# =============================================================================

@router.get("/storage")
async def get_storage_locations(
    user: UtenteResponse = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Lista storage locations configurati.

    Returns:
        Lista storage con stato
    """
    return backup_manager.get_storage_locations()


@router.post("/storage")
async def add_storage_location(
    request: StorageRequest,
    user: UtenteResponse = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Aggiunge storage location.

    Richiede ruolo admin.

    Args:
        request: Configurazione storage

    Returns:
        Esito aggiunta
    """
    result = backup_manager.add_storage_location(
        name=request.name,
        storage_type=request.storage_type,
        path=request.path,
        config=request.config,
        capacity_gb=request.capacity_gb,
        operator_id=user.id_operatore
    )

    if not result['success']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result['message']
        )

    return result
