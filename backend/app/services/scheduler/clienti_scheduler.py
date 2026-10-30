# =============================================================================
# SERV.O - CLIENTI SCHEDULER
# =============================================================================
# Sync automatica anagrafica clienti ERP da FTP (ANAG_TOT_V_*.csv)
# Orario: Lun-Ven alle 09:15, report email con le differenze rispetto
# all'anagrafica precedente.
# =============================================================================

import csv
import io
import os
from datetime import datetime
from html import escape
from typing import Any, Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ..anagrafica.sync_clienti import sync_clienti_erp, SyncClientiResult
from ..email.sender import EmailSender
from ...database_pg import get_db

_scheduler: Optional[BackgroundScheduler] = None
_schedule_label = ''
_last_run: Optional[datetime] = None
_last_result: Optional[Dict[str, Any]] = None

# Righe per sezione nel corpo mail; l'elenco completo e' nell'allegato CSV
MAX_RIGHE_MAIL = 50

_STILE = """
    body { font-family: Arial, sans-serif; margin: 20px; }
    h2 { color: #1e40af; }
    table { border-collapse: collapse; width: 100%; margin: 15px 0; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 13px; }
    th { background-color: #f3f4f6; }
    .success { color: #059669; }
    .warning { color: #d97706; }
    .error { color: #dc2626; }
    .highlight { background-color: #fef3c7; }
    .footer { margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 12px; color: #6b7280; }
"""


def _tabella_clienti(titolo: str, clienti, classe: str = '') -> str:
    if not clienti:
        return ''
    righe = ''.join(
        f"<tr><td>{escape(c['codice_cliente'])}</td>"
        f"<td>{escape(c['ragione_sociale_2'] or c['ragione_sociale_1'])}</td>"
        f"<td>{escape(c['localita'])} ({escape(c['provincia'])})</td>"
        f"<td>{escape(c['partita_iva'])}</td><td>{escape(c['min_id'])}</td>"
        f"<td>{escape(c['farmacia_categoria'])}</td><td>{escape(c['deposito_riferimento'])}</td></tr>"
        for c in clienti[:MAX_RIGHE_MAIL]
    )
    altri = len(clienti) - MAX_RIGHE_MAIL
    return f"""
        <h3 class="{classe}">{titolo} ({len(clienti)})</h3>
        <table>
            <tr><th>Codice</th><th>Ragione sociale</th><th>Località</th><th>P.IVA</th>
                <th>MIN_ID</th><th>Cat.</th><th>Dep.</th></tr>
            {righe}
        </table>
        {f'<p><small>... e altri {altri}: vedi allegato.</small></p>' if altri > 0 else ''}
    """


def _tabella_modificati(modificati) -> str:
    if not modificati:
        return ''
    righe = ''
    for m in modificati[:MAX_RIGHE_MAIL]:
        for i, cambio in enumerate(m['cambi']):
            intestazione = (
                f"<td rowspan='{len(m['cambi'])}'>{escape(m['codice_cliente'])}</td>"
                f"<td rowspan='{len(m['cambi'])}'>{escape(m['ragione_sociale'])}</td>"
                if i == 0 else ''
            )
            righe += (
                f"<tr>{intestazione}<td>{escape(cambio['campo'])}</td>"
                f"<td>{escape(cambio['prima'])}</td><td class='highlight'>{escape(cambio['dopo'])}</td></tr>"
            )
    altri = len(modificati) - MAX_RIGHE_MAIL
    return f"""
        <h3>Clienti modificati ({len(modificati)})</h3>
        <table>
            <tr><th>Codice</th><th>Ragione sociale</th><th>Campo</th><th>Prima</th><th>Dopo</th></tr>
            {righe}
        </table>
        {f'<p><small>... e altri {altri}: vedi allegato.</small></p>' if altri > 0 else ''}
    """


def _allegato_differenze(result: SyncClientiResult) -> Optional[Dict[str, Any]]:
    """CSV (';', UTF-8 con BOM per Excel) con tutte le differenze."""
    if not (result.nuovi or result.eliminati or result.modificati):
        return None
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=';')
    w.writerow(['tipo', 'codice_cliente', 'ragione_sociale', 'campo', 'prima', 'dopo'])
    for c in result.nuovi:
        w.writerow(['NUOVO', c['codice_cliente'], c['ragione_sociale_2'] or c['ragione_sociale_1'], '', '', ''])
    for c in result.eliminati:
        w.writerow(['ELIMINATO', c['codice_cliente'], c['ragione_sociale_2'] or c['ragione_sociale_1'], '', '', ''])
    for m in result.modificati:
        for cambio in m['cambi']:
            w.writerow(['MODIFICATO', m['codice_cliente'], m['ragione_sociale'],
                        cambio['campo'], cambio['prima'], cambio['dopo']])
    data = (result.data_file or datetime.now().date()).strftime('%Y_%m_%d')
    return {
        'filename': f'differenze_clienti_{data}.csv',
        'content': ('﻿' + buf.getvalue()).encode('utf-8'),
        'mime_type': 'text/csv',
    }


def _format_email(result: SyncClientiResult) -> tuple:
    now = datetime.now()
    oggi = now.strftime('%d/%m/%Y')
    ha_differenze = bool(result.nuovi or result.eliminati or result.modificati)

    if result.esito == 'BLOCCATO':
        subject = f"[SERVO] Sync Anagrafica Clienti BLOCCATA - {oggi}"
    elif not result.success:
        subject = f"[SERVO] Sync Anagrafica Clienti FALLITA - {oggi}"
    elif result.esito == 'NESSUN_FILE_NUOVO':
        subject = f"[SERVO] Sync Anagrafica Clienti - Nessun file nuovo {oggi}"
    elif ha_differenze:
        subject = f"[SERVO] Sync Anagrafica Clienti - Aggiornamenti del {oggi}"
    else:
        subject = f"[SERVO] Sync Anagrafica Clienti - Nessuna differenza {oggi}"

    classe_stato = 'success' if result.success else 'error'
    etichetta_stato = {
        'IMPORTATO': 'Completata',
        'NESSUN_FILE_NUOVO': 'Nessun file nuovo',
        'BLOCCATO': 'BLOCCATA',
    }.get(result.esito, 'FALLITA')

    body = f"""
    <html>
    <head><style>{_STILE}</style></head>
    <body>
        <h2>Sincronizzazione Anagrafica Clienti (ERP)</h2>
        <p><strong>Data:</strong> {now.strftime('%d/%m/%Y %H:%M')}</p>
        <p><strong>Stato:</strong> <span class="{classe_stato}">{etichetta_stato}</span></p>
        <p>{escape(result.messaggio)}</p>
    """

    if result.file and not result.file_del_giorno:
        body += f"""
        <div style="background-color: #fef3c7; padding: 15px; border-radius: 5px; margin: 15px 0;">
            <strong>Attenzione:</strong> il file di oggi non era presente; usato il più recente,
            {escape(result.file)}.
        </div>
        """

    if result.esito == 'IMPORTATO':
        body += f"""
        <table>
            <tr><th>Metrica</th><th>Valore</th></tr>
            <tr><td>File</td><td>{escape(result.file or '')}</td></tr>
            <tr><td>Clienti nel file</td><td>{result.righe_file:,}</td></tr>
            <tr><td>Clienti prima</td><td>{result.totale_prima:,}</td></tr>
            <tr><td>Clienti dopo</td><td><strong>{result.totale_dopo:,}</strong></td></tr>
            <tr><td>Nuovi</td><td class="{'highlight' if result.nuovi else ''}">{len(result.nuovi)}</td></tr>
            <tr><td>Eliminati</td><td class="{'warning highlight' if result.eliminati else ''}">{len(result.eliminati)}</td></tr>
            <tr><td>Modificati</td><td class="{'highlight' if result.modificati else ''}">{len(result.modificati)}</td></tr>
        </table>
        """
        revisione = result.import_result.get('revisione_ordini')
        if revisione:
            body += (
                f"<p>Ordini con deposito mancante risolti dopo l'import: "
                f"{revisione.get('anomalie_risolte', 0)}</p>"
            )
        body += _tabella_clienti('Clienti nuovi', result.nuovi)
        body += _tabella_clienti('Clienti eliminati', result.eliminati, 'warning')
        body += _tabella_modificati(result.modificati)

    body += f"""
        <div class="footer">
            <p>Durata: {result.durata_secondi:.1f} secondi</p>
            <p>Email generata automaticamente da SERV.O</p>
        </div>
    </body>
    </html>
    """
    return subject, body


def _send_report_email(result: SyncClientiResult):
    """Stessi destinatari del report sync ministeriale."""
    recipients = os.getenv('SYNC_REPORT_EMAIL') or os.getenv('ADMIN_EMAIL') or os.getenv('SMTP_USER', '')
    if not recipients:
        print("⏭️ Nessun destinatario configurato per report sync clienti")
        return

    try:
        db = get_db()
        sender = EmailSender(db)
        if not sender.is_configured(db):
            print("⏭️ Email non configurata, skip invio report sync clienti")
            return

        subject, body = _format_email(result)
        allegato = _allegato_differenze(result)
        for recipient in recipients.split(','):
            recipient = recipient.strip()
            if not recipient:
                continue
            esito = sender.send(
                to=recipient,
                subject=subject,
                body_html=body,
                email_type='sync_clienti_report',
                attachments=[allegato] if allegato else None,
            )
            if esito['success']:
                print(f"📧 Report sync clienti inviato a {recipient}")
            else:
                print(f"⚠️ Errore invio report sync clienti a {recipient}: {esito.get('error')}")
        db.commit()

    except Exception as e:
        print(f"⚠️ Errore invio email report sync clienti: {e}")


def _run_clienti_sync(forza: bool = False):
    global _last_run, _last_result

    _last_run = datetime.now()
    print(f"👥 [{_last_run:%Y-%m-%d %H:%M:%S}] Sync Anagrafica Clienti - Avvio...")

    result = sync_clienti_erp(forza=forza)
    _last_result = {
        'success': result.success,
        'esito': result.esito,
        'message': result.messaggio,
        'file': result.file,
        'timestamp': _last_run.isoformat(),
        'nuovi': len(result.nuovi),
        'eliminati': len(result.eliminati),
        'modificati': len(result.modificati),
        'totale_dopo': result.totale_dopo,
    }
    print(f"{'✅' if result.success else '⚠️'} Sync Anagrafica Clienti: {result.messaggio}")

    _send_report_email(result)


def init_clienti_scheduler(hour: int = 9, minute: int = 15) -> bool:
    """Schedulazione default: Lun-Ven alle 09:15. Disattivabile con CLIENTI_SYNC_ENABLED=false."""
    global _scheduler, _schedule_label

    if os.getenv('CLIENTI_SYNC_ENABLED', 'true').lower() != 'true':
        print("⏭️ Clienti Scheduler: disabilitato da configurazione (CLIENTI_SYNC_ENABLED=false)")
        return False

    try:
        _scheduler = BackgroundScheduler(
            timezone='Europe/Rome',
            job_defaults={'coalesce': True, 'max_instances': 1}
        )
        _scheduler.add_job(
            _run_clienti_sync,
            trigger=CronTrigger(hour=hour, minute=minute, day_of_week='mon-fri', timezone='Europe/Rome'),
            id='clienti_sync',
            name='Anagrafica Clienti ERP Sync',
            replace_existing=True
        )
        _scheduler.start()
        _schedule_label = f"Lun-Ven alle {hour:02d}:{minute:02d}"

        next_run = _scheduler.get_job('clienti_sync').next_run_time
        print(f"👥 Clienti Scheduler attivato ({_schedule_label})")
        print(f"   Prossima esecuzione: {next_run.strftime('%Y-%m-%d %H:%M') if next_run else 'N/A'}")
        return True

    except Exception as e:
        print(f"❌ Errore inizializzazione Clienti Scheduler: {e}")
        return False


def shutdown_clienti_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("👥 Clienti Scheduler arrestato")


def get_clienti_scheduler_status() -> Dict[str, Any]:
    if not _scheduler:
        return {'enabled': False, 'running': False, 'reason': 'Scheduler non inizializzato'}
    job = _scheduler.get_job('clienti_sync')
    return {
        'enabled': True,
        'running': _scheduler.running,
        'schedule': _schedule_label,
        'next_run': job.next_run_time.isoformat() if job and job.next_run_time else None,
        'last_run': _last_run.isoformat() if _last_run else None,
        'last_result': _last_result,
    }


def run_clienti_sync_now(forza: bool = False) -> Dict[str, Any]:
    _run_clienti_sync(forza=forza)
    return _last_result or {'success': False, 'error': 'Nessun risultato'}
