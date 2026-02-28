# =============================================================================
# SERV.O v7.0 - EXPORT GENERATOR
# =============================================================================
# Logica principale generazione tracciati TO_T/TO_D
# =============================================================================

import os
import re
import time
from typing import Dict, Any, List
from datetime import datetime

from ...config import config
from ...database_pg import get_db, log_operation
from ...utils import calcola_q_totale
from ..supervisione import può_emettere_tracciato
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


def generate_tracciati_per_ordine(
    output_dir: str = None,
    ordini_ids: List[int] = None
) -> List[Dict[str, Any]]:
    """
    Genera file tracciato TO_T e TO_D - UN FILE PER OGNI ORDINE.

    Args:
        output_dir: Directory output (default: config.OUTPUT_DIR)
        ordini_ids: Lista ID ordini da esportare (default: tutti pronti)

    Returns:
        Lista di dict con info sui file generati
    """
    db = get_db()
    output_dir = output_dir or config.OUTPUT_DIR

    # Crea directory se non esiste
    os.makedirs(output_dir, exist_ok=True)

    # Query ordini
    if ordini_ids:
        placeholders = ','.join(['?' for _ in ordini_ids])
        query = f"""
            SELECT * FROM V_ORDINI_COMPLETI
            WHERE id_testata IN ({placeholders})
            AND lookup_method != 'NESSUNO'
            ORDER BY vendor, numero_ordine_vendor
        """
        ordini = db.execute(query, ordini_ids).fetchall()
    else:
        ordini = db.execute("""
            SELECT * FROM V_ORDINI_COMPLETI
            WHERE stato NOT IN ('SCARTATO', 'PENDING_REVIEW')
            AND lookup_method != 'NESSUNO'
            AND stato != 'ESPORTATO'
            ORDER BY vendor, numero_ordine_vendor
        """).fetchall()

    if not ordini:
        return []

    results = []

    for ordine in ordini:
        ordine_dict = dict(ordine)
        id_testata = ordine_dict['id_testata']
        # Supporta sia 'numero_ordine' che 'numero_ordine_vendor'
        numero_ordine = ordine_dict.get('numero_ordine') or ordine_dict.get('numero_ordine_vendor') or ''
        # Suffisso incrementale per evitare duplicati nel sistema ricevente
        suffix = _get_export_suffix(db, id_testata)
        numero_ordine_tracciato = f"{numero_ordine}.{suffix}"
        ordine_dict['numero_ordine'] = numero_ordine_tracciato
        vendor = ordine_dict['vendor']

        # v11.2: Recupera deposito_riferimento per codice vendor nel tracciato
        deposito_row = db.execute("""
            SELECT deposito_riferimento FROM ordini_testata WHERE id_testata = ?
        """, (id_testata,)).fetchone()
        ordine_dict['deposito_riferimento'] = deposito_row['deposito_riferimento'] if deposito_row else None

        # v11.3: Verifica deposito_riferimento - solo CT e CL sono abilitati per tracciati
        DEPOSITI_ABILITATI = ('CT', 'CL')
        deposito = ordine_dict.get('deposito_riferimento')
        if not deposito or deposito.upper() not in DEPOSITI_ABILITATI:
            continue  # Skip ordini senza deposito valido

        # Verifica se ordine puo essere esportato (nessuna supervisione pending)
        if not può_emettere_tracciato(id_testata):
            continue

        # Carica dettagli
        dettagli = db.execute("""
            SELECT d.*, v.min_id
            FROM V_DETTAGLI_COMPLETI d
            JOIN V_ORDINI_COMPLETI v ON d.id_testata = v.id_testata
            WHERE d.id_testata = ?
            ORDER BY d.n_riga
        """, (id_testata,)).fetchall()

        # v11.3: Nome file con formato TO_T_AAMMGG_HHMMSS.txt
        # Anti-collisione: se file esiste, aspetta 1 sec e rigenera
        timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
        filename_t = f"TO_T_{timestamp}.txt"
        filename_d = f"TO_D_{timestamp}.txt"
        path_t = os.path.join(output_dir, filename_t)
        path_d = os.path.join(output_dir, filename_d)

        max_retries = 5
        retry_count = 0
        while (os.path.exists(path_t) or os.path.exists(path_d)) and retry_count < max_retries:
            time.sleep(1)
            timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
            filename_t = f"TO_T_{timestamp}.txt"
            filename_d = f"TO_D_{timestamp}.txt"
            path_t = os.path.join(output_dir, filename_t)
            path_d = os.path.join(output_dir, filename_d)
            retry_count += 1

        # Genera TO_T (una sola riga per questo ordine)
        line_t = generate_to_t_line(ordine_dict)

        # Genera TO_D
        lines_d = []
        for det in dettagli:
            det_dict = dict(det)
            # Salta solo child (i parent espositore vanno inclusi!)
            # I child sono gia aggregati nel parent
            if det_dict.get('is_child'):
                continue

            # Aggiungi dati testata al dettaglio
            det_dict['numero_ordine'] = numero_ordine_tracciato
            det_dict['min_id'] = ordine_dict.get('min_id') or ''
            det_dict['codice_sito'] = ordine_dict.get('anag_codice_sito')

            # v11.5: VALIDAZIONE RIGIDA QUANTITÀ TRACCIATO
            # Verifica che il totale nel tracciato non superi q_da_evadere
            q_venduta = int(det_dict.get('q_venduta') or 0)
            q_sconto_merce = int(det_dict.get('q_sconto_merce') or 0)
            q_omaggio = int(det_dict.get('q_omaggio') or 0)
            q_da_evadere = det_dict.get('q_da_evadere')
            totale_tracciato = q_venduta + q_sconto_merce + q_omaggio

            if q_da_evadere is not None:
                q_da_evadere = int(q_da_evadere) if q_da_evadere else 0
                det_dict['_q_da_evadere_originale'] = q_da_evadere
                if totale_tracciato > q_da_evadere:
                    # Skip riga con errore e logga warning
                    continue

            # Workaround ERP DOC: prezzo × quantità
            _applica_workaround_erp_doc(det_dict, vendor)

            line = generate_to_d_line(det_dict)
            lines_d.append(line)

        # Scrivi file
        with open(path_t, 'w', encoding=config.ENCODING) as f:
            f.write(line_t + '\r\n')

        with open(path_d, 'w', encoding=config.ENCODING) as f:
            f.write('\r\n'.join(lines_d))
            if lines_d:
                f.write('\r\n')

        # Aggiorna stato ordine
        db.execute(
            "UPDATE ORDINI_TESTATA SET stato = 'ESPORTATO' WHERE id_testata = ?",
            (id_testata,)
        )

        results.append({
            'id_testata': id_testata,
            'numero_ordine': numero_ordine,
            'vendor': vendor,
            'file_to_t': filename_t,
            'file_to_d': filename_d,
            'path_to_t': path_t,
            'path_to_d': path_d,
            'num_righe': len(lines_d)
        })

    # Registra esportazione complessiva
    if results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        cursor = db.execute("""
            INSERT INTO ESPORTAZIONI
            (nome_tracciato_generato, data_tracciato, nome_file_to_t, nome_file_to_d,
             num_testate, num_dettagli, stato)
            VALUES (?, ?, ?, ?, ?, ?, 'GENERATO')
        """, (
            timestamp,
            datetime.now().strftime('%Y-%m-%d'),
            f"{len(results)} file TO_T",
            f"{len(results)} file TO_D",
            len(results),
            sum(r['num_righe'] for r in results)
        ))

        id_esportazione = cursor.lastrowid

        # Registra dettaglio esportazione
        for r in results:
            db.execute("""
                INSERT INTO ESPORTAZIONI_DETTAGLIO (id_esportazione, id_testata)
                VALUES (?, ?)
            """, (id_esportazione, r['id_testata']))

        log_operation('GENERA_TRACCIATI', 'ESPORTAZIONI', id_esportazione,
                     f"Generati {len(results)} tracciati")

    db.commit()
    return results


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

    # v11.3: Verifica deposito_riferimento - solo CT e CL sono abilitati per tracciati
    DEPOSITI_ABILITATI = ('CT', 'CL')
    deposito = ordine_dict.get('deposito_riferimento')
    if not deposito:
        return {
            'success': False,
            'error': 'Deposito di riferimento non specificato. Impossibile generare tracciato.'
        }
    if deposito.upper() not in DEPOSITI_ABILITATI:
        return {
            'success': False,
            'error': f'Deposito "{deposito}" non abilitato per generazione tracciati. Depositi validi: {", ".join(DEPOSITI_ABILITATI)}'
        }

    # 1a. Verifica stato ordine - blocca generazione per stati non validi
    stato_ordine = ordine_dict.get('stato', 'ESTRATTO')
    stati_bloccanti = {
        'PENDING_REVIEW': 'IN REVISIONE',
        'ANOMALIA': 'ANOMALIA',
    }
    if stato_ordine in stati_bloccanti:
        stato_label = stati_bloccanti[stato_ordine]
        return {
            'success': False,
            'error': f'Ordine in stato {stato_label}. Impossibile generare tracciato. Risolvere le anomalie prima di procedere.'
        }

    # v11.4: Verifica supervisioni pending - blocco anche se stato non è PENDING_REVIEW
    # Inclusa supervisione_prezzo
    supervisioni_pending = db.execute("""
        SELECT
            (SELECT COUNT(*) FROM supervisione_espositore WHERE id_testata = %s AND stato = 'PENDING') +
            (SELECT COUNT(*) FROM supervisione_listino WHERE id_testata = %s AND stato = 'PENDING') +
            (SELECT COUNT(*) FROM supervisione_lookup WHERE id_testata = %s AND stato = 'PENDING') +
            (SELECT COUNT(*) FROM supervisione_aic WHERE id_testata = %s AND stato = 'PENDING') +
            (SELECT COUNT(*) FROM supervisione_prezzo WHERE id_testata = %s AND stato = 'PENDING') as total
    """, (id_testata, id_testata, id_testata, id_testata, id_testata)).fetchone()

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

    # Suffisso incrementale per evitare duplicati nel sistema ricevente
    suffix = _get_export_suffix(db, id_testata)
    numero_ordine_tracciato = f"{numero_ordine}.{suffix}"
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

    # 6. Aggiorna stato righe esportate
    # LOGICA v6.2.1: q_evasa += q_da_evadere, poi q_da_evadere = 0
    righe_complete = 0
    righe_parziali = 0

    for det_dict in righe_esportate:
        id_dettaglio = det_dict['id_dettaglio']
        q_da_evadere = det_dict.get('_q_da_evadere_originale', 0) or det_dict.get('q_da_evadere', 0) or 0

        # Recupera riga originale per calcolo quantita
        riga_orig = db.execute("""
            SELECT q_venduta, q_sconto_merce, q_omaggio, q_evasa
            FROM ORDINI_DETTAGLIO WHERE id_dettaglio = ?
        """, (id_dettaglio,)).fetchone()

        if riga_orig:
            q_totale = calcola_q_totale(dict(riga_orig))
            q_evasa_precedente = riga_orig['q_evasa'] or 0
        else:
            q_totale = det_dict.get('q_venduta_originale') or det_dict.get('q_originale') or 0
            q_evasa_precedente = 0

        # FIX v6.2.2: Logica unificata per tutti i casi
        # q_evasa = quantita gia esportata in tracciati precedenti
        # q_da_evadere = quantita da esportare in QUESTO tracciato
        # nuovo_q_evasa = cumulativo dopo questo tracciato
        nuovo_q_evasa = q_evasa_precedente + q_da_evadere

        # Calcola residuo
        q_residua = q_totale - nuovo_q_evasa

        # v6.2.1: Determina nuovo stato dopo generazione tracciato
        # - EVASO: riga completamente evasa (q_evasa >= q_totale)
        # - PARZIALE: riga parzialmente evasa (0 < q_evasa < q_totale)
        # - ESTRATTO: nessuna evasione
        if q_totale > 0 and nuovo_q_evasa >= q_totale:
            nuovo_stato = 'EVASO'
            righe_complete += 1
        elif nuovo_q_evasa > 0:
            nuovo_stato = 'PARZIALE'
            righe_parziali += 1
        else:
            nuovo_stato = 'ESTRATTO'

        # Aggiorna riga: q_evasa += q_da_evadere, q_da_evadere = 0
        # ESCLUDI righe ARCHIVIATO - stato finale immutabile (v9.1)
        db.execute("""
            UPDATE ORDINI_DETTAGLIO
            SET stato_riga = ?,
                q_evasa = ?,
                q_da_evadere = 0,
                q_residua = ?,
                confermato_da = ?,
                data_conferma = ?,
                num_esportazioni = COALESCE(num_esportazioni, 0) + 1,
                ultima_esportazione = ?,
                id_ultima_esportazione = ?
            WHERE id_dettaglio = ?
              AND stato_riga != 'ARCHIVIATO'
        """, (
            nuovo_stato, nuovo_q_evasa, q_residua, operatore, now.isoformat(),
            now.isoformat(), id_esportazione, id_dettaglio
        ))

    # 7. AGGIORNA STATO TUTTE LE RIGHE dell'ordine
    # Corregge lo stato anche per righe non processate in questo tracciato
    # (es. righe gia evase in tracciati precedenti)

    # Righe completamente evase -> EVASO (escluso ARCHIVIATO)
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'EVASO'
        WHERE id_testata = ?
          AND (is_child = FALSE OR is_child IS NULL)
          AND q_evasa >= (COALESCE(q_venduta,0) + COALESCE(q_sconto_merce,0) + COALESCE(q_omaggio,0))
          AND (COALESCE(q_venduta,0) + COALESCE(q_sconto_merce,0) + COALESCE(q_omaggio,0)) > 0
          AND stato_riga != 'ARCHIVIATO'
    """, (id_testata,))

    # Righe parzialmente evase -> PARZIALE (escluso ARCHIVIATO)
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'PARZIALE'
        WHERE id_testata = ?
          AND (is_child = FALSE OR is_child IS NULL)
          AND q_evasa > 0
          AND q_evasa < (COALESCE(q_venduta,0) + COALESCE(q_sconto_merce,0) + COALESCE(q_omaggio,0))
          AND stato_riga != 'ARCHIVIATO'
    """, (id_testata,))

    # Righe con q_da_evadere > 0 ma non ancora esportate -> CONFERMATO (escluso ARCHIVIATO)
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'CONFERMATO'
        WHERE id_testata = ?
          AND (is_child = FALSE OR is_child IS NULL)
          AND (q_evasa IS NULL OR q_evasa = 0)
          AND q_da_evadere > 0
          AND stato_riga != 'ARCHIVIATO'
    """, (id_testata,))

    # Righe senza evasione e senza q_da_evadere -> ESTRATTO (escluso ARCHIVIATO)
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'ESTRATTO'
        WHERE id_testata = ?
          AND (is_child = FALSE OR is_child IS NULL)
          AND (q_evasa IS NULL OR q_evasa = 0)
          AND (q_da_evadere IS NULL OR q_da_evadere = 0)
          AND stato_riga != 'ARCHIVIATO'
    """, (id_testata,))

    # 8. Verifica stato complessivo ordine
    # Conta righe totali e righe completamente evase
    # v6.2: q_totale = q_venduta + q_sconto_merce + q_omaggio
    stats = db.execute("""
        SELECT
            COUNT(*) as totale,
            SUM(CASE
                WHEN q_evasa >= (COALESCE(q_venduta,0) + COALESCE(q_sconto_merce,0) + COALESCE(q_omaggio,0))
                     AND (COALESCE(q_venduta,0) + COALESCE(q_sconto_merce,0) + COALESCE(q_omaggio,0)) > 0
                THEN 1 ELSE 0 END) as complete,
            SUM(CASE
                WHEN q_evasa > 0
                     AND q_evasa < (COALESCE(q_venduta,0) + COALESCE(q_sconto_merce,0) + COALESCE(q_omaggio,0))
                THEN 1 ELSE 0 END) as parziali,
            SUM(CASE WHEN q_evasa IS NULL OR q_evasa = 0 THEN 1 ELSE 0 END) as non_evase
        FROM ORDINI_DETTAGLIO
        WHERE id_testata = ? AND (is_child = FALSE OR is_child IS NULL)
    """, (id_testata,)).fetchone()

    totale_righe = stats['totale'] or 0
    righe_complete_tot = stats['complete'] or 0
    righe_parziali_tot = stats['parziali'] or 0
    righe_non_evase = stats['non_evase'] or 0

    # 8. Aggiorna stato ordine: VALIDATO dopo generazione tracciato
    # Lo stato ESPORTATO/PARZ_ESPORTATO verrà assegnato dopo invio FTP
    # EVASO/PARZ_EVASO saranno gestiti manualmente (fase futura)
    if righe_complete_tot > 0 or righe_parziali_tot > 0:
        db.execute("""
            UPDATE ORDINI_TESTATA
            SET stato = 'VALIDATO',
                data_validazione = COALESCE(data_validazione, datetime('now')),
                validato_da = COALESCE(validato_da, ?)
            WHERE id_testata = ?
        """, (operatore, id_testata))
        stato_ordine = 'VALIDATO'
    else:
        # Nessuna riga evasa - mantieni stato precedente
        stato_ordine = ordine_dict.get('stato', 'ESTRATTO')

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

    db.commit()

    log_operation('VALIDA_TRACCIATO', 'ORDINI_TESTATA', id_testata,
                 f"Generato tracciato: {len(lines_d)} righe. Stato ordine: {stato_ordine}",
                 operatore=operatore)

    # Costruisci messaggio con eventuali warning
    message = f"Tracciato generato: {len(lines_d)} righe esportate. Stato ordine: {stato_ordine}"
    if validation_warnings:
        message += f"\n\nAvvisi: {len(validation_warnings)}"
        for w in validation_warnings:
            message += f"\n- {w}"

    return {
        'success': True,
        'id_testata': id_testata,
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
            'righe_complete': righe_complete_tot,
            'righe_parziali': righe_parziali_tot,
            'righe_non_evase': righe_non_evase
        },
        'validation_warnings': validation_warnings,
        'message': message
    }
