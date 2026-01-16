# =============================================================================
# SERV.O v9.0 - BACKUP MODULE BASE CLASS
# =============================================================================
# Classe astratta per moduli backup.
# Ogni modulo (WAL, Full, Incremental, etc.) eredita da BackupModule.
# =============================================================================

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# =============================================================================
# ENUMS E DATACLASSES
# =============================================================================

class BackupStatus(str, Enum):
    """Stati possibili di un backup."""
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class ModuleStatus(str, Enum):
    """Stati di un modulo backup."""
    NOT_CONFIGURED = "not_configured"
    CONFIGURED = "configured"
    ENABLED = "enabled"
    ERROR = "error"


@dataclass
class BackupResult:
    """Risultato di un'operazione di backup."""
    success: bool
    message: str
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[int] = None
    checksum: Optional[str] = None
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Converte in dizionario."""
        return {
            'success': self.success,
            'message': self.message,
            'file_path': self.file_path,
            'file_size_bytes': self.file_size_bytes,
            'duration_seconds': self.duration_seconds,
            'checksum': self.checksum,
            'error': self.error,
            'details': self.details,
        }


@dataclass
class ValidationResult:
    """Risultato validazione configurazione."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'valid': self.valid,
            'errors': self.errors,
            'warnings': self.warnings,
        }


@dataclass
class ModuleInfo:
    """Informazioni su un modulo backup."""
    name: str
    tier: int
    title: str
    description: str
    enabled: bool
    configured: bool
    status: ModuleStatus
    last_run: Optional[datetime] = None
    last_status: Optional[BackupStatus] = None
    requires_packages: List[str] = field(default_factory=list)
    requires_sudo: bool = False
    config: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# CLASSE BASE MODULO BACKUP
# =============================================================================

class BackupModule(ABC):
    """
    Classe astratta per moduli backup.

    Ogni modulo deve implementare:
    - validate_config(): Valida configurazione
    - configure(): Configura il modulo (crea directory, script, etc.)
    - execute(): Esegue backup
    - test(): Testa funzionamento
    - get_status(): Stato corrente
    - cleanup(): Pulizia vecchi backup

    Attributi:
        name: Nome identificativo modulo (es: 'wal_archive')
        tier: Livello priorità (1-6)
        title: Titolo visualizzato
        description: Descrizione funzionalità
        config: Configurazione corrente
    """

    # Metadati modulo (override nelle sottoclassi)
    name: str = "base"
    tier: int = 0
    title: str = "Base Module"
    description: str = "Modulo base - non usare direttamente"

    # Requisiti
    requires_packages: List[str] = []
    requires_sudo: bool = False

    def __init__(self, config: Dict[str, Any] = None):
        """
        Inizializza modulo con configurazione.

        Args:
            config: Dizionario configurazione modulo
        """
        self.config = config or {}
        self._enabled = False
        self._configured = False

    # =========================================================================
    # METODI ASTRATTI (da implementare)
    # =========================================================================

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Valida configurazione modulo.

        Args:
            config: Configurazione da validare

        Returns:
            ValidationResult con valid=True/False, errors e warnings
        """
        pass

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> BackupResult:
        """
        Configura il modulo.

        Operazioni tipiche:
        - Crea directory necessarie
        - Genera script bash
        - Prepara configurazioni PostgreSQL

        Args:
            config: Configurazione da applicare

        Returns:
            BackupResult con esito e dettagli
        """
        pass

    @abstractmethod
    def execute(self) -> BackupResult:
        """
        Esegue backup.

        Returns:
            BackupResult con esito, path file, dimensione, etc.
        """
        pass

    @abstractmethod
    def test(self) -> BackupResult:
        """
        Testa funzionamento modulo.

        Verifica che tutto sia configurato correttamente
        senza eseguire un backup completo.

        Returns:
            BackupResult con esito test
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Stato corrente modulo.

        Returns:
            Dict con: enabled, healthy, last_backup, etc.
        """
        pass

    @abstractmethod
    def cleanup(self, retention_days: int = None) -> BackupResult:
        """
        Pulizia backup vecchi secondo retention policy.

        Args:
            retention_days: Giorni da mantenere (override config)

        Returns:
            BackupResult con numero file eliminati, spazio liberato
        """
        pass

    # =========================================================================
    # METODI OPZIONALI (override se necessario)
    # =========================================================================

    def generate_scripts(self) -> Dict[str, str]:
        """
        Genera script bash necessari per il modulo.

        Returns:
            Dict con nome_script -> contenuto
        """
        return {}

    def get_required_packages(self) -> List[str]:
        """
        Lista pacchetti Linux necessari.

        Returns:
            Lista nomi pacchetti (es: ['gzip', 'rsync'])
        """
        return self.requires_packages

    def get_manual_steps(self) -> List[str]:
        """
        Istruzioni manuali per admin (es: comandi sudo).

        Returns:
            Lista istruzioni testuali
        """
        return []

    # =========================================================================
    # METODI UTILITY
    # =========================================================================

    def get_info(self) -> ModuleInfo:
        """Ritorna informazioni complete sul modulo."""
        return ModuleInfo(
            name=self.name,
            tier=self.tier,
            title=self.title,
            description=self.description,
            enabled=self._enabled,
            configured=self._configured,
            status=self._get_module_status(),
            requires_packages=self.requires_packages,
            requires_sudo=self.requires_sudo,
            config=self.config,
        )

    def _get_module_status(self) -> ModuleStatus:
        """Determina stato modulo."""
        if self._enabled:
            return ModuleStatus.ENABLED
        if self._configured:
            return ModuleStatus.CONFIGURED
        return ModuleStatus.NOT_CONFIGURED

    def set_enabled(self, enabled: bool):
        """Imposta stato enabled."""
        self._enabled = enabled

    def set_configured(self, configured: bool):
        """Imposta stato configured."""
        self._configured = configured

    def update_config(self, config: Dict[str, Any]):
        """Aggiorna configurazione."""
        self.config.update(config)
