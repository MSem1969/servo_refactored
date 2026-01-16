# =============================================================================
# TO_EXTRACTOR v6.0 - SUPERVISIONE SERVICE
# =============================================================================
# Gestione supervisione umana e machine learning per espositori
# secondo REGOLE_ANGELINI v3.0
#
# FUNZIONALITÀ:
# 1. SUPERVISIONE UMANA:
#    - Blocco ordini con anomalie bloccanti
#    - Workflow APPROVE/REJECT/MODIFY
#    - Notifiche e audit trail
#
# 2. MACHINE LEARNING:
#    - Pattern signature per identificare anomalie simili
#    - Conteggio approvazioni per pattern
#    - Promozione automatica a "criterio ordinario" dopo 5 approvazioni
#    - Applicazione automatica criteri appresi
# =============================================================================

import hashlib
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from ..database_pg import get_db, log_operation
from .ml_pattern_matching import (
    normalizza_descrizione_espositore,
    salva_sequenza_child_pattern
)


# =============================================================================
# COSTANTI
# =============================================================================

# Soglia per promozione pattern a "ordinario"
# Dopo N approvazioni con stesso pattern, diventa automatico
SOGLIA_PROMOZIONE = 5

# Fasce scostamento per normalizzazione pattern
# Usate per raggruppare scostamenti simili
FASCE_NORMALIZZATE = {
    (-10, 0): '-10/0%',
    (-20, -10): '-20/-10%',
    (-50, -20): '-50/-20%',
    (0, 10): '0/+10%',
    (10, 20): '+10/+20%',
    (20, 50): '+20/+50%',
}


# =============================================================================
# PATTERN SIGNATURE
# =============================================================================

def calcola_pattern_signature(
    vendor: str,
    codice_anomalia: str,
    codice_espositore: str,
    pezzi_per_unita: int,
    fascia_scostamento: str
) -> str:
    """
    Calcola signature univoca per un pattern anomalia.
    
    La signature permette di identificare anomalie "simili" che possono
    essere gestite automaticamente dopo sufficiente apprendimento.
    
    Componenti signature:
    - vendor: Es. "ANGELINI"
    - codice_anomalia: Es. "ESP-A01"
    - codice_espositore: Codice prodotto parent
    - pezzi_per_unita: Pezzi attesi per unità espositore
    - fascia_scostamento: Fascia normalizzata (BASSO, MEDIO, etc.)
    
    Args:
        vendor: Codice vendor
        codice_anomalia: Codice tipo anomalia
        codice_espositore: Codice prodotto espositore
        pezzi_per_unita: Pezzi per unità
        fascia_scostamento: Fascia scostamento
        
    Returns:
        SHA256 hash troncato a 16 caratteri
    """
    # Normalizza componenti
    componenti = [
        vendor.upper().strip(),
        codice_anomalia.upper().strip(),
        codice_espositore.strip(),
        str(pezzi_per_unita),
        fascia_scostamento.upper().strip(),
    ]
    
    # Concatena e calcola hash
    stringa_pattern = '|'.join(componenti)
    hash_full = hashlib.sha256(stringa_pattern.encode('utf-8')).hexdigest()
    
    # Tronca a 16 caratteri per leggibilità
    return hash_full[:16].upper()


def normalizza_fascia_scostamento(percentuale: float) -> str:
    """
    Normalizza percentuale scostamento in fascia discreta.
    
    Questo permette di raggruppare scostamenti simili nello stesso pattern,
    aumentando le possibilità di apprendimento.
    
    Args:
        percentuale: Scostamento in percentuale (es: -12.5)
        
    Returns:
        Fascia normalizzata (es: "-20/-10%")
    """
    if percentuale == 0:
        return 'ZERO'
    
    for (low, high), label in FASCE_NORMALIZZATE.items():
        if low <= percentuale < high:
            return label
    
    # Fuori range
    if percentuale < -50:
        return '<-50%'
    else:
        return '>+50%'


def genera_descrizione_pattern(anomalia: Dict) -> str:
    """
    Genera descrizione leggibile del pattern.
    
    Args:
        anomalia: Dati anomalia
        
    Returns:
        Descrizione pattern
    """
    codice = anomalia.get('codice_anomalia', '')
    esp = anomalia.get('espositore_codice', '')
    pezzi_a = anomalia.get('pezzi_attesi', 0)
    pezzi_t = anomalia.get('pezzi_trovati', 0)
    fascia = anomalia.get('fascia_scostamento', '')
    
    return f"{codice} su espositore {esp} (attesi {pezzi_a}, trovati {pezzi_t}, fascia {fascia})"


# =============================================================================
# SUPERVISIONE UMANA - GESTIONE RICHIESTE
# =============================================================================

def crea_richiesta_supervisione(
    id_testata: int,
    id_anomalia: int,
    anomalia: Dict
) -> int:
    """
    Crea nuova richiesta di supervisione per un'anomalia.
    
    Inserisce record in SUPERVISIONE_ESPOSITORE con stato PENDING
    e calcola pattern signature per ML.
    
    Args:
        id_testata: ID ordine in ORDINI_TESTATA
        id_anomalia: ID anomalia in ANOMALIE
        anomalia: Dati completi anomalia
        
    Returns:
        ID supervisione creata
    """
    db = get_db()
    
    # Calcola pattern signature
    pezzi_attesi = anomalia.get('pezzi_attesi', 0)
    pezzi_trovati = anomalia.get('pezzi_trovati', 0)
    
    if pezzi_attesi > 0:
        scostamento_pct = ((pezzi_trovati - pezzi_attesi) / pezzi_attesi) * 100
    else:
        scostamento_pct = 0
    
    fascia_norm = normalizza_fascia_scostamento(scostamento_pct)
    
    pattern_sig = calcola_pattern_signature(
        vendor='ANGELINI',
        codice_anomalia=anomalia.get('codice_anomalia', ''),
        codice_espositore=anomalia.get('espositore_codice', ''),
        pezzi_per_unita=pezzi_attesi,
        fascia_scostamento=fascia_norm
    )
    
    # Inserisci richiesta supervisione
    cursor = db.execute("""
        INSERT INTO SUPERVISIONE_ESPOSITORE
        (id_testata, id_anomalia, codice_anomalia, codice_espositore,
         descrizione_espositore, pezzi_attesi, pezzi_trovati,
         valore_calcolato, pattern_signature, stato)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
    """, (
        id_testata,
        id_anomalia,
        anomalia.get('codice_anomalia', ''),
        anomalia.get('espositore_codice', ''),
        anomalia.get('valore_anomalo', ''),
        pezzi_attesi,
        pezzi_trovati,
        0.0,  # valore_calcolato viene aggiornato dopo
        pattern_sig,
    ))

    db.commit()
    id_supervisione = cursor.lastrowid
    
    # Assicura che il pattern esista nella tabella criteri
    _assicura_pattern_esistente(pattern_sig, anomalia)
    
    # Log operazione
    log_operation(
        'CREA_SUPERVISIONE',
        'SUPERVISIONE_ESPOSITORE',
        id_supervisione,
        f"Creata supervisione per ordine {id_testata}, pattern {pattern_sig}"
    )
    
    return id_supervisione


def blocca_ordine_per_supervisione(id_testata: int):
    """
    Blocca un ordine settando stato PENDING_REVIEW.
    
    L'ordine non potrà essere esportato finché tutte le supervisioni
    non sono state gestite.
    
    Args:
        id_testata: ID ordine da bloccare
    """
    db = get_db()
    
    db.execute("""
        UPDATE ORDINI_TESTATA 
        SET stato = 'PENDING_REVIEW' 
        WHERE id_testata = ?
    """, (id_testata,))
    
    db.commit()
    
    log_operation(
        'BLOCCA_ORDINE',
        'ORDINI_TESTATA',
        id_testata,
        'Ordine bloccato per supervisione espositore'
    )


def sblocca_ordine_se_completo(id_testata: int):
    """
    Sblocca ordine se non ci sono più supervisioni pending.
    
    Verifica che tutte le supervisioni siano state gestite,
    poi riporta lo stato a ESTRATTO.
    
    Args:
        id_testata: ID ordine da verificare
    """
    db = get_db()
    
    # Verifica supervisioni pending
    pending = db.execute("""
        SELECT COUNT(*) FROM SUPERVISIONE_ESPOSITORE 
        WHERE id_testata = ? AND stato = 'PENDING'
    """, (id_testata,)).fetchone()[0]
    
    if pending == 0:
        db.execute("""
            UPDATE ORDINI_TESTATA 
            SET stato = 'ESTRATTO' 
            WHERE id_testata = ? AND stato = 'PENDING_REVIEW'
        """, (id_testata,))
        db.commit()
        
        log_operation(
            'SBLOCCA_ORDINE',
            'ORDINI_TESTATA',
            id_testata,
            'Ordine sbloccato dopo completamento supervisioni'
        )


# =============================================================================
# SUPERVISIONE UMANA - DECISIONI
# =============================================================================

def approva_supervisione(id_supervisione: int, operatore: str, note: str = None) -> bool:
    """
    Approva una richiesta di supervisione.

    Effetti:
    1. Aggiorna stato a APPROVED
    2. Registra approvazione nel pattern ML
    3. Se raggiunta soglia, promuove pattern a ordinario
    4. Sblocca ordine se era l'ultima supervisione pending
    5. v6.2: Salva sequenza child nel pattern per ML

    Args:
        id_supervisione: ID supervisione
        operatore: Username operatore
        note: Note opzionali

    Returns:
        True se successo
    """
    db = get_db()

    # Recupera dati supervisione
    sup = db.execute(
        "SELECT * FROM SUPERVISIONE_ESPOSITORE WHERE id_supervisione = ?",
        (id_supervisione,)
    ).fetchone()

    if not sup:
        return False

    sup = dict(sup)

    # Aggiorna stato supervisione
    db.execute("""
        UPDATE SUPERVISIONE_ESPOSITORE
        SET stato = 'APPROVED',
            operatore = ?,
            timestamp_decisione = CURRENT_TIMESTAMP,
            note = ?
        WHERE id_supervisione = ?
    """, (operatore, note, id_supervisione))

    # Registra approvazione pattern
    registra_approvazione_pattern(sup['pattern_signature'], operatore)

    # v6.2: Estrai e salva sequenza child per ML
    _salva_child_sequence_da_supervisione(db, sup)

    db.commit()

    # Sblocca ordine se completo
    sblocca_ordine_se_completo(sup['id_testata'])

    log_operation(
        'APPROVA_SUPERVISIONE',
        'SUPERVISIONE_ESPOSITORE',
        id_supervisione,
        f"Approvato",
        operatore=operatore
    )

    return True


def _salva_child_sequence_da_supervisione(db, sup: dict) -> None:
    """
    Estrae child confermati da supervisione e salva nel pattern ML.

    v6.2: Chiamata dopo approvazione supervisione per alimentare
    l'apprendimento ML con la sequenza child corretta.

    Args:
        db: Connessione database
        sup: Dizionario supervisione con id_testata e codice_espositore
    """
    # Trova il dettaglio espositore parent
    parent = db.execute("""
        SELECT id_dettaglio, descrizione
        FROM ordini_dettaglio
        WHERE id_testata = ?
          AND codice_originale = ?
          AND is_espositore = TRUE
        LIMIT 1
    """, (sup['id_testata'], sup['codice_espositore'])).fetchone()

    if not parent:
        return

    parent = dict(parent)

    # Estrai tutti i child di questo parent
    children = db.execute("""
        SELECT codice_aic, codice_originale, descrizione, q_venduta AS quantita
        FROM ordini_dettaglio
        WHERE id_testata = ?
          AND id_parent_espositore = ?
          AND is_child = TRUE
        ORDER BY n_riga
    """, (sup['id_testata'], parent['id_dettaglio'])).fetchall()

    if not children:
        return

    # Prepara sequenza child per salvataggio
    child_sequence = [
        {
            'aic': row['codice_aic'],
            'codice': row['codice_originale'],
            'descrizione': row['descrizione'],
            'quantita': row['quantita']
        }
        for row in children
    ]

    # Normalizza descrizione espositore
    desc_norm = normalizza_descrizione_espositore(parent['descrizione'])

    # Salva nel pattern
    salva_sequenza_child_pattern(
        pattern_signature=sup['pattern_signature'],
        child_sequence=child_sequence,
        descrizione_normalizzata=desc_norm
    )


def rifiuta_supervisione(id_supervisione: int, operatore: str, note: str = None) -> bool:
    """
    Rifiuta una richiesta di supervisione.

    Effetti:
    1. Aggiorna stato a REJECTED
    2. Reset conteggio approvazioni pattern
    3. Sblocca ordine se era l'ultima supervisione pending (v6.2.4 fix)

    Args:
        id_supervisione: ID supervisione
        operatore: Username operatore
        note: Note opzionali (obbligatorie per motivazione)

    Returns:
        True se successo
    """
    db = get_db()

    # Recupera dati supervisione
    sup = db.execute(
        "SELECT * FROM SUPERVISIONE_ESPOSITORE WHERE id_supervisione = ?",
        (id_supervisione,)
    ).fetchone()

    if not sup:
        return False

    sup = dict(sup)

    # Aggiorna stato supervisione
    db.execute("""
        UPDATE SUPERVISIONE_ESPOSITORE
        SET stato = 'REJECTED',
            operatore = ?,
            timestamp_decisione = datetime('now'),
            note = ?
        WHERE id_supervisione = ?
    """, (operatore, note, id_supervisione))

    # Reset pattern (rifiuto invalida apprendimento precedente)
    registra_rifiuto_pattern(sup['pattern_signature'])

    db.commit()

    # v6.2.4: Sblocca ordine se non ci sono più supervisioni pending
    sblocca_ordine_se_completo(sup['id_testata'])

    log_operation(
        'RIFIUTA_SUPERVISIONE',
        'SUPERVISIONE_ESPOSITORE',
        id_supervisione,
        f"Rifiutato: {note}",
        operatore=operatore
    )

    return True


def modifica_supervisione(
    id_supervisione: int, 
    operatore: str, 
    modifiche: Dict,
    note: str = None
) -> bool:
    """
    Modifica manualmente i dati di un ordine in supervisione.
    
    Effetti:
    1. Salva modifiche in modifiche_manuali_json
    2. Aggiorna stato a MODIFIED
    3. NON conta come approvazione pattern (caso speciale)
    
    Args:
        id_supervisione: ID supervisione
        operatore: Username operatore
        modifiche: Dizionario modifiche applicate
        note: Note opzionali
        
    Returns:
        True se successo
    """
    db = get_db()
    
    # Recupera dati supervisione
    sup = db.execute(
        "SELECT * FROM SUPERVISIONE_ESPOSITORE WHERE id_supervisione = ?",
        (id_supervisione,)
    ).fetchone()
    
    if not sup:
        return False
    
    sup = dict(sup)
    
    # Aggiorna stato supervisione
    db.execute("""
        UPDATE SUPERVISIONE_ESPOSITORE 
        SET stato = 'MODIFIED', 
            operatore = ?, 
            timestamp_decisione = datetime('now'),
            note = ?,
            modifiche_manuali_json = ?
        WHERE id_supervisione = ?
    """, (operatore, note, json.dumps(modifiche), id_supervisione))
    
    db.commit()
    
    # Sblocca ordine
    sblocca_ordine_se_completo(sup['id_testata'])
    
    log_operation(
        'MODIFICA_SUPERVISIONE',
        'SUPERVISIONE_ESPOSITORE',
        id_supervisione,
        f"Modificato",
        operatore=operatore
    )
    
    return True


# =============================================================================
# MACHINE LEARNING - GESTIONE PATTERN
# =============================================================================

def _assicura_pattern_esistente(pattern_signature: str, anomalia: Dict):
    """
    Assicura che un pattern esista nella tabella criteri.
    
    Se non esiste, lo crea con count_approvazioni = 0.
    
    Args:
        pattern_signature: Signature pattern
        anomalia: Dati anomalia per metadati
    """
    db = get_db()
    
    existing = db.execute(
        "SELECT 1 FROM CRITERI_ORDINARI_ESPOSITORE WHERE pattern_signature = ?",
        (pattern_signature,)
    ).fetchone()
    
    if not existing:
        db.execute("""
            INSERT INTO CRITERI_ORDINARI_ESPOSITORE
            (pattern_signature, pattern_descrizione, vendor, codice_anomalia,
             codice_espositore, pezzi_per_unita, tipo_scostamento, fascia_scostamento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pattern_signature,
            genera_descrizione_pattern(anomalia),
            'ANGELINI',
            anomalia.get('codice_anomalia', ''),
            anomalia.get('espositore_codice', ''),
            anomalia.get('pezzi_attesi', 0),
            'DIFETTO' if anomalia.get('pezzi_trovati', 0) < anomalia.get('pezzi_attesi', 0) else 'ECCESSO',
            anomalia.get('fascia_scostamento', ''),
        ))
        db.commit()


def registra_approvazione_pattern(pattern_signature: str, operatore: str):
    """
    Registra approvazione per un pattern.
    
    Incrementa contatore e, se raggiunta soglia, promuove a ordinario.
    
    Args:
        pattern_signature: Signature pattern
        operatore: Username operatore
    """
    db = get_db()
    
    # Incrementa contatore
    db.execute("""
        UPDATE CRITERI_ORDINARI_ESPOSITORE 
        SET count_approvazioni = count_approvazioni + 1,
            operatori_approvatori = COALESCE(operatori_approvatori || ', ', '') || ?
        WHERE pattern_signature = ?
    """, (operatore, pattern_signature))
    
    # Verifica promozione
    row = db.execute(
        "SELECT count_approvazioni FROM CRITERI_ORDINARI_ESPOSITORE WHERE pattern_signature = ?",
        (pattern_signature,)
    ).fetchone()
    
    if row and row[0] >= SOGLIA_PROMOZIONE:
        # Promuovi a ordinario
        db.execute("""
            UPDATE CRITERI_ORDINARI_ESPOSITORE 
            SET is_ordinario = TRUE, data_promozione = datetime('now')
            WHERE pattern_signature = ? AND is_ordinario = FALSE
        """, (pattern_signature,))
        
        log_operation(
            'PROMOZIONE_PATTERN',
            'CRITERI_ORDINARI_ESPOSITORE',
            None,
            f"Pattern {pattern_signature} promosso a ordinario dopo {SOGLIA_PROMOZIONE} approvazioni"
        )
    
    db.commit()


def registra_rifiuto_pattern(pattern_signature: str):
    """
    Registra rifiuto per un pattern.
    
    Reset contatore approvazioni a 0 (un rifiuto invalida apprendimento).
    
    Args:
        pattern_signature: Signature pattern
    """
    db = get_db()
    
    db.execute("""
        UPDATE CRITERI_ORDINARI_ESPOSITORE 
        SET count_approvazioni = 0,
            is_ordinario = FALSE,
            data_promozione = NULL
        WHERE pattern_signature = ?
    """, (pattern_signature,))
    
    db.commit()
    
    log_operation(
        'RESET_PATTERN',
        'CRITERI_ORDINARI_ESPOSITORE',
        None,
        f"Pattern {pattern_signature} resettato dopo rifiuto"
    )


# =============================================================================
# MACHINE LEARNING - VALUTAZIONE AUTOMATICA
# =============================================================================

def verifica_pattern_ordinario(pattern_signature: str) -> bool:
    """
    Verifica se un pattern è stato promosso a ordinario.
    
    Args:
        pattern_signature: Signature pattern
        
    Returns:
        True se pattern è ordinario (applicabile automaticamente)
    """
    db = get_db()
    
    row = db.execute("""
        SELECT is_ordinario FROM CRITERI_ORDINARI_ESPOSITORE 
        WHERE pattern_signature = ? AND is_ordinario = TRUE
    """, (pattern_signature,)).fetchone()
    
    return row is not None


def valuta_anomalia_con_apprendimento(
    id_testata: int,
    anomalia: Dict
) -> Tuple[bool, Optional[str]]:
    """
    Valuta anomalia usando criteri appresi.
    
    Se pattern è ordinario (>= 5 approvazioni), applica automaticamente
    senza richiedere supervisione umana.
    
    Args:
        id_testata: ID ordine
        anomalia: Dati anomalia
        
    Returns:
        Tuple (applicato_auto, pattern_signature)
        - applicato_auto: True se gestito automaticamente
        - pattern_signature: Signature per riferimento
    """
    db = get_db()
    
    # Calcola pattern
    pezzi_attesi = anomalia.get('pezzi_attesi', 0)
    pezzi_trovati = anomalia.get('pezzi_trovati', 0)
    
    if pezzi_attesi > 0:
        scostamento_pct = ((pezzi_trovati - pezzi_attesi) / pezzi_attesi) * 100
    else:
        scostamento_pct = 0
    
    fascia_norm = normalizza_fascia_scostamento(scostamento_pct)
    
    pattern_sig = calcola_pattern_signature(
        vendor='ANGELINI',
        codice_anomalia=anomalia.get('codice_anomalia', ''),
        codice_espositore=anomalia.get('espositore_codice', ''),
        pezzi_per_unita=pezzi_attesi,
        fascia_scostamento=fascia_norm
    )
    
    # Verifica se ordinario
    if verifica_pattern_ordinario(pattern_sig):
        # Applica automaticamente
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
            f"Criterio ordinario {pattern_sig} applicato automaticamente"
        )
        
        return True, pattern_sig
    
    # Pattern non ordinario: richiede supervisione
    return False, pattern_sig


def log_criterio_applicato(
    id_testata: int,
    id_dettaglio: Optional[int],
    pattern_signature: str,
    automatico: bool = True,
    operatore: str = 'SISTEMA'
):
    """
    Registra applicazione criterio per audit trail.
    
    Args:
        id_testata: ID ordine
        id_dettaglio: ID dettaglio (opzionale)
        pattern_signature: Pattern applicato
        automatico: True se applicato automaticamente
        operatore: Username operatore
    """
    db = get_db()
    
    db.execute("""
        INSERT INTO LOG_CRITERI_APPLICATI
        (id_testata, id_dettaglio, pattern_signature, applicato_automaticamente, operatore)
        VALUES (?, ?, ?, ?, ?)
    """, (id_testata, id_dettaglio, pattern_signature, 1 if automatico else 0, operatore))
    
    db.commit()


# =============================================================================
# QUERY E UTILITÀ
# =============================================================================

def può_emettere_tracciato(id_testata: int) -> bool:
    """
    Verifica se un ordine può essere esportato come tracciato.
    
    Condizioni:
    1. Stato != PENDING_REVIEW
    2. Nessuna supervisione PENDING
    
    Args:
        id_testata: ID ordine
        
    Returns:
        True se ordine può essere esportato
    """
    db = get_db()
    
    # Verifica stato ordine
    ordine = db.execute(
        "SELECT stato FROM ORDINI_TESTATA WHERE id_testata = ?",
        (id_testata,)
    ).fetchone()
    
    if not ordine or ordine['stato'] == 'PENDING_REVIEW':
        return False
    
    # Verifica supervisioni pending
    pending = db.execute("""
        SELECT COUNT(*) FROM SUPERVISIONE_ESPOSITORE 
        WHERE id_testata = ? AND stato = 'PENDING'
    """, (id_testata,)).fetchone()[0]
    
    return pending == 0


def get_supervisioni_per_ordine(id_testata: int) -> List[Dict]:
    """
    Ritorna tutte le supervisioni per un ordine.
    
    Args:
        id_testata: ID ordine
        
    Returns:
        Lista supervisioni
    """
    db = get_db()
    
    rows = db.execute("""
        SELECT se.*, coe.count_approvazioni, coe.is_ordinario
        FROM SUPERVISIONE_ESPOSITORE se
        LEFT JOIN CRITERI_ORDINARI_ESPOSITORE coe 
            ON se.pattern_signature = coe.pattern_signature
        WHERE se.id_testata = ?
        ORDER BY se.timestamp_creazione DESC
    """, (id_testata,)).fetchall()
    
    return [dict(row) for row in rows]


def get_storico_criteri_applicati(limit: int = 50) -> List[Dict]:
    """
    Ritorna storico applicazioni criteri.
    
    Args:
        limit: Numero massimo risultati
        
    Returns:
        Lista log applicazioni
    """
    db = get_db()
    
    rows = db.execute("""
        SELECT 
            lca.*,
            coe.pattern_descrizione,
            ot.numero_ordine_vendor AS numero_ordine,
            v.codice_vendor AS vendor
        FROM LOG_CRITERI_APPLICATI lca
        LEFT JOIN CRITERI_ORDINARI_ESPOSITORE coe 
            ON lca.pattern_signature = coe.pattern_signature
        LEFT JOIN ORDINI_TESTATA ot ON lca.id_testata = ot.id_testata
        LEFT JOIN VENDOR v ON ot.id_vendor = v.id_vendor
        ORDER BY lca.timestamp DESC
        LIMIT ?
    """, (limit,)).fetchall()
    
    return [dict(row) for row in rows]
