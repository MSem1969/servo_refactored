# =============================================================================
# SERV.O v9.0 - WAL ARCHIVE MODULE
# =============================================================================
# TIER 1: Archiviazione continua WAL segments per Point-in-Time Recovery.
# =============================================================================

import os
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List

from .base import BackupModule, BackupResult, ValidationResult


class WALArchiveModule(BackupModule):
    """
    Modulo WAL Archiving per PostgreSQL.

    Configura l'archiviazione automatica dei WAL segments per permettere
    Point-in-Time Recovery (PITR).

    Configurazione richiesta:
        archive_dir: Directory dove archiviare i WAL
        compression: Comprimere con gzip (default: True)
        retention_hours: Ore da mantenere (default: 48)

    Note:
        - Richiede modifica postgresql.conf (sudo)
        - Richiede restart PostgreSQL dopo configurazione
    """

    # Metadati modulo
    name = "wal_archive"
    tier = 1
    title = "WAL Archiving"
    description = "Archiviazione continua WAL segments per Point-in-Time Recovery (PITR). Permette di recuperare il database a qualsiasi momento nel tempo."

    # Requisiti
    requires_packages = ["gzip"]
    requires_sudo = True

    # Configurazione default
    DEFAULT_CONFIG = {
        'archive_dir': '/backup/postgresql/wal_archive',
        'compression': True,
        'retention_hours': 48,
    }

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        # Merge con default
        for key, value in self.DEFAULT_CONFIG.items():
            if key not in self.config:
                self.config[key] = value

    # =========================================================================
    # IMPLEMENTAZIONE METODI ASTRATTI
    # =========================================================================

    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Valida configurazione WAL archiving."""
        errors = []
        warnings = []

        # Verifica archive_dir
        archive_dir = config.get('archive_dir')
        if not archive_dir:
            errors.append("archive_dir è obbligatorio")
        elif not archive_dir.startswith('/'):
            errors.append("archive_dir deve essere un path assoluto")

        # Verifica retention
        retention = config.get('retention_hours', 48)
        if not isinstance(retention, int) or retention < 1:
            errors.append("retention_hours deve essere un intero >= 1")
        elif retention < 24:
            warnings.append(f"retention_hours={retention} è molto basso. Consigliato almeno 24 ore.")

        # Verifica spazio disco (se directory esiste)
        if archive_dir and Path(archive_dir).exists():
            try:
                stat = os.statvfs(archive_dir)
                free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
                if free_gb < 1:
                    errors.append(f"Spazio insufficiente: {free_gb:.1f} GB (minimo 1 GB)")
                elif free_gb < 5:
                    warnings.append(f"Spazio disponibile basso: {free_gb:.1f} GB (consigliato >= 5 GB)")
            except OSError as e:
                warnings.append(f"Impossibile verificare spazio disco: {e}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def configure(self, config: Dict[str, Any]) -> BackupResult:
        """
        Configura WAL archiving.

        Steps:
        1. Valida configurazione
        2. Genera script archive_wal.sh
        3. Restituisce istruzioni per admin
        """
        # Valida prima
        validation = self.validate_config(config)
        if not validation.valid:
            return BackupResult(
                success=False,
                message="Configurazione non valida",
                error="; ".join(validation.errors),
                details={'validation': validation.to_dict()}
            )

        self.update_config(config)
        archive_dir = self.config['archive_dir']
        compression = self.config.get('compression', True)

        # Genera script
        scripts = self.generate_scripts()
        script_content = scripts.get('archive_wal.sh', '')

        # Istruzioni manuali per admin
        manual_steps = [
            f"# 1. Crea directory archivio",
            f"sudo mkdir -p {archive_dir}",
            f"sudo chown postgres:postgres {archive_dir}",
            f"sudo chmod 700 {archive_dir}",
            "",
            f"# 2. Crea script di archiviazione",
            f"sudo tee /usr/local/bin/archive_wal.sh << 'EOFSCRIPT'",
            script_content,
            "EOFSCRIPT",
            f"sudo chmod +x /usr/local/bin/archive_wal.sh",
            "",
            f"# 3. Configura PostgreSQL",
            f"sudo nano /etc/postgresql/15/main/postgresql.conf",
            "",
            "# Aggiungi/modifica queste righe:",
            "archive_mode = on",
            f"archive_command = '/usr/local/bin/archive_wal.sh %p %f'",
            "wal_level = replica",
            "",
            f"# 4. Riavvia PostgreSQL",
            f"sudo systemctl restart postgresql",
            "",
            f"# 5. Verifica configurazione",
            f"sudo -u postgres psql -c \"SHOW archive_mode;\"",
            f"sudo -u postgres psql -c \"SHOW archive_command;\"",
        ]

        self.set_configured(True)

        return BackupResult(
            success=True,
            message="Configurazione WAL archiving generata",
            details={
                'archive_dir': archive_dir,
                'compression': compression,
                'script_generated': True,
                'requires_sudo': True,
                'manual_steps': manual_steps,
            }
        )

    def execute(self) -> BackupResult:
        """
        Forza switch WAL per creare nuovo segment da archiviare.

        Utile per test o per forzare archiviazione prima di manutenzione.
        """
        start_time = datetime.now()

        try:
            result = subprocess.run(
                ["sudo", "-u", "postgres", "psql", "-d", "to_extractor_v2",
                 "-t", "-c", "SELECT pg_switch_wal();"],
                capture_output=True,
                text=True,
                timeout=30
            )

            duration = int((datetime.now() - start_time).total_seconds())

            if result.returncode != 0:
                return BackupResult(
                    success=False,
                    message="Errore switch WAL",
                    error=result.stderr,
                    duration_seconds=duration
                )

            wal_position = result.stdout.strip()

            return BackupResult(
                success=True,
                message=f"WAL switch completato: {wal_position}",
                duration_seconds=duration,
                details={'wal_position': wal_position}
            )

        except subprocess.TimeoutExpired:
            return BackupResult(
                success=False,
                message="Timeout switch WAL",
                error="Comando scaduto dopo 30 secondi"
            )
        except Exception as e:
            return BackupResult(
                success=False,
                message="Errore esecuzione switch WAL",
                error=str(e)
            )

    def test(self) -> BackupResult:
        """
        Testa configurazione WAL archiving.

        Verifica:
        1. archive_mode = on
        2. archive_command configurato
        3. Directory archivio accessibile
        4. WAL recenti presenti
        """
        results = {
            'archive_mode': False,
            'archive_command': False,
            'archive_dir_exists': False,
            'archive_dir_writable': False,
            'wal_files_count': 0,
            'recent_wal_files': 0,
        }
        errors = []

        # 1. Verifica archive_mode
        try:
            result = subprocess.run(
                ["sudo", "-u", "postgres", "psql", "-d", "to_extractor_v2",
                 "-t", "-c", "SHOW archive_mode;"],
                capture_output=True,
                text=True,
                timeout=10
            )
            archive_mode = result.stdout.strip()
            results['archive_mode'] = archive_mode == 'on'
            results['archive_mode_value'] = archive_mode

            if archive_mode != 'on':
                errors.append(f"archive_mode = '{archive_mode}' (deve essere 'on')")

        except Exception as e:
            errors.append(f"Errore verifica archive_mode: {e}")

        # 2. Verifica archive_command
        try:
            result = subprocess.run(
                ["sudo", "-u", "postgres", "psql", "-d", "to_extractor_v2",
                 "-t", "-c", "SHOW archive_command;"],
                capture_output=True,
                text=True,
                timeout=10
            )
            archive_command = result.stdout.strip()
            results['archive_command'] = bool(archive_command and archive_command != '(disabled)')
            results['archive_command_value'] = archive_command

            if not results['archive_command']:
                errors.append("archive_command non configurato")

        except Exception as e:
            errors.append(f"Errore verifica archive_command: {e}")

        # 3. Verifica directory archivio
        archive_dir = Path(self.config.get('archive_dir', '/backup/postgresql/wal_archive'))

        if archive_dir.exists():
            results['archive_dir_exists'] = True

            # Verifica scrittura
            try:
                test_file = archive_dir / '.write_test'
                test_file.touch()
                test_file.unlink()
                results['archive_dir_writable'] = True
            except (PermissionError, OSError):
                errors.append(f"Directory {archive_dir} non scrivibile")

            # Conta WAL files
            compression = self.config.get('compression', True)
            pattern = '*.gz' if compression else '0*'
            wal_files = list(archive_dir.glob(pattern))
            results['wal_files_count'] = len(wal_files)

            # WAL ultimi 60 minuti
            cutoff = datetime.now().timestamp() - 3600
            recent = [f for f in wal_files if f.stat().st_mtime > cutoff]
            results['recent_wal_files'] = len(recent)

        else:
            errors.append(f"Directory {archive_dir} non esiste")

        # Determina successo
        success = (
            results['archive_mode'] and
            results['archive_command'] and
            results['archive_dir_exists'] and
            results['archive_dir_writable']
        )

        if success:
            message = f"WAL archiving configurato correttamente. File archiviati: {results['wal_files_count']}"
        else:
            message = "WAL archiving non configurato correttamente"

        return BackupResult(
            success=success,
            message=message,
            error="; ".join(errors) if errors else None,
            details=results
        )

    def get_status(self) -> Dict[str, Any]:
        """Stato corrente WAL archiving."""
        archive_dir = Path(self.config.get('archive_dir', '/backup/postgresql/wal_archive'))

        status = {
            'enabled': self._enabled,
            'configured': self._configured,
            'healthy': False,
            'archive_dir': str(archive_dir),
            'archive_dir_exists': archive_dir.exists(),
            'wal_count': 0,
            'wal_count_24h': 0,
            'total_size_mb': 0,
            'oldest_wal': None,
            'newest_wal': None,
        }

        if not archive_dir.exists():
            return status

        # Conta e analizza WAL
        compression = self.config.get('compression', True)
        pattern = '*.gz' if compression else '0*'
        wal_files = list(archive_dir.glob(pattern))

        if wal_files:
            status['wal_count'] = len(wal_files)

            # Dimensione totale
            total_bytes = sum(f.stat().st_size for f in wal_files)
            status['total_size_mb'] = round(total_bytes / (1024 * 1024), 2)

            # Timestamps
            mtimes = [f.stat().st_mtime for f in wal_files]
            status['oldest_wal'] = datetime.fromtimestamp(min(mtimes)).isoformat()
            status['newest_wal'] = datetime.fromtimestamp(max(mtimes)).isoformat()

            # WAL ultime 24h
            cutoff_24h = datetime.now().timestamp() - 86400
            recent_24h = [t for t in mtimes if t > cutoff_24h]
            status['wal_count_24h'] = len(recent_24h)

            # Healthy se ci sono WAL recenti (ultimo 1h)
            newest = max(mtimes)
            status['healthy'] = (datetime.now().timestamp() - newest) < 3600

        return status

    def cleanup(self, retention_hours: int = None) -> BackupResult:
        """Rimuove WAL più vecchi di retention_hours."""
        retention = retention_hours or self.config.get('retention_hours', 48)
        archive_dir = Path(self.config.get('archive_dir', '/backup/postgresql/wal_archive'))

        if not archive_dir.exists():
            return BackupResult(
                success=False,
                message="Directory archivio non esiste",
                error=f"Path: {archive_dir}"
            )

        compression = self.config.get('compression', True)
        pattern = '*.gz' if compression else '0*'
        wal_files = list(archive_dir.glob(pattern))

        cutoff = datetime.now().timestamp() - (retention * 3600)
        deleted = []
        freed_bytes = 0
        errors = []

        for wal_file in wal_files:
            try:
                if wal_file.stat().st_mtime < cutoff:
                    size = wal_file.stat().st_size
                    wal_file.unlink()
                    deleted.append(wal_file.name)
                    freed_bytes += size
            except OSError as e:
                errors.append(f"{wal_file.name}: {e}")

        freed_mb = round(freed_bytes / (1024 * 1024), 2)

        return BackupResult(
            success=len(errors) == 0,
            message=f"Cleanup completato: {len(deleted)} file eliminati, {freed_mb} MB liberati",
            error="; ".join(errors) if errors else None,
            details={
                'deleted_count': len(deleted),
                'deleted_files': deleted[:20],  # Max 20 per non esplodere
                'freed_mb': freed_mb,
                'retention_hours': retention,
            }
        )

    # =========================================================================
    # SCRIPT GENERATION
    # =========================================================================

    def generate_scripts(self) -> Dict[str, str]:
        """Genera script archive_wal.sh."""
        archive_dir = self.config.get('archive_dir', '/backup/postgresql/wal_archive')
        compression = self.config.get('compression', True)

        if compression:
            archive_cmd = f'gzip -c "$WAL_PATH" > "$ARCHIVE_DIR/$WAL_FILENAME.gz"'
        else:
            archive_cmd = f'cp "$WAL_PATH" "$ARCHIVE_DIR/$WAL_FILENAME"'

        script = f'''#!/bin/bash
# =============================================================================
# archive_wal.sh - Generato da SERV.O v9.0
# =============================================================================
# Script per archiviazione WAL PostgreSQL.
# Chiamato da archive_command in postgresql.conf
# =============================================================================

ARCHIVE_DIR="{archive_dir}"
WAL_PATH="$1"        # %p - path completo WAL
WAL_FILENAME="$2"    # %f - nome file WAL

# Crea directory se non esiste
mkdir -p "$ARCHIVE_DIR"

# Archivia WAL
{archive_cmd}

# Verifica successo
if [ $? -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - OK: $WAL_FILENAME" >> /var/log/postgresql/wal_archive.log
    exit 0
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERRORE: $WAL_FILENAME" >> /var/log/postgresql/wal_archive.log
    exit 1
fi
'''
        return {'archive_wal.sh': script}

    def get_manual_steps(self) -> List[str]:
        """Istruzioni per configurazione manuale."""
        archive_dir = self.config.get('archive_dir', '/backup/postgresql/wal_archive')

        return [
            f"1. Crea directory: sudo mkdir -p {archive_dir}",
            f"2. Permessi: sudo chown postgres:postgres {archive_dir}",
            f"3. Modifica /etc/postgresql/15/main/postgresql.conf:",
            f"   archive_mode = on",
            f"   archive_command = '/usr/local/bin/archive_wal.sh %p %f'",
            f"   wal_level = replica",
            f"4. Riavvia PostgreSQL: sudo systemctl restart postgresql",
        ]
