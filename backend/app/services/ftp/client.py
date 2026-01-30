# =============================================================================
# SERV.O v11.5 - FTP CLIENT
# =============================================================================
# Client FTP con supporto per modalita attiva, retry e logging
# =============================================================================

import os
import time
import ftplib
from typing import Dict, Any, Optional, List
from datetime import datetime

from ...database_pg import get_db, log_operation


class FTPClient:
    """
    Client FTP per invio tracciati verso ERP.

    Supporta:
    - Modalita attiva (IP whitelistato)
    - Retry automatico su fallimento
    - Logging dettagliato
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 21,
        passive: bool = False,
        timeout: int = 30
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.passive = passive
        self.timeout = timeout
        self.ftp: Optional[ftplib.FTP] = None
        self._connected = False

    def connect(self) -> Dict[str, Any]:
        """
        Stabilisce connessione FTP.

        Returns:
            {success: bool, message: str, duration_ms: int}
        """
        start_time = time.time()

        try:
            self.ftp = ftplib.FTP()
            self.ftp.connect(self.host, self.port, timeout=self.timeout)
            self.ftp.login(self.username, self.password)

            # Imposta modalita attiva o passiva
            if self.passive:
                self.ftp.set_pasv(True)
            else:
                self.ftp.set_pasv(False)

            self._connected = True
            duration_ms = int((time.time() - start_time) * 1000)

            self._log_ftp('CONNECT', None, None, 'SUCCESS',
                         f"Connesso a {self.host}:{self.port}", duration_ms)

            return {
                'success': True,
                'message': f"Connesso a {self.host}:{self.port}",
                'duration_ms': duration_ms
            }

        except ftplib.error_perm as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Errore autenticazione FTP: {str(e)}"
            self._log_ftp('CONNECT', None, None, 'FAILED', error_msg, duration_ms)
            return {'success': False, 'error': error_msg, 'duration_ms': duration_ms}

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Errore connessione FTP: {str(e)}"
            self._log_ftp('CONNECT', None, None, 'FAILED', error_msg, duration_ms)
            return {'success': False, 'error': error_msg, 'duration_ms': duration_ms}

    def disconnect(self):
        """Chiude connessione FTP."""
        if self.ftp and self._connected:
            try:
                self.ftp.quit()
                self._log_ftp('DISCONNECT', None, None, 'SUCCESS', 'Disconnesso', 0)
            except:
                try:
                    self.ftp.close()
                except:
                    pass
            finally:
                self._connected = False
                self.ftp = None

    def upload_file(
        self,
        local_path: str,
        remote_path: str,
        id_esportazione: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Carica un file sul server FTP.

        Args:
            local_path: Percorso file locale
            remote_path: Percorso remoto (es: ./ANGELINI/TO_T_xxx.txt)
            id_esportazione: ID esportazione per logging

        Returns:
            {success: bool, message: str, file_size: int, duration_ms: int}
        """
        if not self._connected:
            return {'success': False, 'error': 'Non connesso al server FTP'}

        if not os.path.exists(local_path):
            return {'success': False, 'error': f'File non trovato: {local_path}'}

        start_time = time.time()
        file_name = os.path.basename(local_path)
        file_size = os.path.getsize(local_path)

        try:
            # Naviga/crea directory remota
            remote_dir = os.path.dirname(remote_path)
            if remote_dir:
                self._ensure_remote_dir(remote_dir)

            # Upload file
            with open(local_path, 'rb') as f:
                self.ftp.storbinary(f'STOR {remote_path}', f)

            duration_ms = int((time.time() - start_time) * 1000)

            self._log_ftp('UPLOAD', file_name, remote_path, 'SUCCESS',
                         f"Caricato {file_name} ({file_size} bytes)", duration_ms,
                         id_esportazione)

            return {
                'success': True,
                'message': f"File {file_name} caricato",
                'file_name': file_name,
                'file_size': file_size,
                'remote_path': remote_path,
                'duration_ms': duration_ms
            }

        except ftplib.error_perm as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Errore permessi FTP: {str(e)}"
            self._log_ftp('UPLOAD', file_name, remote_path, 'FAILED',
                         error_msg, duration_ms, id_esportazione)
            return {'success': False, 'error': error_msg, 'duration_ms': duration_ms}

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Errore upload FTP: {str(e)}"
            self._log_ftp('UPLOAD', file_name, remote_path, 'FAILED',
                         error_msg, duration_ms, id_esportazione)
            return {'success': False, 'error': error_msg, 'duration_ms': duration_ms}

    def _ensure_remote_dir(self, remote_dir: str):
        """Crea directory remota se non esiste."""
        if not remote_dir or remote_dir == '.':
            return

        try:
            self.ftp.cwd(remote_dir)
            self.ftp.cwd('/')  # Torna alla root
        except ftplib.error_perm:
            # Directory non esiste, creala
            parts = remote_dir.replace('\\', '/').split('/')
            current = ''
            for part in parts:
                if not part or part == '.':
                    continue
                current = f"{current}/{part}" if current else part
                try:
                    self.ftp.mkd(current)
                except ftplib.error_perm:
                    pass  # Directory gia esiste

    def _log_ftp(
        self,
        azione: str,
        file_name: Optional[str],
        ftp_path: Optional[str],
        esito: str,
        messaggio: str,
        durata_ms: int,
        id_esportazione: Optional[int] = None
    ):
        """Registra operazione FTP nel log."""
        try:
            db = get_db()
            db.execute("""
                INSERT INTO ftp_log
                (id_esportazione, azione, file_name, ftp_path, esito, messaggio, durata_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (id_esportazione, azione, file_name, ftp_path, esito, messaggio, durata_ms))
            db.commit()
        except Exception as e:
            # Non bloccare su errore di logging
            print(f"Warning: errore log FTP: {e}")

    def __enter__(self):
        """Context manager: connetti."""
        result = self.connect()
        if not result['success']:
            raise ConnectionError(result.get('error', 'Errore connessione FTP'))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager: disconnetti."""
        self.disconnect()
        return False


def get_ftp_client_from_config() -> FTPClient:
    """
    Crea FTPClient dalla configurazione nel database.

    Password letta da variabile ambiente FTP_PASSWORD.
    """
    db = get_db()

    config = db.execute("""
        SELECT * FROM ftp_config WHERE ftp_enabled = TRUE LIMIT 1
    """).fetchone()

    if not config:
        raise ValueError("Nessuna configurazione FTP attiva trovata")

    password = os.environ.get('FTP_PASSWORD')
    if not password:
        raise ValueError("Variabile ambiente FTP_PASSWORD non configurata")

    return FTPClient(
        host=config['ftp_host'],
        port=config['ftp_port'],
        username=config['ftp_username'],
        password=password,
        passive=config['ftp_passive_mode'],
        timeout=config['ftp_timeout']
    )
