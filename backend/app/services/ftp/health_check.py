# =============================================================================
# SERV.O v11.6 - FTP HEALTH CHECK
# =============================================================================
# Scansione giornaliera server FTP remoto per rilevare:
# - File .log (errori di trasmissione lato ricevente)
# - File dati.lok stale (>36h = crash sistema ricevente)
# =============================================================================

import ftplib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from ...database_pg import get_db, log_operation

logger = logging.getLogger('ftp_health_check')
logger.setLevel(logging.INFO)

# Soglia ore per considerare un lock file "stale"
STALE_LOCK_HOURS = 36

# Directory da scansionare (solo operative, escluse _BK)
FTP_DIRS = [
    'ANGELINI', 'BAYER', 'CHIESI', 'CODIFI', 'COOPER',
    'DOC', 'DOMPE', 'MENARINI', 'OPELLA', 'PERRIGO',
    'RECKITT', 'TRANSFER', 'VIATRIS'
]

# Mesi FTP (listing inglese)
MONTHS = {
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
    'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
    'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
}


def _parse_ftp_date(line: str) -> Optional[datetime]:
    """
    Estrae datetime da una riga di listing FTP.

    Formato: -rw-r--r-- 1 ftp ftp  19722 Mar 27 16:27 filename.txt
    """
    try:
        parts = line.split()
        if len(parts) < 9:
            return None

        month_str = parts[5]
        day = int(parts[6])
        time_or_year = parts[7]

        month = MONTHS.get(month_str)
        if not month:
            return None

        now = datetime.now()

        if ':' in time_or_year:
            # Formato "HH:MM" - anno corrente (o precedente se data futura)
            hour, minute = map(int, time_or_year.split(':'))
            dt = datetime(now.year, month, day, hour, minute)
            # Se la data è nel futuro, è dell'anno scorso
            if dt > now + timedelta(days=1):
                dt = dt.replace(year=now.year - 1)
        else:
            # Formato "YYYY" - solo anno, senza orario
            year = int(time_or_year)
            dt = datetime(year, month, day)

        return dt
    except (ValueError, IndexError):
        return None


def _parse_ftp_filename(line: str) -> Optional[str]:
    """Estrae il nome file da una riga di listing FTP."""
    parts = line.split()
    if len(parts) >= 9:
        return ' '.join(parts[8:])  # Nome file potrebbe avere spazi
    return None


def scan_ftp_directories() -> Dict[str, Any]:
    """
    Scansiona tutte le directory FTP per anomalie.

    Rileva:
    - File .log → errore trasmissione lato ricevente
    - File dati.lok con data > 36h → crash sistema ricevente

    Returns:
        {
            success: bool,
            timestamp: str,
            directories_scanned: int,
            problems: [
                {
                    directory: str,
                    type: 'LOG_FILE' | 'STALE_LOCK',
                    filename: str,
                    file_date: str,
                    details: str
                }
            ],
            summary: str
        }
    """
    db = get_db()
    now = datetime.now()
    problems = []
    dirs_scanned = 0
    errors = []

    # Recupera configurazione FTP da ftp_endpoints (primo attivo)
    # oppure da ftp_config
    ftp_host = None
    ftp_port = 21
    ftp_username = None
    ftp_password = None
    ftp_passive = False
    ftp_timeout = 30

    try:
        # Prima prova ftp_endpoints
        endpoint = db.execute("""
            SELECT DISTINCT ftp_host, ftp_port, ftp_username,
                   ftp_password_encrypted, ftp_passive_mode, ftp_timeout
            FROM ftp_endpoints
            WHERE attivo = TRUE
            LIMIT 1
        """).fetchone()

        if endpoint:
            from ..crypto import decrypt_password
            ftp_host = endpoint['ftp_host']
            ftp_port = endpoint['ftp_port']
            ftp_username = endpoint['ftp_username']
            ftp_password = decrypt_password(endpoint['ftp_password_encrypted'])
            ftp_passive = endpoint['ftp_passive_mode']
            ftp_timeout = endpoint['ftp_timeout']
        else:
            # Fallback su ftp_config
            import os
            config = db.execute("""
                SELECT ftp_host, ftp_port, ftp_username, ftp_passive_mode, ftp_timeout
                FROM ftp_config WHERE ftp_enabled = TRUE LIMIT 1
            """).fetchone()

            if not config:
                return {
                    'success': False,
                    'error': 'Nessuna configurazione FTP attiva',
                    'timestamp': now.isoformat(),
                    'problems': [],
                    'directories_scanned': 0
                }

            ftp_host = config['ftp_host']
            ftp_port = config['ftp_port']
            ftp_username = config['ftp_username']
            ftp_passive = config['ftp_passive_mode']
            ftp_timeout = config['ftp_timeout']
            ftp_password = os.environ.get('FTP_PASSWORD')

            if not ftp_password:
                return {
                    'success': False,
                    'error': 'Password FTP non configurata',
                    'timestamp': now.isoformat(),
                    'problems': [],
                    'directories_scanned': 0
                }

    except Exception as e:
        return {
            'success': False,
            'error': f'Errore lettura configurazione FTP: {str(e)}',
            'timestamp': now.isoformat(),
            'problems': [],
            'directories_scanned': 0
        }

    # Connessione FTP
    ftp = None
    try:
        ftp = ftplib.FTP(timeout=ftp_timeout)
        ftp.connect(ftp_host, ftp_port)
        ftp.login(ftp_username, ftp_password)
        ftp.set_pasv(ftp_passive)

        logger.info(f"Health check FTP: connesso a {ftp_host}")

        for directory in FTP_DIRS:
            try:
                # Lista dettagliata della directory
                lines = []
                ftp.retrlines(f'LIST {directory}/', lines.append)
                dirs_scanned += 1

                for line in lines:
                    filename = _parse_ftp_filename(line)
                    if not filename:
                        continue

                    file_date = _parse_ftp_date(line)

                    # Check 1: File .log (errore trasmissione)
                    if filename.lower().endswith('.log'):
                        problems.append({
                            'directory': directory,
                            'type': 'LOG_FILE',
                            'filename': filename,
                            'file_date': file_date.isoformat() if file_date else 'N/A',
                            'details': f'File di errore trasmissione trovato in {directory}'
                        })

                    # Check 2: File dati.lok stale (>36h)
                    if filename.lower() == 'dati.lok' and file_date:
                        age_hours = (now - file_date).total_seconds() / 3600
                        if age_hours >= STALE_LOCK_HOURS:
                            problems.append({
                                'directory': directory,
                                'type': 'STALE_LOCK',
                                'filename': filename,
                                'file_date': file_date.isoformat(),
                                'age_hours': round(age_hours, 1),
                                'details': f'Lock file fermo da {round(age_hours)}h '
                                           f'(soglia: {STALE_LOCK_HOURS}h) - '
                                           f'possibile crash sistema ricevente'
                            })

            except ftplib.error_perm as e:
                # Directory non accessibile (potrebbe non esistere)
                logger.warning(f"Health check: directory {directory} non accessibile: {e}")
                errors.append(f'{directory}: {str(e)}')
            except Exception as e:
                logger.warning(f"Health check: errore scansione {directory}: {e}")
                errors.append(f'{directory}: {str(e)}')

        ftp.quit()

    except Exception as e:
        logger.error(f"Health check FTP: errore connessione: {e}")
        if ftp:
            try:
                ftp.close()
            except:
                pass
        return {
            'success': False,
            'error': f'Errore connessione FTP: {str(e)}',
            'timestamp': now.isoformat(),
            'problems': [],
            'directories_scanned': dirs_scanned
        }

    # Costruisci summary
    log_files = [p for p in problems if p['type'] == 'LOG_FILE']
    stale_locks = [p for p in problems if p['type'] == 'STALE_LOCK']

    if problems:
        summary = (
            f"{len(problems)} problema/i: "
            f"{len(log_files)} file .log, "
            f"{len(stale_locks)} lock stale"
        )
    else:
        summary = f"Nessun problema rilevato su {dirs_scanned} directory"

    # Log nel DB
    log_operation(
        'FTP_HEALTH_CHECK',
        'ftp',
        0,
        summary + (f' | Errori accesso: {len(errors)}' if errors else ''),
        operatore='SCHEDULER'
    )

    result = {
        'success': True,
        'timestamp': now.isoformat(),
        'directories_scanned': dirs_scanned,
        'problems': problems,
        'problems_count': len(problems),
        'log_files_count': len(log_files),
        'stale_locks_count': len(stale_locks),
        'summary': summary,
        'errors': errors if errors else None
    }

    # Se ci sono problemi, invia alert email
    if problems:
        _send_health_check_alert(problems, summary)

    return result


def _send_health_check_alert(problems: List[Dict], summary: str):
    """Invia email alert per problemi rilevati dall'health check."""
    try:
        from ..email.sender import EmailSender

        db = get_db()

        email_config = db.execute("""
            SELECT admin_notifica_email FROM email_config LIMIT 1
        """).fetchone()

        if not email_config or not email_config['admin_notifica_email']:
            logger.warning("Health check: nessun destinatario email configurato")
            return

        recipients = email_config['admin_notifica_email']

        # Costruisci corpo email
        body = f"""
        <h2>SERV.O - FTP Health Check Alert</h2>
        <p><strong>Data:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        <p><strong>Riepilogo:</strong> {summary}</p>

        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
            <tr style="background-color: #f2f2f2;">
                <th>Directory</th>
                <th>Tipo</th>
                <th>File</th>
                <th>Data File</th>
                <th>Dettagli</th>
            </tr>
        """

        for p in problems:
            tipo_label = 'Errore Trasmissione' if p['type'] == 'LOG_FILE' else 'Lock Stale'
            bg_color = '#fff3cd' if p['type'] == 'LOG_FILE' else '#f8d7da'

            age_info = ''
            if p.get('age_hours'):
                age_info = f" ({p['age_hours']}h)"

            body += f"""
            <tr style="background-color: {bg_color};">
                <td><strong>{p['directory']}</strong></td>
                <td>{tipo_label}</td>
                <td>{p['filename']}</td>
                <td>{p['file_date']}{age_info}</td>
                <td>{p['details']}</td>
            </tr>
            """

        body += """
        </table>
        <br>
        <p><strong>Azioni richieste:</strong></p>
        <ul>
            <li><strong>File .log:</strong> Verificare il contenuto del file per capire l'errore di trasmissione</li>
            <li><strong>Lock stale:</strong> Contattare il gestore del sistema ricevente per rimuovere il lock orfano</li>
        </ul>
        <p><em>SERV.O - Health Check Automatico</em></p>
        """

        sender = EmailSender(db)
        sender.send(
            to=recipients,
            subject=f"[SERV.O] FTP Health Check - {len(problems)} problema/i rilevato/i",
            body_html=body,
            email_type='ftp_health_check'
        )

        logger.info(f"Health check: alert email inviato a {recipients}")

    except Exception as e:
        logger.error(f"Health check: errore invio alert email: {e}")
