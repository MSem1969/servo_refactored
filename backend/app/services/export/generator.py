# =============================================================================
# SERV.O v7.0 - EXPORT GENERATOR
# =============================================================================
# Logica principale generazione tracciati TO_T/TO_D
# =============================================================================

import os
import re
import time
from typing import Dict, Any
from datetime import datetime

from ...config import config
from ...database_pg import get_db, log_operation
from .formatters import generate_to_t_line, generate_to_d_line
from .validators import valida_campi_tracciato


def _applica_workaround_erp_doc(det_dict: dict, vendor: str) -> None:
    """
    Workaround bug ERP DOC_GENERICI: l'ERP tratta il prezzo unitario come
    valore complessivo riga e lo divide per quantità.
    Moltiplichiamo prezzo × q_venduta così dopo la divisione ERP
    il prezzo unitario risulta corretto.

    Da rimuovere quando il bug ERP sarà corretto.
    """
    if vendor != 'DOC_GENERICI':
        return

    q_venduta = int(det_dict.get('q_venduta') or 0)
    if q_venduta <= 0:
        return

    # Risolvi fallback prezzo_scontare -> prezzo_listino (come in to_d.py)
    prezzo_scontare = float(det_dict.get('prezzo_scontare') or det_dict.get('prezzo_listino') or 0)

    for campo, valore in [
        ('prezzo_netto', float(det_dict.get('prezzo_netto') or 0)),
        ('prezzo_scontare', prezzo_scontare),
        ('prezzo_pubblico', float(det_dict.get('prezzo_pubblico') or 0)),
    ]:
        det_dict[campo] = valore * q_venduta


def _get_export_suffix(db, id_testata: int) -> int:
    """Conta esportazioni precedenti per questo ordine e restituisce il prossimo numero."""
    count = db.execute(
        "SELECT COUNT(*) FROM esportazioni_dettaglio WHERE id_testata = %s",
        (id_testata,)
    ).fetchone()[0]
    return count + 1  # Il corrente INSERT avviene dopo la generazione


def _apply_export_suffix(numero_ordine: str, db, id_testata: int, force: bool = False) -> str:
    """
    Applica il suffisso `.N` al numero ordine per il tracciato EDI.

    Modalita' normale (force=False):
      - Se `numero_ordine` contiene gia' un punto (es. clone parziale "ORD001.2"),
        il numero e' restituito invariato: il suffisso e' gia' materializzato in
        `numero_ordine_vendor` del clone.
      - Altrimenti applica `.N` calcolato da `esportazioni_dettaglio`.

    Modalita' riemissione (force=True):
      - Applica SEMPRE `.N` come tail, anche se il numero contiene gia' un punto.
        Es. "ORD001" -> "ORD001.2", "ORD001.2" -> "ORD001.2.3".
        Necessario per evitare collisioni quando si riemette un clone parziale.
    """
    if not force and '.' in (numero_ordine or ''):
        return numero_ordine
    suffix = _get_export_suffix(db, id_testata)
    return f"{numero_ordine}.{suffix}"


def valida_e_genera_tracciato(
    id_testata: int,
    operatore: str,
    validazione_massiva: bool = False
) -> Dict[str, Any]:
    """
    Valida e genera tracciato TO_T/TO_D per un ordine.

    LOGICA v6.2:
    - Se validazione_massiva=True (Dashboard): conferma TUTTE le righe, copia q_venduta->q_evasa
    - Se validazione_massiva=False (Dettaglio): esporta SOLO righe gia CONFERMATE con q_evasa > 0

    Args:
        id_testata: ID ordine
        operatore: Nome operatore
        validazione_massiva: Se True, conferma tutte le righe prima dell'export

    Returns:
        Dict con success, file paths, statistiche
    """
    db = get_db()
    now = datetime.now()
    timestamp = now.strftime('%Y%m%d_%H%M%S')

    # 1. Carica ordine
    ordine = db.execute("""
        SELECT * FROM V_ORDINI_COMPLETI WHERE id_testata = ?
    """, (id_testata,)).fetchone()

    if not ordine:
        return {'success': False, 'error': 'Ordine non trovato'}

    ordine_dict = dict(ordine)
    # Normalizza numero_ordine (supporta sia 'numero_ordine' che 'numero_ordine_vendor')
    ordine_dict['numero_ordine'] = ordine_dict.get('numero_ordine') or ordine_dict.get('numero_ordine_vendor') or ''

    # v11.2: Recupera deposito_riferimento per codice vendor nel tracciato
    deposito_row = db.execute("""
        SELECT deposito_riferimento FROM ordini_testata WHERE id_testata = %s
    """, (id_testata,)).fetchone()
    ordine_dict['deposito_riferimento'] = deposito_row['deposito_riferimento'] if deposito_row else None

    # 1a. Verifica stato ordine - blocca generazione per stati ANOMALIA
    stato_ordine = ordine_dict.get('stato', 'ESTRATTO')
    if stato_ordine == 'ANOMALIA':
        return {
            'success': False,
            'error': 'Ordine in stato ANOMALIA. Impossibile generare tracciato. Risolvere le anomalie prima di procedere.'
        }

    # v11.4: Verifica supervisioni pending - blocca anche se stato != ANOMALIA
    # Inclusa supervisione_prezzo
    # v12.0: Aggiunta supervisione_erp al conteggio pending
    supervisioni_pending = db.execute("""
        SELECT
            (SELECT COUNT(*) FROM supervisione_espositore WHERE id_testata = %s AND stato = 'PENDING') +
            (SELECT COUNT(*) FROM supervisione_listino WHERE id_testata = %s AND stato = 'PENDING') +
            (SELECT COUNT(*) FROM supervisione_lookup WHERE id_testata = %s AND stato = 'PENDING') +
            (SELECT COUNT(*) FROM supervisione_aic WHERE id_testata = %s AND stato = 'PENDING') +
            (SELECT COUNT(*) FROM supervisione_prezzo WHERE id_testata = %s AND stato = 'PENDING') +
            COALESCE((SELECT COUNT(*) FROM supervisione_erp WHERE id_testata = %s AND stato = 'PENDING'), 0) as total
    """, (id_testata, id_testata, id_testata, id_testata, id_testata, id_testata)).fetchone()

    if supervisioni_pending and supervisioni_pending['total'] > 0:
        return {
            'success': False,
            'error': f'Ordine ha {supervisioni_pending["total"]} supervisioni in attesa. Risolvere le supervisioni prima di generare il tracciato.'
        }

    # 1c. Verifica anomalie aperte bloccanti
    anomalie_aperte = db.execute("""
        SELECT COUNT(*) as cnt FROM anomalie
        WHERE id_testata = %s
        AND stato IN ('APERTA', 'IN_GESTIONE')
        AND livello IN ('ERRORE', 'CRITICO')
    """, (id_testata,)).fetchone()

    if anomalie_aperte and anomalie_aperte['cnt'] > 0:
        return {
            'success': False,
            'error': f'Ordine ha {anomalie_aperte["cnt"]} anomalie bloccanti non risolte. Risolvere le anomalie prima di generare il tracciato.'
        }

    # 1b. Verifica che l'ordine abbia righe
    righe_count = db.execute("""
        SELECT COUNT(*) FROM ORDINI_DETTAGLIO
        WHERE id_testata = ? AND (is_child = FALSE OR is_child IS NULL)
    """, (id_testata,)).fetchone()[0]

    if righe_count == 0:
        return {'success': False, 'error': 'Impossibile generare tracciato: ordine senza righe dettaglio.'}

    # 2. VALIDAZIONE MASSIVA - FIX v6.2.3
    # Logica basata su STATO ORDINE (testata):
    # - Ordine CONFERMATO (pronto export) -> NON toccare q_da_evadere, usa valori esistenti
    # - Ordine ESTRATTO/altri -> imposta q_da_evadere = q_totale per evasione totale
    if validazione_massiva:
        stato_ordine = ordine_dict.get('stato', 'ESTRATTO')

        # Se ordine NON e gia CONFERMATO, imposta q_da_evadere = q_totale per tutte le righe
        if stato_ordine != 'CONFERMATO':
            # Imposta q_da_evadere = q_totale per righe parent
            db.execute("""
                UPDATE ORDINI_DETTAGLIO
                SET q_da_evadere = COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0),
                    stato_riga = 'CONFERMATO'
                WHERE id_testata = ?
                  AND (is_child = FALSE OR is_child IS NULL)
                  AND stato_riga NOT IN ('EVASO', 'PARZIALE', 'ARCHIVIATO')
                  AND (COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0)) > 0
            """, (id_testata,))

            # Imposta q_da_evadere = q_totale per CHILD_ESPOSITORE
            db.execute("""
                UPDATE ORDINI_DETTAGLIO
                SET q_da_evadere = COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0),
                    stato_riga = 'CONFERMATO'
                WHERE id_testata = ?
                  AND is_child = TRUE
                  AND stato_riga NOT IN ('EVASO', 'PARZIALE', 'ARCHIVIATO')
            """, (id_testata,))
            db.commit()
        # else: Ordine CONFERMATO -> q_da_evadere gia impostato, non modificare

        # Carica righe con q_da_evadere > 0 (sia per ordini CONFERMATO che altri)
        # ESCLUDI righe ARCHIVIATO - stato finale immutabile (v9.1)
        dettagli = db.execute("""
            SELECT * FROM ORDINI_DETTAGLIO
            WHERE id_testata = ?
              AND COALESCE(q_da_evadere, 0) > 0
              AND (is_child = FALSE OR is_child IS NULL)
              AND stato_riga != 'ARCHIVIATO'
            ORDER BY n_riga
        """, (id_testata,)).fetchall()

        if not dettagli:
            return {
                'success': False,
                'error': 'Impossibile generare tracciato: quantità da evadere = 0 per tutte le righe. Confermare le righe o impostare le quantità da evadere.'
            }
    else:
        # Per dettaglio: carica righe con q_da_evadere > 0 (quantita da esportare in questo tracciato)
        # ESCLUDI righe ARCHIVIATO - stato finale immutabile (v9.1)
        dettagli = db.execute("""
            SELECT * FROM ORDINI_DETTAGLIO
            WHERE id_testata = ?
              AND q_da_evadere > 0
              AND (is_child = FALSE OR is_child IS NULL)
              AND stato_riga != 'ARCHIVIATO'
            ORDER BY n_riga
        """, (id_testata,)).fetchall()

        if not dettagli:
            return {
                'success': False,
                'error': 'Impossibile generare tracciato: quantità da evadere = 0 per tutte le righe. Inserire le quantità nella colonna "Da Evadere".'
            }

    # 3. VALIDAZIONE CAMPI OBBLIGATORI (v6.2.4)
    # Verifica campi TO_T e TO_D prima di generare
    validazione = valida_campi_tracciato(ordine_dict, dettagli)

    if not validazione['valid']:
        # Blocca generazione con errori dettagliati
        error_msg = "BLOCCO GENERAZIONE TRACCIATO\n\n"
        error_msg += "Campi obbligatori mancanti o non validi:\n"
        error_msg += "\n".join(f"- {e}" for e in validazione['errors'])

        if validazione['warnings']:
            error_msg += "\n\nAvvisi:\n"
            error_msg += "\n".join(f"- {w}" for w in validazione['warnings'])

        return {
            'success': False,
            'error': error_msg,
            'validation_errors': validazione['errors'],
            'validation_warnings': validazione['warnings']
        }

    # Se ci sono solo warning, li includeremo nella risposta finale
    validation_warnings = validazione['warnings']

    # 4. Genera tracciati
    numero_ordine = ordine_dict['numero_ordine']
    vendor = ordine_dict['vendor']

    # Suffisso incrementale, salvo per cloni parziali con suffisso gia' nel DB
    numero_ordine_tracciato = _apply_export_suffix(numero_ordine, db, id_testata)
    ordine_dict['numero_ordine'] = numero_ordine_tracciato

    # v11.3: Nome file con formato TO_T_AAMMGG_HHMMSS.txt
    # Verifica collisione: se file esiste, aspetta 1 sec e rigenera timestamp
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
    filename_t = f"TO_T_{timestamp}.txt"
    filename_d = f"TO_D_{timestamp}.txt"
    path_t = os.path.join(config.OUTPUT_DIR, filename_t)
    path_d = os.path.join(config.OUTPUT_DIR, filename_d)

    # Anti-collisione: se file esiste, aspetta e rigenera
    max_retries = 5
    retry_count = 0
    while (os.path.exists(path_t) or os.path.exists(path_d)) and retry_count < max_retries:
        time.sleep(1)
        timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
        filename_t = f"TO_T_{timestamp}.txt"
        filename_d = f"TO_D_{timestamp}.txt"
        path_t = os.path.join(config.OUTPUT_DIR, filename_t)
        path_d = os.path.join(config.OUTPUT_DIR, filename_d)
        retry_count += 1

    # Genera TO_T (testata)
    line_t = generate_to_t_line(ordine_dict)

    # Genera TO_D (dettagli) - usando q_da_evadere (quantita da esportare in QUESTO tracciato)
    lines_d = []
    righe_esportate = []

    try:
      for det in dettagli:
        det_dict = dict(det)

        # Prepara dati per tracciato
        det_dict['numero_ordine'] = numero_ordine_tracciato
        det_dict['min_id'] = ordine_dict.get('min_id') or ''
        det_dict['codice_sito'] = ordine_dict.get('anag_codice_sito')
        # Base per la stima data consegna quando la riga non ce l'ha
        det_dict['data_ordine'] = ordine_dict.get('data_ordine')

        # v11.5: VALIDAZIONE RIGIDA QUANTITÀ TRACCIATO
        # I valori nel tracciato devono corrispondere ESATTAMENTE ai valori originali
        # q_da_evadere è usato solo per controllo, NON per sovrascrivere le quantità
        q_da_evadere = det_dict.get('q_da_evadere', 0) or 0
        det_dict['_q_da_evadere_originale'] = q_da_evadere  # Salva per post-processing

        # Calcola quantità originali (valori da DB, NON modificati)
        q_venduta_orig = int(det_dict.get('q_venduta') or 0)
        q_sconto_merce_orig = int(det_dict.get('q_sconto_merce') or 0)
        q_omaggio_orig = int(det_dict.get('q_omaggio') or 0)
        q_totale_orig = q_venduta_orig + q_sconto_merce_orig + q_omaggio_orig

        # REGOLA: Se SalesQuantity è 0, DEVE restare 0 anche se ci sono omaggi
        # Il totale nel tracciato (SalesQuantity + QuantityFreePieces) non deve MAI
        # superare q_da_evadere (la quantità effettivamente da evadere)

        if q_da_evadere >= q_totale_orig:
            # Evasione totale: usa i valori originali SENZA modifiche
            # q_venduta resta il valore originale (può essere 0)
            pass  # I valori in det_dict sono già corretti dal DB
        else:
            # Evasione parziale: proporziona le quantità
            # Mantiene la proporzione originale tra q_venduta e omaggi
            if q_totale_orig > 0:
                ratio = q_da_evadere / q_totale_orig
                # Calcola le quantità proporzionate
                q_venduta_prop = int(q_venduta_orig * ratio)
                q_sconto_merce_prop = int(q_sconto_merce_orig * ratio)
                q_omaggio_prop = int(q_omaggio_orig * ratio)

                # Aggiusta arrotondamenti per garantire totale = q_da_evadere
                totale_prop = q_venduta_prop + q_sconto_merce_prop + q_omaggio_prop
                diff = q_da_evadere - totale_prop

                # Distribuisci la differenza (preferibilmente su q_venduta se > 0)
                if diff != 0:
                    if q_venduta_prop > 0:
                        q_venduta_prop += diff
                    elif q_omaggio_prop > 0:
                        q_omaggio_prop += diff
                    else:
                        q_sconto_merce_prop += diff

                det_dict['q_venduta'] = q_venduta_prop
                det_dict['q_sconto_merce'] = q_sconto_merce_prop
                det_dict['q_omaggio'] = q_omaggio_prop

        # VALIDAZIONE FINALE: verifica che il totale tracciato <= q_da_evadere
        q_venduta_final = int(det_dict.get('q_venduta') or 0)
        q_sconto_merce_final = int(det_dict.get('q_sconto_merce') or 0)
        q_omaggio_final = int(det_dict.get('q_omaggio') or 0)
        totale_tracciato = q_venduta_final + q_sconto_merce_final + q_omaggio_final

        if totale_tracciato > q_da_evadere:
            # Errore critico: le quantità nel tracciato superano quelle da evadere
            raise ValueError(
                f"Riga {det_dict.get('n_riga')}: totale tracciato ({totale_tracciato}) > "
                f"q_da_evadere ({q_da_evadere}). "
                f"Dettaglio: q_venduta={q_venduta_final}, q_sconto_merce={q_sconto_merce_final}, "
                f"q_omaggio={q_omaggio_final}"
            )

        # Workaround ERP DOC: prezzo × quantità
        _applica_workaround_erp_doc(det_dict, vendor)

        line = generate_to_d_line(det_dict)
        lines_d.append(line)
        righe_esportate.append(det_dict)

    except ValueError as e:
        # v11.5: Errore di validazione quantità - restituisci messaggio utente chiaro
        return {
            'success': False,
            'error': f"ERRORE VALIDAZIONE QUANTITÀ TRACCIATO\n\n{str(e)}\n\n"
                     "Il totale delle quantità nel tracciato (SalesQuantity + QuantityFreePieces) "
                     "non può superare la quantità da evadere. Verificare i dati dell'ordine."
        }

    # 4. Scrivi file
    with open(path_t, 'w', encoding=config.ENCODING) as f:
        f.write(line_t + '\r\n')

    with open(path_d, 'w', encoding=config.ENCODING) as f:
        f.write('\r\n'.join(lines_d))
        if lines_d:
            f.write('\r\n')

    # 5. Registra esportazione
    # v11.3: nome_tracciato_generato usa timestamp (es: 260127_143052)
    cursor = db.execute("""
        INSERT INTO ESPORTAZIONI
        (nome_tracciato_generato, data_tracciato, nome_file_to_t, nome_file_to_d,
         num_testate, num_dettagli, stato)
        VALUES (?, date('now'), ?, ?, 1, ?, 'GENERATO')
    """, (timestamp, filename_t, filename_d, len(lines_d)))

    id_esportazione = cursor.lastrowid

    db.execute("""
        INSERT INTO ESPORTAZIONI_DETTAGLIO (id_esportazione, id_testata)
        VALUES (?, ?)
    """, (id_esportazione, id_testata))

    # 6. Aggiorna stato righe esportate → ESPORTATO
    # NOTA: q_evasa NON viene modificato dall'export. L'evasione reale
    # avviene a registrazione bolla (routers/ordini.py aggiorna_evasione)
    # leggendo q_esportata che memorizza la quantita' di questo export.
    for det_dict in righe_esportate:
        id_dettaglio = det_dict['id_dettaglio']
        db.execute("""
            UPDATE ORDINI_DETTAGLIO
            SET stato_riga = 'ESPORTATO',
                q_esportata = COALESCE(q_da_evadere, 0),
                q_da_evadere = 0,
                confermato_da = ?,
                data_conferma = ?,
                num_esportazioni = COALESCE(num_esportazioni, 0) + 1,
                ultima_esportazione = ?,
                id_ultima_esportazione = ?
            WHERE id_dettaglio = ?
              AND stato_riga != 'ARCHIVIATO'
        """, (
            operatore, now.isoformat(), now.isoformat(),
            id_esportazione, id_dettaglio
        ))

    # 7. Aggiorna stato ordine: VALIDATO dopo generazione tracciato.
    # Lo stato ESPORTATO/PARZ_ESPORTATO verra' assegnato dopo invio FTP
    # (ftp/sender.py). EVASO/PARZ_EVASO solo a registrazione bolla.
    db.execute("""
        UPDATE ORDINI_TESTATA
        SET stato = 'VALIDATO',
            data_validazione = COALESCE(data_validazione, datetime('now')),
            validato_da = COALESCE(validato_da, ?)
        WHERE id_testata = ?
    """, (operatore, id_testata))
    stato_ordine = 'VALIDATO'

    # v11.0: Chiudi anomalie INFO e ATTENZIONE quando ordine viene validato
    # Le anomalie ERRORE e CRITICO devono essere risolte manualmente prima della validazione
    db.execute("""
        UPDATE anomalie
        SET stato = 'RISOLTA',
            data_risoluzione = %s,
            note_risoluzione = COALESCE(note_risoluzione || ' | ', '') || %s
        WHERE id_testata = %s
          AND stato IN ('APERTA', 'IN_GESTIONE')
          AND livello IN ('INFO', 'ATTENZIONE')
    """, (now.isoformat(), f'Chiusa automaticamente con validazione ordine (operatore: {operatore})', id_testata))

    # v11.6: Consegne ripartite. Se ci sono righe non archiviate con residuo
    # > 0 dopo l'export, genera clone parziale ".N" in stato ESTRATTO.
    # Stessa transazione del generator -> atomicita' garantita.
    from ..orders.fulfillment import crea_clone_parziale
    id_clone = crea_clone_parziale(id_testata, operatore=operatore)

    db.commit()

    log_operation('VALIDA_TRACCIATO', 'ORDINI_TESTATA', id_testata,
                 f"Generato tracciato: {len(lines_d)} righe. Stato ordine: {stato_ordine}",
                 operatore=operatore)

    if id_clone:
        log_operation('CREA_CLONE_PARZIALE', 'ORDINI_TESTATA', id_clone,
                     f"Clone parziale generato da id_testata={id_testata} (consegna ripartita)",
                     operatore=operatore)

    # Costruisci messaggio con eventuali warning
    message = f"Tracciato generato: {len(lines_d)} righe esportate. Stato ordine: {stato_ordine}"
    if validation_warnings:
        message += f"\n\nAvvisi: {len(validation_warnings)}"
        for w in validation_warnings:
            message += f"\n- {w}"
    if id_clone:
        message += f"\n\nConsegna ripartita: generato ordine .N (id_testata={id_clone}) con le righe residue."

    return {
        'success': True,
        'id_testata': id_testata,
        'id_clone_parziale': id_clone,
        'stato': stato_ordine,
        'tracciato': {
            'to_t': {
                'filename': filename_t,
                'path': path_t,
                'download_url': f"/api/v1/tracciati/download/{filename_t}"
            },
            'to_d': {
                'filename': filename_d,
                'path': path_d,
                'download_url': f"/api/v1/tracciati/download/{filename_d}",
                'num_righe': len(lines_d)
            }
        },
        'statistiche': {
            'righe_esportate': len(lines_d),
            # Conteggi EVASO/PARZIALE/non-evase non sono piu' disponibili
            # all'export: la transizione a EVASO avviene solo a registrazione
            # bolla. Mantenuti per retro-compat API (sempre 0 al momento dell'export).
            'righe_complete': 0,
            'righe_parziali': 0,
            'righe_non_evase': len(lines_d)
        },
        'validation_warnings': validation_warnings,
        'message': message
    }
