# =============================================================================
# SERV.O v6.0 - PDF PROCESSOR SERVICE
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

# Text encoding fix
try:
    import ftfy
    FTFY_AVAILABLE = True
except ImportError:
    FTFY_AVAILABLE = False
    print("⚠️ ftfy non disponibile - usando fix manuale")


def _fix_encoding_manual(text: str) -> str:
    """
    Fix manuale per mojibake UTF-8 comuni in italiano.
    Usato come fallback se ftfy non è disponibile.

    Pattern: UTF-8 bytes interpretati come Latin-1
    """
    if not text:
        return text

    # Approccio: prova a decodificare come se fosse Latin-1 encodato in UTF-8
    try:
        # Se il testo contiene sequenze mojibake tipiche, prova a fixarle
        if '\xc3' in text or 'Ã' in text:
            # Encode come Latin-1, decode come UTF-8
            fixed = text.encode('latin-1', errors='ignore').decode('utf-8', errors='ignore')
            if fixed and len(fixed) > 0:
                return fixed
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass

    # Fallback: replace pattern specifici comuni
    replacements = [
        ('Ã¬', 'ì'),  # ì - i grave
        ('Ã¨', 'è'),  # è - e grave
        ('Ã²', 'ò'),  # ò - o grave
        ('Ã¹', 'ù'),  # ù - u grave
        ('Ã ', 'à'),  # à - a grave (con spazio dopo)
        ('Ã©', 'é'),  # é - e acute
        ('Ã³', 'ó'),  # ó - o acute
    ]

    for mojibake, correct in replacements:
        text = text.replace(mojibake, correct)

    return text

from ..config import config
from ..database_pg import get_db, get_vendor_id, log_operation
from ..utils import compute_file_hash, generate_order_key, calcola_q_totale
from .extraction import get_extractor, detect_vendor
from .lookup import lookup_farmacia, lookup_cliente_by_piva
from .supervisione import (
    valuta_anomalia_con_apprendimento,
    crea_richiesta_supervisione,
    blocca_ordine_per_supervisione,
)
from .espositore import CODICI_ANOMALIA, LOOKUP_SCORE_GRAVE, LOOKUP_SCORE_ORDINARIA
from .listini import arricchisci_ordine_con_listino
from .crm.tickets.commands import create_ticket
from .crm.attachments import save_attachment


# =============================================================================
# v11.3: TICKET AUTOMATICO PER VENDOR NON RICONOSCIUTO
# =============================================================================

SYSTEM_USER_ID = 1  # Admin user per ticket automatici


def _crea_ticket_vendor_sconosciuto(
    db,
    filename: str,
    file_content: bytes,
    id_acquisizione: int,
    confidence: float
) -> Optional[int]:
    """
    Crea automaticamente un ticket CRM quando un documento non viene riconosciuto.

    v11.3: Apre ticket di assistenza tecnica per analisi nuovo documento.

    Args:
        db: Connessione database
        filename: Nome file originale
        file_content: Contenuto binario del PDF
        id_acquisizione: ID acquisizione collegata
        confidence: Confidence score del detection

    Returns:
        ID ticket creato o None se errore
    """
    try:
        # Crea ticket
        ticket_data = {
            'categoria': 'assistenza',
            'oggetto': 'ANALISI NUOVO DOCUMENTO',
            'contenuto': f"""RICHIESTA AUTOMATICA - VENDOR NON RICONOSCIUTO

Il sistema ha ricevuto un documento PDF che non è stato possibile classificare.

**Dettagli:**
- File: {filename}
- ID Acquisizione: {id_acquisizione}
- Confidence detection: {confidence:.1%}
- Data/Ora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

**Azione richiesta:**
Analizzare il documento allegato per determinare se:
1. È un nuovo vendor da implementare
2. È un formato variante di un vendor esistente
3. È un documento non gestibile dal sistema

Il documento originale è allegato a questo ticket.""",
            'priorita': 'alta',
            'pagina_origine': 'upload',
            'pagina_dettaglio': f'Acquisizione #{id_acquisizione}'
        }

        result = create_ticket(db, ticket_data, SYSTEM_USER_ID)

        if not result.get('success'):
            print(f"⚠️ Errore creazione ticket vendor sconosciuto: {result.get('error')}")
            return None

        ticket_id = result['id_ticket']

        # Allega il PDF al ticket
        attach_result = save_attachment(
            db,
            ticket_id,
            file_content,
            filename,
            'application/pdf',
            SYSTEM_USER_ID
        )

        if not attach_result.get('success'):
            print(f"⚠️ Errore allegato ticket: {attach_result.get('error')}")
            # Ticket creato ma senza allegato - non è critico

        print(f"✅ Ticket #{ticket_id} creato per documento non riconosciuto: {filename}")
        return ticket_id

    except Exception as e:
        print(f"⚠️ Errore creazione ticket vendor sconosciuto: {e}")
        return None


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
                # v10.6: x_tolerance aumentata per rilevare meglio gli spazi tra parole
                # Default è 3, aumentiamo a 5 per evitare "CANTARERODEI" invece di "CANTARERO DEI"
                page_text = page.extract_text(x_tolerance=5, y_tolerance=3) or ""

                # v10.6: Fix encoding issues (UTF-8 mojibake come "BONDÃ¬" -> "BONDì")
                # Prima prova con ftfy se disponibile, poi applica fix manuale come backup
                if FTFY_AVAILABLE:
                    page_text = ftfy.fix_text(page_text)
                # Applica sempre il fix manuale per catturare pattern non gestiti da ftfy
                page_text = _fix_encoding_manual(page_text)

                text += page_text + "\n"
                lines.extend(page_text.split('\n'))
        
        # =====================================================================
        # 3. RILEVA VENDOR
        # =====================================================================
        vendor, confidence = detect_vendor(text, filename)
        result['vendor'] = vendor

        # v6.2: Vendor UNKNOWN non blocca più l'elaborazione
        # L'ordine viene inserito con anomalia bloccante EXT-A01
        # v11.3: Crea anche ticket CRM automatico per analisi
        is_vendor_unknown = vendor == "UNKNOWN"
        if is_vendor_unknown:
            result['anomalie'].append(f'Vendor non riconosciuto - estrattore generico (confidence: {confidence})')
            # v11.3: Crea ticket CRM per assistenza tecnica
            # Nota: la creazione del ticket avviene PRIMA dell'inserimento acquisizione
            # per garantire che il PDF venga allegato anche se l'elaborazione fallisce
        
        # =====================================================================
        # 4. OTTIENI/CREA VENDOR ID
        # =====================================================================
        # Per vendor UNKNOWN, usa 'GENERIC' come codice
        vendor_code = 'GENERIC' if is_vendor_unknown else vendor
        id_vendor = get_vendor_id(vendor_code)
        if not id_vendor:
            db.execute(
                "INSERT INTO VENDOR (codice_vendor) VALUES (%s)",
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
            INSERT INTO acquisizioni
            (nome_file_originale, nome_file_storage, percorso_storage, hash_file,
             dimensione_bytes, id_vendor, is_duplicato, id_acquisizione_originale, stato)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'IN_ELABORAZIONE')
            RETURNING id_acquisizione
        """, (filename, nome_storage, percorso_storage, hash_file,
              len(file_content), id_vendor, is_duplicato, id_acq_originale))
        id_acquisizione = cursor.fetchone()[0]
        db.commit()
        result['id_acquisizione'] = id_acquisizione

        # =====================================================================
        # 5.5 v11.3: TICKET AUTOMATICO PER VENDOR SCONOSCIUTO
        # =====================================================================
        if is_vendor_unknown:
            ticket_id = _crea_ticket_vendor_sconosciuto(
                db, filename, file_content, id_acquisizione, confidence
            )
            if ticket_id:
                result['ticket_assistenza'] = ticket_id
                result['anomalie'].append(
                    f'Ticket assistenza #{ticket_id} creato per analisi documento'
                )

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
                WHERE ot.id_acquisizione = %s
                LIMIT 1
            """, (id_acq_originale,)).fetchone()
            
            stato_ordine = 'SCONOSCIUTO'
            info_ordine = ''
            if ordine_esistente:
                stato_ordine = ordine_esistente['stato']
                info_ordine = f"Ordine {ordine_esistente['numero_ordine_vendor']} ({ordine_esistente['vendor']}) - {ordine_esistente['ragione_sociale_1']}"
            
            db.execute("""
                INSERT INTO ANOMALIE (id_acquisizione, tipo_anomalia, livello, descrizione)
                VALUES (%s, 'DUPLICATO_PDF', 'ATTENZIONE', 'PDF già caricato precedentemente')
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
        orders_data = extractor(text, lines, pdf_path)
        
        # =====================================================================
        # 7.5 ARRICCHIMENTO LISTINO (v10.0 - Generale per tutti i vendor)
        # =====================================================================
        # Arricchisce con prezzi da listino le righe che non hanno prezzo_netto
        # Se la riga ha già un prezzo valido (estratto dal PDF), viene mantenuto
        for order_data in orders_data:
            order_data, anomalie_listino = arricchisci_ordine_con_listino(order_data, vendor)
            if anomalie_listino:
                result['anomalie'].append(
                    f"Ordine {order_data.get('numero_ordine')}: {len(anomalie_listino)} anomalie listino"
                )

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
                num_ordini_estratti = %s, 
                data_elaborazione = NOW()
            WHERE id_acquisizione = %s
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
                UPDATE ACQUISIZIONI SET stato = 'ERRORE', messaggio_errore = %s
                WHERE id_acquisizione = %s
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

    # v11.2: Recupera deposito_riferimento da anagrafica_clienti
    deposito_riferimento = None
    if piva_estratta:
        cliente_info = lookup_cliente_by_piva(piva_estratta)
        if cliente_info:
            deposito_riferimento = cliente_info.get('deposito_riferimento')

    # Genera chiave univoca
    cod_min = order_data.get('codice_ministeriale', '')
    if not cod_min and id_farm:
        farm_row = db.execute(
            "SELECT min_id FROM ANAGRAFICA_FARMACIE WHERE id_farmacia = %s",
            (id_farm,)
        ).fetchone()
        cod_min = farm_row['min_id'] if farm_row else ''
    if not cod_min and id_parafarm:
        para_row = db.execute(
            "SELECT codice_sito FROM ANAGRAFICA_PARAFARMACIE WHERE id_parafarmacia = %s",
            (id_parafarm,)
        ).fetchone()
        cod_min = para_row['codice_sito'] if para_row else ''
    
    chiave_univoca = generate_order_key(vendor, order_data.get('numero_ordine', 'ND'), cod_min)

    # Verifica ordine duplicato
    existing_order = db.execute(
        "SELECT id_testata, numero_ordine_vendor, ragione_sociale_1, stato FROM ORDINI_TESTATA WHERE chiave_univoca_ordine = %s",
        (chiave_univoca,)
    ).fetchone()

    # v10.4: Se duplicato, BLOCCA l'inserimento (non creare con suffisso)
    if existing_order:
        info_dup = f"Ordine {existing_order['numero_ordine_vendor']} ({vendor}) - {existing_order['ragione_sociale_1']} - Stato: {existing_order['stato']}"
        result['anomalie'].append(
            f"ORDINE DUPLICATO BLOCCATO: {order_data.get('numero_ordine')} - Esiste già: {info_dup}"
        )
        # Inserisci anomalia nell'acquisizione (non nell'ordine perché non viene creato)
        db.execute("""
            INSERT INTO ANOMALIE (id_acquisizione, tipo_anomalia, livello, codice_anomalia, descrizione, valore_anomalo)
            VALUES (%s, 'DUPLICATO_ORDINE', 'ATTENZIONE', 'DUP-A01', %s, %s)
        """, (
            id_acquisizione,
            f"Ordine duplicato bloccato - stesso vendor, numero ordine e cliente già presente",
            f"Chiave: {chiave_univoca}, Originale ID: {existing_order['id_testata']}"
        ))
        db.commit()
        return result  # Non creare l'ordine, ritorna subito

    # Se arriviamo qui, l'ordine non è duplicato
    is_ordine_dup = False
    id_testata_orig = None
    stato = 'ANOMALIA' if lookup_method == 'NESSUNO' else 'ESTRATTO'
    
    # Prepara valori estratti (immutabili)
    ragione_sociale_val = order_data.get('ragione_sociale', '')[:50] if order_data.get('ragione_sociale') else ''
    indirizzo_val = order_data.get('indirizzo', '')[:50] if order_data.get('indirizzo') else ''
    cap_val = order_data.get('cap', '')
    citta_val = order_data.get('citta', '')
    provincia_val = order_data.get('provincia', '')
    data_ordine_val = _convert_date_to_iso(order_data.get('data_ordine', ''))
    data_consegna_val = _convert_date_to_iso(order_data.get('data_consegna', ''))

    # v7.0: Determina fonte anagrafica iniziale
    fonte_anagrafica = 'ESTRATTO'
    if id_farm:
        fonte_anagrafica = 'LOOKUP_FARMACIA'
    elif id_parafarm:
        fonte_anagrafica = 'LOOKUP_PARAFARMACIA'

    # Inserisci testata con campi estratti (v7.0: Data Lineage, v11.2: deposito_riferimento)
    cursor = db.execute("""
        INSERT INTO ordini_testata
        (id_acquisizione, id_vendor, numero_ordine_vendor, data_ordine, data_consegna,
         partita_iva_estratta, codice_ministeriale_estratto, ragione_sociale_1,
         indirizzo, cap, citta, provincia, nome_agente, gg_dilazione_1,
         id_farmacia_lookup, id_parafarmacia_lookup, lookup_method, lookup_source, lookup_score,
         chiave_univoca_ordine, is_ordine_duplicato, id_testata_originale, stato,
         ragione_sociale_1_estratta, indirizzo_estratto, cap_estratto,
         citta_estratta, provincia_estratta, data_ordine_estratta, data_consegna_estratta,
         fonte_anagrafica, deposito_riferimento)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id_testata
    """, (
        id_acquisizione, id_vendor, order_data.get('numero_ordine', ''),
        data_ordine_val, data_consegna_val,
        order_data.get('partita_iva', ''), order_data.get('codice_ministeriale', ''),
        ragione_sociale_val, indirizzo_val, cap_val, citta_val, provincia_val,
        order_data.get('nome_agente', ''),
        order_data.get('gg_dilazione', config.GG_DILAZIONE_DEFAULT),
        id_farm, id_parafarm, lookup_method, lookup_source, lookup_score,
        chiave_univoca, is_ordine_dup, id_testata_orig, stato,
        ragione_sociale_val, indirizzo_val, cap_val,
        citta_val, provincia_val, data_ordine_val, data_consegna_val,
        fonte_anagrafica, deposito_riferimento
    ))
    id_testata = cursor.fetchone()[0]
    db.commit()

    # v6.2.4: Se lookup ha trovato farmacia, popola header con dati anagrafica
    if id_farm or id_parafarm:
        from .lookup import popola_header_da_anagrafica
        popola_header_da_anagrafica(id_testata)

    # =========================================================================
    # ANOMALIE BLOCCANTI v6.2
    # =========================================================================
    richiede_supervisione = False

    # 1. ANOMALIA EXT-A01: Estrattore generico (vendor non riconosciuto)
    # v10.5: Aggiunta creazione supervisione per permettere risoluzione
    if is_vendor_unknown:
        cursor = db.execute("""
            INSERT INTO ANOMALIE
            (id_testata, tipo_anomalia, livello, codice_anomalia,
             descrizione, valore_anomalo, richiede_supervisione)
            VALUES (%s, 'ESTRAZIONE', 'ERRORE', 'EXT-A01', %s, %s, TRUE)
            RETURNING id_anomalia
        """, (
            id_testata,
            CODICI_ANOMALIA['EXT-A01'],
            f"Vendor rilevato: UNKNOWN"
        ))
        id_anomalia_ext = cursor.fetchone()[0]

        # v10.5: Crea supervisione per EXT-A01 (tipo LOOKUP per gestione unificata)
        anomalia_ext = {
            'tipo_anomalia': 'ESTRAZIONE',
            'codice_anomalia': 'EXT-A01',
            'vendor': 'UNKNOWN',
            'partita_iva_estratta': order_data.get('partita_iva', ''),
            'ragione_sociale_estratta': order_data.get('ragione_sociale', ''),
            'citta_estratta': order_data.get('citta', ''),
            'lookup_method': 'NESSUNO',
            'lookup_score': None,
        }
        crea_richiesta_supervisione(id_testata, id_anomalia_ext, anomalia_ext)

        richiede_supervisione = True
        result['anomalie'].append(
            f"Ordine {order_data.get('numero_ordine')}: {CODICI_ANOMALIA['EXT-A01']} - richiede supervisione"
        )

    # 2. ANOMALIA LKP-A02: Farmacia non trovata (GRAVE - bloccante)
    if lookup_method == 'NESSUNO':
        cursor = db.execute("""
            INSERT INTO ANOMALIE
            (id_testata, tipo_anomalia, livello, codice_anomalia,
             descrizione, valore_anomalo, richiede_supervisione)
            VALUES (%s, 'LOOKUP', 'ERRORE', 'LKP-A02', %s, %s, TRUE)
            RETURNING id_anomalia
        """, (
            id_testata,
            CODICI_ANOMALIA['LKP-A02'],
            f"P.IVA: {order_data.get('partita_iva', 'N/D')}"
        ))
        id_anomalia_lkp = cursor.fetchone()[0]

        # v8.0: Crea supervisione lookup
        # v8.1: Aggiunta destinazione per pattern univoco (supporto multipunto)
        anomalia_lkp = {
            'tipo_anomalia': 'LOOKUP',
            'codice_anomalia': 'LKP-A02',
            'vendor': vendor or 'UNKNOWN',
            'partita_iva_estratta': order_data.get('partita_iva', ''),
            'ragione_sociale_estratta': order_data.get('ragione_sociale', ''),
            'citta_estratta': order_data.get('citta', ''),
            'lookup_method': lookup_method,
            'lookup_score': None,
        }
        crea_richiesta_supervisione(id_testata, id_anomalia_lkp, anomalia_lkp)

        richiede_supervisione = True
        result['anomalie'].append(f"Ordine {order_data.get('numero_ordine')}: lookup fallito - richiede supervisione")

    # 3. ANOMALIA LKP-A04: P.IVA mismatch tra PDF e anagrafica (GRAVE - bloccante) v8.2
    elif lookup_method == 'MIN_ID_PIVA_MISMATCH':
        cursor = db.execute("""
            INSERT INTO ANOMALIE
            (id_testata, tipo_anomalia, livello, codice_anomalia,
             descrizione, valore_anomalo, richiede_supervisione)
            VALUES (%s, 'LOOKUP', 'ERRORE', 'LKP-A04', %s, %s, TRUE)
            RETURNING id_anomalia
        """, (
            id_testata,
            CODICI_ANOMALIA['LKP-A04'],
            f"P.IVA PDF: {order_data.get('partita_iva', 'N/D')} - Probabile subentro/cambio proprietà"
        ))
        id_anomalia_lkp = cursor.fetchone()[0]

        # Crea supervisione lookup
        anomalia_lkp = {
            'tipo_anomalia': 'LOOKUP',
            'codice_anomalia': 'LKP-A04',
            'vendor': vendor or 'UNKNOWN',
            'partita_iva_estratta': order_data.get('partita_iva', ''),
            'ragione_sociale_estratta': order_data.get('ragione_sociale', ''),
            'citta_estratta': order_data.get('citta', ''),
            'lookup_method': lookup_method,
            'lookup_score': lookup_score,
        }
        crea_richiesta_supervisione(id_testata, id_anomalia_lkp, anomalia_lkp)

        richiede_supervisione = True
        result['anomalie'].append(
            f"Ordine {order_data.get('numero_ordine')}: P.IVA mismatch - verifica obbligatoria (probabile subentro)"
        )

    # 4. ANOMALIA LKP-A01: Lookup score < 80% (GRAVE - bloccante)
    elif lookup_score is not None and lookup_score < LOOKUP_SCORE_GRAVE:
        cursor = db.execute("""
            INSERT INTO ANOMALIE
            (id_testata, tipo_anomalia, livello, codice_anomalia,
             descrizione, valore_anomalo, richiede_supervisione)
            VALUES (%s, 'LOOKUP', 'ERRORE', 'LKP-A01', %s, %s, TRUE)
            RETURNING id_anomalia
        """, (
            id_testata,
            f"{CODICI_ANOMALIA['LKP-A01']} (score: {lookup_score}%)",
            f"Metodo: {lookup_method}, Score: {lookup_score}%"
        ))
        id_anomalia_lkp = cursor.fetchone()[0]

        # v8.0: Crea supervisione lookup
        # v8.1: Aggiunta destinazione per pattern univoco (supporto multipunto)
        anomalia_lkp = {
            'tipo_anomalia': 'LOOKUP',
            'codice_anomalia': 'LKP-A01',
            'vendor': vendor or 'UNKNOWN',
            'partita_iva_estratta': order_data.get('partita_iva', ''),
            'ragione_sociale_estratta': order_data.get('ragione_sociale', ''),
            'citta_estratta': order_data.get('citta', ''),
            'lookup_method': lookup_method,
            'lookup_score': lookup_score,
        }
        crea_richiesta_supervisione(id_testata, id_anomalia_lkp, anomalia_lkp)

        richiede_supervisione = True
        result['anomalie'].append(
            f"Ordine {order_data.get('numero_ordine')}: lookup score grave ({lookup_score}%) - richiede supervisione"
        )

    # 5. ANOMALIA LKP-A03: Lookup score 80-95% (ORDINARIA - non bloccante)
    elif lookup_score is not None and lookup_score < LOOKUP_SCORE_ORDINARIA:
        db.execute("""
            INSERT INTO ANOMALIE
            (id_testata, tipo_anomalia, livello, codice_anomalia,
             descrizione, valore_anomalo, richiede_supervisione)
            VALUES (%s, 'LOOKUP', 'ATTENZIONE', 'LKP-A03', %s, %s, FALSE)
        """, (
            id_testata,
            f"{CODICI_ANOMALIA['LKP-A03']} (score: {lookup_score}%)",
            f"Metodo: {lookup_method}, Score: {lookup_score}%"
        ))
        # NON bloccante - solo segnalazione
        result['anomalie'].append(
            f"Ordine {order_data.get('numero_ordine')}: lookup score medio ({lookup_score}%) - verifica consigliata"
        )

    # 6. ANOMALIA LKP-A05: Cliente non trovato in anagrafica_clienti (CRITICO - bloccante) v8.2
    # v10.5: Aggiunta creazione supervisione per permettere risoluzione
    # Verifica se la P.IVA estratta esiste in anagrafica_clienti (necessario per deposito di riferimento)
    piva_estratta = order_data.get('partita_iva', '').strip()
    if piva_estratta:
        cliente_exists = db.execute("""
            SELECT COUNT(*) FROM anagrafica_clienti
            WHERE partita_iva = %s
        """, (piva_estratta,)).fetchone()[0]

        if cliente_exists == 0:
            cursor = db.execute("""
                INSERT INTO ANOMALIE
                (id_testata, tipo_anomalia, livello, codice_anomalia,
                 descrizione, valore_anomalo, richiede_supervisione)
                VALUES (%s, 'LOOKUP', 'ERRORE', 'LKP-A05', %s, %s, TRUE)
                RETURNING id_anomalia
            """, (
                id_testata,
                CODICI_ANOMALIA['LKP-A05'],
                f"P.IVA: {piva_estratta} - Cliente non in anagrafica, deposito non determinabile"
            ))
            id_anomalia_lkp = cursor.fetchone()[0]

            # v10.5: Crea supervisione per LKP-A05
            anomalia_lkp = {
                'tipo_anomalia': 'LOOKUP',
                'codice_anomalia': 'LKP-A05',
                'vendor': vendor or 'UNKNOWN',
                'partita_iva_estratta': piva_estratta,
                'ragione_sociale_estratta': order_data.get('ragione_sociale', ''),
                'citta_estratta': order_data.get('citta', ''),
                'lookup_method': lookup_method,
                'lookup_score': lookup_score,
            }
            crea_richiesta_supervisione(id_testata, id_anomalia_lkp, anomalia_lkp)

            richiede_supervisione = True
            result['anomalie'].append(
                f"Ordine {order_data.get('numero_ordine')}: cliente non trovato in anagrafica clienti (P.IVA: {piva_estratta}) - richiede supervisione"
            )
        else:
            # 7. ANOMALIA DEP-A01: Cliente in anagrafica ma senza deposito (v11.3 - ERRORE bloccante)
            # Se il cliente è in anagrafica ma non ha deposito_riferimento assegnato
            if not deposito_riferimento:
                cursor = db.execute("""
                    INSERT INTO ANOMALIE
                    (id_testata, tipo_anomalia, livello, codice_anomalia,
                     descrizione, valore_anomalo, richiede_supervisione)
                    VALUES (%s, 'DEPOSITO', 'ERRORE', 'DEP-A01', %s, %s, TRUE)
                    RETURNING id_anomalia
                """, (
                    id_testata,
                    CODICI_ANOMALIA['DEP-A01'],
                    f"P.IVA: {piva_estratta} - Cliente senza deposito assegnato"
                ))
                id_anomalia_dep = cursor.fetchone()[0]

                # Crea supervisione per DEP-A01 (tipo LOOKUP per gestione unificata)
                anomalia_dep = {
                    'tipo_anomalia': 'DEPOSITO',
                    'codice_anomalia': 'DEP-A01',
                    'vendor': vendor or 'UNKNOWN',
                    'partita_iva_estratta': piva_estratta,
                    'ragione_sociale_estratta': order_data.get('ragione_sociale', ''),
                    'citta_estratta': order_data.get('citta', ''),
                    'depositi_validi': 'CT, CL',
                }
                crea_richiesta_supervisione(id_testata, id_anomalia_dep, anomalia_dep)

                richiede_supervisione = True
                result['anomalie'].append(
                    f"Ordine {order_data.get('numero_ordine')}: deposito di riferimento mancante (P.IVA: {piva_estratta}) - richiede impostazione manuale"
                )

    # 8. ANOMALIA DEP-A01 (v11.3 FIX): Farmacia trovata via lookup ma senza deposito
    # Caso: P.IVA non estratta ma farmacia trovata via MIN_ID o ragione sociale
    # Se abbiamo id_farmacia_lookup ma deposito_riferimento è ancora NULL
    if not piva_estratta and (id_farm or id_parafarm) and not deposito_riferimento:
        # Cerca la P.IVA dalla farmacia/parafarmacia trovata
        piva_lookup = None
        if id_farm:
            farm_row = db.execute(
                "SELECT partita_iva FROM ANAGRAFICA_FARMACIE WHERE id_farmacia = %s",
                (id_farm,)
            ).fetchone()
            piva_lookup = farm_row['partita_iva'] if farm_row else None
        elif id_parafarm:
            para_row = db.execute(
                "SELECT partita_iva FROM ANAGRAFICA_PARAFARMACIE WHERE id_parafarmacia = %s",
                (id_parafarm,)
            ).fetchone()
            piva_lookup = para_row['partita_iva'] if para_row else None

        cursor = db.execute("""
            INSERT INTO ANOMALIE
            (id_testata, tipo_anomalia, livello, codice_anomalia,
             descrizione, valore_anomalo, richiede_supervisione)
            VALUES (%s, 'DEPOSITO', 'ERRORE', 'DEP-A01', %s, %s, TRUE)
            RETURNING id_anomalia
        """, (
            id_testata,
            CODICI_ANOMALIA['DEP-A01'],
            f"P.IVA: {piva_lookup or 'N/D'} - Farmacia trovata via lookup ma deposito non determinabile"
        ))
        id_anomalia_dep = cursor.fetchone()[0]

        # Crea supervisione per DEP-A01
        anomalia_dep = {
            'tipo_anomalia': 'DEPOSITO',
            'codice_anomalia': 'DEP-A01',
            'vendor': vendor or 'UNKNOWN',
            'partita_iva_estratta': piva_lookup or '',
            'ragione_sociale_estratta': order_data.get('ragione_sociale', ''),
            'citta_estratta': order_data.get('citta', ''),
            'depositi_validi': 'CT, CL',
            'id_farmacia_lookup': id_farm,
            'id_parafarmacia_lookup': id_parafarm,
        }
        crea_richiesta_supervisione(id_testata, id_anomalia_dep, anomalia_dep)

        richiede_supervisione = True
        result['anomalie'].append(
            f"Ordine {order_data.get('numero_ordine')}: deposito di riferimento mancante (farmacia trovata via lookup) - richiede impostazione manuale"
        )

    # Inserisci righe dettaglio (con gestione parent-child espositori)
    # v10.6: Propaga data_consegna dalla testata alle righe che non hanno data propria
    data_consegna_testata = order_data.get('data_consegna', '')
    current_parent_id = None
    for riga in order_data.get('righe', []):
        # v10.6: Se la riga non ha data_consegna propria, usa quella della testata
        if not riga.get('data_consegna_riga') and not riga.get('data_consegna'):
            riga['data_consegna'] = data_consegna_testata

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
    # CHECK LST-A01: PRODOTTI IN VENDITA SENZA PREZZO (v10.1)
    # =========================================================================
    # Cerca righe con q_venduta > 0 e prezzo_netto = 0/NULL
    # Crea supervisione_listino per ogni riga (unificato con anomalie listino)
    # v10.3: Escludi anche:
    # - Righe SC.MERCE/omaggi (q_sconto_merce > 0 o q_omaggio > 0)
    # - Parent espositori (is_espositore = TRUE)
    # - Righe con tipo_riga SC.MERCE o omaggio
    righe_senza_prezzo = db.execute("""
        SELECT od.id_dettaglio, od.n_riga, od.codice_aic, od.descrizione, od.q_venduta, od.prezzo_netto
        FROM ordini_dettaglio od
        WHERE od.id_testata = %s
          AND COALESCE(od.q_venduta, 0) > 0
          AND COALESCE(od.prezzo_netto, 0) = 0
          AND COALESCE(od.is_child, FALSE) = FALSE  -- Escludi child espositori
          AND COALESCE(od.is_espositore, FALSE) = FALSE  -- v10.3: Escludi parent espositori
          AND COALESCE(od.q_sconto_merce, 0) = 0  -- v10.3: Escludi righe sconto merce
          AND COALESCE(od.q_omaggio, 0) = 0  -- v10.3: Escludi righe omaggio
          AND COALESCE(od.tipo_riga, '') NOT IN ('SCONTO_MERCE', 'MATERIALE_POP', 'PARENT_ESPOSITORE', 'CHILD_ESPOSITORE')
          AND NOT EXISTS (
              SELECT 1 FROM anomalie a
              WHERE a.id_dettaglio = od.id_dettaglio
              AND a.codice_anomalia = 'LST-A01'
          )
        ORDER BY od.n_riga
    """, (id_testata,)).fetchall()

    if righe_senza_prezzo:
        for riga in righe_senza_prezzo:
            descrizione_specifica = f"Prezzo mancante per AIC {riga['codice_aic'] or 'N/D'} - {riga['descrizione'][:40] if riga['descrizione'] else 'N/D'}"

            # v10.4: Verifica se esiste già un'anomalia generica (senza id_dettaglio) per lo stesso AIC
            # Se sì, aggiornala con i dettagli specifici invece di crearne una nuova
            existing_generic = db.execute("""
                SELECT id_anomalia FROM anomalie
                WHERE id_testata = %s
                AND codice_anomalia = 'LST-A01'
                AND valore_anomalo = %s
                AND id_dettaglio IS NULL
            """, (id_testata, riga['codice_aic'])).fetchone()

            if existing_generic:
                # Aggiorna anomalia generica con dettagli specifici
                db.execute("""
                    UPDATE anomalie SET
                        id_dettaglio = %s,
                        descrizione = %s,
                        livello = 'ERRORE'
                    WHERE id_anomalia = %s
                """, (riga['id_dettaglio'], descrizione_specifica, existing_generic['id_anomalia']))
                id_anomalia = existing_generic['id_anomalia']
            else:
                # Crea nuova anomalia LST-A01 per la riga
                cursor = db.execute("""
                    INSERT INTO anomalie
                    (id_testata, id_dettaglio, tipo_anomalia, livello, codice_anomalia,
                     descrizione, valore_anomalo, richiede_supervisione)
                    VALUES (%s, %s, 'LISTINO', 'ERRORE', 'LST-A01', %s, %s, TRUE)
                    RETURNING id_anomalia
                """, (
                    id_testata,
                    riga['id_dettaglio'],
                    descrizione_specifica,
                    riga['codice_aic'] or 'NO_AIC'
                ))
                id_anomalia = cursor.fetchone()[0]

            # Crea supervisione_listino per ogni riga
            anomalia_listino = {
                'tipo_anomalia': 'LISTINO',
                'codice_anomalia': 'LST-A01',
                'vendor': vendor,
                'valore_anomalo': riga['codice_aic'],
                'n_riga': riga['n_riga'],
                'descrizione': riga['descrizione'],
                'id_dettaglio': riga['id_dettaglio'],  # Passa id_dettaglio direttamente
            }
            crea_richiesta_supervisione(id_testata, id_anomalia, anomalia_listino)

        richiede_supervisione = True
        result['anomalie'].append(
            f"Ordine {order_data.get('numero_ordine')}: {len(righe_senza_prezzo)} prodotti senza prezzo - richiede supervisione listino"
        )

    # =========================================================================
    # CHECK AIC-A01: PRODOTTI SENZA CODICE AIC VALIDO (v9.1)
    # =========================================================================
    # Cerca righe senza codice AIC valido (esattamente 9 CIFRE NUMERICHE)
    # IMPORTANTE: regex ^\d{9}$ verifica che sia ESATTAMENTE 9 cifre numeriche
    # Esclude child espositori che possono non avere AIC
    righe_senza_aic = db.execute("""
        SELECT id_dettaglio, n_riga, codice_aic, codice_originale, descrizione
        FROM ordini_dettaglio
        WHERE id_testata = %s
          AND (codice_aic IS NULL OR codice_aic = '' OR codice_aic !~ '^[0-9]{9}$')
          AND COALESCE(is_child, FALSE) = FALSE
        ORDER BY n_riga
    """, (id_testata,)).fetchall()

    if righe_senza_aic:
        from .supervision.aic import crea_supervisione_aic, valuta_anomalia_aic

        for riga_senza_aic in righe_senza_aic:
            # Prepara descrizione anomalia
            descrizione_anomalia = f"{CODICI_ANOMALIA.get('AIC-A01', 'Codice AIC mancante o non valido - verifica obbligatoria')}"

            # Inserisci anomalia GRAVE per ogni riga
            cursor = db.execute("""
                INSERT INTO anomalie
                (id_testata, id_dettaglio, tipo_anomalia, livello, codice_anomalia,
                 descrizione, valore_anomalo, richiede_supervisione)
                VALUES (%s, %s, 'AIC', 'ERRORE', 'AIC-A01', %s, %s, TRUE)
                RETURNING id_anomalia
            """, (
                id_testata,
                riga_senza_aic['id_dettaglio'],
                descrizione_anomalia,
                f"Codice originale: {riga_senza_aic['codice_originale'] or 'N/D'}, Descrizione: {riga_senza_aic['descrizione'][:30] if riga_senza_aic['descrizione'] else 'N/D'}"
            ))
            id_anomalia_aic = cursor.fetchone()[0]

            # Prepara dati anomalia per supervisione
            anomalia_aic = {
                'tipo_anomalia': 'AIC',
                'codice_anomalia': 'AIC-A01',
                'vendor': vendor or 'UNKNOWN',
                'n_riga': riga_senza_aic['n_riga'],
                'id_dettaglio': riga_senza_aic['id_dettaglio'],
                'descrizione_prodotto': riga_senza_aic['descrizione'],
                'codice_originale': riga_senza_aic['codice_originale'],
            }

            # Valuta con apprendimento ML - può auto-applicare se pattern ordinario
            applicato_auto, _ = valuta_anomalia_aic(id_testata, anomalia_aic)

            if not applicato_auto:
                # Crea richiesta supervisione AIC
                crea_supervisione_aic(id_testata, id_anomalia_aic, anomalia_aic)
                richiede_supervisione = True

        if richiede_supervisione:
            result['anomalie'].append(
                f"Ordine {order_data.get('numero_ordine')}: {len(righe_senza_aic)} prodotti senza codice AIC valido - richiede supervisione"
            )

    # =========================================================================
    # GESTIONE ANOMALIE ESPOSITORE (ANGELINI v3.0)
    # =========================================================================
    anomalie_esp = order_data.get('anomalie_espositore', [])
    # NOTA: richiede_supervisione già impostato sopra per anomalie LOOKUP/ESTRAZIONE

    for anomalia in anomalie_esp:
        # Inserisci anomalia nel database
        cursor = db.execute("""
            INSERT INTO anomalie
            (id_testata, tipo_anomalia, livello, codice_anomalia,
             descrizione, valore_anomalo, richiede_supervisione, pattern_signature)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_anomalia
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

        id_anomalia = cursor.fetchone()[0]

        # Se richiede supervisione, valuta con ML
        if anomalia.get('richiede_supervisione'):
            applicato_auto, pattern_sig = valuta_anomalia_con_apprendimento(
                id_testata, anomalia
            )

            # Aggiorna pattern signature nell'anomalia
            db.execute("""
                UPDATE ANOMALIE SET pattern_signature = %s WHERE id_anomalia = %s
            """, (pattern_sig, id_anomalia))

            if not applicato_auto:
                # Crea richiesta supervisione
                crea_richiesta_supervisione(id_testata, id_anomalia, anomalia)
                richiede_supervisione = True
                result['anomalie'].append(
                    f"Ordine {order_data.get('numero_ordine')}: richiede supervisione per {anomalia.get('codice_anomalia')}"
                )

    # =========================================================================
    # GESTIONE ANOMALIE LISTINO (CODIFI v7.0)
    # v10.4: Skip se esiste già un'anomalia specifica per lo stesso AIC
    # =========================================================================
    anomalie_listino = order_data.get('anomalie_listino', [])

    for anomalia in anomalie_listino:
        codice_aic = anomalia.get('valore_anomalo', '')
        codice_anomalia = anomalia.get('codice_anomalia', '')

        # v10.4: Verifica se esiste già un'anomalia LST-A01 per questo AIC
        # (creata dalla sezione CHECK LST-A01 con descrizione più specifica)
        if codice_anomalia == 'LST-A01' and codice_aic:
            existing = db.execute("""
                SELECT id_anomalia FROM anomalie
                WHERE id_testata = %s
                AND codice_anomalia = 'LST-A01'
                AND valore_anomalo = %s
            """, (id_testata, codice_aic)).fetchone()

            if existing:
                # Anomalia specifica già esiste, skip questa generica
                continue

        # Inserisci anomalia nel database
        cursor = db.execute("""
            INSERT INTO anomalie
            (id_testata, tipo_anomalia, livello, codice_anomalia,
             descrizione, valore_anomalo, richiede_supervisione, pattern_signature)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_anomalia
        """, (
            id_testata,
            anomalia.get('tipo_anomalia', 'LISTINO'),
            anomalia.get('livello', 'ERRORE'),
            codice_anomalia,
            anomalia.get('descrizione', ''),
            codice_aic,
            bool(anomalia.get('richiede_supervisione', False)),
            None,
        ))

        id_anomalia = cursor.fetchone()[0]

        # Se richiede supervisione, valuta con ML
        if anomalia.get('richiede_supervisione'):
            applicato_auto, pattern_sig = valuta_anomalia_con_apprendimento(
                id_testata, anomalia
            )

            # Aggiorna pattern signature nell'anomalia
            db.execute("""
                UPDATE ANOMALIE SET pattern_signature = %s WHERE id_anomalia = %s
            """, (pattern_sig, id_anomalia))

            if not applicato_auto:
                # Crea richiesta supervisione
                crea_richiesta_supervisione(id_testata, id_anomalia, anomalia)
                richiede_supervisione = True
                result['anomalie'].append(
                    f"Ordine {order_data.get('numero_ordine')}: richiede supervisione listino per {anomalia.get('codice_anomalia')}"
                )

    # Se almeno un'anomalia richiede supervisione, blocca ordine
    if richiede_supervisione:
        blocca_ordine_per_supervisione(id_testata)
    # =========================================================================
    # v11.3 FIX: AGGIORNA STATO ORDINE SE CI SONO ANOMALIE BLOCCANTI
    # =========================================================================
    # Check finale: se ci sono anomalie ERRORE/CRITICO aperte, stato = ANOMALIA
    anomalie_bloccanti = db.execute("""
        SELECT COUNT(*) as cnt FROM anomalie
        WHERE id_testata = %s
        AND stato IN ('APERTA', 'IN_GESTIONE')
        AND livello IN ('ERRORE', 'CRITICO')
    """, (id_testata,)).fetchone()

    if anomalie_bloccanti and anomalie_bloccanti['cnt'] > 0:
        db.execute("""
            UPDATE ordini_testata
            SET stato = 'ANOMALIA'
            WHERE id_testata = %s
            AND stato NOT IN ('EVASO', 'ARCHIVIATO')
        """, (id_testata,))
        result['stato'] = 'ANOMALIA'

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

    # v7.0: Prepara valori estratti per tracciabilità
    descrizione_val = riga.get('descrizione', '')[:40] if riga.get('descrizione') else ''
    codice_aic_val = riga.get('codice_aic', '')
    codice_originale_val = riga.get('codice_originale', '')

    # Determina fonte codice AIC
    fonte_codice_aic = 'ESTRATTO'
    if codice_originale_val and codice_originale_val != codice_aic_val:
        fonte_codice_aic = 'NORMALIZZATO'

    cursor = db.execute("""
        INSERT INTO ordini_dettaglio
        (id_testata, n_riga, codice_aic, codice_originale, descrizione,
         q_venduta, q_sconto_merce, q_omaggio, data_consegna_riga,
         sconto_1, sconto_2, sconto_3, sconto_4,
         prezzo_netto, prezzo_pubblico, aliquota_iva,
         is_espositore, is_child, is_no_aic,
         tipo_riga, id_parent_espositore, espositore_metadata,
         q_originale, q_residua, q_esportata,
         descrizione_estratta, fonte_codice_aic, fonte_quantita)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s)
        RETURNING id_dettaglio
    """, (
        id_testata, n_riga,
        codice_aic_val,
        codice_originale_val,
        descrizione_val,
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
        calcola_q_totale(riga),  # q_originale
        calcola_q_totale(riga),  # q_residua
        0,  # q_esportata = 0
        descrizione_val,  # descrizione_estratta
        fonte_codice_aic,  # fonte_codice_aic
        'ESTRATTO'  # fonte_quantita
    ))

    # Ottieni id riga inserita
    id_det = cursor.fetchone()[0]

    # v9.4: Anomalia espositore INFO con dettaglio child
    if is_esp:
        # Estrai dettaglio child dai metadata
        import json
        child_desc = ""
        metadata_str = riga.get('espositore_metadata', '')
        if metadata_str:
            try:
                metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
                child_dettaglio = metadata.get('child_dettaglio', [])
                if child_dettaglio:
                    child_parts = []
                    for c in child_dettaglio[:5]:  # Max 5 child
                        desc_short = c.get('descrizione', '')[:15] if c.get('descrizione') else c.get('codice', '')
                        child_parts.append(f"{c.get('aic', c.get('codice', 'N/D'))} {desc_short} x{c.get('quantita', 0)}")
                    child_desc = ", ".join(child_parts)
                    if len(child_dettaglio) > 5:
                        child_desc += f" (+{len(child_dettaglio) - 5} altri)"
            except:
                pass

        descrizione_anomalia = "Riga espositore parent elaborata"
        if child_desc:
            descrizione_anomalia += f"\nChild: {child_desc}"

        db.execute("""
            INSERT INTO ANOMALIE (id_testata, id_dettaglio, tipo_anomalia, livello, descrizione, valore_anomalo)
            VALUES (%s, %s, 'ESPOSITORE', 'INFO', %s, %s)
        """, (id_testata, id_det, descrizione_anomalia, riga.get('descrizione', '')))

    return id_det


def _save_acquisition_error(db, filename: str, hash_file: str, 
                           file_content: bytes, error_msg: str):
    """Salva acquisizione in stato errore."""
    nome_storage = f"{uuid.uuid4().hex}_{filename}"
    db.execute("""
        INSERT INTO ACQUISIZIONI 
        (nome_file_originale, nome_file_storage, hash_file, dimensione_bytes,
         stato, messaggio_errore)
        VALUES (%s, %s, %s, %s, 'ERRORE', %s)
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
        LIMIT %s
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
