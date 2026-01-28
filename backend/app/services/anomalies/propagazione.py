# =============================================================================
# SERV.O v10.6 - PROPAGAZIONE ANOMALIE
# =============================================================================
# Servizio unificato per risoluzione anomalie con propagazione
#
# GERARCHIA DI PROPAGAZIONE:
# - ORDINE: Tutte le anomalie identiche dello stesso ordine (default)
# - GLOBALE: Tutte le anomalie identiche stesso vendor (solo Supervisore+)
#
# VINCOLI RUOLO:
# - Operatore: Solo livello ORDINE (stesso ordine)
# - Supervisore: Tutti i livelli incluso GLOBALE
#
# ML PATTERN:
# - Incremento contatore = numero anomalie risolte
# =============================================================================

from typing import Dict, List, Optional, Tuple
from enum import Enum

from ...database_pg import get_db, log_operation


class LivelloPropagazione(str, Enum):
    """Livelli di propagazione anomalie."""
    ORDINE = 'ORDINE'      # Tutte le anomalie identiche dell'ordine (default)
    GLOBALE = 'GLOBALE'    # Tutte le anomalie identiche stesso vendor


def get_livello_permesso(ruolo: str) -> List[str]:
    """
    Ritorna i livelli di propagazione permessi per un ruolo.

    Args:
        ruolo: Ruolo utente (admin, superuser, supervisore, operatore, readonly)

    Returns:
        Lista livelli permessi
    """
    ruolo = ruolo.lower() if ruolo else 'operatore'

    if ruolo in ('admin', 'superuser', 'supervisore'):
        return ['ORDINE', 'GLOBALE']
    else:
        # Operatore e altri: solo ORDINE (stesso ordine)
        return ['ORDINE']


def calcola_chiave_anomalia(anomalia: Dict) -> str:
    """
    Calcola chiave univoca per identificare anomalie identiche.

    La chiave dipende dal tipo di anomalia:
    - LOOKUP: codice_anomalia + partita_iva
    - LISTINO/PREZZO: codice_anomalia + codice_aic
    - ESPOSITORE: codice_anomalia + pattern_signature
    - AIC: codice_anomalia + descrizione_normalizzata
    - ESTRAZIONE: codice_anomalia + vendor
    """
    codice = anomalia.get('codice_anomalia') or ''
    tipo = anomalia.get('tipo_anomalia') or ''

    if tipo == 'LOOKUP' or codice.startswith('LKP-'):
        # Per LOOKUP: P.IVA identifica il cliente
        piva = anomalia.get('partita_iva') or ''
        return f"LKP:{codice}:{piva}"

    elif tipo == 'LISTINO' or codice.startswith('LST-') or codice.startswith('PRICE-'):
        # Per LISTINO/PREZZO: AIC identifica il prodotto
        aic = anomalia.get('codice_aic') or anomalia.get('valore_anomalo', '').split(':')[0] or ''
        return f"LST:{codice}:{aic}"

    elif tipo == 'ESPOSITORE' or codice.startswith('ESP-'):
        # Per ESPOSITORE: usa pattern_signature
        pattern = anomalia.get('pattern_signature', '')
        return f"ESP:{codice}:{pattern}"

    elif codice.startswith('AIC-'):
        # Per AIC: descrizione normalizzata
        desc = _normalizza_descrizione(anomalia.get('descrizione', ''))
        return f"AIC:{codice}:{desc}"

    elif tipo == 'ESTRAZIONE' or codice.startswith('EXT-'):
        # Per ESTRAZIONE: vendor
        vendor = anomalia.get('vendor', 'UNKNOWN')
        return f"EXT:{codice}:{vendor}"

    else:
        # Default: solo codice anomalia + id_testata
        return f"GEN:{codice}:{anomalia.get('id_testata', '')}"


def _normalizza_descrizione(descrizione: str) -> str:
    """Normalizza descrizione per matching."""
    import re
    if not descrizione:
        return ''
    desc = ' '.join(str(descrizione).upper().split())
    desc = re.sub(r'[^\w\s]', '', desc)
    return desc[:50]


def trova_anomalie_identiche(
    id_anomalia: int,
    livello: LivelloPropagazione
) -> List[Dict]:
    """
    Trova tutte le anomalie identiche secondo il livello richiesto.

    Args:
        id_anomalia: ID anomalia di riferimento
        livello: Livello di propagazione

    Returns:
        Lista anomalie identiche (inclusa quella di riferimento)
    """
    db = get_db()

    # Recupera anomalia di riferimento con dati completi
    # v10.5: Include ragione_sociale e citta per calcolo pattern signature LKP
    anomalia_ref = db.execute("""
        SELECT
            a.id_anomalia, a.id_testata, a.id_dettaglio, a.tipo_anomalia,
            a.codice_anomalia, a.livello, a.descrizione, a.valore_anomalo,
            a.stato, a.pattern_signature,
            ot.partita_iva_estratta as partita_iva,
            ot.ragione_sociale_1 as ragione_sociale, ot.citta,
            ot.numero_ordine_vendor,
            v.codice_vendor as vendor,
            od.codice_aic
        FROM anomalie a
        LEFT JOIN ordini_testata ot ON a.id_testata = ot.id_testata
        LEFT JOIN vendor v ON ot.id_vendor = v.id_vendor
        LEFT JOIN ordini_dettaglio od ON a.id_dettaglio = od.id_dettaglio
        WHERE a.id_anomalia = %s
    """, (id_anomalia,)).fetchone()

    if not anomalia_ref:
        return []

    anomalia_ref = dict(anomalia_ref)
    chiave = calcola_chiave_anomalia(anomalia_ref)

    # Costruisci query per trovare anomalie identiche
    # v10.5: Include ragione_sociale e citta per calcolo pattern signature LKP
    base_query = """
        SELECT
            a.id_anomalia, a.id_testata, a.id_dettaglio, a.tipo_anomalia,
            a.codice_anomalia, a.livello, a.descrizione, a.valore_anomalo,
            a.stato, a.pattern_signature,
            ot.partita_iva_estratta as partita_iva,
            ot.ragione_sociale_1 as ragione_sociale, ot.citta,
            ot.numero_ordine_vendor,
            v.codice_vendor as vendor,
            od.codice_aic
        FROM anomalie a
        LEFT JOIN ordini_testata ot ON a.id_testata = ot.id_testata
        LEFT JOIN vendor v ON ot.id_vendor = v.id_vendor
        LEFT JOIN ordini_dettaglio od ON a.id_dettaglio = od.id_dettaglio
        WHERE a.stato IN ('APERTA', 'IN_GESTIONE')
          AND a.codice_anomalia = %s
    """
    params = [anomalia_ref['codice_anomalia']]

    # Aggiungi filtro per livello ORDINE
    if livello == LivelloPropagazione.ORDINE:
        base_query += " AND a.id_testata = %s"
        params.append(anomalia_ref['id_testata'])

    # Aggiungi filtro specifico per tipo anomalia
    codice = anomalia_ref['codice_anomalia']

    if codice.startswith('LKP-'):
        piva = anomalia_ref.get('partita_iva', '')
        if piva:
            base_query += " AND ot.partita_iva_estratta = %s"
            params.append(piva)

    elif codice.startswith('LST-') or codice.startswith('PRICE-'):
        aic = anomalia_ref.get('codice_aic', '')
        if aic:
            base_query += " AND od.codice_aic = %s"
            params.append(aic)

    elif codice.startswith('ESP-'):
        pattern = anomalia_ref.get('pattern_signature', '')
        if pattern:
            base_query += " AND a.pattern_signature = %s"
            params.append(pattern)

    elif codice.startswith('AIC-'):
        # Per AIC usa descrizione normalizzata
        desc = _normalizza_descrizione(anomalia_ref.get('descrizione', ''))
        if desc:
            base_query += " AND UPPER(REGEXP_REPLACE(LEFT(a.descrizione, 50), '[^\\w\\s]', '', 'g')) = %s"
            params.append(desc)

    elif codice.startswith('EXT-'):
        vendor = anomalia_ref.get('vendor', '')
        if vendor:
            base_query += " AND v.codice_vendor = %s"
            params.append(vendor)

    base_query += " ORDER BY a.id_anomalia"

    rows = db.execute(base_query, params).fetchall()
    return [dict(r) for r in rows]


def conta_anomalie_identiche(id_anomalia: int) -> Dict[str, int]:
    """
    Conta anomalie identiche per ogni livello di propagazione.
    Utile per mostrare nel frontend quante anomalie verrebbero risolte.

    Returns:
        {
            'ordine': N,
            'globale': M
        }
    """
    return {
        'ordine': len(trova_anomalie_identiche(id_anomalia, LivelloPropagazione.ORDINE)),
        'globale': len(trova_anomalie_identiche(id_anomalia, LivelloPropagazione.GLOBALE))
    }


def risolvi_anomalia_con_propagazione(
    id_anomalia: int,
    livello: LivelloPropagazione,
    operatore: str,
    ruolo: str,
    note: str = None,
    dati_correzione: Dict = None
) -> Dict:
    """
    Risolve anomalia con propagazione opzionale.

    Args:
        id_anomalia: ID anomalia da risolvere
        livello: Livello di propagazione
        operatore: Username operatore
        ruolo: Ruolo operatore (per verifica permessi)
        note: Note risoluzione
        dati_correzione: Dati correttivi opzionali (es. nuovo AIC, nuovo prezzo)

    Returns:
        {
            'success': bool,
            'anomalie_risolte': int,
            'ordini_coinvolti': list,
            'ml_pattern_incrementato': int,
            'error': str (se fallito)
        }
    """
    db = get_db()

    # Verifica permessi
    livelli_permessi = get_livello_permesso(ruolo)
    if livello.value not in livelli_permessi:
        return {
            'success': False,
            'error': f"Ruolo {ruolo} non può usare propagazione {livello.value}. Permessi: {livelli_permessi}"
        }

    # Trova anomalie da risolvere
    anomalie = trova_anomalie_identiche(id_anomalia, livello)

    if not anomalie:
        return {'success': False, 'error': f"Anomalia {id_anomalia} non trovata"}

    # Verifica che l'anomalia di riferimento sia ancora aperta
    anomalia_ref = next((a for a in anomalie if a['id_anomalia'] == id_anomalia), None)
    if not anomalia_ref:
        return {'success': False, 'error': f"Anomalia {id_anomalia} non trovata nella lista"}

    if anomalia_ref['stato'] == 'RISOLTA':
        return {'success': False, 'error': "Anomalia già risolta"}

    try:
        anomalie_risolte = 0
        ordini_coinvolti = set()
        supervisioni_approvate = 0

        for anomalia in anomalie:
            if anomalia['stato'] in ('APERTA', 'IN_GESTIONE'):
                # Risolvi anomalia
                # NOTA: id_operatore_gestione è INTEGER, operatore è username string
                # Includiamo l'operatore nella nota invece di usare la colonna FK
                db.execute("""
                    UPDATE anomalie
                    SET stato = 'RISOLTA',
                        data_risoluzione = CURRENT_TIMESTAMP,
                        note_risoluzione = %s
                    WHERE id_anomalia = %s
                """, (
                    f"[{livello.value}] Operatore: {operatore} - {note or 'Risolto con propagazione'}",
                    anomalia['id_anomalia']
                ))

                anomalie_risolte += 1
                if anomalia['id_testata']:
                    ordini_coinvolti.add(anomalia['id_testata'])

                # Approva supervisioni collegate
                sup_count = _approva_supervisioni_collegate(
                    db, anomalia['id_anomalia'], operatore
                )
                supervisioni_approvate += sup_count

        # Incrementa pattern ML per il numero di anomalie risolte
        ml_incremento = 0
        if livello in (LivelloPropagazione.ORDINE, LivelloPropagazione.GLOBALE) and anomalie_risolte > 1:
            ml_incremento = _incrementa_pattern_ml(
                db, anomalia_ref, operatore, anomalie_risolte
            )
        elif anomalie_risolte == 1:
            # Singola anomalia: incrementa di 1
            ml_incremento = _incrementa_pattern_ml(
                db, anomalia_ref, operatore, 1
            )

        # Sblocca ordini coinvolti
        for id_testata in ordini_coinvolti:
            _sblocca_ordine_se_possibile(db, id_testata)

        db.commit()

        # Log operazione
        log_operation(
            'RISOLVI_ANOMALIA_PROPAGAZIONE',
            'ANOMALIE',
            id_anomalia,
            f"Risolte {anomalie_risolte} anomalie ({livello.value}), "
            f"{len(ordini_coinvolti)} ordini, ML +{ml_incremento}",
            dati={
                'livello': livello.value,
                'anomalie_risolte': anomalie_risolte,
                'ordini_coinvolti': list(ordini_coinvolti),
                'ml_incremento': ml_incremento,
            },
            operatore=operatore
        )

        return {
            'success': True,
            'anomalie_risolte': anomalie_risolte,
            'ordini_coinvolti': list(ordini_coinvolti),
            'supervisioni_approvate': supervisioni_approvate,
            'ml_pattern_incrementato': ml_incremento,
            'livello': livello.value
        }

    except Exception as e:
        db.rollback()
        return {'success': False, 'error': str(e)}


def _approva_supervisioni_collegate(db, id_anomalia: int, operatore: str) -> int:
    """
    Approva tutte le supervisioni collegate a un'anomalia.

    v11.4: Inclusa supervisione_prezzo

    Returns:
        Numero supervisioni approvate
    """
    count = 0

    # Supervisione espositore
    result = db.execute("""
        UPDATE supervisione_espositore
        SET stato = 'APPROVED',
            operatore = %s,
            timestamp_decisione = CURRENT_TIMESTAMP,
            note = COALESCE(note || ' - ', '') || '[AUTO] Risolto da anomalia'
        WHERE id_anomalia = %s AND stato = 'PENDING'
    """, (operatore, id_anomalia))
    count += result.rowcount if hasattr(result, 'rowcount') else 0

    # Supervisione listino
    result = db.execute("""
        UPDATE supervisione_listino
        SET stato = 'APPROVED',
            operatore = %s,
            timestamp_decisione = CURRENT_TIMESTAMP,
            note = COALESCE(note || ' - ', '') || '[AUTO] Risolto da anomalia'
        WHERE id_anomalia = %s AND stato = 'PENDING'
    """, (operatore, id_anomalia))
    count += result.rowcount if hasattr(result, 'rowcount') else 0

    # Supervisione lookup
    result = db.execute("""
        UPDATE supervisione_lookup
        SET stato = 'APPROVED',
            operatore = %s,
            timestamp_decisione = CURRENT_TIMESTAMP,
            note = COALESCE(note || ' - ', '') || '[AUTO] Risolto da anomalia'
        WHERE id_anomalia = %s AND stato = 'PENDING'
    """, (operatore, id_anomalia))
    count += result.rowcount if hasattr(result, 'rowcount') else 0

    # Supervisione AIC
    result = db.execute("""
        UPDATE supervisione_aic
        SET stato = 'APPROVED',
            operatore = %s,
            timestamp_decisione = CURRENT_TIMESTAMP,
            note = COALESCE(note || ' - ', '') || '[AUTO] Risolto da anomalia'
        WHERE id_anomalia = %s AND stato = 'PENDING'
    """, (operatore, id_anomalia))
    count += result.rowcount if hasattr(result, 'rowcount') else 0

    # v11.4: Supervisione prezzo
    result = db.execute("""
        UPDATE supervisione_prezzo
        SET stato = 'APPROVED',
            operatore = %s,
            timestamp_decisione = CURRENT_TIMESTAMP,
            note = COALESCE(note || ' - ', '') || '[AUTO] Risolto da anomalia'
        WHERE id_anomalia = %s AND stato = 'PENDING'
    """, (operatore, id_anomalia))
    count += result.rowcount if hasattr(result, 'rowcount') else 0

    return count


def _incrementa_pattern_ml(db, anomalia: Dict, operatore: str, count: int) -> int:
    """
    Incrementa pattern ML per l'anomalia risolta.

    Args:
        db: Database connection
        anomalia: Dati anomalia
        operatore: Username operatore
        count: Numero di incrementi

    Returns:
        Incremento effettuato (0 se pattern non trovato)
    """
    from ..supervision.constants import SOGLIA_PROMOZIONE

    codice = anomalia.get('codice_anomalia', '')
    id_anomalia = anomalia.get('id_anomalia')
    pattern_sig = anomalia.get('pattern_signature', '')

    # v10.5: Se pattern_signature non è nell'anomalia, prova a recuperarlo
    # dalla supervisione collegata (che ha la signature corretta)
    if not pattern_sig and id_anomalia:
        # Prova supervisione_lookup
        if codice.startswith('LKP-'):
            sup = db.execute("""
                SELECT pattern_signature FROM supervisione_lookup
                WHERE id_anomalia = %s LIMIT 1
            """, (id_anomalia,)).fetchone()
            if sup and sup['pattern_signature']:
                pattern_sig = sup['pattern_signature']

        # Prova supervisione_espositore
        elif codice.startswith('ESP-'):
            sup = db.execute("""
                SELECT pattern_signature FROM supervisione_espositore
                WHERE id_anomalia = %s LIMIT 1
            """, (id_anomalia,)).fetchone()
            if sup and sup['pattern_signature']:
                pattern_sig = sup['pattern_signature']

        # Prova supervisione_listino
        elif codice.startswith('LST-') or codice.startswith('PRICE-'):
            sup = db.execute("""
                SELECT pattern_signature FROM supervisione_listino
                WHERE id_anomalia = %s LIMIT 1
            """, (id_anomalia,)).fetchone()
            if sup and sup['pattern_signature']:
                pattern_sig = sup['pattern_signature']

    if not pattern_sig:
        # Calcola pattern signature se non trovato
        pattern_sig = _calcola_pattern_signature(anomalia)

    if not pattern_sig:
        return 0

    # Determina tabella criteri in base al tipo
    if codice.startswith('ESP-'):
        table = 'criteri_ordinari_espositore'
    elif codice.startswith('LST-') or codice.startswith('PRICE-'):
        table = 'criteri_ordinari_listino'
    elif codice.startswith('LKP-'):
        table = 'criteri_ordinari_lookup'
    elif codice.startswith('AIC-'):
        table = 'criteri_ordinari_aic'
    else:
        return 0

    # Prova ad aggiornare pattern esistente
    result = db.execute(f"""
        UPDATE {table}
        SET count_approvazioni = count_approvazioni + %s,
            operatori_approvatori = COALESCE(operatori_approvatori || ', ', '') || %s
        WHERE pattern_signature = %s
        RETURNING count_approvazioni
    """, (count, f"{operatore}(x{count})", pattern_sig)).fetchone()

    if result:
        # Verifica promozione
        if result[0] >= SOGLIA_PROMOZIONE:
            db.execute(f"""
                UPDATE {table}
                SET is_ordinario = TRUE, data_promozione = CURRENT_TIMESTAMP
                WHERE pattern_signature = %s AND is_ordinario = FALSE
            """, (pattern_sig,))
        return count

    return 0


def _calcola_pattern_signature(anomalia: Dict) -> str:
    """
    Calcola pattern signature per anomalia.

    IMPORTANTE: Deve usare lo stesso algoritmo delle funzioni di creazione
    supervision per garantire che le signature matchino.
    """
    import hashlib

    codice = anomalia.get('codice_anomalia', '')
    vendor = anomalia.get('vendor', 'UNKNOWN')

    if codice.startswith('LKP-'):
        # v10.5: Usa stesso formato di calcola_pattern_signature_lookup in lookup.py
        # Include: vendor, codice, piva, ragione_sociale normalizzata, citta normalizzata
        piva = anomalia.get('partita_iva') or anomalia.get('partita_iva_estratta', '') or 'NO_PIVA'
        rs = ' '.join((anomalia.get('ragione_sociale') or anomalia.get('ragione_sociale_estratta', '') or '').upper().split())[:50]
        citta = ' '.join((anomalia.get('citta') or anomalia.get('citta_estratta', '') or '').upper().split())[:30]
        key = f"{vendor}|{codice}|{piva}|{rs}|{citta}"
    elif codice.startswith('LST-') or codice.startswith('PRICE-'):
        aic = anomalia.get('codice_aic', '')
        key = f"{vendor}|{codice}|{aic}"
    elif codice.startswith('AIC-'):
        desc = _normalizza_descrizione(anomalia.get('descrizione', ''))
        key = f"{vendor}|{desc}"
    elif codice.startswith('ESP-'):
        # Per ESPOSITORE usa pattern_signature esistente se presente
        existing = anomalia.get('pattern_signature', '')
        if existing:
            return existing
        # Altrimenti calcola
        desc = _normalizza_descrizione(anomalia.get('descrizione', ''))
        key = f"{vendor}|ESP|{desc}"
    else:
        return anomalia.get('pattern_signature', '')

    return hashlib.md5(key.encode()).hexdigest()[:16]


def _sblocca_ordine_se_possibile(db, id_testata: int):
    """Sblocca ordine se tutte anomalie e supervisioni risolte."""
    # Conta anomalie aperte
    anomalie = db.execute("""
        SELECT COUNT(*) as cnt FROM anomalie
        WHERE id_testata = %s AND stato IN ('APERTA', 'IN_GESTIONE')
    """, (id_testata,)).fetchone()

    # v11.4: Conta supervisioni pending su tutte le tabelle (inclusa prezzo)
    sup_count = 0
    for table in ['supervisione_espositore', 'supervisione_listino',
                  'supervisione_lookup', 'supervisione_aic', 'supervisione_prezzo']:
        try:
            row = db.execute(f"""
                SELECT COUNT(*) as cnt FROM {table}
                WHERE id_testata = %s AND stato = 'PENDING'
            """, (id_testata,)).fetchone()
            sup_count += row['cnt'] if row else 0
        except:
            pass

    if (anomalie['cnt'] if anomalie else 0) == 0 and sup_count == 0:
        db.execute("""
            UPDATE ordini_testata
            SET stato = 'ESTRATTO'
            WHERE id_testata = %s AND stato IN ('ANOMALIA', 'PENDING_REVIEW')
        """, (id_testata,))
