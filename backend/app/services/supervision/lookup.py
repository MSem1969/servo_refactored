# =============================================================================
# SERV.O v8.0 - SUPERVISION LOOKUP
# =============================================================================
# Gestione supervisione anomalie LKP-A01 (score < 80%) e LKP-A02 (non trovato)
# =============================================================================

import hashlib
from typing import Dict, Optional, Tuple

from ...database_pg import get_db, log_operation
from .constants import SOGLIA_PROMOZIONE, SOGLIA_PROMOZIONE_ORDINARIA


def calcola_pattern_signature_lookup(
    vendor: str,
    codice_anomalia: str,
    partita_iva: str,
    ragione_sociale: str = '',
    citta: str = ''
) -> str:
    """
    Calcola signature univoca per pattern lookup.

    v8.1: Aggiunta ragione_sociale e città per supporto aziende multipunto.
    Pattern: VENDOR|CODICE_ANOMALIA|PARTITA_IVA|RAGIONE_SOCIALE_NORM|CITTA_NORM

    Args:
        vendor: Codice vendor
        codice_anomalia: LKP-A01 o LKP-A02
        partita_iva: P.IVA estratta dal PDF
        ragione_sociale: Ragione sociale estratta (normalizzata)
        citta: Città estratta (normalizzata)

    Returns:
        Hash 16 caratteri
    """
    # Normalizza ragione sociale e città (uppercase, rimuovi spazi extra)
    rs_norm = ' '.join((ragione_sociale or '').upper().split())[:50]
    citta_norm = ' '.join((citta or '').upper().split())[:30]

    raw = f"{vendor or 'UNKNOWN'}|{codice_anomalia}|{partita_iva or 'NO_PIVA'}|{rs_norm}|{citta_norm}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _assicura_pattern_lookup_esistente(pattern_sig: str, anomalia: Dict):
    """
    Assicura che un pattern lookup esista nella tabella criteri.
    Crea record se non esiste.

    v8.1: Descrizione include destinazione per supporto multipunto.
    """
    db = get_db()

    existing = db.execute(
        "SELECT 1 FROM criteri_ordinari_lookup WHERE pattern_signature = %s",
        (pattern_sig,)
    ).fetchone()

    if not existing:
        vendor = anomalia.get('vendor', 'UNKNOWN')
        partita_iva = anomalia.get('partita_iva_estratta', '')
        codice_anomalia = anomalia.get('codice_anomalia', '')
        # v8.1: Dati destinazione per descrizione più chiara
        ragione_sociale = anomalia.get('ragione_sociale_estratta', '')
        citta = anomalia.get('citta_estratta', '')

        # v8.1: Descrizione include destinazione per identificare il punto vendita
        if ragione_sociale:
            destinazione = f"{ragione_sociale[:40]}"
            if citta:
                destinazione += f" - {citta}"
            descrizione = f"Lookup {vendor} - {codice_anomalia} - {destinazione}"
        else:
            descrizione = f"Lookup {vendor} - {codice_anomalia} - P.IVA {partita_iva or 'N/A'}"

        db.execute("""
            INSERT INTO criteri_ordinari_lookup
            (pattern_signature, pattern_descrizione, vendor, codice_anomalia, partita_iva_pattern)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            pattern_sig,
            descrizione,
            vendor,
            codice_anomalia,
            partita_iva,
        ))
        db.commit()


def crea_supervisione_lookup(
    id_testata: int,
    id_anomalia: int,
    anomalia: Dict
) -> int:
    """
    Crea supervisione per anomalia lookup (LKP-A01, LKP-A02, LKP-A04).

    Args:
        id_testata: ID ordine in ORDINI_TESTATA
        id_anomalia: ID anomalia in ANOMALIE
        anomalia: Dati completi anomalia

    Returns:
        ID supervisione creata
    """
    db = get_db()

    vendor = anomalia.get('vendor', 'UNKNOWN')
    partita_iva = anomalia.get('partita_iva_estratta', '')
    codice_anomalia = anomalia.get('codice_anomalia', '')
    lookup_method = anomalia.get('lookup_method', '')
    lookup_score = anomalia.get('lookup_score')
    # v8.1: Dati destinazione per pattern univoco multipunto
    ragione_sociale = anomalia.get('ragione_sociale_estratta', '')
    citta = anomalia.get('citta_estratta', '')

    # Calcola pattern signature per lookup (v8.1: include destinazione)
    pattern_sig = calcola_pattern_signature_lookup(
        vendor, codice_anomalia, partita_iva, ragione_sociale, citta
    )

    # Inserisci richiesta supervisione lookup
    cursor = db.execute("""
        INSERT INTO supervisione_lookup
        (id_testata, id_anomalia, codice_anomalia, vendor, partita_iva_estratta,
         lookup_method, lookup_score, pattern_signature, stato)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')
        RETURNING id_supervisione
    """, (
        id_testata,
        id_anomalia,
        codice_anomalia,
        vendor,
        partita_iva,
        lookup_method,
        lookup_score,
        pattern_sig,
    ))

    id_supervisione = cursor.fetchone()[0]
    db.commit()

    # Assicura che il pattern esista nella tabella criteri lookup
    _assicura_pattern_lookup_esistente(pattern_sig, anomalia)

    # Log operazione
    log_operation(
        'CREA_SUPERVISIONE',
        'SUPERVISIONE_LOOKUP',
        id_supervisione,
        f"Creata supervisione lookup per ordine {id_testata}, P.IVA {partita_iva}"
    )

    return id_supervisione


def approva_supervisione_lookup(
    id_supervisione: int,
    operatore: str,
    min_id: str = None,
    id_farmacia: int = None,
    note: str = None
) -> bool:
    """
    Approva una supervisione lookup.

    Effetti:
    1. Aggiorna stato a APPROVED
    2. Registra MIN ID assegnato (se fornito)
    3. Aggiorna ordine con la farmacia selezionata
    4. Registra approvazione nel pattern ML
    5. Sblocca ordine se era l'ultima supervisione pending

    Args:
        id_supervisione: ID supervisione
        operatore: Username operatore
        min_id: MIN ID farmacia da assegnare
        id_farmacia: ID farmacia selezionata da anagrafica
        note: Note opzionali

    Returns:
        True se successo
    """
    from .requests import sblocca_ordine_se_completo

    db = get_db()

    # Recupera dati supervisione
    sup = db.execute(
        "SELECT * FROM supervisione_lookup WHERE id_supervisione = %s",
        (id_supervisione,)
    ).fetchone()

    if not sup:
        return False

    sup = dict(sup)

    # Aggiorna stato supervisione
    db.execute("""
        UPDATE supervisione_lookup
        SET stato = 'APPROVED',
            operatore = %s,
            timestamp_decisione = CURRENT_TIMESTAMP,
            note = %s,
            min_id_assegnato = %s,
            id_farmacia_selezionata = %s
        WHERE id_supervisione = %s
    """, (operatore, note, min_id, id_farmacia, id_supervisione))

    # Se fornito MIN ID, aggiorna ordine
    if min_id and id_farmacia:
        db.execute("""
            UPDATE ordini_testata
            SET id_farmacia_lookup = %s,
                lookup_method = 'SUPERVISIONE',
                lookup_score = 100
            WHERE id_testata = %s
        """, (id_farmacia, sup['id_testata']))

    # Registra approvazione pattern (v11.4: passa anche min_id e id_farmacia)
    registra_approvazione_pattern_lookup(sup['pattern_signature'], operatore, min_id, id_farmacia)

    db.commit()

    # Sblocca ordine se completo
    sblocca_ordine_se_completo(sup['id_testata'])

    log_operation(
        'APPROVA_SUPERVISIONE',
        'SUPERVISIONE_LOOKUP',
        id_supervisione,
        f"Approvato, MIN ID: {min_id}",
        operatore=operatore
    )

    return True


def rifiuta_supervisione_lookup(
    id_supervisione: int,
    operatore: str,
    note: str = None
) -> bool:
    """
    Rifiuta una supervisione lookup.

    Effetti:
    1. Aggiorna stato a REJECTED
    2. Reset conteggio approvazioni pattern
    3. Sblocca ordine se era l'ultima supervisione pending

    Args:
        id_supervisione: ID supervisione
        operatore: Username operatore
        note: Note opzionali (motivo rifiuto)

    Returns:
        True se successo
    """
    from .requests import sblocca_ordine_se_completo

    db = get_db()

    # Recupera dati supervisione
    sup = db.execute(
        "SELECT * FROM supervisione_lookup WHERE id_supervisione = %s",
        (id_supervisione,)
    ).fetchone()

    if not sup:
        return False

    sup = dict(sup)

    # Aggiorna stato supervisione
    db.execute("""
        UPDATE supervisione_lookup
        SET stato = 'REJECTED',
            operatore = %s,
            timestamp_decisione = CURRENT_TIMESTAMP,
            note = %s
        WHERE id_supervisione = %s
    """, (operatore, note, id_supervisione))

    # Reset pattern
    registra_rifiuto_pattern_lookup(sup['pattern_signature'])

    db.commit()

    # Sblocca ordine se completo
    sblocca_ordine_se_completo(sup['id_testata'])

    log_operation(
        'RIFIUTA_SUPERVISIONE',
        'SUPERVISIONE_LOOKUP',
        id_supervisione,
        f"Rifiutato: {note}",
        operatore=operatore
    )

    return True


def registra_approvazione_pattern_lookup(
    pattern_signature: str,
    operatore: str,
    min_id: str = None,
    id_farmacia: int = None
):
    """
    Registra approvazione per un pattern lookup.

    Incrementa contatore e, se raggiunta soglia, promuove a ordinario.
    v8.1: Soglia differenziata per tipo anomalia:
    - LKP-A03 (score >= 80%): 1 conferma = automatico
    - LKP-A01, LKP-A02 (score < 80%): 5 conferme = automatico

    v11.4: Aggiunto salvataggio min_id_default e id_farmacia_default
    """
    db = get_db()

    # Incrementa contatore e salva farmacia default se fornita
    if min_id and id_farmacia:
        db.execute("""
            UPDATE criteri_ordinari_lookup
            SET count_approvazioni = count_approvazioni + 1,
                operatori_approvatori = COALESCE(operatori_approvatori || ', ', '') || %s,
                min_id_default = COALESCE(min_id_default, %s),
                id_farmacia_default = COALESCE(id_farmacia_default, %s)
            WHERE pattern_signature = %s
        """, (operatore, min_id, id_farmacia, pattern_signature))
    else:
        db.execute("""
            UPDATE criteri_ordinari_lookup
            SET count_approvazioni = count_approvazioni + 1,
                operatori_approvatori = COALESCE(operatori_approvatori || ', ', '') || %s
            WHERE pattern_signature = %s
        """, (operatore, pattern_signature))

    # Recupera contatore e codice anomalia per determinare soglia
    row = db.execute("""
        SELECT count_approvazioni, codice_anomalia
        FROM criteri_ordinari_lookup
        WHERE pattern_signature = %s
    """, (pattern_signature,)).fetchone()

    if row:
        count = row[0]
        codice_anomalia = row[1] or ''

        # v8.1: LKP-A03 (ordinaria) usa soglia 1, altre (gravi) usano soglia 5
        soglia = SOGLIA_PROMOZIONE_ORDINARIA if codice_anomalia == 'LKP-A03' else SOGLIA_PROMOZIONE

        if count >= soglia:
            # Promuovi a ordinario
            db.execute("""
                UPDATE criteri_ordinari_lookup
                SET is_ordinario = TRUE, data_promozione = CURRENT_TIMESTAMP
                WHERE pattern_signature = %s AND is_ordinario = FALSE
            """, (pattern_signature,))

            log_operation(
                'PROMOZIONE_PATTERN',
                'CRITERI_ORDINARI_LOOKUP',
                None,
                f"Pattern lookup {pattern_signature} promosso a ordinario dopo {soglia} approvazioni (anomalia {codice_anomalia})"
            )

    db.commit()


def registra_rifiuto_pattern_lookup(pattern_signature: str):
    """
    Registra rifiuto per un pattern lookup.
    Reset contatore approvazioni a 0.
    """
    db = get_db()

    db.execute("""
        UPDATE criteri_ordinari_lookup
        SET count_approvazioni = 0,
            is_ordinario = FALSE,
            data_promozione = NULL
        WHERE pattern_signature = %s
    """, (pattern_signature,))

    db.commit()

    log_operation(
        'RESET_PATTERN',
        'CRITERI_ORDINARI_LOOKUP',
        None,
        f"Pattern lookup {pattern_signature} resettato dopo rifiuto"
    )


def verifica_pattern_lookup_ordinario(pattern_signature: str) -> bool:
    """
    Verifica se un pattern lookup e stato promosso a ordinario.

    Args:
        pattern_signature: Signature pattern

    Returns:
        True se pattern e ordinario (applicabile automaticamente)
    """
    db = get_db()

    row = db.execute("""
        SELECT is_ordinario FROM criteri_ordinari_lookup
        WHERE pattern_signature = %s AND is_ordinario = TRUE
    """, (pattern_signature,)).fetchone()

    return row is not None


def valuta_anomalia_lookup(
    id_testata: int,
    anomalia: Dict
) -> Tuple[bool, Optional[str]]:
    """
    Valuta anomalia lookup usando criteri appresi.

    Se pattern e ordinario e ha MIN ID default, applica automaticamente.

    Args:
        id_testata: ID ordine
        anomalia: Dati anomalia

    Returns:
        Tuple (applicato_auto, pattern_signature)
    """
    from .ml import log_criterio_applicato

    vendor = anomalia.get('vendor', 'UNKNOWN')
    partita_iva = anomalia.get('partita_iva_estratta', '')
    codice_anomalia = anomalia.get('codice_anomalia', '')
    # v8.1: Dati destinazione per pattern univoco multipunto
    ragione_sociale = anomalia.get('ragione_sociale_estratta', '')
    citta = anomalia.get('citta_estratta', '')

    pattern_sig = calcola_pattern_signature_lookup(
        vendor, codice_anomalia, partita_iva, ragione_sociale, citta
    )

    db = get_db()

    # Verifica se ordinario E ha un default
    row = db.execute("""
        SELECT is_ordinario, min_id_default, id_farmacia_default
        FROM criteri_ordinari_lookup
        WHERE pattern_signature = %s AND is_ordinario = TRUE
    """, (pattern_sig,)).fetchone()

    if row and row['min_id_default']:
        # Applica automaticamente con il MIN ID salvato
        db.execute("""
            UPDATE ordini_testata
            SET id_farmacia_lookup = %s,
                lookup_method = 'ML_AUTO',
                lookup_score = 100
            WHERE id_testata = %s
        """, (row['id_farmacia_default'], id_testata))
        db.commit()

        log_criterio_applicato(
            id_testata=id_testata,
            id_dettaglio=None,
            pattern_signature=pattern_sig,
            automatico=True,
            operatore='SISTEMA'
        )

        log_operation(
            'APPLICA_CRITERIO_AUTO',
            'ORDINI_TESTATA',
            id_testata,
            f"Criterio lookup ordinario {pattern_sig} applicato automaticamente"
        )

        return True, pattern_sig

    # Pattern non ordinario o senza default: richiede supervisione
    return False, pattern_sig
