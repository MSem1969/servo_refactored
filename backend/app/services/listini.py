# =============================================================================
# SERV.O v7.0 - LISTINI VENDOR SERVICE
# =============================================================================
# Gestione listini prezzi per vendor che non includono prezzi nei PDF
# Struttura allineata al tracciato TO_D per popolamento campi prezzo/sconto
# Vendor supportati: CODIFI, altri in futuro
# =============================================================================

import csv
import math
import os
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from ..database_pg import get_db


# =============================================================================
# CONFIGURAZIONE MAPPING COLONNE PER VENDOR
# =============================================================================

# Mapping colonne CSV -> campi database per ogni vendor
# I campi TO_D target sono: sconto_1-4, prezzo_netto, prezzo_scontare, prezzo_pubblico, aliquota_iva, scorporo_iva
VENDOR_CSV_MAPPINGS = {
    'CODIFI': {
        # Campi obbligatori per lookup
        'codice_aic': 'AFCODI',           # Codice AIC
        'descrizione': 'CVDPRO',          # Descrizione prodotto
        # Sconti
        'sconto_1': 'CVSCO1',             # Sconto % 1 (formato italiano con virgola)
        'sconto_2': 'CVSCO2',             # Sconto % 2
        # sconto_3 e sconto_4 non presenti nel CSV CODIFI -> default 0
        # Prezzi
        'prezzo_pubblico_csv': 'AFPEU1',  # Prezzo pubblico formato XXXXXYYY (3 dec impliciti, es: 37130 → 37.130)
        'prezzo_csv_originale': 'CVPVEN', # Prezzo vendita originale (spesso 0)
        # IVA
        'aliquota_iva': 'AFAIVA',         # Aliquota IVA (intero es: 10, 22)
        # Altri
        'data_decorrenza': 'AFDVA1',      # Data formato YYYYMMDD
    }
}


# =============================================================================
# FUNZIONI PARSING VALORI
# =============================================================================

def parse_decimal_it(value: str) -> Optional[float]:
    """
    Converte valore decimale italiano (virgola) in float.
    Es: "38,35" -> 38.35
    """
    if not value or value.strip() == '' or value.strip() == '0':
        return None
    try:
        # Rimuovi spazi e sostituisci virgola con punto
        cleaned = value.strip().replace(',', '.')
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def parse_prezzo_intero(value: str, decimals: int = 2) -> Optional[float]:
    """
    Converte prezzo in formato intero con decimali impliciti.
    Es: "00013590" con 2 decimali -> 135.90
    """
    if not value or value.strip() == '' or value.strip() == '0':
        return None
    try:
        # Rimuovi zeri iniziali ma mantieni il numero
        cleaned = value.strip().lstrip('0') or '0'
        val_int = int(cleaned)
        divisor = 10 ** decimals
        return val_int / divisor
    except (ValueError, TypeError):
        return None


def parse_data_yyyymmdd(value: str) -> Optional[str]:
    """
    Converte data formato YYYYMMDD in formato ISO YYYY-MM-DD.
    Es: "20180206" -> "2018-02-06"
    """
    if not value or len(value) != 8:
        return None
    try:
        year = value[:4]
        month = value[4:6]
        day = value[6:8]
        # Valida che sia una data valida
        datetime(int(year), int(month), int(day))
        return f"{year}-{month}-{day}"
    except (ValueError, TypeError):
        return None


def normalizza_codice_aic(codice: str) -> str:
    """
    Normalizza codice AIC a 9 cifre con zero padding.
    Es: "39887070" -> "039887070"
    """
    if not codice:
        return ''
    # Rimuovi spazi e caratteri non numerici
    cleaned = ''.join(c for c in str(codice).strip() if c.isdigit())
    # Padding a 9 cifre
    return cleaned.zfill(9)


def ceil_decimal(value: float, decimals: int = 2) -> float:
    """
    Arrotonda per eccesso a N decimali.
    Es: 123.541 con 2 decimali -> 123.55
    """
    if value is None:
        return None
    multiplier = 10 ** decimals
    return math.ceil(value * multiplier) / multiplier


def scorporo_iva(prezzo_ivato: float, aliquota_iva: float) -> Optional[float]:
    """
    Calcola prezzo netto da prezzo IVA inclusa.
    Formula: prezzo_ivato / ((100 + IVA) / 100)
    Arrotonda con metodo standard al secondo decimale.

    Es: 135.90 con IVA 10% -> 135.90 / 1.10 = 123.545... -> 123.55

    Args:
        prezzo_ivato: Prezzo con IVA inclusa
        aliquota_iva: Aliquota IVA (es: 10, 22)

    Returns:
        Prezzo netto arrotondato a 2 decimali
    """
    if prezzo_ivato is None or prezzo_ivato <= 0:
        return None
    if aliquota_iva is None or aliquota_iva < 0:
        aliquota_iva = 0

    divisore = (100 + aliquota_iva) / 100
    prezzo_netto = prezzo_ivato / divisore

    # Arrotondamento standard a 2 decimali
    return round(prezzo_netto, 2)


# =============================================================================
# IMPORT CSV
# =============================================================================

def import_listino_csv(
    csv_content: bytes = None,
    filepath: str = None,
    vendor: str = 'CODIFI',
    filename: str = None,
    clear_existing: bool = True,
    scorporo_iva_default: str = 'S'
) -> Tuple[bool, Dict[str, Any]]:
    """
    Importa listino da file CSV per un vendor specifico.
    I dati vengono mappati ai campi allineati al tracciato TO_D.

    Args:
        csv_content: Contenuto CSV come bytes (alternativo a filepath)
        filepath: Percorso file CSV (alternativo a csv_content)
        vendor: Codice vendor (es: 'CODIFI')
        filename: Nome file origine per tracciabilità
        clear_existing: Se True, elimina righe esistenti per il vendor
        scorporo_iva_default: Valore default per NetVATPrice ('S'=Netto, 'N'=IVA inclusa)

    Returns:
        (success, result_dict) dove result_dict contiene:
        - imported: numero righe importate
        - skipped: numero righe saltate
        - errors: lista errori
        - filename: nome file
    """
    vendor_upper = vendor.upper()

    # Verifica mapping vendor supportato
    if vendor_upper not in VENDOR_CSV_MAPPINGS:
        return False, {
            'error': f"Vendor {vendor_upper} non supportato. Vendor disponibili: {list(VENDOR_CSV_MAPPINGS.keys())}"
        }

    # Verifica che sia fornito almeno uno tra csv_content e filepath
    if csv_content is None and filepath is None:
        return False, {'error': 'Fornire csv_content o filepath'}

    if filepath and not os.path.exists(filepath):
        return False, {'error': f"File non trovato: {filepath}"}

    mapping = VENDOR_CSV_MAPPINGS[vendor_upper]
    db = get_db()

    # Determina filename
    if filename:
        result_filename = filename
    elif filepath:
        result_filename = os.path.basename(filepath)
    else:
        result_filename = f"upload_{vendor_upper}.csv"

    result = {
        'imported': 0,
        'skipped': 0,
        'errors': [],
        'filename': result_filename
    }

    try:
        # Cancella righe esistenti per il vendor se richiesto
        if clear_existing:
            cursor = db.execute(
                "DELETE FROM listini_vendor WHERE vendor = %s",
                (vendor_upper,)
            )
            deleted = cursor.rowcount
            db.commit()
            print(f"   🗑️ Eliminate {deleted} righe esistenti per {vendor_upper}")

        # Prepara contenuto CSV
        if csv_content is not None:
            # Decodifica bytes in stringa
            try:
                content_str = csv_content.decode('utf-8')
            except UnicodeDecodeError:
                content_str = csv_content.decode('latin-1', errors='replace')
            lines = content_str.splitlines()
        else:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.read().splitlines()

        # Rileva delimitatore dalla prima riga
        if not lines:
            return False, {'error': 'File CSV vuoto'}

        sample = '\n'.join(lines[:5])
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=',;')
        except csv.Error:
            # Default a virgola
            dialect = csv.excel
            dialect.delimiter = ','

        reader = csv.DictReader(lines, dialect=dialect)

        # Verifica colonne richieste (solo quelle definite nel mapping)
        headers = reader.fieldnames or []
        required_cols = ['codice_aic', 'descrizione']
        missing = [mapping[col] for col in required_cols if mapping.get(col) and mapping[col] not in headers]
        if missing:
            return False, {
                'error': f"Colonne obbligatorie mancanti nel CSV: {missing}. Colonne trovate: {headers}"
            }

        for row_num, row in enumerate(reader, start=2):
            try:
                # Estrai codice AIC
                codice_aic_raw = row.get(mapping['codice_aic'], '').strip()
                if not codice_aic_raw:
                    result['skipped'] += 1
                    continue

                codice_aic = normalizza_codice_aic(codice_aic_raw)

                # Parse valori
                descrizione = row.get(mapping['descrizione'], '').strip()[:100]

                # Sconti da CSV (sconto_3 e sconto_4 non presenti in CODIFI)
                sconto_1_csv = parse_decimal_it(row.get(mapping.get('sconto_1', ''), ''))
                sconto_2_csv = parse_decimal_it(row.get(mapping.get('sconto_2', ''), ''))
                sconto_3_csv = parse_decimal_it(row.get(mapping.get('sconto_3', ''), ''))
                sconto_4_csv = parse_decimal_it(row.get(mapping.get('sconto_4', ''), ''))

                # Prezzi da CSV
                # CODIFI usa 3 decimali impliciti (es: 37130 → 37.130, non 371.30)
                prezzo_pubblico_csv = parse_prezzo_intero(row.get(mapping.get('prezzo_pubblico_csv', ''), ''), decimals=3)
                prezzo_csv_originale = parse_decimal_it(row.get(mapping.get('prezzo_csv_originale', ''), ''))

                # IVA
                aliquota_iva_raw = row.get(mapping.get('aliquota_iva', ''), '')
                aliquota_iva = float(aliquota_iva_raw) if aliquota_iva_raw.replace('.', '').replace(',', '').isdigit() else None

                # Data decorrenza
                data_decorrenza = parse_data_yyyymmdd(row.get(mapping.get('data_decorrenza', ''), ''))

                # =====================================================
                # LOGICA CALCOLO PREZZI CODIFI
                # =====================================================
                # Caso 1: CVPVEN > 0 -> prezzo netto diretto, sconti = 0
                # Caso 2: CVPVEN = 0/null -> scorporo IVA da prezzo pubblico
                # =====================================================

                if prezzo_csv_originale and prezzo_csv_originale > 0:
                    # CASO 1: Prezzo netto fornito direttamente
                    prezzo_netto = prezzo_csv_originale
                    prezzo_scontare = prezzo_csv_originale
                    prezzo_pubblico = prezzo_pubblico_csv  # Manteniamo per riferimento
                    # Sconti = 0 quando prezzo netto è diretto
                    sconto_1 = 0
                    sconto_2 = 0
                    sconto_3 = 0
                    sconto_4 = 0
                    flag_scorporo = 'S'  # Prezzo già netto
                else:
                    # CASO 2: Calcola prezzo netto da scorporo IVA
                    prezzo_pubblico = prezzo_pubblico_csv
                    prezzo_scontare = prezzo_pubblico_csv
                    prezzo_netto = scorporo_iva(prezzo_pubblico_csv, aliquota_iva)
                    # Manteniamo sconti da CSV (per tracciabilità)
                    sconto_1 = sconto_1_csv
                    sconto_2 = sconto_2_csv
                    sconto_3 = sconto_3_csv
                    sconto_4 = sconto_4_csv
                    flag_scorporo = 'N'  # Prezzo era IVA inclusa, scorporato

                # Insert or update (PostgreSQL syntax)
                db.execute("""
                    INSERT INTO listini_vendor (
                        vendor, codice_aic, descrizione,
                        sconto_1, sconto_2, sconto_3, sconto_4,
                        prezzo_netto, prezzo_scontare, prezzo_pubblico,
                        aliquota_iva, scorporo_iva,
                        prezzo_csv_originale, prezzo_pubblico_csv,
                        data_decorrenza, fonte_file, attivo, data_import
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, NOW())
                    ON CONFLICT (vendor, codice_aic) DO UPDATE SET
                        descrizione = EXCLUDED.descrizione,
                        sconto_1 = EXCLUDED.sconto_1,
                        sconto_2 = EXCLUDED.sconto_2,
                        sconto_3 = EXCLUDED.sconto_3,
                        sconto_4 = EXCLUDED.sconto_4,
                        prezzo_netto = EXCLUDED.prezzo_netto,
                        prezzo_scontare = EXCLUDED.prezzo_scontare,
                        prezzo_pubblico = EXCLUDED.prezzo_pubblico,
                        aliquota_iva = EXCLUDED.aliquota_iva,
                        scorporo_iva = EXCLUDED.scorporo_iva,
                        prezzo_csv_originale = EXCLUDED.prezzo_csv_originale,
                        prezzo_pubblico_csv = EXCLUDED.prezzo_pubblico_csv,
                        data_decorrenza = EXCLUDED.data_decorrenza,
                        fonte_file = EXCLUDED.fonte_file,
                        attivo = TRUE,
                        data_import = NOW()
                """, (
                    vendor_upper, codice_aic, descrizione,
                    sconto_1, sconto_2, sconto_3, sconto_4,
                    prezzo_netto, prezzo_scontare, prezzo_pubblico,
                    aliquota_iva, flag_scorporo,
                    prezzo_csv_originale, prezzo_pubblico_csv,
                    data_decorrenza, result_filename
                ))

                result['imported'] += 1

            except Exception as e:
                result['errors'].append(f"Riga {row_num}: {str(e)}")
                result['skipped'] += 1

        db.commit()

        # Statistiche finali
        count = db.execute(
            "SELECT COUNT(*) FROM listini_vendor WHERE vendor = %s",
            (vendor_upper,)
        ).fetchone()[0]
        result['total_in_db'] = count

        return True, result

    except Exception as e:
        db.rollback()
        return False, {'error': f"Errore import: {str(e)}"}


# =============================================================================
# LOOKUP FUNZIONI
# =============================================================================

def get_prezzo_listino(
    codice_aic: str,
    vendor: str = None
) -> Optional[Dict[str, Any]]:
    """
    Recupera dati prezzo/sconti da listino per un codice AIC.
    Ritorna tutti i campi TO_D necessari per il tracciato.

    Args:
        codice_aic: Codice AIC (verrà normalizzato)
        vendor: Se specificato, cerca solo per quel vendor

    Returns:
        Dict con dati listino (campi TO_D) o None se non trovato
    """
    db = get_db()
    aic_normalized = normalizza_codice_aic(codice_aic)

    if vendor:
        row = db.execute("""
            SELECT * FROM listini_vendor
            WHERE codice_aic = %s AND vendor = %s AND attivo = TRUE
        """, (aic_normalized, vendor.upper())).fetchone()
    else:
        row = db.execute("""
            SELECT * FROM listini_vendor
            WHERE codice_aic = %s AND attivo = TRUE
            ORDER BY data_import DESC
            LIMIT 1
        """, (aic_normalized,)).fetchone()

    return dict(row) if row else None


def get_listino_vendor(vendor: str, limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Recupera tutti i prodotti del listino per un vendor.
    """
    db = get_db()
    rows = db.execute("""
        SELECT * FROM listini_vendor
        WHERE vendor = %s AND attivo = TRUE
        ORDER BY descrizione
        LIMIT %s
    """, (vendor.upper(), limit)).fetchall()

    return [dict(row) for row in rows]


def get_listino_stats() -> Dict[str, Any]:
    """
    Statistiche sui listini caricati.
    """
    db = get_db()

    # Conteggi per vendor
    vendor_stats = db.execute("""
        SELECT vendor,
               COUNT(*) as prodotti,
               MAX(data_import) as ultimo_import,
               MAX(fonte_file) as ultimo_file
        FROM listini_vendor
        WHERE attivo = TRUE
        GROUP BY vendor
    """).fetchall()

    result = {
        'totale_prodotti': 0,
        'vendors': {}
    }

    for row in vendor_stats:
        result['vendors'][row['vendor']] = {
            'prodotti': row['prodotti'],
            'ultimo_import': row['ultimo_import'],
            'ultimo_file': row['ultimo_file']
        }
        result['totale_prodotti'] += row['prodotti']

    return result


def search_listino(
    query: str,
    vendor: str = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Cerca prodotti nel listino per descrizione o codice AIC.
    """
    db = get_db()
    search_term = f"%{query}%"

    if vendor:
        rows = db.execute("""
            SELECT * FROM listini_vendor
            WHERE vendor = %s AND attivo = TRUE
              AND (descrizione ILIKE %s OR codice_aic LIKE %s)
            ORDER BY descrizione
            LIMIT %s
        """, (vendor.upper(), search_term, search_term, limit)).fetchall()
    else:
        rows = db.execute("""
            SELECT * FROM listini_vendor
            WHERE attivo = TRUE
              AND (descrizione ILIKE %s OR codice_aic LIKE %s)
            ORDER BY vendor, descrizione
            LIMIT %s
        """, (search_term, search_term, limit)).fetchall()

    return [dict(row) for row in rows]


# =============================================================================
# CALCOLO PREZZI TO_D
# =============================================================================

def calcola_prezzo_netto(
    prezzo_scontare: float,
    sconto_1: float = None,
    sconto_2: float = None,
    sconto_3: float = None,
    sconto_4: float = None,
    formula: str = 'SCONTO_CASCATA'
) -> Tuple[Optional[float], str]:
    """
    Calcola NetVendorPrice (prezzo_netto) applicando sconti al PriceToDiscount.

    Formule supportate:
    - SCONTO_CASCATA: prezzo * (1-s1/100) * (1-s2/100) * (1-s3/100) * (1-s4/100)
    - SCONTO_SOMMA: prezzo * (1 - (s1+s2+s3+s4)/100)

    Args:
        prezzo_scontare: PriceToDiscount - prezzo base da scontare
        sconto_1-4: Percentuali sconto (Discount1-4)
        formula: Formula di calcolo

    Returns:
        (prezzo_netto, formula_descrizione)
    """
    if prezzo_scontare is None or prezzo_scontare <= 0:
        return None, ''

    s1 = sconto_1 or 0
    s2 = sconto_2 or 0
    s3 = sconto_3 or 0
    s4 = sconto_4 or 0

    if formula == 'SCONTO_CASCATA':
        # Applica sconti in cascata
        prezzo = prezzo_scontare
        for s in [s1, s2, s3, s4]:
            if s > 0:
                prezzo = prezzo * (1 - s / 100)
        formula_str = f"PtD * (1-{s1}/100) * (1-{s2}/100) * (1-{s3}/100) * (1-{s4}/100)"
    elif formula == 'SCONTO_SOMMA':
        # Applica somma sconti
        sconto_totale = s1 + s2 + s3 + s4
        prezzo = prezzo_scontare * (1 - sconto_totale / 100)
        formula_str = f"PtD * (1 - ({s1}+{s2}+{s3}+{s4})/100)"
    else:
        return None, f"Formula non supportata: {formula}"

    return round(prezzo, 2), formula_str


def aggiorna_prezzi_netti(
    vendor: str,
    formula: str = 'SCONTO_CASCATA',
    usa_prezzo_pubblico: bool = True
) -> Dict[str, Any]:
    """
    Calcola e aggiorna prezzo_netto e prezzo_scontare per tutti i prodotti di un vendor.
    Da chiamare dopo l'import o quando cambiano le regole di calcolo.

    Args:
        vendor: Codice vendor
        formula: Formula da usare per il calcolo
        usa_prezzo_pubblico: Se True, usa prezzo_pubblico come prezzo_scontare

    Returns:
        Dict con statistiche aggiornamento
    """
    db = get_db()
    vendor_upper = vendor.upper()

    # Recupera tutti i prodotti del vendor
    rows = db.execute("""
        SELECT id_listino, prezzo_pubblico, prezzo_scontare,
               sconto_1, sconto_2, sconto_3, sconto_4
        FROM listini_vendor
        WHERE vendor = %s AND attivo = TRUE
    """, (vendor_upper,)).fetchall()

    updated = 0
    skipped = 0

    for row in rows:
        # Determina prezzo da scontare
        if usa_prezzo_pubblico:
            prezzo_base = row['prezzo_pubblico']
        else:
            prezzo_base = row['prezzo_scontare'] or row['prezzo_pubblico']

        prezzo_netto, formula_str = calcola_prezzo_netto(
            prezzo_base,
            row['sconto_1'],
            row['sconto_2'],
            row['sconto_3'],
            row['sconto_4'],
            formula
        )

        if prezzo_netto is not None:
            db.execute("""
                UPDATE listini_vendor
                SET prezzo_netto = %s,
                    prezzo_scontare = %s
                WHERE id_listino = %s
            """, (prezzo_netto, prezzo_base, row['id_listino']))
            updated += 1
        else:
            skipped += 1

    db.commit()

    return {
        'vendor': vendor_upper,
        'updated': updated,
        'skipped': skipped,
        'formula': formula
    }


# =============================================================================
# FUNZIONI PER ESTRAZIONE CON ANOMALIE
# =============================================================================

def arricchisci_riga_con_listino(
    riga: Dict[str, Any],
    vendor: str = None
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Arricchisce una riga ordine con dati dal listino.
    Ritorna anche eventuale anomalia se AIC non trovato o prezzo mancante.

    LOGICA v10.0 (generalizzata):
    - Se la riga ha già un prezzo_netto valido (>0) → skip, mantiene prezzo PDF
    - Se prezzo_netto è None/0/vuoto → cerca nel listino generale
    - Il vendor è opzionale e usato solo per messaggi anomalie

    Args:
        riga: Dict con dati riga (deve contenere 'codice_aic')
        vendor: Codice vendor (opzionale, per logging anomalie)

    Returns:
        (riga_arricchita, anomalia) dove anomalia è None se tutto OK
    """
    codice_aic = riga.get('codice_aic', '')
    anomalia = None

    # Se non c'è codice AIC, non possiamo fare lookup
    if not codice_aic:
        return riga, None

    # v10.2: Escludi righe SC.MERCE, P.O.P. e omaggi dalla verifica listino
    # Queste righe hanno correttamente prezzo = 0 e non devono generare anomalia
    tipo_posizione = (riga.get('tipo_posizione') or '').upper()
    tipo_riga = (riga.get('tipo_riga') or '').upper()

    # Escludi per tipo_posizione (dall'estrattore)
    if tipo_posizione in ('SC.MERCE', 'SCMERCE', 'P.O.P.', 'P.O.P', 'POP'):
        riga['fonte_prezzi'] = 'OMAGGIO'
        return riga, None

    # Escludi per tipo_riga (dall'elaborazione espositore)
    if tipo_riga in ('SCONTO_MERCE', 'MATERIALE_POP'):
        riga['fonte_prezzi'] = 'OMAGGIO'
        return riga, None

    # Escludi se q_venduta = 0 e (q_sconto_merce > 0 o q_omaggio > 0)
    q_venduta = riga.get('q_venduta', 0) or 0
    q_sconto_merce = riga.get('q_sconto_merce', 0) or 0
    q_omaggio = riga.get('q_omaggio', 0) or 0

    if q_venduta == 0 and (q_sconto_merce > 0 or q_omaggio > 0):
        riga['fonte_prezzi'] = 'OMAGGIO'
        return riga, None

    # v10.0: Se la riga ha già un prezzo valido estratto dal PDF, non sovrascrivere
    prezzo_esistente = riga.get('prezzo_netto')
    if prezzo_esistente is not None and prezzo_esistente > 0:
        riga['fonte_prezzi'] = 'PDF'
        return riga, None

    # Cerca nel listino generale (senza filtro vendor)
    listino = get_prezzo_listino(codice_aic)

    if not listino:
        # LST-A01: AIC non trovato nel listino
        vendor_info = f' (vendor: {vendor})' if vendor else ''
        anomalia = {
            'tipo_anomalia': 'LISTINO',
            'livello': 'ERRORE',
            'codice_anomalia': 'LST-A01',
            'descrizione': f'Codice AIC {codice_aic} non trovato nel listino{vendor_info}',
            'valore_anomalo': codice_aic,
            'richiede_supervisione': True,
            'n_riga': riga.get('n_riga'),
            'vendor': vendor,
        }
        riga['fonte_prezzi'] = 'MANCANTE'
        return riga, anomalia

    # Arricchisci con campi listino
    # Mapping: campo_listino -> campo_riga (per INSERT in ORDINI_DETTAGLIO)
    mapping_campi = {
        'sconto_1': 'sconto1',  # ORDINI_DETTAGLIO usa sconto1, non sconto_1
        'sconto_2': 'sconto2',
        'sconto_3': 'sconto3',
        'sconto_4': 'sconto4',
        'prezzo_netto': 'prezzo_netto',
        'prezzo_pubblico': 'prezzo_pubblico',
        'aliquota_iva': 'aliquota_iva',
    }

    for campo_listino, campo_riga in mapping_campi.items():
        if listino.get(campo_listino) is not None:
            riga[campo_riga] = listino[campo_listino]

    # Verifica che il prezzo netto sia presente
    if not listino.get('prezzo_netto'):
        # LST-A02: Prezzo mancante nel listino
        anomalia = {
            'tipo_anomalia': 'LISTINO',
            'livello': 'ATTENZIONE',
            'codice_anomalia': 'LST-A02',
            'descrizione': f'Prezzo mancante nel listino per AIC {codice_aic}',
            'valore_anomalo': codice_aic,
            'richiede_supervisione': True,
            'n_riga': riga.get('n_riga'),
            'vendor': vendor,
        }

    # Marca fonte prezzi
    riga['fonte_prezzi'] = 'LISTINO'
    riga['id_listino'] = listino.get('id_listino')

    return riga, anomalia


def arricchisci_ordine_con_listino(
    order_data: Dict[str, Any],
    vendor: str
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Arricchisce tutte le righe di un ordine con dati dal listino.
    Usato solo per vendor che richiedono listino (es: CODIFI).

    Args:
        order_data: Dict ordine con campo 'righe'
        vendor: Codice vendor

    Returns:
        (order_data_arricchito, lista_anomalie_listino)
    """
    anomalie = []
    righe_arricchite = []

    for riga in order_data.get('righe', []):
        riga_arricchita, anomalia = arricchisci_riga_con_listino(riga, vendor)
        righe_arricchite.append(riga_arricchita)

        if anomalia:
            anomalie.append(anomalia)

    order_data['righe'] = righe_arricchite

    # Aggiungi riepilogo
    if anomalie:
        order_data['anomalie_listino'] = anomalie

    return order_data, anomalie


# v10.0: DEPRECATO - Il listino è ora generale per tutti i vendor
# L'arricchimento avviene per qualsiasi riga senza prezzo_netto valido
# Mantenuto per retrocompatibilità import ma non più usato nella logica
VENDORS_RICHIEDONO_LISTINO = set()  # Deprecato - listino ora generale
