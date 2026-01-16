# =============================================================================
# SERV.O v9.0 - FULL BACKUP MODULE
# =============================================================================
# TIER 2: Backup completo periodico con pg_dump.
# =============================================================================

import os
import subprocess
import hashlib
import gzip
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List

from .base import BackupModule, BackupResult, ValidationResult


class FullBackupModule(BackupModule):
    """
    Modulo backup completo PostgreSQL con pg_dump.

    Crea dump completi del database compresso con gzip.
    Naming: to_extractor_YYYYMMDD_HHMMSS.sql.gz

    Configurazione richiesta:
        backup_dir: Directory dove salvare i backup
        compression: Comprimere con gzip (default: True)
        retention_days: Giorni da mantenere (default: 7)
        format: Formato dump ('custom', 'plain', 'directory') - default: custom
    """

    # Metadati modulo
    name = "full_backup"
    tier = 2
    title = "Backup Completo"
    description = "Backup full periodico con pg_dump. Crea un dump completo del database compresso."

    # Requisiti
    requires_packages = ["postgresql-client", "gzip"]
    requires_sudo = False  # pg_dump non richiede sudo se l'utente ha permessi

    # Configurazione default
    DEFAULT_CONFIG = {
        'backup_dir': '/backup/postgresql/full',
        'compression': True,
        'retention_days': 7,
        'format': 'custom',  # 'custom' = pg_dump -Fc (più efficiente per restore)
        'database': 'to_extractor_v2',
        'user': 'to_extractor_user',
        'host': '127.0.0.1',
        'port': 5432,
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
        """Valida configurazione backup completo."""
        errors = []
        warnings = []

        # Verifica backup_dir
        backup_dir = config.get('backup_dir')
        if not backup_dir:
            errors.append("backup_dir è obbligatorio")
        elif not backup_dir.startswith('/'):
            errors.append("backup_dir deve essere un path assoluto")

        # Verifica retention
        retention = config.get('retention_days', 7)
        if not isinstance(retention, int) or retention < 1:
            errors.append("retention_days deve essere un intero >= 1")
        elif retention > 30:
            warnings.append(f"retention_days={retention} è elevato. Verifica spazio disco.")

        # Verifica formato
        fmt = config.get('format', 'custom')
        if fmt not in ('custom', 'plain', 'directory'):
            errors.append(f"format '{fmt}' non valido. Usa: custom, plain, directory")

        # Verifica spazio disco
        if backup_dir and Path(backup_dir).exists():
            try:
                stat = os.statvfs(backup_dir)
                free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
                if free_gb < 1:
                    errors.append(f"Spazio insufficiente: {free_gb:.1f} GB (minimo 1 GB)")
                elif free_gb < 5:
                    warnings.append(f"Spazio disponibile basso: {free_gb:.1f} GB")
            except OSError as e:
                warnings.append(f"Impossibile verificare spazio disco: {e}")

        # Verifica database
        database = config.get('database', 'to_extractor_v2')
        if not database:
            errors.append("database è obbligatorio")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def configure(self, config: Dict[str, Any]) -> BackupResult:
        """
        Configura backup completo.

        Steps:
        1. Valida configurazione
        2. Crea directory backup
        3. Verifica connessione database
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
        backup_dir = Path(self.config['backup_dir'])

        # Crea directory se non esiste
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            return BackupResult(
                success=False,
                message="Impossibile creare directory backup",
                error=f"Permessi insufficienti per {backup_dir}",
                details={
                    'manual_steps': [
                        f"sudo mkdir -p {backup_dir}",
                        f"sudo chown $USER:$USER {backup_dir}",
                    ]
                }
            )

        # Verifica connessione database
        test_result = self._test_db_connection()
        if not test_result['success']:
            return BackupResult(
                success=False,
                message="Impossibile connettersi al database",
                error=test_result.get('error', 'Errore sconosciuto'),
            )

        self.set_configured(True)

        return BackupResult(
            success=True,
            message="Configurazione backup completo OK",
            details={
                'backup_dir': str(backup_dir),
                'format': self.config['format'],
                'compression': self.config['compression'],
                'retention_days': self.config['retention_days'],
                'database': self.config['database'],
            }
        )

    def execute(self) -> BackupResult:
        """
        Esegue backup completo con pg_dump.

        Returns:
            BackupResult con path file, dimensione, checksum
        """
        start_time = datetime.now()
        backup_dir = Path(self.config['backup_dir'])

        # Crea directory se non esiste
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Nome file con timestamp
        timestamp = start_time.strftime('%Y%m%d_%H%M%S')
        fmt = self.config['format']
        compression = self.config['compression']

        if fmt == 'custom':
            extension = '.dump'
        elif fmt == 'directory':
            extension = ''
        else:
            extension = '.sql'

        if compression and fmt != 'custom':  # custom già compresso
            extension += '.gz'

        filename = f"to_extractor_{timestamp}{extension}"
        file_path = backup_dir / filename

        # Costruisci comando pg_dump
        cmd = self._build_pg_dump_command(file_path, fmt, compression)

        try:
            # Esegui pg_dump
            env = os.environ.copy()
            # Leggi password da .env se disponibile
            # Path: modules -> backup -> services -> app -> backend/.env
            env_file = Path(__file__).parent.parent.parent.parent.parent / '.env'
            if env_file.exists():
                with open(env_file) as f:
                    for line in f:
                        if line.startswith('PG_PASSWORD='):
                            env['PGPASSWORD'] = line.split('=', 1)[1].strip()
                            break

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 ora max
                env=env
            )

            duration = int((datetime.now() - start_time).total_seconds())

            if result.returncode != 0:
                return BackupResult(
                    success=False,
                    message="Errore pg_dump",
                    error=result.stderr,
                    duration_seconds=duration
                )

            # Verifica file creato
            if not file_path.exists() and fmt != 'directory':
                return BackupResult(
                    success=False,
                    message="File backup non creato",
                    error="pg_dump completato ma file non trovato",
                    duration_seconds=duration
                )

            # Calcola dimensione e checksum
            if fmt == 'directory':
                file_size = sum(f.stat().st_size for f in file_path.rglob('*') if f.is_file())
                checksum = None
            else:
                file_size = file_path.stat().st_size
                checksum = self._calculate_checksum(file_path)

            return BackupResult(
                success=True,
                message=f"Backup completato: {filename}",
                file_path=str(file_path),
                file_size_bytes=file_size,
                duration_seconds=duration,
                checksum=checksum,
                details={
                    'format': fmt,
                    'compression': compression,
                    'database': self.config['database'],
                }
            )

        except subprocess.TimeoutExpired:
            return BackupResult(
                success=False,
                message="Timeout backup",
                error="pg_dump scaduto dopo 1 ora"
            )
        except Exception as e:
            return BackupResult(
                success=False,
                message="Errore esecuzione backup",
                error=str(e)
            )

    def test(self) -> BackupResult:
        """
        Testa configurazione backup completo.

        Verifica:
        1. Connessione database
        2. Directory backup accessibile
        3. pg_dump disponibile
        4. Backup recente presente (se già eseguito)
        """
        results = {
            'db_connection': False,
            'backup_dir_exists': False,
            'backup_dir_writable': False,
            'pg_dump_available': False,
            'recent_backup_exists': False,
            'backup_count': 0,
            'total_size_mb': 0,
        }
        errors = []

        # 1. Connessione database
        db_test = self._test_db_connection()
        results['db_connection'] = db_test['success']
        if not db_test['success']:
            errors.append(f"Database: {db_test.get('error', 'errore sconosciuto')}")

        # 2. Directory backup
        backup_dir = Path(self.config['backup_dir'])
        if backup_dir.exists():
            results['backup_dir_exists'] = True

            # Test scrittura
            try:
                test_file = backup_dir / '.write_test'
                test_file.touch()
                test_file.unlink()
                results['backup_dir_writable'] = True
            except (PermissionError, OSError):
                errors.append(f"Directory {backup_dir} non scrivibile")

            # Conta backup esistenti
            backup_files = list(backup_dir.glob('to_extractor_*'))
            results['backup_count'] = len(backup_files)

            if backup_files:
                # Dimensione totale
                total_bytes = sum(f.stat().st_size for f in backup_files if f.is_file())
                results['total_size_mb'] = round(total_bytes / (1024 * 1024), 2)

                # Backup recente (ultime 24h)
                cutoff = datetime.now().timestamp() - 86400
                recent = [f for f in backup_files if f.stat().st_mtime > cutoff]
                results['recent_backup_exists'] = len(recent) > 0
                results['recent_backup_count'] = len(recent)

        else:
            errors.append(f"Directory {backup_dir} non esiste")

        # 3. pg_dump disponibile
        try:
            result = subprocess.run(['which', 'pg_dump'], capture_output=True, text=True)
            results['pg_dump_available'] = result.returncode == 0
            if result.returncode == 0:
                results['pg_dump_path'] = result.stdout.strip()
            else:
                errors.append("pg_dump non trovato nel PATH")
        except Exception:
            errors.append("Impossibile verificare pg_dump")

        # Determina successo
        success = (
            results['db_connection'] and
            results['backup_dir_exists'] and
            results['backup_dir_writable'] and
            results['pg_dump_available']
        )

        if success:
            message = f"Backup completo configurato. Backup esistenti: {results['backup_count']}"
        else:
            message = "Backup completo non configurato correttamente"

        return BackupResult(
            success=success,
            message=message,
            error="; ".join(errors) if errors else None,
            details=results
        )

    def get_status(self) -> Dict[str, Any]:
        """Stato corrente backup completo."""
        backup_dir = Path(self.config['backup_dir'])

        status = {
            'enabled': self._enabled,
            'configured': self._configured,
            'healthy': False,
            'backup_dir': str(backup_dir),
            'backup_dir_exists': backup_dir.exists(),
            'backup_count': 0,
            'backup_count_7d': 0,
            'total_size_mb': 0,
            'oldest_backup': None,
            'newest_backup': None,
        }

        if not backup_dir.exists():
            return status

        # Analizza backup esistenti
        backup_files = list(backup_dir.glob('to_extractor_*'))

        if backup_files:
            status['backup_count'] = len(backup_files)

            # Dimensione totale
            total_bytes = sum(f.stat().st_size for f in backup_files if f.is_file())
            status['total_size_mb'] = round(total_bytes / (1024 * 1024), 2)

            # Timestamps
            mtimes = [f.stat().st_mtime for f in backup_files if f.is_file()]
            if mtimes:
                status['oldest_backup'] = datetime.fromtimestamp(min(mtimes)).isoformat()
                status['newest_backup'] = datetime.fromtimestamp(max(mtimes)).isoformat()

                # Backup ultimi 7 giorni
                cutoff_7d = datetime.now().timestamp() - (7 * 86400)
                recent_7d = [t for t in mtimes if t > cutoff_7d]
                status['backup_count_7d'] = len(recent_7d)

                # Healthy se backup recente (ultime 24h)
                newest = max(mtimes)
                status['healthy'] = (datetime.now().timestamp() - newest) < 86400

        return status

    def cleanup(self, retention_days: int = None) -> BackupResult:
        """Rimuove backup più vecchi di retention_days."""
        retention = retention_days or self.config.get('retention_days', 7)
        backup_dir = Path(self.config['backup_dir'])

        if not backup_dir.exists():
            return BackupResult(
                success=False,
                message="Directory backup non esiste",
                error=f"Path: {backup_dir}"
            )

        backup_files = list(backup_dir.glob('to_extractor_*'))
        cutoff = datetime.now().timestamp() - (retention * 86400)

        deleted = []
        freed_bytes = 0
        errors = []

        for backup_file in backup_files:
            try:
                if backup_file.stat().st_mtime < cutoff:
                    if backup_file.is_dir():
                        size = sum(f.stat().st_size for f in backup_file.rglob('*') if f.is_file())
                        shutil.rmtree(backup_file)
                    else:
                        size = backup_file.stat().st_size
                        backup_file.unlink()
                    deleted.append(backup_file.name)
                    freed_bytes += size
            except OSError as e:
                errors.append(f"{backup_file.name}: {e}")

        freed_mb = round(freed_bytes / (1024 * 1024), 2)

        return BackupResult(
            success=len(errors) == 0,
            message=f"Cleanup completato: {len(deleted)} backup eliminati, {freed_mb} MB liberati",
            error="; ".join(errors) if errors else None,
            details={
                'deleted_count': len(deleted),
                'deleted_files': deleted,
                'freed_mb': freed_mb,
                'retention_days': retention,
            }
        )

    # =========================================================================
    # METODI HELPER
    # =========================================================================

    def _test_db_connection(self) -> Dict[str, Any]:
        """Testa connessione al database."""
        try:
            cmd = [
                'psql',
                '-h', self.config.get('host', '127.0.0.1'),
                '-p', str(self.config.get('port', 5432)),
                '-U', self.config.get('user', 'to_extractor_user'),
                '-d', self.config.get('database', 'to_extractor_v2'),
                '-c', 'SELECT 1;'
            ]

            env = os.environ.copy()
            # Path: modules -> backup -> services -> app -> backend/.env
            env_file = Path(__file__).parent.parent.parent.parent.parent / '.env'
            if env_file.exists():
                with open(env_file) as f:
                    for line in f:
                        if line.startswith('PG_PASSWORD='):
                            env['PGPASSWORD'] = line.split('=', 1)[1].strip()
                            break

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )

            return {
                'success': result.returncode == 0,
                'error': result.stderr if result.returncode != 0 else None
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _build_pg_dump_command(self, file_path: Path, fmt: str, compression: bool) -> List[str]:
        """Costruisce comando pg_dump."""
        cmd = [
            'pg_dump',
            '-h', self.config.get('host', '127.0.0.1'),
            '-p', str(self.config.get('port', 5432)),
            '-U', self.config.get('user', 'to_extractor_user'),
            '-d', self.config.get('database', 'to_extractor_v2'),
        ]

        if fmt == 'custom':
            cmd.extend(['-Fc', '-f', str(file_path)])
        elif fmt == 'directory':
            cmd.extend(['-Fd', '-f', str(file_path)])
        else:  # plain
            if compression:
                cmd.extend(['-f', str(file_path).replace('.gz', '')])
            else:
                cmd.extend(['-f', str(file_path)])

        return cmd

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calcola MD5 checksum del file."""
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
