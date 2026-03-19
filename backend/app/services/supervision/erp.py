# =============================================================================
# SERV.O v12.0 - ERP VALIDATION SUPERVISION
# =============================================================================
# Gestione supervisione per anomalie ERP (mismatch MIN_ID/P.IVA con
# anagrafica_clienti). Dopo 5 correzioni concordanti, rettifica automatica
# dell'anagrafica_clienti.
# =============================================================================

import hashlib
from typing import Dict, Any, Optional

from ...database_pg import get_db, log_operation
from .constants import SOGLIA_PROMOZIONE


def calcola_pattern_signature_erp(min_id: str) -> str:
    """
    Calcola signature univoca per pattern ERP.
    Basata sul MIN_ID normalizzato (senza zeri iniziali).
    """
    min_id_norm = (min_id or '').strip().lstrip('0') or '0'
    raw = f"ERP|{min_id_norm}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def valida_coerenza_erp(min_id: str, partita_iva: str) -> Dict[str, Any]:
    """
    Valida la coppia MIN_ID + P.IVA contro anagrafica_clienti.

    Returns:
        {
            'valido': bool,
            'codice_anomalia': str or None,  # ERP-A01, ERP-A02
            'messaggio': str,
            'piva_erp': str or None,  # P.IVA in anagrafica_clienti
            'min_id_norm': str,
        }
    """
    if not min_id:
        return {'valido': True, 'codice_anomalia': None, 'messaggio': 'MIN_ID vuoto, skip validazione',
                'piva_erp': None, 'min_id_norm': ''}

    db = get_db()
    min_id_norm = min_id.strip().lstrip('0') or '0'
    piva_norm = (partita_iva or '').strip()

    # Cerca in anagrafica_clienti per MIN_ID
    cliente = db.execute("""
        SELECT partita_iva, min_id, ragione_sociale_1, codice_cliente
        FROM anagrafica_clienti
        WHERE LTRIM(min_id, '0') = %s
        LIMIT 1
    """, (min_id_norm,)).fetchone()

    if not cliente:
        return {
            'valido': False,
            'codice_anomalia': 'ERP-A02',
            'messaggio': f"MIN_ID {min_id_norm} non trovato in anagrafica clienti ERP. "
                         "Il tracciato potrebbe essere scartato dal gestionale.",
            'piva_erp': None,
            'min_id_norm': min_id_norm,
        }

    piva_erp = (cliente['partita_iva'] or '').strip()

    # Confronta P.IVA normalizzate
    if piva_norm and piva_erp and piva_norm != piva_erp:
        return {
            'valido': False,
            'codice_anomalia': 'ERP-A01',
            'messaggio': (
                f"MIN_ID {min_id_norm}: P.IVA tracciato={piva_norm}, "
                f"P.IVA ERP={piva_erp} ({cliente.get('ragione_sociale_1', '')}). "
                "Il tracciato verrebbe scartato dal gestionale."
            ),
            'piva_erp': piva_erp,
            'min_id_norm': min_id_norm,
        }

    return {
        'valido': True,
        'codice_anomalia': None,
        'messaggio': 'OK',
        'piva_erp': piva_erp,
        'min_id_norm': min_id_norm,
    }


def crea_supervisione_erp(
    id_testata: int,
    id_anomalia: int,
    min_id: str,
    partita_iva_tracciato: str,
    partita_iva_erp: str = None,
) -> int:
    """
    Crea richiesta supervisione ERP per mismatch P.IVA.

    Returns:
        ID supervisione creata
    """
    db = get_db()

    pattern_sig = calcola_pattern_signature_erp(min_id)
    min_id_norm = (min_id or '').strip().lstrip('0') or '0'

    # Inserisci richiesta supervisione
    cursor = db.execute("""
        INSERT INTO supervisione_erp
        (id_testata, id_anomalia, pattern_signature, min_id,
         partita_iva_tracciato, partita_iva_erp, stato)
        VALUES (%s, %s, %s, %s, %s, %s, 'PENDING')
        RETURNING id_supervisione
    """, (
        id_testata,
        id_anomalia,
        pattern_sig,
        min_id_norm,
        (partita_iva_tracciato or '').strip(),
        (partita_iva_erp or '').strip(),
    ))

    id_supervisione = cursor.fetchone()[0]

    # Assicura che il pattern esista nella tabella criteri
    _assicura_pattern_erp_esistente(pattern_sig, min_id_norm)

    db.commit()

    log_operation(
        'CREA_SUPERVISIONE',
        'SUPERVISIONE_ERP',
        id_supervisione,
        f"Creata supervisione ERP per ordine {id_testata}, MIN_ID {min_id_norm}"
    )

    return id_supervisione


def _assicura_pattern_erp_esistente(pattern_sig: str, min_id: str):
    """Crea record criteri se non esiste."""
    db = get_db()

    existing = db.execute(
        "SELECT 1 FROM criteri_ordinari_erp WHERE pattern_signature = %s",
        (pattern_sig,)
    ).fetchone()

    if not existing:
        db.execute("""
            INSERT INTO criteri_ordinari_erp
            (pattern_signature, pattern_descrizione, min_id)
            VALUES (%s, %s, %s)
        """, (
            pattern_sig,
            f"ERP validation - MIN_ID {min_id}",
            min_id,
        ))
        db.commit()


def approva_supervisione_erp(
    id_supervisione: int,
    operatore: str,
    partita_iva_corretta: str,
    min_id_corretto: str = None,
    note: str = None,
) -> Dict[str, Any]:
    """
    Approva supervisione ERP con P.IVA corretta.
    Aggiorna ordine, incrementa pattern ML, e se soglia raggiunta
    rettifica anagrafica_clienti.

    Returns:
        Dict con risultato operazione
    """
    db = get_db()

    # Recupera supervisione
    sup = db.execute("""
        SELECT * FROM supervisione_erp WHERE id_supervisione = %s
    """, (id_supervisione,)).fetchone()

    if not sup:
        return {'success': False, 'error': 'Supervisione non trovata'}

    if sup['stato'] != 'PENDING':
        return {'success': False, 'error': f'Supervisione già in stato {sup["stato"]}'}

    id_testata = sup['id_testata']
    pattern_sig = sup['pattern_signature']
    min_id = min_id_corretto or sup['min_id']
    piva_corretta = partita_iva_corretta.strip()

    # 1. Aggiorna supervisione
    db.execute("""
        UPDATE supervisione_erp
        SET stato = 'APPROVED',
            operatore = %s,
            partita_iva_corretta = %s,
            min_id_corretto = %s,
            note = %s,
            timestamp_decisione = CURRENT_TIMESTAMP
        WHERE id_supervisione = %s
    """, (operatore, piva_corretta, min_id, note, id_supervisione))

    # 2. Aggiorna P.IVA sull'ordine
    db.execute("""
        UPDATE ordini_testata
        SET partita_iva_estratta = %s
        WHERE id_testata = %s
    """, (piva_corretta, id_testata))

    # Se MIN_ID diverso, aggiorna anche quello
    if min_id_corretto and min_id_corretto != sup['min_id']:
        db.execute("""
            UPDATE ordini_testata
            SET codice_ministeriale_estratto = %s
            WHERE id_testata = %s
        """, (min_id_corretto, id_testata))

    # 3. Chiudi anomalia collegata
    if sup['id_anomalia']:
        db.execute("""
            UPDATE anomalie
            SET stato = 'RISOLTA',
                data_risoluzione = CURRENT_TIMESTAMP,
                note_risoluzione = %s
            WHERE id_anomalia = %s AND stato IN ('APERTA', 'IN_GESTIONE')
        """, (
            f"Operatore: {operatore} - P.IVA corretta: {piva_corretta}. {note or ''}",
            sup['id_anomalia']
        ))

    # 4. Incrementa pattern ML e verifica soglia
    rettifica = _registra_approvazione_pattern_erp(
        pattern_sig, operatore, piva_corretta, min_id
    )

    # 5. Sblocca ordine
    from .requests import sblocca_ordine_se_completo
    db.commit()
    sblocca_ordine_se_completo(id_testata)

    result = {
        'success': True,
        'id_supervisione': id_supervisione,
        'id_testata': id_testata,
        'partita_iva_corretta': piva_corretta,
    }
    result.update(rettifica)
    return result


def _registra_approvazione_pattern_erp(
    pattern_sig: str,
    operatore: str,
    partita_iva_corretta: str,
    min_id: str,
) -> Dict[str, Any]:
    """
    Registra approvazione pattern ERP e verifica soglia per rettifica anagrafica.

    Returns:
        Dict con info su rettifica:
        - rettifica_eseguita: bool
        - count_approvazioni: int
        - soglia: int
    """
    db = get_db()

    # Aggiorna pattern: incrementa counter, salva P.IVA corretta
    result = db.execute("""
        UPDATE criteri_ordinari_erp
        SET count_approvazioni = count_approvazioni + 1,
            operatori_approvatori = COALESCE(operatori_approvatori || ', ', '') || %s,
            partita_iva_corretta = %s
        WHERE pattern_signature = %s
        RETURNING count_approvazioni
    """, (operatore, partita_iva_corretta, pattern_sig)).fetchone()

    if not result:
        return {'rettifica_eseguita': False, 'count_approvazioni': 0, 'soglia': SOGLIA_PROMOZIONE}

    count = result[0]

    # Verifica soglia per promozione + rettifica anagrafica
    rettifica_eseguita = False
    if count >= SOGLIA_PROMOZIONE:
        # Promuovi pattern
        db.execute("""
            UPDATE criteri_ordinari_erp
            SET is_ordinario = TRUE,
                data_promozione = COALESCE(data_promozione, CURRENT_TIMESTAMP)
            WHERE pattern_signature = %s AND is_ordinario = FALSE
        """, (pattern_sig,))

        # Rettifica anagrafica_clienti
        rettifica_eseguita = _rettifica_anagrafica_clienti(
            min_id, partita_iva_corretta, operatore, count
        )

        if rettifica_eseguita:
            db.execute("""
                UPDATE criteri_ordinari_erp
                SET data_rettifica_anagrafica = CURRENT_TIMESTAMP
                WHERE pattern_signature = %s
            """, (pattern_sig,))

    return {
        'rettifica_eseguita': rettifica_eseguita,
        'count_approvazioni': count,
        'soglia': SOGLIA_PROMOZIONE,
    }


def _rettifica_anagrafica_clienti(
    min_id: str,
    partita_iva_corretta: str,
    operatore: str,
    count_approvazioni: int,
) -> bool:
    """
    Rettifica P.IVA in anagrafica_clienti per un MIN_ID.
    Chiamata quando la soglia di 5 correzioni concordanti è raggiunta.

    Returns:
        True se rettifica eseguita
    """
    db = get_db()
    min_id_norm = min_id.strip().lstrip('0') or '0'

    # Verifica che la rettifica non sia già stata fatta
    cliente = db.execute("""
        SELECT id_cliente, partita_iva, ragione_sociale_1
        FROM anagrafica_clienti
        WHERE LTRIM(min_id, '0') = %s
        LIMIT 1
    """, (min_id_norm,)).fetchone()

    if not cliente:
        # MIN_ID non in anagrafica - non possiamo rettificare (ERP-A02)
        log_operation(
            'RETTIFICA_ERP_SKIP',
            'ANAGRAFICA_CLIENTI',
            0,
            f"MIN_ID {min_id_norm} non in anagrafica_clienti - rettifica non possibile "
            f"dopo {count_approvazioni} correzioni concordanti",
            operatore=operatore
        )
        return False

    piva_attuale = (cliente['partita_iva'] or '').strip()
    if piva_attuale == partita_iva_corretta:
        # Già corretto, nulla da fare
        return False

    # Esegui rettifica
    db.execute("""
        UPDATE anagrafica_clienti
        SET partita_iva = %s,
            data_aggiornamento = CURRENT_TIMESTAMP
        WHERE LTRIM(min_id, '0') = %s
    """, (partita_iva_corretta, min_id_norm))

    log_operation(
        'RETTIFICA_ERP_ANAGRAFICA',
        'ANAGRAFICA_CLIENTI',
        cliente['id_cliente'],
        f"Rettifica automatica P.IVA per MIN_ID {min_id_norm}: "
        f"{piva_attuale} → {partita_iva_corretta} "
        f"dopo {count_approvazioni} correzioni concordanti. "
        f"Cliente: {cliente.get('ragione_sociale_1', 'N/D')}",
        operatore=operatore
    )

    return True


def valuta_anomalia_erp(id_testata: int, min_id: str, partita_iva: str) -> Dict[str, Any]:
    """
    Valuta se un'anomalia ERP può essere risolta automaticamente
    (pattern già promosso a ordinario).

    Returns:
        {
            'auto_risolto': bool,
            'partita_iva_corretta': str or None,
            'pattern_sig': str,
        }
    """
    db = get_db()
    pattern_sig = calcola_pattern_signature_erp(min_id)

    # Cerca pattern ordinario
    criterio = db.execute("""
        SELECT partita_iva_corretta, min_id
        FROM criteri_ordinari_erp
        WHERE pattern_signature = %s AND is_ordinario = TRUE
    """, (pattern_sig,)).fetchone()

    if not criterio or not criterio['partita_iva_corretta']:
        return {
            'auto_risolto': False,
            'partita_iva_corretta': None,
            'pattern_sig': pattern_sig,
        }

    piva_corretta = criterio['partita_iva_corretta']

    # Auto-correggi P.IVA sull'ordine
    db.execute("""
        UPDATE ordini_testata
        SET partita_iva_estratta = %s
        WHERE id_testata = %s
    """, (piva_corretta, id_testata))

    db.commit()

    log_operation(
        'AUTO_CORREZIONE_ERP',
        'ORDINI_TESTATA',
        id_testata,
        f"Auto-correzione P.IVA per MIN_ID {min_id}: {partita_iva} → {piva_corretta} "
        f"(pattern ordinario {pattern_sig})"
    )

    return {
        'auto_risolto': True,
        'partita_iva_corretta': piva_corretta,
        'pattern_sig': pattern_sig,
    }
