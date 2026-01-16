# =============================================================================
# SERV.O v6.2 - ML PATTERN MATCHING SERVICE
# =============================================================================
# Sistema di Machine Learning per riconoscimento automatico associazioni
# parent/child negli espositori, basato su apprendimento dalle anomalie.
#
# PRINCIPIO FONDAMENTALE:
# Il sistema ML lavora ESCLUSIVAMENTE sulle ANOMALIE segnalate.
# La conferma normale degli ordini NON contribuisce all'apprendimento.
# Solo le anomalie approvate in supervisione alimentano il pattern ML.
# =============================================================================

import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..database_pg import get_db, log_operation


# =============================================================================
# COSTANTI E SOGLIE
# =============================================================================

# Soglie per decisione ML
ML_THRESHOLD_AUTO_APPLY = 80   # >= 80% -> applica automaticamente (bypass supervisione)
ML_THRESHOLD_WARNING = 50      # 50-80% -> applica con warning (non bloccante)
ML_THRESHOLD_SUPERVISION = 50  # < 50% -> supervisione obbligatoria (ESP-A06)

# Soglia promozione pattern (importata da supervisione)
SOGLIA_PROMOZIONE = 5

# Pesi per algoritmo similarity
WEIGHT_JACCARD = 0.40          # Similarity codici AIC (40%)
WEIGHT_LCS = 0.30              # Ordine sequenziale LCS (30%)
WEIGHT_QUANTITY = 0.20         # Quantita totali (20%)
WEIGHT_COUNT = 0.10            # Numero elementi (10%)


# =============================================================================
# DECISIONI ML
# =============================================================================

@dataclass
class MLDecision:
    """Risultato decisione ML."""
    decision: str               # 'APPLY_ML', 'APPLY_WARNING', 'SEND_SUPERVISION'
    similarity_score: float     # Score 0-100
    reason: str                 # Motivazione decisione
    details: Dict               # Dettagli calcolo similarity


# =============================================================================
# NORMALIZZAZIONE DESCRIZIONE
# =============================================================================

def normalizza_descrizione_espositore(descrizione: str) -> str:
    """
    Normalizza descrizione espositore per matching.

    Trasformazioni:
    - Uppercase
    - Rimuovi caratteri speciali
    - Normalizza spazi multipli
    - Rimuovi numeri variabili (es: quantita)

    Args:
        descrizione: Descrizione originale

    Returns:
        Descrizione normalizzata

    Example:
        "FSTAND 24PZ Vitamina C 1000mg" -> "FSTAND PZ VITAMINA C MG"
    """
    if not descrizione:
        return ''

    # Uppercase
    desc = descrizione.upper()

    # Rimuovi caratteri speciali tranne spazi
    desc = re.sub(r'[^\w\s]', ' ', desc)

    # Rimuovi numeri (variabili tra ordini)
    desc = re.sub(r'\d+', '', desc)

    # Normalizza spazi multipli
    desc = re.sub(r'\s+', ' ', desc).strip()

    return desc


# =============================================================================
# ALGORITMO SIMILARITY SEQUENZE CHILD
# =============================================================================

def calcola_similarity_sequenze(
    seq_estratta: List[Dict],
    seq_pattern: List[Dict]
) -> Tuple[float, Dict]:
    """
    Calcola similarity tra sequenza child estratta e pattern appreso.

    Metriche combinate:
    - Jaccard similarity su codici AIC (40%)
    - Ordine sequenziale LCS (30%)
    - Quantita totali (20%)
    - Numero elementi (10%)

    Args:
        seq_estratta: Lista child estratti [{aic, codice, descrizione, quantita}, ...]
        seq_pattern: Lista child pattern [{aic, codice, descrizione, quantita}, ...]

    Returns:
        Tuple (similarity_score 0-100, details dict)
    """
    if not seq_pattern:
        # Nessun pattern da confrontare
        return 0.0, {'error': 'Nessun pattern disponibile'}

    if not seq_estratta:
        # Nessun child estratto
        return 0.0, {'error': 'Nessuna riga child estratta'}

    # Estrai codici AIC per confronto
    aic_estratti = set(item.get('aic', item.get('codice_aic', '')) for item in seq_estratta)
    aic_pattern = set(item.get('aic', item.get('codice_aic', '')) for item in seq_pattern)

    # 1. JACCARD SIMILARITY sui codici AIC
    jaccard = _calcola_jaccard(aic_estratti, aic_pattern)

    # 2. LCS - Longest Common Subsequence (ordine)
    seq_aic_estratti = [item.get('aic', item.get('codice_aic', '')) for item in seq_estratta]
    seq_aic_pattern = [item.get('aic', item.get('codice_aic', '')) for item in seq_pattern]
    lcs_score = _calcola_lcs_score(seq_aic_estratti, seq_aic_pattern)

    # 3. QUANTITA TOTALI
    qty_estratta = sum(int(item.get('quantita', 0)) for item in seq_estratta)
    qty_pattern = sum(int(item.get('quantita', 0)) for item in seq_pattern)
    qty_score = _calcola_qty_similarity(qty_estratta, qty_pattern)

    # 4. NUMERO ELEMENTI
    count_estratti = len(seq_estratta)
    count_pattern = len(seq_pattern)
    count_score = _calcola_count_similarity(count_estratti, count_pattern)

    # SCORE COMBINATO
    similarity = (
        WEIGHT_JACCARD * jaccard +
        WEIGHT_LCS * lcs_score +
        WEIGHT_QUANTITY * qty_score +
        WEIGHT_COUNT * count_score
    ) * 100  # Converti in percentuale

    details = {
        'jaccard': round(jaccard * 100, 2),
        'lcs': round(lcs_score * 100, 2),
        'quantity': round(qty_score * 100, 2),
        'count': round(count_score * 100, 2),
        'weights': {
            'jaccard': WEIGHT_JACCARD,
            'lcs': WEIGHT_LCS,
            'quantity': WEIGHT_QUANTITY,
            'count': WEIGHT_COUNT
        },
        'aic_estratti': list(aic_estratti),
        'aic_pattern': list(aic_pattern),
        'aic_comuni': list(aic_estratti & aic_pattern),
        'aic_solo_estratti': list(aic_estratti - aic_pattern),
        'aic_solo_pattern': list(aic_pattern - aic_estratti),
        'qty_estratta': qty_estratta,
        'qty_pattern': qty_pattern,
        'count_estratti': count_estratti,
        'count_pattern': count_pattern,
    }

    return round(similarity, 2), details


def _calcola_jaccard(set_a: set, set_b: set) -> float:
    """
    Calcola Jaccard similarity tra due set.

    J(A,B) = |A ∩ B| / |A ∪ B|
    """
    if not set_a and not set_b:
        return 1.0  # Due set vuoti sono identici

    intersezione = len(set_a & set_b)
    unione = len(set_a | set_b)

    if unione == 0:
        return 0.0

    return intersezione / unione


def _calcola_lcs_score(seq_a: List[str], seq_b: List[str]) -> float:
    """
    Calcola score basato su Longest Common Subsequence.

    Normalizzato rispetto alla lunghezza massima.
    """
    if not seq_a or not seq_b:
        return 0.0

    # Algoritmo LCS dinamico
    m, n = len(seq_a), len(seq_b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if seq_a[i-1] == seq_b[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])

    lcs_length = dp[m][n]
    max_length = max(m, n)

    return lcs_length / max_length if max_length > 0 else 0.0


def _calcola_qty_similarity(qty_a: int, qty_b: int) -> float:
    """
    Calcola similarity tra quantita totali.

    Usa formula: 1 - |diff| / max(a, b)
    """
    if qty_a == 0 and qty_b == 0:
        return 1.0

    if qty_a == 0 or qty_b == 0:
        return 0.0

    diff = abs(qty_a - qty_b)
    max_qty = max(qty_a, qty_b)

    return max(0.0, 1.0 - (diff / max_qty))


def _calcola_count_similarity(count_a: int, count_b: int) -> float:
    """
    Calcola similarity tra numero elementi.

    Usa formula: 1 - |diff| / max(a, b)
    """
    if count_a == 0 and count_b == 0:
        return 1.0

    if count_a == 0 or count_b == 0:
        return 0.0

    diff = abs(count_a - count_b)
    max_count = max(count_a, count_b)

    return max(0.0, 1.0 - (diff / max_count))


# =============================================================================
# DECISIONE ML
# =============================================================================

def determina_decisione_ml(similarity_score: float) -> MLDecision:
    """
    Determina decisione ML basata su similarity score.

    Soglie:
    - >= 80%: APPLY_ML (applicazione automatica, bypass supervisione)
    - 50-80%: APPLY_WARNING (applica con warning, non bloccante)
    - < 50%: SEND_SUPERVISION (ESP-A06, supervisione obbligatoria)

    Args:
        similarity_score: Score 0-100

    Returns:
        MLDecision con decision, reason, details
    """
    if similarity_score >= ML_THRESHOLD_AUTO_APPLY:
        return MLDecision(
            decision='APPLY_ML',
            similarity_score=similarity_score,
            reason=f"Similarity {similarity_score:.1f}% >= {ML_THRESHOLD_AUTO_APPLY}%: pattern applicato automaticamente",
            details={'threshold_used': ML_THRESHOLD_AUTO_APPLY}
        )

    elif similarity_score >= ML_THRESHOLD_WARNING:
        return MLDecision(
            decision='APPLY_WARNING',
            similarity_score=similarity_score,
            reason=f"Similarity {similarity_score:.1f}% tra {ML_THRESHOLD_WARNING}% e {ML_THRESHOLD_AUTO_APPLY}%: applicato con warning",
            details={'threshold_used': ML_THRESHOLD_WARNING}
        )

    else:
        return MLDecision(
            decision='SEND_SUPERVISION',
            similarity_score=similarity_score,
            reason=f"Similarity {similarity_score:.1f}% < {ML_THRESHOLD_SUPERVISION}%: conflitto grave, supervisione obbligatoria",
            details={'threshold_used': ML_THRESHOLD_SUPERVISION}
        )


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def cerca_pattern_per_espositore(
    vendor: str,
    descrizione_espositore: str,
    codice_espositore: str
) -> Optional[Dict]:
    """
    Cerca pattern ML esistente per un espositore.

    Cerca prima per codice_espositore, poi per descrizione normalizzata.
    Ritorna solo pattern con is_ordinario = TRUE.

    Args:
        vendor: Codice vendor
        descrizione_espositore: Descrizione espositore
        codice_espositore: Codice espositore

    Returns:
        Pattern dict o None se non trovato
    """
    db = get_db()

    # Prima cerca per codice espositore esatto
    row = db.execute("""
        SELECT * FROM criteri_ordinari_espositore
        WHERE vendor = %s
          AND codice_espositore = %s
          AND is_ordinario = TRUE
          AND child_sequence_json IS NOT NULL
        ORDER BY count_approvazioni DESC
        LIMIT 1
    """, (vendor, codice_espositore)).fetchone()

    if row:
        return dict(row)

    # Fallback: cerca per descrizione normalizzata
    desc_norm = normalizza_descrizione_espositore(descrizione_espositore)
    if desc_norm:
        row = db.execute("""
            SELECT * FROM criteri_ordinari_espositore
            WHERE vendor = %s
              AND descrizione_normalizzata = %s
              AND is_ordinario = TRUE
              AND child_sequence_json IS NOT NULL
            ORDER BY count_approvazioni DESC
            LIMIT 1
        """, (vendor, desc_norm)).fetchone()

        if row:
            return dict(row)

    return None


def salva_sequenza_child_pattern(
    pattern_signature: str,
    child_sequence: List[Dict],
    descrizione_normalizzata: str
) -> bool:
    """
    Salva sequenza child nel pattern dopo approvazione supervisione.

    Args:
        pattern_signature: Signature pattern
        child_sequence: Lista child [{aic, codice, descrizione, quantita}, ...]
        descrizione_normalizzata: Descrizione normalizzata espositore

    Returns:
        True se salvato con successo
    """
    db = get_db()

    try:
        db.execute("""
            UPDATE criteri_ordinari_espositore
            SET child_sequence_json = %s,
                descrizione_normalizzata = %s,
                num_child_attesi = %s
            WHERE pattern_signature = %s
        """, (
            json.dumps(child_sequence, ensure_ascii=False),
            descrizione_normalizzata,
            len(child_sequence),
            pattern_signature
        ))

        db.commit()

        log_operation(
            'SALVA_CHILD_SEQUENCE',
            'CRITERI_ORDINARI_ESPOSITORE',
            None,
            f"Salvata sequenza {len(child_sequence)} child per pattern {pattern_signature}"
        )

        return True

    except Exception as e:
        db.rollback()
        log_operation(
            'ERRORE_SALVA_CHILD',
            'CRITERI_ORDINARI_ESPOSITORE',
            None,
            f"Errore salvataggio child per {pattern_signature}: {str(e)}"
        )
        return False


def log_decisione_ml(
    id_testata: int,
    id_dettaglio: Optional[int],
    pattern_signature: str,
    descrizione_espositore: str,
    child_estratta: List[Dict],
    child_pattern: List[Dict],
    similarity_score: float,
    decision: str,
    decision_reason: str
) -> int:
    """
    Registra decisione ML nel log per audit trail.

    Args:
        id_testata: ID ordine
        id_dettaglio: ID dettaglio (opzionale)
        pattern_signature: Pattern confrontato
        descrizione_espositore: Descrizione espositore
        child_estratta: Sequenza child estratta
        child_pattern: Sequenza child pattern
        similarity_score: Score calcolato
        decision: Decisione (APPLY_ML, APPLY_WARNING, SEND_SUPERVISION)
        decision_reason: Motivazione

    Returns:
        ID log inserito
    """
    db = get_db()

    cursor = db.execute("""
        INSERT INTO log_ml_decisions
        (id_testata, id_dettaglio, pattern_signature, descrizione_espositore,
         child_sequence_estratta, child_sequence_pattern,
         similarity_score, decision, decision_reason)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id_log
    """, (
        id_testata,
        id_dettaglio,
        pattern_signature,
        descrizione_espositore,
        json.dumps(child_estratta, ensure_ascii=False),
        json.dumps(child_pattern, ensure_ascii=False),
        similarity_score,
        decision,
        decision_reason
    ))

    id_log = cursor.fetchone()[0]
    db.commit()

    return id_log


def aggiorna_esito_ml(
    id_log: int,
    final_outcome: str,
    operatore: str
) -> bool:
    """
    Aggiorna esito finale di una decisione ML dopo supervisione.

    Args:
        id_log: ID log decisione
        final_outcome: Esito (CORRECT, INCORRECT, MODIFIED)
        operatore: Username operatore

    Returns:
        True se aggiornato
    """
    db = get_db()

    try:
        db.execute("""
            UPDATE log_ml_decisions
            SET final_outcome = %s,
                operatore = %s
            WHERE id_log = %s
        """, (final_outcome, operatore, id_log))

        db.commit()
        return True

    except Exception:
        db.rollback()
        return False


def aggiorna_statistiche_pattern(
    pattern_signature: str,
    successo: bool
) -> None:
    """
    Aggiorna statistiche applicazione pattern.

    Args:
        pattern_signature: Signature pattern
        successo: True se applicazione corretta
    """
    db = get_db()

    if successo:
        db.execute("""
            UPDATE criteri_ordinari_espositore
            SET total_applications = COALESCE(total_applications, 0) + 1,
                successful_applications = COALESCE(successful_applications, 0) + 1
            WHERE pattern_signature = %s
        """, (pattern_signature,))
    else:
        db.execute("""
            UPDATE criteri_ordinari_espositore
            SET total_applications = COALESCE(total_applications, 0) + 1
            WHERE pattern_signature = %s
        """, (pattern_signature,))

    db.commit()


# =============================================================================
# WORKFLOW ML INTEGRATO
# =============================================================================

def valuta_espositore_con_ml(
    id_testata: int,
    id_dettaglio: int,
    vendor: str,
    codice_espositore: str,
    descrizione_espositore: str,
    child_estratti: List[Dict]
) -> Tuple[str, Optional[Dict]]:
    """
    Valuta espositore usando sistema ML.

    Workflow:
    1. Cerca pattern ordinario per questo espositore
    2. Se trovato, calcola similarity con child estratti
    3. Determina decisione basata su soglie
    4. Log decisione per audit

    Args:
        id_testata: ID ordine
        id_dettaglio: ID riga dettaglio espositore
        vendor: Codice vendor
        codice_espositore: Codice espositore
        descrizione_espositore: Descrizione espositore
        child_estratti: Lista child estratti dal PDF

    Returns:
        Tuple (decision, anomalia_esp_a06 o None)
        decision: 'NO_PATTERN', 'APPLY_ML', 'APPLY_WARNING', 'SEND_SUPERVISION'
    """
    # 1. Cerca pattern
    pattern = cerca_pattern_per_espositore(vendor, descrizione_espositore, codice_espositore)

    if not pattern:
        # Nessun pattern ordinario trovato
        return 'NO_PATTERN', None

    # 2. Estrai sequenza pattern
    child_pattern = json.loads(pattern.get('child_sequence_json', '[]'))

    if not child_pattern:
        return 'NO_PATTERN', None

    # 3. Calcola similarity
    similarity, details = calcola_similarity_sequenze(child_estratti, child_pattern)

    # 4. Determina decisione
    ml_decision = determina_decisione_ml(similarity)

    # 5. Log decisione
    log_decisione_ml(
        id_testata=id_testata,
        id_dettaglio=id_dettaglio,
        pattern_signature=pattern['pattern_signature'],
        descrizione_espositore=descrizione_espositore,
        child_estratta=child_estratti,
        child_pattern=child_pattern,
        similarity_score=similarity,
        decision=ml_decision.decision,
        decision_reason=ml_decision.reason
    )

    # 6. Se SEND_SUPERVISION, genera anomalia ESP-A06
    anomalia = None
    if ml_decision.decision == 'SEND_SUPERVISION':
        anomalia = {
            'tipo_anomalia': 'ESPOSITORE',
            'livello': 'ERRORE',
            'codice_anomalia': 'ESP-A06',
            'descrizione': f"Conflitto pattern ML vs estrazione: similarity {similarity:.1f}% < {ML_THRESHOLD_SUPERVISION}%",
            'valore_anomalo': f"{codice_espositore}: {descrizione_espositore}",
            'richiede_supervisione': True,
            'espositore_codice': codice_espositore,
            'pattern_signature': pattern['pattern_signature'],
            'similarity_score': similarity,
            'ml_details': details,
        }

    return ml_decision.decision, anomalia


def get_statistiche_ml() -> Dict:
    """
    Ritorna statistiche sistema ML per dashboard.

    Returns:
        Dict con statistiche aggregate
    """
    db = get_db()

    # Pattern totali vs ordinari
    patterns = db.execute("""
        SELECT
            COUNT(*) as totali,
            SUM(CASE WHEN is_ordinario THEN 1 ELSE 0 END) as ordinari,
            SUM(CASE WHEN child_sequence_json IS NOT NULL THEN 1 ELSE 0 END) as con_sequenza
        FROM criteri_ordinari_espositore
    """).fetchone()

    # Decisioni ML ultimi 30 giorni
    decisioni = db.execute("""
        SELECT
            decision,
            COUNT(*) as count
        FROM log_ml_decisions
        WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '30 days'
        GROUP BY decision
    """).fetchall()

    # Accuracy (decisioni con esito)
    accuracy = db.execute("""
        SELECT
            COUNT(*) as totali,
            SUM(CASE WHEN final_outcome = 'CORRECT' THEN 1 ELSE 0 END) as corretti
        FROM log_ml_decisions
        WHERE final_outcome IS NOT NULL
    """).fetchone()

    return {
        'pattern_totali': patterns['totali'] if patterns else 0,
        'pattern_ordinari': patterns['ordinari'] if patterns else 0,
        'pattern_con_sequenza': patterns['con_sequenza'] if patterns else 0,
        'decisioni_30d': {row['decision']: row['count'] for row in decisioni},
        'accuracy': {
            'totali': accuracy['totali'] if accuracy else 0,
            'corretti': accuracy['corretti'] if accuracy else 0,
            'percentuale': round((accuracy['corretti'] / accuracy['totali'] * 100) if accuracy and accuracy['totali'] > 0 else 0, 1)
        }
    }


# =============================================================================
# v6.2: PATTERN DA RISOLUZIONE ANOMALIE (anche INFO)
# =============================================================================

def genera_pattern_signature_espositore(
    vendor: str,
    codice_espositore: str,
    descrizione_normalizzata: str
) -> str:
    """
    Genera signature univoca per pattern espositore.

    Per anomalie INFO usiamo una signature semplificata basata su:
    - vendor
    - codice_espositore
    - descrizione normalizzata

    Args:
        vendor: Codice vendor
        codice_espositore: Codice espositore
        descrizione_normalizzata: Descrizione normalizzata

    Returns:
        Signature univoca (16 char hex)
    """
    import hashlib

    componenti = [
        vendor.upper().strip(),
        codice_espositore.strip(),
        descrizione_normalizzata,
    ]

    stringa = '|'.join(componenti)
    hash_full = hashlib.sha256(stringa.encode('utf-8')).hexdigest()

    return hash_full[:16].upper()


def registra_pattern_da_anomalia_risolta(
    id_anomalia: int,
    id_testata: int,
    operatore: str = 'SISTEMA'
) -> bool:
    """
    Registra/aggiorna pattern ML quando un'anomalia ESPOSITORE viene risolta.

    Questa funzione viene chiamata quando un operatore risolve un'anomalia
    di tipo ESPOSITORE (anche INFO). Estrae la sequenza child dall'ordine
    e la salva nel pattern, incrementando il contatore approvazioni.

    Args:
        id_anomalia: ID anomalia risolta
        id_testata: ID ordine
        operatore: Username operatore

    Returns:
        True se pattern registrato/aggiornato con successo
    """
    db = get_db()

    try:
        # 1. Trova gli espositori nell'ordine
        espositori = db.execute("""
            SELECT id_dettaglio, codice_originale, descrizione
            FROM ordini_dettaglio
            WHERE id_testata = %s
              AND is_espositore = TRUE
              AND (is_child = FALSE OR is_child IS NULL)
            ORDER BY n_riga
        """, (id_testata,)).fetchall()

        if not espositori:
            return False

        # 2. Recupera vendor dall'ordine
        ordine = db.execute("""
            SELECT v.codice_vendor AS vendor
            FROM ordini_testata ot
            JOIN vendor v ON ot.id_vendor = v.id_vendor
            WHERE ot.id_testata = %s
        """, (id_testata,)).fetchone()

        if not ordine:
            return False

        vendor = ordine['vendor']

        # 3. Per ogni espositore, registra/aggiorna pattern
        for esp in espositori:
            esp = dict(esp)
            codice_esp = esp['codice_originale']
            descrizione = esp['descrizione']
            id_dettaglio = esp['id_dettaglio']

            # Normalizza descrizione
            desc_norm = normalizza_descrizione_espositore(descrizione)

            # Genera signature
            pattern_sig = genera_pattern_signature_espositore(vendor, codice_esp, desc_norm)

            # Estrai child di questo espositore
            children = db.execute("""
                SELECT codice_aic, codice_originale, descrizione, q_venduta AS quantita
                FROM ordini_dettaglio
                WHERE id_testata = %s
                  AND id_parent_espositore = %s
                  AND is_child = TRUE
                ORDER BY n_riga
            """, (id_testata, id_dettaglio)).fetchall()

            child_sequence = [
                {
                    'aic': c['codice_aic'],
                    'codice': c['codice_originale'],
                    'descrizione': c['descrizione'],
                    'quantita': c['quantita']
                }
                for c in children
            ]

            # 4. Verifica se pattern esiste
            existing = db.execute("""
                SELECT pattern_signature, count_approvazioni, child_sequence_json
                FROM criteri_ordinari_espositore
                WHERE pattern_signature = %s
            """, (pattern_sig,)).fetchone()

            if existing:
                # Aggiorna pattern esistente
                existing = dict(existing)
                new_count = (existing['count_approvazioni'] or 0) + 1
                is_ordinario = new_count >= SOGLIA_PROMOZIONE

                # Aggiorna solo se la nuova sequenza ha child
                if child_sequence:
                    db.execute("""
                        UPDATE criteri_ordinari_espositore
                        SET count_approvazioni = %s,
                            is_ordinario = %s,
                            child_sequence_json = %s,
                            descrizione_normalizzata = %s,
                            num_child_attesi = %s,
                            data_promozione = CASE WHEN %s AND data_promozione IS NULL THEN CURRENT_TIMESTAMP ELSE data_promozione END
                        WHERE pattern_signature = %s
                    """, (
                        new_count,
                        is_ordinario,
                        json.dumps(child_sequence, ensure_ascii=False),
                        desc_norm,
                        len(child_sequence),
                        is_ordinario,
                        pattern_sig
                    ))
                else:
                    # Solo incrementa contatore
                    db.execute("""
                        UPDATE criteri_ordinari_espositore
                        SET count_approvazioni = %s,
                            is_ordinario = %s,
                            data_promozione = CASE WHEN %s AND data_promozione IS NULL THEN CURRENT_TIMESTAMP ELSE data_promozione END
                        WHERE pattern_signature = %s
                    """, (new_count, is_ordinario, is_ordinario, pattern_sig))

                log_operation(
                    'AGGIORNA_PATTERN_ML',
                    'CRITERI_ORDINARI_ESPOSITORE',
                    None,
                    f"Pattern {pattern_sig} aggiornato: count={new_count}, ordinario={is_ordinario}",
                    operatore=operatore
                )

            else:
                # Crea nuovo pattern
                db.execute("""
                    INSERT INTO criteri_ordinari_espositore
                    (pattern_signature, pattern_descrizione, vendor, codice_espositore,
                     descrizione_normalizzata, child_sequence_json, num_child_attesi,
                     count_approvazioni, is_ordinario)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 1, FALSE)
                """, (
                    pattern_sig,
                    f"Espositore {codice_esp}: {descrizione[:50]}",
                    vendor,
                    codice_esp,
                    desc_norm,
                    json.dumps(child_sequence, ensure_ascii=False) if child_sequence else None,
                    len(child_sequence)
                ))

                log_operation(
                    'CREA_PATTERN_ML',
                    'CRITERI_ORDINARI_ESPOSITORE',
                    None,
                    f"Nuovo pattern {pattern_sig} per espositore {codice_esp}",
                    operatore=operatore
                )

        db.commit()
        return True

    except Exception as e:
        db.rollback()
        log_operation(
            'ERRORE_PATTERN_ML',
            'CRITERI_ORDINARI_ESPOSITORE',
            None,
            f"Errore registrazione pattern da anomalia {id_anomalia}: {str(e)}"
        )
        return False


def verifica_pattern_ordinario_per_espositore(
    vendor: str,
    codice_espositore: str,
    descrizione_espositore: str,
    child_estratti: List[Dict]
) -> Tuple[bool, Optional[float]]:
    """
    Verifica se esiste pattern ordinario per un espositore.

    Usato prima di generare anomalia INFO per evitare
    segnalazioni ripetute su pattern gia' validati.

    Args:
        vendor: Codice vendor
        codice_espositore: Codice espositore
        descrizione_espositore: Descrizione espositore
        child_estratti: Lista child estratti

    Returns:
        Tuple (pattern_ordinario_valido, similarity_score)
        - pattern_ordinario_valido: True se esiste pattern ordinario con similarity >= 80%
        - similarity_score: Score calcolato (None se no pattern)
    """
    desc_norm = normalizza_descrizione_espositore(descrizione_espositore)
    pattern_sig = genera_pattern_signature_espositore(vendor, codice_espositore, desc_norm)

    db = get_db()

    # Cerca pattern
    pattern = db.execute("""
        SELECT is_ordinario, child_sequence_json
        FROM criteri_ordinari_espositore
        WHERE pattern_signature = %s
    """, (pattern_sig,)).fetchone()

    if not pattern:
        return False, None

    pattern = dict(pattern)

    if not pattern['is_ordinario']:
        return False, None

    # Pattern ordinario trovato, calcola similarity
    child_pattern = json.loads(pattern['child_sequence_json'] or '[]')

    if not child_pattern:
        # Pattern ordinario ma senza sequenza child, accetta comunque
        return True, 100.0

    similarity, _ = calcola_similarity_sequenze(child_estratti, child_pattern)

    # Se similarity >= 80%, pattern valido
    if similarity >= ML_THRESHOLD_AUTO_APPLY:
        return True, similarity

    return False, similarity


# =============================================================================
# v6.2: PROCESSAMENTO RETROATTIVO ANOMALIE
# =============================================================================

def processa_anomalie_risolte_retroattive() -> Dict:
    """
    Processa retroattivamente tutte le anomalie ESPOSITORE già risolte.

    Crea pattern ML da anomalie storiche che erano state risolte
    prima dell'implementazione del sistema ML.

    Returns:
        Dict con statistiche processamento
    """
    db = get_db()

    # Trova tutte le anomalie ESPOSITORE risolte con id_testata
    anomalie = db.execute("""
        SELECT DISTINCT a.id_anomalia, a.id_testata
        FROM anomalie a
        WHERE a.tipo_anomalia = 'ESPOSITORE'
          AND a.stato = 'RISOLTA'
          AND a.id_testata IS NOT NULL
        ORDER BY a.data_creazione
    """).fetchall()

    stats = {
        'totale_anomalie': len(anomalie),
        'processate': 0,
        'successo': 0,
        'errori': 0,
        'pattern_creati': 0,
        'pattern_aggiornati': 0
    }

    # Conta pattern prima del processamento
    pattern_prima = db.execute(
        "SELECT COUNT(*) as count FROM criteri_ordinari_espositore"
    ).fetchone()['count']

    for anomalia in anomalie:
        anomalia = dict(anomalia)
        try:
            success = registra_pattern_da_anomalia_risolta(
                id_anomalia=anomalia['id_anomalia'],
                id_testata=anomalia['id_testata'],
                operatore='RETROATTIVO'
            )

            stats['processate'] += 1
            if success:
                stats['successo'] += 1
            else:
                stats['errori'] += 1

        except Exception as e:
            stats['errori'] += 1
            log_operation(
                'ERRORE_RETROATTIVO',
                'ANOMALIE',
                anomalia['id_anomalia'],
                f"Errore processamento retroattivo: {str(e)}"
            )

    # Conta pattern dopo il processamento
    pattern_dopo = db.execute(
        "SELECT COUNT(*) as count FROM criteri_ordinari_espositore"
    ).fetchone()['count']

    stats['pattern_creati'] = pattern_dopo - pattern_prima
    stats['pattern_aggiornati'] = stats['successo'] - stats['pattern_creati']

    # Log operazione
    log_operation(
        'PROCESSAMENTO_RETROATTIVO',
        'CRITERI_ORDINARI_ESPOSITORE',
        None,
        f"Processate {stats['processate']} anomalie: {stats['successo']} OK, {stats['errori']} errori, {stats['pattern_creati']} nuovi pattern"
    )

    return stats
