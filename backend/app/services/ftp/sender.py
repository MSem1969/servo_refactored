# =============================================================================
# SERV.O v11.5 - FTP SENDER
# =============================================================================
# Logica invio batch tracciati via FTP con retry e alert
# =============================================================================

import os
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from ...database_pg import get_db, log_operation
from ...config import config
from .client import FTPClient, get_ftp_client_from_config


class FTPSender:
    """
    Gestisce invio batch tracciati via FTP.

    - Cerca esportazioni in stato PENDING/RETRY
    - Mappa vendor -> path FTP
    - Invia coppie TO_T + TO_D
    - Retry su fallimento (max 3 tentativi)
    - Alert email su fallimento finale
    """

    def __init__(self):
        self.db = get_db()
        self._vendor_mapping: Dict[int, str] = {}
        self._load_vendor_mapping()

    def _load_vendor_mapping(self):
        """Carica mapping id_vendor -> path FTP da ftp_endpoints (con fallback su ftp_vendor_mapping)."""
        # Primario: ftp_endpoints (gestito dal frontend) + join vendor per id_vendor
        mappings = self.db.execute("""
            SELECT v.id_vendor, fe.ftp_path
            FROM ftp_endpoints fe
            JOIN vendor v ON UPPER(fe.vendor_code) = UPPER(v.codice_vendor)
            WHERE fe.attivo = TRUE
        """).fetchall()

        self._vendor_mapping = {m['id_vendor']: m['ftp_path'] for m in mappings}

        # Fallback: ftp_vendor_mapping (vecchia tabella) per vendor non in ftp_endpoints
        try:
            old_mappings = self.db.execute("""
                SELECT id_vendor, ftp_path FROM ftp_vendor_mapping
                WHERE attivo = TRUE AND id_vendor IS NOT NULL
            """).fetchall()
            for m in old_mappings:
                if m['id_vendor'] not in self._vendor_mapping:
                    self._vendor_mapping[m['id_vendor']] = m['ftp_path']
        except Exception:
            pass  # Tabella potrebbe non esistere più

    def get_ftp_path_for_vendor(self, id_vendor: int) -> Optional[str]:
        """
        Restituisce il path FTP per un vendor.

        Args:
            id_vendor: ID vendor (FK verso tabella vendor)

        Returns:
            Path FTP (es: ./ANGELINI) o None se non mappato
        """
        return self._vendor_mapping.get(id_vendor)

    def get_pending_exports(self) -> List[Dict[str, Any]]:
        """
        Recupera esportazioni da inviare via FTP.

        Cerca:
        - stato_ftp = 'PENDING' (nuove)
        - stato_ftp = 'RETRY' con tentativi < max

        Returns:
            Lista di esportazioni con info file
        """
        ftp_config = self.db.execute("""
            SELECT max_tentativi FROM ftp_config WHERE ftp_enabled = TRUE LIMIT 1
        """).fetchone()

        max_tentativi = ftp_config['max_tentativi'] if ftp_config else 3

        exports = self.db.execute("""
            SELECT e.*, ot.id_vendor as vendor, ot.deposito_riferimento
            FROM esportazioni e
            JOIN esportazioni_dettaglio ed ON e.id_esportazione = ed.id_esportazione
            JOIN ordini_testata ot ON ed.id_testata = ot.id_testata
            WHERE e.stato_ftp IN ('PENDING', 'RETRY')
              AND e.tentativi_ftp < %s
            ORDER BY e.data_generazione ASC
        """, (max_tentativi,)).fetchall()

        return [dict(e) for e in exports]

    def send_export(
        self,
        id_esportazione: int,
        ftp_client: FTPClient
    ) -> Dict[str, Any]:
        """
        Invia una singola esportazione (coppia TO_T + TO_D).

        Args:
            id_esportazione: ID esportazione
            ftp_client: Client FTP connesso

        Returns:
            {success: bool, files_sent: list, error: str}
        """
        # Recupera info esportazione
        export = self.db.execute("""
            SELECT e.*, ot.id_vendor as vendor, ot.deposito_riferimento
            FROM esportazioni e
            JOIN esportazioni_dettaglio ed ON e.id_esportazione = ed.id_esportazione
            JOIN ordini_testata ot ON ed.id_testata = ot.id_testata
            WHERE e.id_esportazione = %s
        """, (id_esportazione,)).fetchone()

        if not export:
            return {'success': False, 'error': 'Esportazione non trovata'}

        # Blocca reinvio di esportazioni già completate
        if export['stato_ftp'] in ('SENT', 'SKIPPED', 'ALERT_SENT'):
            return {
                'success': False,
                'error': f"Esportazione già completata (stato: {export['stato_ftp']}). Reinvio non consentito."
            }

        vendor = export['vendor']
        file_to_t = export['nome_file_to_t']
        file_to_d = export['nome_file_to_d']

        # Verifica mapping vendor
        ftp_path = self.get_ftp_path_for_vendor(vendor)
        if not ftp_path:
            # Vendor non mappato -> skip FTP, marca come SKIPPED
            self._update_export_status(id_esportazione, 'SKIPPED',
                                       f'Vendor {vendor} non mappato per FTP')
            return {
                'success': True,
                'skipped': True,
                'message': f'Vendor {vendor} non configurato per invio FTP'
            }

        # Aggiorna stato a SENDING
        self._update_export_status(id_esportazione, 'SENDING')

        files_sent = []
        errors = []

        # Invia TO_T
        if file_to_t:
            local_path_t = os.path.join(config.OUTPUT_DIR, file_to_t)
            remote_path_t = f"{ftp_path}/{file_to_t}"

            result_t = ftp_client.upload_file(local_path_t, remote_path_t, id_esportazione)
            if result_t['success']:
                files_sent.append(file_to_t)
            else:
                errors.append(f"TO_T: {result_t.get('error')}")

        # Invia TO_D
        if file_to_d:
            local_path_d = os.path.join(config.OUTPUT_DIR, file_to_d)
            remote_path_d = f"{ftp_path}/{file_to_d}"

            result_d = ftp_client.upload_file(local_path_d, remote_path_d, id_esportazione)
            if result_d['success']:
                files_sent.append(file_to_d)
            else:
                errors.append(f"TO_D: {result_d.get('error')}")

        # Verifica risultato
        expected_files = 2 if file_to_t and file_to_d else 1
        if len(files_sent) == expected_files:
            # Successo completo
            self._update_export_status(
                id_esportazione, 'SENT',
                ftp_path=ftp_path,
                files_sent=files_sent
            )
            # Aggiorna stato ordini collegati: VALIDATO → ESPORTATO/PARZ_ESPORTATO
            self._update_ordini_stato_esportato(id_esportazione)
            return {'success': True, 'files_sent': files_sent, 'ftp_path': ftp_path}
        else:
            # Fallimento parziale o totale
            error_msg = '; '.join(errors)
            self._increment_retry(id_esportazione, error_msg)
            return {'success': False, 'error': error_msg, 'files_sent': files_sent}

    def _update_export_status(
        self,
        id_esportazione: int,
        stato: str,
        error: Optional[str] = None,
        ftp_path: Optional[str] = None,
        files_sent: Optional[List[str]] = None
    ):
        """Aggiorna stato esportazione FTP."""
        updates = ["stato_ftp = %s"]
        params = [stato]

        if stato == 'SENT':
            updates.append("data_invio_ftp = CURRENT_TIMESTAMP")

        if error:
            updates.append("ultimo_errore_ftp = %s")
            params.append(error)

        if ftp_path:
            updates.append("ftp_path_remoto = %s")
            params.append(ftp_path)

        if files_sent:
            updates.append("ftp_file_inviati = %s")
            params.append(json.dumps(files_sent))

        params.append(id_esportazione)

        self.db.execute(f"""
            UPDATE esportazioni
            SET {', '.join(updates)}
            WHERE id_esportazione = %s
        """, params)
        self.db.commit()

    def _update_ordini_stato_esportato(self, id_esportazione: int):
        """
        Aggiorna stato ordini collegati all'esportazione dopo invio FTP con successo.

        Per ogni ordine in stato VALIDATO:
        - Se tutte le righe (non child) hanno q_evasa >= q_totale → ESPORTATO
        - Altrimenti → PARZ_ESPORTATO
        """
        # Recupera tutti gli id_testata collegati all'esportazione
        testate = self.db.execute("""
            SELECT DISTINCT ed.id_testata
            FROM esportazioni_dettaglio ed
            JOIN ordini_testata ot ON ed.id_testata = ot.id_testata
            WHERE ed.id_esportazione = %s
              AND ot.stato = 'VALIDATO'
        """, (id_esportazione,)).fetchall()

        for row in testate:
            id_testata = row['id_testata']

            stats = self.db.execute("""
                SELECT
                    COUNT(*) as totale,
                    SUM(CASE
                        WHEN q_evasa >= (COALESCE(q_venduta,0) + COALESCE(q_sconto_merce,0) + COALESCE(q_omaggio,0))
                             AND (COALESCE(q_venduta,0) + COALESCE(q_sconto_merce,0) + COALESCE(q_omaggio,0)) > 0
                        THEN 1 ELSE 0 END) as complete
                FROM ORDINI_DETTAGLIO
                WHERE id_testata = %s AND (is_child = FALSE OR is_child IS NULL)
            """, (id_testata,)).fetchone()

            totale = stats['totale'] or 0
            complete = stats['complete'] or 0

            if totale > 0 and complete == totale:
                nuovo_stato = 'ESPORTATO'
            else:
                nuovo_stato = 'PARZ_ESPORTATO'

            self.db.execute("""
                UPDATE ORDINI_TESTATA
                SET stato = %s
                WHERE id_testata = %s AND stato = 'VALIDATO'
            """, (nuovo_stato, id_testata))

        self.db.commit()

    def _increment_retry(self, id_esportazione: int, error: str):
        """Incrementa contatore retry e aggiorna stato."""
        # Recupera tentativi attuali
        export = self.db.execute("""
            SELECT tentativi_ftp FROM esportazioni WHERE id_esportazione = %s
        """, (id_esportazione,)).fetchone()

        tentativi = (export['tentativi_ftp'] or 0) + 1

        # Recupera max tentativi
        ftp_config = self.db.execute("""
            SELECT max_tentativi FROM ftp_config WHERE ftp_enabled = TRUE LIMIT 1
        """).fetchone()
        max_tentativi = ftp_config['max_tentativi'] if ftp_config else 3

        if tentativi >= max_tentativi:
            nuovo_stato = 'FAILED'
        else:
            nuovo_stato = 'RETRY'

        self.db.execute("""
            UPDATE esportazioni
            SET stato_ftp = %s,
                tentativi_ftp = %s,
                ultimo_errore_ftp = %s
            WHERE id_esportazione = %s
        """, (nuovo_stato, tentativi, error, id_esportazione))
        self.db.commit()

    def get_failed_exports_for_alert(self) -> List[Dict[str, Any]]:
        """Recupera esportazioni FAILED che richiedono alert."""
        exports = self.db.execute("""
            SELECT e.*, ot.id_vendor as vendor, ot.numero_ordine_vendor
            FROM esportazioni e
            JOIN esportazioni_dettaglio ed ON e.id_esportazione = ed.id_esportazione
            JOIN ordini_testata ot ON ed.id_testata = ot.id_testata
            WHERE e.stato_ftp = 'FAILED'
            ORDER BY e.data_generazione DESC
        """).fetchall()

        return [dict(e) for e in exports]


def invia_tracciati_batch() -> Dict[str, Any]:
    """
    Funzione principale per invio batch tracciati via FTP.

    Chiamata dallo scheduler ogni 10 minuti.

    Returns:
        {
            success: bool,
            sent: int,
            failed: int,
            skipped: int,
            errors: list
        }
    """
    db = get_db()

    # Verifica se FTP e abilitato
    ftp_config = db.execute("""
        SELECT * FROM ftp_config WHERE ftp_enabled = TRUE AND batch_enabled = TRUE LIMIT 1
    """).fetchone()

    if not ftp_config:
        return {
            'success': True,
            'message': 'FTP batch non abilitato',
            'sent': 0, 'failed': 0, 'skipped': 0
        }

    sender = FTPSender()
    pending = sender.get_pending_exports()

    if not pending:
        return {
            'success': True,
            'message': 'Nessuna esportazione da inviare',
            'sent': 0, 'failed': 0, 'skipped': 0
        }

    results = {
        'sent': 0,
        'failed': 0,
        'skipped': 0,
        'errors': []
    }

    try:
        # Connetti FTP
        ftp_client = get_ftp_client_from_config()
        with ftp_client:
            # Processa ogni esportazione
            processed_ids = set()
            for export in pending:
                id_exp = export['id_esportazione']
                if id_exp in processed_ids:
                    continue
                processed_ids.add(id_exp)

                result = sender.send_export(id_exp, ftp_client)

                if result.get('skipped'):
                    results['skipped'] += 1
                elif result['success']:
                    results['sent'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'id_esportazione': id_exp,
                        'error': result.get('error')
                    })

    except Exception as e:
        results['errors'].append({'error': f'Errore connessione FTP: {str(e)}'})
        log_operation('FTP_BATCH_ERROR', 'esportazioni', 0, str(e), operatore='SCHEDULER')

    # Invia alert se ci sono fallimenti definitivi
    failed_exports = sender.get_failed_exports_for_alert()
    if failed_exports:
        _send_failure_alert(failed_exports)

    # Log operazione batch
    log_operation('FTP_BATCH', 'esportazioni', 0,
                 f"Batch FTP: {results['sent']} inviati, {results['failed']} falliti, {results['skipped']} skippati",
                 operatore='SCHEDULER')

    results['success'] = results['failed'] == 0
    return results


def _send_failure_alert(failed_exports: List[Dict[str, Any]]):
    """Invia email alert per esportazioni fallite."""
    try:
        from ..email.sender import EmailSender

        db = get_db()

        # Recupera lista email admin
        email_config = db.execute("""
            SELECT admin_notifica_email FROM email_config LIMIT 1
        """).fetchone()

        if not email_config or not email_config['admin_notifica_email']:
            return

        recipients = email_config['admin_notifica_email']

        # Costruisci corpo email
        body = """
        <h2>ALERT: Fallimento invio tracciati FTP</h2>
        <p>I seguenti tracciati NON sono stati inviati al server FTP dopo tutti i tentativi:</p>
        <table border="1" cellpadding="5">
            <tr>
                <th>ID Esportazione</th>
                <th>Vendor</th>
                <th>Ordine</th>
                <th>File TO_T</th>
                <th>File TO_D</th>
                <th>Errore</th>
            </tr>
        """

        for exp in failed_exports:
            body += f"""
            <tr>
                <td>{exp['id_esportazione']}</td>
                <td>{exp.get('vendor', 'N/A')}</td>
                <td>{exp.get('numero_ordine_vendor', 'N/A')}</td>
                <td>{exp.get('nome_file_to_t', 'N/A')}</td>
                <td>{exp.get('nome_file_to_d', 'N/A')}</td>
                <td>{exp.get('ultimo_errore_ftp', 'N/A')}</td>
            </tr>
            """

        body += """
        </table>
        <p>Verificare la connessione FTP e riprovare manualmente.</p>
        <p><em>SERV.O Sistema Automatico</em></p>
        """

        sender = EmailSender(db)
        sender.send(
            to=recipients,
            subject=f"[SERV.O ALERT] Fallimento invio FTP - {len(failed_exports)} tracciati",
            body_html=body,
            email_type='ftp_alert'
        )

        # Marca esportazioni come "alert inviato"
        for exp in failed_exports:
            db.execute("""
                UPDATE esportazioni
                SET stato_ftp = 'ALERT_SENT',
                    note = COALESCE(note || ' | ', '') || %s
                WHERE id_esportazione = %s
            """, (f'Alert email inviato {datetime.now().isoformat()}', exp['id_esportazione']))

        db.commit()

    except Exception as e:
        print(f"Errore invio alert FTP: {e}")
        log_operation('FTP_ALERT_ERROR', 'esportazioni', 0, str(e), operatore='SCHEDULER')
