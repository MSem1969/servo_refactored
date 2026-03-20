# =============================================================================
# SERV.O v12.1 - BACKUP SCHEDULER
# =============================================================================
# Backup giornaliero: pg_dump locale + upload FTP su cartella TRANSFER
# Riusa FTPClient esistente (stessa connessione dei transfer order)
# =============================================================================

import os
import subprocess
import hashlib
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from ...database_pg import get_db, log_operation
from ...config import config


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

BACKUP_DIR = os.getenv('BACKUP_DIR', '/app/backup')
BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', '7'))
FTP_BACKUP_PATH = './TRANSFER'
BACKUP_PREFIX = 'servo_backup'


# =============================================================================
# FUNZIONI BACKUP
# =============================================================================

def execute_backup(triggered_by: str = 'manual') -> Dict[str, Any]:
    """
    Esegue backup completo: pg_dump locale + upload FTP.

    Args:
        triggered_by: 'manual', 'scheduled', 'pre-migration'

    Returns:
        Dict con risultati backup locale e FTP
    """
    result = {
        'success': False,
        'triggered_by': triggered_by,
        'timestamp': datetime.now().isoformat(),
        'local': None,
        'ftp': None,
    }

    # Step 1: Backup locale
    local_result = _execute_local_backup()
    result['local'] = local_result

    if not local_result['success']:
        result['error'] = f"Backup locale fallito: {local_result.get('error')}"
        _log_backup(result)
        return result

    # Step 2: Upload FTP
    ftp_result = _upload_to_ftp(local_result['file_path'], local_result['file_name'])
    result['ftp'] = ftp_result

    # Step 3: Cleanup vecchi backup locali
    cleanup_result = _cleanup_old_backups()
    result['cleanup'] = cleanup_result

    result['success'] = local_result['success']
    if not ftp_result['success']:
        result['warning'] = f"Backup locale OK ma upload FTP fallito: {ftp_result.get('error')}"

    _log_backup(result)
    return result


def _execute_local_backup() -> Dict[str, Any]:
    """Esegue pg_dump e salva il backup localmente."""
    start_time = datetime.now()
    backup_dir = Path(BACKUP_DIR)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = start_time.strftime('%Y%m%d_%H%M%S')
    filename = f"{BACKUP_PREFIX}_{timestamp}.dump"
    file_path = backup_dir / filename

    # Credenziali DB
    db_host = os.getenv('PG_HOST', 'localhost')
    db_port = os.getenv('PG_PORT', '5432')
    db_user = os.getenv('PG_USER', 'servo_user')
    db_password = os.getenv('PG_PASSWORD', '')
    db_name = os.getenv('PG_DB', 'servo')

    cmd = [
        'pg_dump',
        '-h', db_host,
        '-p', str(db_port),
        '-U', db_user,
        '-d', db_name,
        '-Fc',  # Formato custom (compresso)
        '--no-owner',
        '--no-privileges',
        '-f', str(file_path),
    ]

    try:
        env = os.environ.copy()
        env['PGPASSWORD'] = db_password

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,
            env=env
        )

        duration = int((datetime.now() - start_time).total_seconds())

        if proc.returncode != 0:
            return {
                'success': False,
                'error': proc.stderr.strip(),
                'duration_seconds': duration,
            }

        if not file_path.exists():
            return {
                'success': False,
                'error': 'File backup non creato',
                'duration_seconds': duration,
            }

        file_size = file_path.stat().st_size
        checksum = hashlib.md5(file_path.read_bytes()).hexdigest()

        return {
            'success': True,
            'file_path': str(file_path),
            'file_name': filename,
            'file_size': file_size,
            'file_size_mb': round(file_size / (1024 * 1024), 2),
            'checksum': checksum,
            'duration_seconds': duration,
        }

    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Timeout pg_dump (1 ora)'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _upload_to_ftp(file_path: str, file_name: str) -> Dict[str, Any]:
    """Upload backup su server FTP nella cartella TRANSFER."""
    from ...services.ftp.client import get_ftp_client_from_config

    try:
        client = get_ftp_client_from_config()

        with client:
            remote_path = f"{FTP_BACKUP_PATH}/{file_name}"
            upload_result = client.upload_file(file_path, remote_path)
            return upload_result

    except ValueError as e:
        return {'success': False, 'error': f'Configurazione FTP: {str(e)}'}
    except ConnectionError as e:
        return {'success': False, 'error': f'Connessione FTP: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': f'Errore FTP: {str(e)}'}


def _cleanup_old_backups() -> Dict[str, Any]:
    """Rimuove backup locali più vecchi di BACKUP_RETENTION_DAYS."""
    backup_dir = Path(BACKUP_DIR)
    if not backup_dir.exists():
        return {'removed': 0}

    cutoff = datetime.now() - timedelta(days=BACKUP_RETENTION_DAYS)
    removed = 0

    for f in backup_dir.glob(f'{BACKUP_PREFIX}_*.dump'):
        try:
            if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                f.unlink()
                removed += 1
        except Exception:
            pass

    return {'removed': removed, 'retention_days': BACKUP_RETENTION_DAYS}


def get_backup_status() -> Dict[str, Any]:
    """Stato corrente dei backup: ultimo backup, file locali, spazio."""
    backup_dir = Path(BACKUP_DIR)

    backups = []
    if backup_dir.exists():
        for f in sorted(backup_dir.glob(f'{BACKUP_PREFIX}_*.dump'), reverse=True):
            backups.append({
                'file_name': f.name,
                'file_size_mb': round(f.stat().st_size / (1024 * 1024), 2),
                'created_at': datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })

    return {
        'backup_dir': str(backup_dir),
        'retention_days': BACKUP_RETENTION_DAYS,
        'ftp_path': FTP_BACKUP_PATH,
        'backup_count': len(backups),
        'backups': backups[:10],
        'last_backup': backups[0] if backups else None,
    }


def _log_backup(result: Dict[str, Any]):
    """Registra risultato backup nel log operazioni."""
    try:
        status = 'OK' if result['success'] else 'ERRORE'
        details = f"Triggered: {result.get('triggered_by', 'unknown')}"
        if result.get('local', {}).get('success'):
            details += f" | Local: {result['local'].get('file_size_mb', '?')} MB"
        if result.get('ftp', {}).get('success'):
            details += f" | FTP: OK"
        elif result.get('ftp'):
            details += f" | FTP: FALLITO"

        log_operation('BACKUP', 'SISTEMA', None, f"Backup {status} - {details}")
    except Exception:
        pass


# =============================================================================
# SCHEDULER
# =============================================================================

_scheduler_thread: Optional[threading.Timer] = None
_scheduler_running = False


def start_backup_scheduler(hour: int = 2, minute: int = 0):
    """
    Avvia scheduler backup giornaliero.

    Args:
        hour: Ora esecuzione (default: 02:00)
        minute: Minuti (default: 00)
    """
    global _scheduler_running
    _scheduler_running = True

    def _schedule_next():
        if not _scheduler_running:
            return

        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)

        delay = (target - now).total_seconds()
        print(f"📦 Backup Scheduler: prossimo backup alle {target.strftime('%d/%m/%Y %H:%M')}")

        global _scheduler_thread
        _scheduler_thread = threading.Timer(delay, _run_scheduled_backup, args=(hour, minute))
        _scheduler_thread.daemon = True
        _scheduler_thread.start()

    _schedule_next()


def _run_scheduled_backup(hour: int, minute: int):
    """Esegue backup schedulato e ripianifica il prossimo."""
    try:
        print(f"📦 Backup Scheduler: esecuzione backup giornaliero...")
        result = execute_backup(triggered_by='scheduled')
        if result['success']:
            print(f"📦 Backup OK: {result['local'].get('file_name')} ({result['local'].get('file_size_mb')} MB)")
            if result.get('ftp', {}).get('success'):
                print(f"📦 FTP upload OK")
            else:
                print(f"⚠️ FTP upload fallito: {result.get('ftp', {}).get('error')}")
        else:
            print(f"❌ Backup FALLITO: {result.get('error')}")
    except Exception as e:
        print(f"❌ Backup Scheduler errore: {e}")

    # Ripianifica
    start_backup_scheduler(hour, minute)


def stop_backup_scheduler():
    """Ferma scheduler backup."""
    global _scheduler_running, _scheduler_thread
    _scheduler_running = False
    if _scheduler_thread:
        _scheduler_thread.cancel()
        _scheduler_thread = None
    print("📦 Backup Scheduler arrestato")
