# =============================================================================
# TO_EXTRACTOR v6.0 - PDF PROCESSOR SERVICE
# =============================================================================
# Convertito da notebook Colab - Cella 13
# Elabora PDF e inserisce dati nel database
# =============================================================================

import os
import io
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

# PDF extraction
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("⚠️ pdfplumber non disponibile")

from ..config import config
from ..database_pg import get_db, get_vendor_id, log_operation
from ..utils import compute_file_hash, detect_vendor, generate_order_key, calcola_q_totale
from ..extractors import get_extractor
from .lookup import lookup_farmacia
from .supervisione import (
    valuta_anomalia_con_apprendimento,
    crea_richiesta_supervisione,
    blocca_ordine_per_supervisione,
)
from .espositore import CODICI_ANOMALIA, LOOKUP_SCORE_GRAVE, LOOKUP_SCORE_ORDINARIA


# =============================================================================
# UTILITY DATE - PostgreSQL richiede formato ISO (YYYY-MM-DD)
# =============================================================================

def _convert_date_to_iso(date_str: str) -> Optional[str]:
    """
    Converte data da formato italiano (DD/MM/YYYY) a ISO (YYYY-MM-DD).
    Ritorna None per date vuote (PostgreSQL non accetta stringhe vuote per DATE).
    """
    if not date_str or date_str.strip() == '':
        return None

    # Se contiene '/', assumiamo formato DD/MM/YYYY
    if '/' in date_str:
        parts = date_str.split('/')
        if len(parts) == 3:
            day, month, year = parts
            # Normalizza anno a 4 cifre
            if len(year) == 2:
                year = '20' + year
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    # Già in formato ISO o altro, ritorna invariato
    return date_str


# =============================================================================
# FUNZIONE PRINCIPALE
# =============================================================================

def process_pdf(
    filename: str, 
    file_content: bytes, 
    pdf_path: str = None,
    save_to_disk: bool = True
) -> Dict[str, Any]:
    """
    Elabora un PDF e inserisce i dati nel database.
    
    Args:
        filename: Nome file originale
        file_content: Contenuto binario del PDF
        pdf_path: Percorso file su disco (opzionale, per estrattori con coordinate)
        save_to_disk: Se True, salva il PDF nella cartella uploads
        
    Returns:
        Dict con statistiche elaborazione:
        - filename: nome file
        - status: 'OK', 'DUPLICATO', 'ERRORE'
        - vendor: codice vendor rilevato
        - ordini: numero ordini estratti
        - righe: numero righe prodotto
        - anomalie: lista messaggi anomalia
        - id_acquisizione: ID record ACQUISIZIONI
    """
    result = {
        'filename': filename,
        'status': 'OK',
        'vendor': '',
        'ordini': 0,
        'righe': 0,
        'anomalie': [],
        'id_acquisizione': None,
    }
    
    db = get_db()
    
    try:
        # =====================================================================
        # 1. CALCOLA HASH E VERIFICA DUPLICATO
        # =====================================================================
        hash_file = compute_file_hash(file_content)
        
        existing = db.execute(
            "SELECT id_acquisizione FROM ACQUISIZIONI WHERE hash_file = ?",
            (hash_file,)
        ).fetchone()
        
        is_duplicato = True if existing else False
        id_acq_originale = existing['id_acquisizione'] if existing else None
        
        # =====================================================================
        # 2. ESTRAI TESTO DAL PDF
        # =====================================================================
        if not PDFPLUMBER_AVAILABLE:
            raise ImportError("pdfplumber non installato")
        
        pdf_file = io.BytesIO(file_content)
        text = ""
        lines = []
        
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
                lines.extend(page_text.split('\n'))
        
        # =====================================================================
        # 3. RILEVA VENDOR
        # =====================================================================
        vendor, confidence = detect_vendor(text, filename)
        result['vendor'] = vendor

        # v6.2: Vendor UNKNOWN non blocca più l'elaborazione
        # L'ordine viene inserito con anomalia bloccante EXT-A01
        is_vendor_unknown = vendor == "UNKNOWN"
        if is_vendor_unknown:
            result['anomalie'].append(f'Vendor non riconosciuto - estrattore generico (confidence: {confidence})')
        
        # =====================================================================
        # 4. OTTIENI/CREA VENDOR ID
        # =====================================================================
        # Per vendor UNKNOWN, usa 'GENERIC' come codice
        vendor_code = 'GENERIC' if is_vendor_unknown else vendor
        id_vendor = get_vendor_id(vendor_code)
        if not id_vendor:
            db.execute(
                "INSERT INTO VENDOR (codice_vendor) VALUES (?)",
                (vendor_code,)
            )
            db.commit()
            id_vendor = get_vendor_id(vendor_code)
        
        # =====================================================================
        # 5. SALVA PDF E CREA RECORD ACQUISIZIONE
        # =====================================================================
        nome_storage = f"{uuid.uuid4().hex}_{filename}"
        percorso_storage = None
        
        if save_to_disk:
            # Crea directory se non esiste
            os.makedirs(config.UPLOAD_DIR, exist_ok=True)
            percorso_storage = os.path.join(config.UPLOAD_DIR, nome_storage)
            with open(percorso_storage, 'wb') as f:
                f.write(file_content)
            # Usa questo path per estrattori che richiedono coordinate
            if not pdf_path:
                pdf_path = percorso_storage
        
        cursor = db.execute("""
            INSERT INTO ACQUISIZIONI
            (nome_file_originale, nome_file_storage, percorso_storage, hash_file,
             dimensione_bytes, id_vendor, is_duplicato, id_acquisizione_originale, stato)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'IN_ELABORAZIONE')
        """, (filename, nome_storage, percorso_storage, hash_file,
              len(file_content), id_vendor, is_duplicato, id_acq_originale))
        db.commit()

        id_acquisizione = cursor.lastrowid
        result['id_acquisizione'] = id_acquisizione
        
        # =====================================================================
        # 6. GESTIONE DUPLICATO PDF
        # =====================================================================
        if is_duplicato:
            # Recupera info sull'ordine esistente
            ordine_esistente = db.execute("""
                SELECT ot.numero_ordine_vendor, ot.stato, ot.ragione_sociale_1,
                       v.codice_vendor as vendor
                FROM ORDINI_TESTATA ot
                JOIN VENDOR v ON ot.id_vendor = v.id_vendor
                WHERE ot.id_acquisizione = ?
                LIMIT 1
            """, (id_acq_originale,)).fetchone()
            
            stato_ordine = 'SCONOSCIUTO'
            info_ordine = ''
            if ordine_esistente:
                stato_ordine = ordine_esistente['stato']
                info_ordine = f"Ordine {ordine_esistente['numero_ordine_vendor']} ({ordine_esistente['vendor']}) - {ordine_esistente['ragione_sociale_1']}"
            
            db.execute("""
                INSERT INTO ANOMALIE (id_acquisizione, tipo_anomalia, livello, descrizione)
                VALUES (?, 'DUPLICATO_PDF', 'ATTENZIONE', 'PDF già caricato precedentemente')
            """, (id_acquisizione,))
            db.execute(
                "UPDATE ACQUISIZIONI SET stato = 'SCARTATO' WHERE id_acquisizione = ?", 
                (id_acquisizione,)
            )
            db.commit()
            
            result['status'] = 'DUPLICATO'
            result['duplicato_info'] = {
                'id_acquisizione_originale': id_acq_originale,
                'stato_ordine': stato_ordine,
                'info_ordine': info_ordine
            }
            result['anomalie'].append(f'PDF già caricato. {info_ordine} - Stato: {stato_ordine}')
            return result
        
        # =====================================================================
        # 7. ESTRAI DATI CON ESTRATTORE SPECIFICO
        # =====================================================================
        extractor = get_extractor(vendor)
        orders_data = extractor.extract(text, lines, pdf_path)
        
        # =====================================================================
        # 8. INSERISCI ORDINI NEL DATABASE
        # =====================================================================
        for order_data in orders_data:
            if not order_data.get('numero_ordine') and not order_data.get('righe'):
                continue

            order_result = _insert_order(
                db, id_acquisizione, id_vendor, vendor_code, order_data,
                is_vendor_unknown=is_vendor_unknown
            )
            
            result['ordini'] += 1
            result['righe'] += order_result['righe']
            result['anomalie'].extend(order_result['anomalie'])
        
        # =====================================================================
        # 9. AGGIORNA STATO ACQUISIZIONE
        # =====================================================================
        db.execute("""
            UPDATE ACQUISIZIONI 
            SET stato = 'ELABORATO', 
                num_ordini_estratti = ?, 
                data_elaborazione = datetime('now')
            WHERE id_acquisizione = ?
        """, (result['ordini'], id_acquisizione))
        db.commit()
        
        # Log operazione
        log_operation('UPLOAD_PDF', 'ACQUISIZIONI', id_acquisizione,
                     f"Elaborato {filename}: {result['ordini']} ordini, {result['righe']} righe")
        
    except Exception as e:
        result['status'] = 'ERRORE'
        result['anomalie'].append(str(e))
        
        if result['id_acquisizione']:
            db.execute("""
                UPDATE ACQUISIZIONI SET stato = 'ERRORE', messaggio_errore = ?
                WHERE id_acquisizione = ?
            """, (str(e), result['id_acquisizione']))
            db.commit()
    
    return result


# =============================================================================
# FUNZIONI HELPER
# =============================================================================

def _insert_order(
    db,
    id_acquisizione: int,
    id_vendor: int,
    vendor: str,
    order_data: Dict,
    is_vendor_unknown: bool = False
) -> Dict[str, Any]:
    """
    Inserisce un singolo ordine nel database.

    v6.2: Aggiunge anomalie bloccanti per:
    - EXT-A01: Vendor non riconosciuto (estrattore generico)
    - LKP-A01: Lookup score < 80%
    """
    result = {'righe': 0, 'anomalie': []}
    
    # Verifica se i dati estratti sono sufficienti (caso ANGELINI con MIN_ID + P.IVA)
    min_id_estratto = order_data.get('codice_ministeriale', '').strip()
    piva_estratta = order_data.get('partita_iva', '').strip()
    
    # Se ho MIN_ID (almeno 6 cifre) e P.IVA (11 cifre), i dati sono completi
    # Non serve lookup, uso direttamente i dati estratti
    if min_id_estratto and len(min_id_estratto) >= 6 and piva_estratta and len(piva_estratta) == 11:
        # Dati completi dal documento - lookup opzionale per collegamento anagrafica
        id_farm, id_parafarm, lookup_method, lookup_source, lookup_score = lookup_farmacia(order_data)
        
        # Se lookup non trova, non è un errore - i dati estratti sono sufficienti
        if lookup_method == 'NESSUNO':
            lookup_method = 'DOCUMENTO_COMPLETO'
            lookup_score = 100  # I dati vengono dal documento, sono affidabili
    else:
        # Dati incompleti - lookup necessario
        id_farm, id_parafarm, lookup_method, lookup_source, lookup_score = lookup_farmacia(order_data)
    
    # Genera chiave univoca
    cod_min = order_data.get('codice_ministeriale', '')
    if not cod_min and id_farm:
        farm_row = db.execute(
            "SELECT min_id FROM ANAGRAFICA_FARMACIE WHERE id_farmacia = ?", 
            (id_farm,)
        ).fetchone()
        cod_min = farm_row['min_id'] if farm_row else ''
    if not cod_min and id_parafarm:
        para_row = db.execute(
            "SELECT codice_sito FROM ANAGRAFICA_PARAFARMACIE WHERE id_parafarmacia = ?", 
            (id_parafarm,)
        ).fetchone()
        cod_min = para_row['codice_sito'] if para_row else ''
    
    chiave_univoca = generate_order_key(vendor, order_data.get('numero_ordine', 'ND'), cod_min)
    
    # Verifica ordine duplicato
    existing_order = db.execute(
        "SELECT id_testata FROM ORDINI_TESTATA WHERE chiave_univoca_ordine = ?",
        (chiave_univoca,)
    ).fetchone()
    
    is_ordine_dup = True if existing_order else False
    id_testata_orig = existing_order['id_testata'] if existing_order else None
    stato = 'ANOMALIA' if lookup_method == 'NESSUNO' else 'ESTRATTO'
    
    # Se duplicato, aggiungi suffisso alla chiave
    if is_ordine_dup:
        chiave_univoca = f"{chiave_univoca}_DUP{id_acquisizione}"
    
    # Inserisci testata
    cursor = db.execute("""
        INSERT INTO ORDINI_TESTATA
        (id_acquisizione, id_vendor, numero_ordine_vendor, data_ordine, data_consegna,
         partita_iva_estratta, codice_ministeriale_estratto, ragione_sociale_1,
         indirizzo, cap, citta, provincia, nome_agente, gg_dilazione_1,
         id_farmacia_lookup, id_parafarmacia_lookup, lookup_method, lookup_source, lookup_score,
         chiave_univoca_ordine, is_ordine_duplicato, id_testata_originale, stato)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        id_acquisizione, id_vendor, order_data.get('numero_ordine', ''),
        _convert_date_to_iso(order_data.get('data_ordine', '')),
        _convert_date_to_iso(order_data.get('data_consegna', '')),
        order_data.get('partita_iva', ''), order_data.get('codice_ministeriale', ''),
        order_data.get('ragione_sociale', '')[:50] if order_data.get('ragione_sociale') else '',
        order_data.get('indirizzo', '')[:50] if order_data.get('indirizzo') else '',
        order_data.get('cap', ''),
        order_data.get('citta', ''), order_data.get('provincia', ''),
        order_data.get('nome_agente', ''),
        order_data.get('gg_dilazione', config.GG_DILAZIONE_DEFAULT),
        id_farm, id_parafarm, lookup_method, lookup_source, lookup_score,
        chiave_univoca, is_ordine_dup, id_testata_orig, stato
    ))
    db.commit()

    id_testata = cursor.lastrowid

    # v6.2.4: Se lookup ha trovato farmacia, popola header con dati anagrafica
    if id_farm or id_parafarm:
        from .lookup import popola_header_da_anagrafica
        popola_header_da_anagrafica(id_testata)

    # =========================================================================
    # ANOMALIE BLOCCANTI v6.2
    # =========================================================================
    richiede_supervisione = False

    # 1. ANOMALIA EXT-A01: Estrattore generico (vendor non riconosciuto)
    if is_vendor_unknown:
        db.execute("""
            INSERT INTO ANOMALIE
            (id_testata, tipo_anomalia, livello, codice_anomalia,
             descrizione, valore_anomalo, richiede_supervisione)
            VALUES (?, 'ESTRAZIONE', 'ERRORE', 'EXT-A01', ?, ?, TRUE)
        """, (
            id_testata,
            CODICI_ANOMALIA['EXT-A01'],
            f"Vendor rilevato: UNKNOWN"
        ))
        richiede_supervisione = True
        result['anomalie'].append(
            f"Ordine {order_data.get('numero_ordine')}: {CODICI_ANOMALIA['EXT-A01']}"
        )

    # 2. ANOMALIA LKP-A02: Farmacia non trovata (GRAVE - bloccante)
    if lookup_method == 'NESSUNO':
        db.execute("""
            INSERT INTO ANOMALIE
            (id_testata, tipo_anomalia, livello, codice_anomalia,
             descrizione, valore_anomalo, richiede_supervisione)
            VALUES (?, 'LOOKUP', 'ERRORE', 'LKP-A02', ?, ?, TRUE)
        """, (
            id_testata,
            CODICI_ANOMALIA['LKP-A02'],
            f"P.IVA: {order_data.get('partita_iva', 'N/D')}"
        ))
        richiede_supervisione = True
        result['anomalie'].append(f"Ordine {order_data.get('numero_ordine')}: lookup fallito")

    # 3. ANOMALIA LKP-A01: Lookup score < 80% (GRAVE - bloccante)
    elif lookup_score is not None and lookup_score < LOOKUP_SCORE_GRAVE:
        db.execute("""
            INSERT INTO ANOMALIE
            (id_testata, tipo_anomalia, livello, codice_anomalia,
             descrizione, valore_anomalo, richiede_supervisione)
            VALUES (?, 'LOOKUP', 'ERRORE', 'LKP-A01', ?, ?, TRUE)
        """, (
            id_testata,
            f"{CODICI_ANOMALIA['LKP-A01']} (score: {lookup_score}%)",
            f"Metodo: {lookup_method}, Score: {lookup_score}%"
        ))
        richiede_supervisione = True
        result['anomalie'].append(
            f"Ordine {order_data.get('numero_ordine')}: lookup score grave ({lookup_score}%)"
        )

    # 4. ANOMALIA LKP-A03: Lookup score 80-95% (ORDINARIA - non bloccante)
    elif lookup_score is not None and lookup_score < LOOKUP_SCORE_ORDINARIA:
        db.execute("""
            INSERT INTO ANOMALIE
            (id_testata, tipo_anomalia, livello, codice_anomalia,
             descrizione, valore_anomalo, richiede_supervisione)
            VALUES (?, 'LOOKUP', 'ATTENZIONE', 'LKP-A03', ?, ?, FALSE)
        """, (
            id_testata,
            f"{CODICI_ANOMALIA['LKP-A03']} (score: {lookup_score}%)",
            f"Metodo: {lookup_method}, Score: {lookup_score}%"
        ))
        # NON bloccante - solo segnalazione
        result['anomalie'].append(
            f"Ordine {order_data.get('numero_ordine')}: lookup score medio ({lookup_score}%) - verifica consigliata"
        )

    if is_ordine_dup:
        db.execute("""
            INSERT INTO ANOMALIE (id_testata, tipo_anomalia, livello, descrizione)
            VALUES (?, 'DUPLICATO_ORDINE', 'ATTENZIONE', 'Ordine già presente nel sistema')
        """, (id_testata,))
        result['anomalie'].append(f"Ordine {order_data.get('numero_ordine')}: duplicato")
    
    # Inserisci righe dettaglio (con gestione parent-child espositori)
    current_parent_id = None
    for riga in order_data.get('righe', []):
        # Se è un parent espositore, traccia il suo id per i child successivi
        if riga.get('tipo_riga') == 'PARENT_ESPOSITORE':
            row_id = _insert_detail_row(db, id_testata, riga)
            current_parent_id = row_id
        elif riga.get('_belongs_to_parent') and current_parent_id:
            # Child espositore: collega al parent
            riga['id_parent_espositore'] = current_parent_id
            _insert_detail_row(db, id_testata, riga)
        else:
            # Riga normale
            _insert_detail_row(db, id_testata, riga)
            current_parent_id = None  # Reset parent se non è child
        result['righe'] += 1

    # Aggiorna contatori righe nella testata
    from .ordini import _aggiorna_contatori_ordine
    _aggiorna_contatori_ordine(id_testata)

    # =========================================================================
    # GESTIONE ANOMALIE ESPOSITORE (ANGELINI v3.0)
    # =========================================================================
    anomalie_esp = order_data.get('anomalie_espositore', [])
    # NOTA: richiede_supervisione già impostato sopra per anomalie LOOKUP/ESTRAZIONE

    for anomalia in anomalie_esp:
        # Inserisci anomalia nel database
        cursor = db.execute("""
            INSERT INTO ANOMALIE
            (id_testata, tipo_anomalia, livello, codice_anomalia,
             descrizione, valore_anomalo, richiede_supervisione, pattern_signature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            id_testata,
            anomalia.get('tipo_anomalia', 'ESPOSITORE'),
            anomalia.get('livello', 'ATTENZIONE'),
            anomalia.get('codice_anomalia', ''),
            anomalia.get('descrizione', ''),
            anomalia.get('valore_anomalo', ''),
            bool(anomalia.get('richiede_supervisione', False)),
            None,  # Pattern viene calcolato dalla supervisione
        ))

        id_anomalia = cursor.lastrowid
        
        # Se richiede supervisione, valuta con ML
        if anomalia.get('richiede_supervisione'):
            applicato_auto, pattern_sig = valuta_anomalia_con_apprendimento(
                id_testata, anomalia
            )
            
            # Aggiorna pattern signature nell'anomalia
            db.execute("""
                UPDATE ANOMALIE SET pattern_signature = ? WHERE id_anomalia = ?
            """, (pattern_sig, id_anomalia))
            
            if not applicato_auto:
                # Crea richiesta supervisione
                crea_richiesta_supervisione(id_testata, id_anomalia, anomalia)
                richiede_supervisione = True
                result['anomalie'].append(
                    f"Ordine {order_data.get('numero_ordine')}: richiede supervisione per {anomalia.get('codice_anomalia')}"
                )
    
    # Se almeno un'anomalia richiede supervisione, blocca ordine
    if richiede_supervisione:
        blocca_ordine_per_supervisione(id_testata)
    
    db.commit()
    return result


def _insert_detail_row(db, id_testata: int, riga: Dict) -> int:
    """
    Inserisce una riga dettaglio nel database con supporto espositori v3.0.

    Returns:
        int: id_dettaglio della riga inserita
    """
    import json

    n_riga = riga.get('n_riga', 1)
    is_esp = True if riga.get('is_espositore') else False
    is_child = True if riga.get('is_child') else False
    is_no_aic = True if not riga.get('codice_aic') or riga.get('is_no_aic') else False

    # Nuovi campi espositore v3.0
    tipo_riga = riga.get('tipo_riga', '')
    id_parent = riga.get('id_parent_espositore')
    esp_metadata = riga.get('espositore_metadata')

    # Serializza metadata se è dict
    if isinstance(esp_metadata, dict):
        esp_metadata = json.dumps(esp_metadata, ensure_ascii=False)

    cursor = db.execute("""
        INSERT INTO ORDINI_DETTAGLIO
        (id_testata, n_riga, codice_aic, codice_originale, descrizione,
         q_venduta, q_sconto_merce, q_omaggio, data_consegna_riga,
         sconto_1, sconto_2, sconto_3, sconto_4,
         prezzo_netto, prezzo_pubblico, aliquota_iva,
         is_espositore, is_child, is_no_aic,
         tipo_riga, id_parent_espositore, espositore_metadata,
         q_originale, q_residua, q_esportata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        id_testata, n_riga,
        riga.get('codice_aic', ''),
        riga.get('codice_originale', ''),
        riga.get('descrizione', '')[:40] if riga.get('descrizione') else '',
        riga.get('q_venduta', 0),
        riga.get('q_sconto_merce', 0) + riga.get('merce_sconto_extra', 0),  # v6.2: BAYER sconto extra
        riga.get('q_omaggio', 0),
        _convert_date_to_iso(riga.get('data_consegna_riga') or riga.get('data_consegna', '')),
        riga.get('sconto1', 0), riga.get('sconto2', 0),
        riga.get('sconto3', 0), riga.get('sconto4', 0),
        riga.get('prezzo_netto', 0), riga.get('prezzo_pubblico', 0),
        riga.get('aliquota_iva', 10),
        is_esp, is_child, is_no_aic,
        tipo_riga, id_parent, esp_metadata,
        # v6.2: Usa funzione condivisa per calcolo quantità
        calcola_q_totale(riga),  # q_originale
        calcola_q_totale(riga),  # q_residua
        0  # q_esportata = 0
    ))

    # Ottieni id riga inserita
    id_det = cursor.lastrowid

    # Anomalia espositore (solo per log, le vere anomalie vengono gestite sopra)
    if is_esp and not riga.get('anomalie_espositore'):
        db.execute("""
            INSERT INTO ANOMALIE (id_testata, id_dettaglio, tipo_anomalia, livello, descrizione)
            VALUES (?, ?, 'ESPOSITORE', 'INFO', 'Riga espositore parent elaborata')
        """, (id_testata, id_det))

    return id_det


def _save_acquisition_error(db, filename: str, hash_file: str, 
                           file_content: bytes, error_msg: str):
    """Salva acquisizione in stato errore."""
    nome_storage = f"{uuid.uuid4().hex}_{filename}"
    db.execute("""
        INSERT INTO ACQUISIZIONI 
        (nome_file_originale, nome_file_storage, hash_file, dimensione_bytes,
         stato, messaggio_errore)
        VALUES (?, ?, ?, ?, 'ERRORE', ?)
    """, (filename, nome_storage, hash_file, len(file_content), error_msg))
    db.commit()


# =============================================================================
# FUNZIONI QUERY
# =============================================================================

def get_recent_uploads(limit: int = 10) -> List[Dict]:
    """Ritorna ultimi PDF caricati."""
    db = get_db()
    rows = db.execute("""
        SELECT a.*, v.codice_vendor as vendor
        FROM ACQUISIZIONI a
        LEFT JOIN VENDOR v ON a.id_vendor = v.id_vendor
        ORDER BY a.data_upload DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(row) for row in rows]


def get_upload_stats() -> Dict[str, Any]:
    """Statistiche upload."""
    db = get_db()
    
    return {
        'totale': db.execute("SELECT COUNT(*) FROM ACQUISIZIONI").fetchone()[0],
        'oggi': db.execute(
            "SELECT COUNT(*) FROM ACQUISIZIONI WHERE data_upload::date = CURRENT_DATE"
        ).fetchone()[0],
        'elaborati': db.execute(
            "SELECT COUNT(*) FROM ACQUISIZIONI WHERE stato = 'ELABORATO'"
        ).fetchone()[0],
        'errori': db.execute(
            "SELECT COUNT(*) FROM ACQUISIZIONI WHERE stato = 'ERRORE'"
        ).fetchone()[0],
        'duplicati': db.execute(
            "SELECT COUNT(*) FROM ACQUISIZIONI WHERE stato = 'SCARTATO'"
        ).fetchone()[0],
    }
