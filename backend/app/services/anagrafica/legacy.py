# =============================================================================
# SERV.O v6.0 - ANAGRAFICA SERVICE
# =============================================================================
# Convertito da notebook Colab - Cella 15
# Import anagrafica farmacie e parafarmacie da CSV ministeriale
# =============================================================================

import io
import os
from typing import Dict, Any, List, Optional

# Pandas per CSV
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("⚠️ pandas non disponibile - import CSV disabilitato")

from ...database_pg import get_db, log_operation


# =============================================================================
# IMPORT FARMACIE
# =============================================================================

def import_anagrafica_farmacie(
    csv_path: str = None, 
    csv_content: bytes = None,
    fonte: str = None
) -> Dict[str, Any]:
    """
    Importa anagrafica farmacie da CSV ministeriale (FRM_FARMA_*).
    
    Args:
        csv_path: Percorso file CSV
        csv_content: Contenuto binario CSV
        fonte: Descrizione fonte dati
        
    Returns:
        Dict con statistiche import
    """
    if not PANDAS_AVAILABLE:
        return {'error': 'pandas non disponibile', 'importate': 0}
    
    result = {
        'importate': 0,
        'errori': 0,
        'totale_db': 0,
        'fonte': fonte or 'upload'
    }
    
    db = get_db()
    
    try:
        # Carica CSV
        if csv_content:
            df = pd.read_csv(io.BytesIO(csv_content), sep=';', encoding='utf-8', dtype=str)
            result['fonte'] = fonte or 'upload'
        elif csv_path:
            df = pd.read_csv(csv_path, sep=';', encoding='utf-8', dtype=str)
            result['fonte'] = fonte or os.path.basename(csv_path)
        else:
            return {'error': 'Specificare csv_path o csv_content', 'importate': 0}

        result['totale_righe_csv'] = len(df)

        # Filtra solo farmacie attive (data_fine_validita = '-')
        # v6.2: Strip whitespace per gestire variazioni formato
        if 'data_fine_validita' in df.columns:
            df['data_fine_validita'] = df['data_fine_validita'].str.strip()
            df = df[df['data_fine_validita'] == '-']

        result['righe_attive'] = len(df)
        
        # Mappa colonne (supporta vari formati CSV ministeriali)
        col_map = {
            'min_id': ['cod_farmacia', 'codice_farmacia', 'min_id', 'codice'],
            'partita_iva': ['p_iva', 'partita_iva', 'piva'],
            'ragione_sociale': ['descrizione_farmacia', 'ragione_sociale', 'denominazione'],
            'indirizzo': ['indirizzo', 'via'],
            'cap': ['cap'],
            'citta': ['comune', 'citta', 'localita'],
            'provincia': ['sigla_provincia', 'provincia', 'prov'],
            'regione': ['regione', 'desc_regione'],
            'data_inizio': ['data_inizio_validita', 'data_inizio'],
            'data_fine': ['data_fine_validita', 'data_fine'],
        }
        
        def get_col(row, field):
            for col in col_map.get(field, []):
                if col in row.index and pd.notna(row.get(col)):
                    return str(row[col]).strip()
            return ''

        def clean_date(date_str):
            """Converte date vuote o '-' in None per PostgreSQL."""
            if not date_str or date_str.strip() in ('-', '', 'NULL', 'null'):
                return None
            return date_str.strip()

        # Contatori debug
        result['skip_empty_minid'] = 0
        result['skip_zero_minid'] = 0

        # Import righe
        for _, row in df.iterrows():
            try:
                min_id = get_col(row, 'min_id')
                if not min_id:
                    result['skip_empty_minid'] += 1
                    continue

                # Normalizza MIN_ID a 9 cifre
                min_id = min_id.strip().zfill(9)
                if min_id == '000000000':
                    result['skip_zero_minid'] += 1
                    continue

                db.execute("""
                    INSERT INTO ANAGRAFICA_FARMACIE
                    (min_id, partita_iva, ragione_sociale, indirizzo, cap,
                     citta, provincia, regione, data_inizio_validita,
                     data_fine_validita, attiva, fonte_dati)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE, ?)
                    ON CONFLICT (min_id) DO UPDATE SET
                        partita_iva = EXCLUDED.partita_iva,
                        ragione_sociale = EXCLUDED.ragione_sociale,
                        indirizzo = EXCLUDED.indirizzo,
                        cap = EXCLUDED.cap,
                        citta = EXCLUDED.citta,
                        provincia = EXCLUDED.provincia,
                        regione = EXCLUDED.regione,
                        data_inizio_validita = EXCLUDED.data_inizio_validita,
                        data_fine_validita = EXCLUDED.data_fine_validita,
                        attiva = EXCLUDED.attiva,
                        fonte_dati = EXCLUDED.fonte_dati
                """, (
                    min_id,
                    get_col(row, 'partita_iva'),
                    get_col(row, 'ragione_sociale')[:100],
                    get_col(row, 'indirizzo')[:100],
                    get_col(row, 'cap')[:5],
                    get_col(row, 'citta'),
                    get_col(row, 'provincia')[:2],
                    get_col(row, 'regione'),
                    clean_date(get_col(row, 'data_inizio')),
                    clean_date(get_col(row, 'data_fine')),
                    result['fonte']
                ))
                result['importate'] += 1

            except Exception as e:
                result['errori'] += 1
                # Debug: salva ultimo errore
                result['ultimo_errore'] = str(e)
        
        db.commit()
        
        # Totale in DB
        result['totale_db'] = db.execute(
            "SELECT COUNT(*) FROM ANAGRAFICA_FARMACIE"
        ).fetchone()[0]
        
        log_operation('IMPORT_FARMACIE', 'ANAGRAFICA_FARMACIE', None,
                     f"Importate {result['importate']} farmacie da {result['fonte']}")
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


# =============================================================================
# IMPORT PARAFARMACIE
# =============================================================================

def import_anagrafica_parafarmacie(
    csv_path: str = None, 
    csv_content: bytes = None,
    fonte: str = None
) -> Dict[str, Any]:
    """
    Importa anagrafica parafarmacie da CSV ministeriale (FRM_PFARMA_*).
    
    Args:
        csv_path: Percorso file CSV
        csv_content: Contenuto binario CSV
        fonte: Descrizione fonte dati
        
    Returns:
        Dict con statistiche import
    """
    if not PANDAS_AVAILABLE:
        return {'error': 'pandas non disponibile', 'importate': 0}
    
    result = {
        'importate': 0,
        'errori': 0,
        'totale_db': 0,
        'fonte': fonte or 'upload'
    }
    
    db = get_db()
    
    try:
        # Carica CSV
        if csv_content:
            df = pd.read_csv(io.BytesIO(csv_content), sep=';', encoding='utf-8', dtype=str)
            result['fonte'] = fonte or 'upload'
        elif csv_path:
            df = pd.read_csv(csv_path, sep=';', encoding='utf-8', dtype=str)
            result['fonte'] = fonte or os.path.basename(csv_path)
        else:
            return {'error': 'Specificare csv_path o csv_content', 'importate': 0}

        result['totale_righe_csv'] = len(df)

        # Filtra solo parafarmacie attive
        # v6.2: Strip whitespace per gestire variazioni formato
        if 'data_fine_validita' in df.columns:
            df['data_fine_validita'] = df['data_fine_validita'].str.strip()
            df = df[df['data_fine_validita'] == '-']

        result['righe_attive'] = len(df)

        # Debug: colonne CSV effettive
        result['colonne_csv'] = list(df.columns)

        # Mappa colonne
        col_map = {
            'codice_sito': ['codice_identificativo_sito', 'codice_sito', 'id_sito'],
            'sito_logistico': ['sito_logistico', 'denominazione', 'ragione_sociale'],
            'partita_iva': ['partita_iva', 'p_iva', 'piva'],
            'indirizzo': ['indirizzo', 'via'],
            'cap': ['cap'],
            'citta': ['comune', 'citta'],
            'provincia': ['sigla_provincia', 'provincia'],
            'regione': ['regione', 'desc_regione'],
            'codice_comune': ['codice_comune'],
            'codice_provincia': ['codice_provincia'],
            'codice_regione': ['codice_regione'],
            'latitudine': ['latitudine', 'lat'],
            'longitudine': ['longitudine', 'lng', 'lon'],
            'data_inizio': ['data_inizio_validita'],
            'data_fine': ['data_fine_validita'],
        }
        
        def get_col(row, field):
            for col in col_map.get(field, []):
                if col in row.index and pd.notna(row.get(col)):
                    return str(row[col]).strip()
            return ''

        def clean_date(date_str):
            """Converte date vuote o '-' in None per PostgreSQL."""
            if not date_str or date_str.strip() in ('-', '', 'NULL', 'null'):
                return None
            return date_str.strip()

        def clean_numeric(val_str):
            """Converte stringhe numeriche in float o None per PostgreSQL."""
            if not val_str or val_str.strip() in ('-', '', 'NULL', 'null'):
                return None
            try:
                # Gestisce sia virgola che punto come separatore decimale
                return float(val_str.strip().replace(',', '.'))
            except (ValueError, TypeError):
                return None

        # Contatori debug
        result['skip_empty_codice'] = 0

        # Import righe
        for _, row in df.iterrows():
            try:
                codice_sito = get_col(row, 'codice_sito')
                if not codice_sito:
                    result['skip_empty_codice'] += 1
                    continue
                
                db.execute("""
                    INSERT INTO ANAGRAFICA_PARAFARMACIE
                    (codice_sito, sito_logistico, partita_iva, indirizzo, cap,
                     codice_comune, citta, codice_provincia, provincia,
                     codice_regione, regione, data_inizio_validita, data_fine_validita,
                     latitudine, longitudine, attiva, fonte_dati)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE, ?)
                    ON CONFLICT (codice_sito) DO UPDATE SET
                        sito_logistico = EXCLUDED.sito_logistico,
                        partita_iva = EXCLUDED.partita_iva,
                        indirizzo = EXCLUDED.indirizzo,
                        cap = EXCLUDED.cap,
                        codice_comune = EXCLUDED.codice_comune,
                        citta = EXCLUDED.citta,
                        codice_provincia = EXCLUDED.codice_provincia,
                        provincia = EXCLUDED.provincia,
                        codice_regione = EXCLUDED.codice_regione,
                        regione = EXCLUDED.regione,
                        data_inizio_validita = EXCLUDED.data_inizio_validita,
                        data_fine_validita = EXCLUDED.data_fine_validita,
                        latitudine = EXCLUDED.latitudine,
                        longitudine = EXCLUDED.longitudine,
                        attiva = EXCLUDED.attiva,
                        fonte_dati = EXCLUDED.fonte_dati
                """, (
                    codice_sito,
                    get_col(row, 'sito_logistico')[:100],
                    get_col(row, 'partita_iva'),
                    get_col(row, 'indirizzo')[:100],
                    get_col(row, 'cap')[:5],
                    get_col(row, 'codice_comune'),
                    get_col(row, 'citta'),
                    get_col(row, 'codice_provincia'),
                    get_col(row, 'provincia')[:2],
                    get_col(row, 'codice_regione'),
                    get_col(row, 'regione'),
                    clean_date(get_col(row, 'data_inizio')),
                    clean_date(get_col(row, 'data_fine')),
                    clean_numeric(get_col(row, 'latitudine')),
                    clean_numeric(get_col(row, 'longitudine')),
                    result['fonte']
                ))
                result['importate'] += 1

            except Exception as e:
                result['errori'] += 1
                result['ultimo_errore'] = str(e)

        db.commit()
        
        # Totale in DB
        result['totale_db'] = db.execute(
            "SELECT COUNT(*) FROM ANAGRAFICA_PARAFARMACIE"
        ).fetchone()[0]
        
        log_operation('IMPORT_PARAFARMACIE', 'ANAGRAFICA_PARAFARMACIE', None,
                     f"Importate {result['importate']} parafarmacie da {result['fonte']}")
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


# =============================================================================
# STATISTICHE E QUERY
# =============================================================================

def get_anagrafica_stats() -> Dict[str, Any]:
    """Ritorna statistiche anagrafica con info ultimo import."""
    db = get_db()

    # Statistiche farmacie con info ultimo import
    farm_stats = {
        'totale': db.execute(
            "SELECT COUNT(*) FROM ANAGRAFICA_FARMACIE"
        ).fetchone()[0],
        'attive': db.execute(
            "SELECT COUNT(*) FROM ANAGRAFICA_FARMACIE WHERE attiva = TRUE"
        ).fetchone()[0],
        'last_import': None,
        'filename': None
    }

    # Ultimo import farmacie
    farm_last = db.execute("""
        SELECT data_import, fonte_dati
        FROM ANAGRAFICA_FARMACIE
        WHERE data_import IS NOT NULL
        ORDER BY data_import DESC
        LIMIT 1
    """).fetchone()
    if farm_last:
        farm_stats['last_import'] = farm_last[0]
        farm_stats['filename'] = farm_last[1]

    # Statistiche parafarmacie con info ultimo import
    para_stats = {
        'totale': db.execute(
            "SELECT COUNT(*) FROM ANAGRAFICA_PARAFARMACIE"
        ).fetchone()[0],
        'attive': db.execute(
            "SELECT COUNT(*) FROM ANAGRAFICA_PARAFARMACIE WHERE attiva = TRUE"
        ).fetchone()[0],
        'last_import': None,
        'filename': None
    }

    # Ultimo import parafarmacie
    para_last = db.execute("""
        SELECT data_import, fonte_dati
        FROM ANAGRAFICA_PARAFARMACIE
        WHERE data_import IS NOT NULL
        ORDER BY data_import DESC
        LIMIT 1
    """).fetchone()
    if para_last:
        para_stats['last_import'] = para_last[0]
        para_stats['filename'] = para_last[1]

    return {
        'farmacie': farm_stats,
        'parafarmacie': para_stats
    }


def search_anagrafica(
    query: str, 
    tipo: str = 'all',
    limit: int = 20
) -> Dict[str, List[Dict]]:
    """
    Ricerca in anagrafica farmacie e/o parafarmacie.
    
    Args:
        query: Testo da cercare
        tipo: 'farmacie', 'parafarmacie', o 'all'
        limit: Max risultati per tipo
        
    Returns:
        Dict con liste farmacie e parafarmacie trovate
    """
    db = get_db()
    result = {'farmacie': [], 'parafarmacie': []}
    query_like = f"%{query}%"
    
    if tipo in ('farmacie', 'all'):
        rows = db.execute("""
            SELECT id_farmacia, min_id, partita_iva, ragione_sociale,
                   indirizzo, cap, citta, provincia
            FROM ANAGRAFICA_FARMACIE
            WHERE attiva = TRUE
            AND (
                ragione_sociale ILIKE ?
                OR citta ILIKE ?
                OR indirizzo ILIKE ?
                OR cap ILIKE ?
                OR provincia ILIKE ?
                OR partita_iva ILIKE ?
                OR min_id ILIKE ?
            )
            ORDER BY
                CASE WHEN citta ILIKE ? THEN 0 ELSE 1 END,
                ragione_sociale
            LIMIT ?
        """, (query_like, query_like, query_like, query_like, query_like, query_like, query_like,
              query_like, limit)).fetchall()
        result['farmacie'] = [dict(row) for row in rows]

    if tipo in ('parafarmacie', 'all'):
        rows = db.execute("""
            SELECT id_parafarmacia, codice_sito, partita_iva,
                   sito_logistico as ragione_sociale,
                   indirizzo, cap, citta, provincia
            FROM ANAGRAFICA_PARAFARMACIE
            WHERE attiva = TRUE
            AND (
                sito_logistico ILIKE ?
                OR citta ILIKE ?
                OR indirizzo ILIKE ?
                OR cap ILIKE ?
                OR provincia ILIKE ?
                OR partita_iva ILIKE ?
                OR codice_sito ILIKE ?
            )
            ORDER BY
                CASE WHEN citta ILIKE ? THEN 0 ELSE 1 END,
                sito_logistico
            LIMIT ?
        """, (query_like, query_like, query_like, query_like, query_like, query_like, query_like,
              query_like, limit)).fetchall()
        result['parafarmacie'] = [dict(row) for row in rows]
    
    return result


def get_farmacia_by_id(id_farmacia: int) -> Optional[Dict]:
    """Ritorna farmacia per ID."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM ANAGRAFICA_FARMACIE WHERE id_farmacia = ?",
        (id_farmacia,)
    ).fetchone()
    return dict(row) if row else None


def get_parafarmacia_by_id(id_parafarmacia: int) -> Optional[Dict]:
    """Ritorna parafarmacia per ID."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM ANAGRAFICA_PARAFARMACIE WHERE id_parafarmacia = ?",
        (id_parafarmacia,)
    ).fetchone()
    return dict(row) if row else None


def get_farmacia_by_min_id(min_id: str) -> Optional[Dict]:
    """Ritorna farmacia per MIN_ID."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM ANAGRAFICA_FARMACIE WHERE min_id = ?",
        (min_id.zfill(9),)
    ).fetchone()
    return dict(row) if row else None


def get_farmacia_by_piva(piva: str) -> List[Dict]:
    """Ritorna farmacie per P.IVA (può essere multipunto)."""
    db = get_db()
    # Normalizza P.IVA (rimuovi zeri iniziali)
    piva_norm = piva.lstrip('0') if piva else ''
    
    rows = db.execute("""
        SELECT * FROM ANAGRAFICA_FARMACIE 
        WHERE LTRIM(REPLACE(COALESCE(partita_iva,''), ' ', ''), '0') = ?
        AND attiva = TRUE
    """, (piva_norm,)).fetchall()
    
    return [dict(row) for row in rows]


# =============================================================================
# PULIZIA E MANUTENZIONE
# =============================================================================

def clear_anagrafica_farmacie() -> int:
    """Elimina tutte le farmacie. Ritorna numero record eliminati."""
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM ANAGRAFICA_FARMACIE").fetchone()[0]
    db.execute("DELETE FROM ANAGRAFICA_FARMACIE")
    db.commit()
    log_operation('CLEAR_FARMACIE', 'ANAGRAFICA_FARMACIE', None,
                 f"Eliminate {count} farmacie")
    return count


def clear_anagrafica_parafarmacie() -> int:
    """Elimina tutte le parafarmacie. Ritorna numero record eliminati."""
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM ANAGRAFICA_PARAFARMACIE").fetchone()[0]
    db.execute("DELETE FROM ANAGRAFICA_PARAFARMACIE")
    db.commit()
    log_operation('CLEAR_PARAFARMACIE', 'ANAGRAFICA_PARAFARMACIE', None,
                 f"Eliminate {count} parafarmacie")
    return count


# =============================================================================
# IMPORT CLIENTI (v9.4)
# =============================================================================

def import_anagrafica_clienti(
    csv_path: str = None,
    csv_content: bytes = None,
    fonte: str = None
) -> Dict[str, Any]:
    """
    Importa anagrafica clienti da CSV.

    Args:
        csv_path: Percorso file CSV
        csv_content: Contenuto binario CSV
        fonte: Descrizione fonte dati

    Returns:
        Dict con statistiche import
    """
    if not PANDAS_AVAILABLE:
        return {'error': 'pandas non disponibile', 'importate': 0}

    result = {
        'importate': 0,
        'aggiornati': 0,
        'errori': 0,
        'totale_db': 0,
        'fonte': fonte or 'upload'
    }

    db = get_db()

    try:
        # Carica CSV - supporta vari encoding e separatori
        def try_read_csv(source, is_content=True):
            """Prova a leggere CSV con vari encoding e separatori."""
            encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            separators = [',', ';']

            for enc in encodings:
                for sep in separators:
                    try:
                        if is_content:
                            df = pd.read_csv(io.BytesIO(source), sep=sep, encoding=enc, dtype=str)
                        else:
                            df = pd.read_csv(source, sep=sep, encoding=enc, dtype=str)
                        if len(df.columns) >= 3:
                            return df, enc, sep
                    except:
                        continue
            return None, None, None

        if csv_content:
            df, enc_used, sep_used = try_read_csv(csv_content, is_content=True)
            result['fonte'] = fonte or 'upload'
            result['encoding'] = enc_used
            result['separatore'] = sep_used
        elif csv_path:
            df, enc_used, sep_used = try_read_csv(csv_path, is_content=False)
            result['fonte'] = fonte or os.path.basename(csv_path)
            result['encoding'] = enc_used
            result['separatore'] = sep_used
        else:
            return {'error': 'Specificare csv_path o csv_content', 'importate': 0}

        if df is None:
            return {'error': 'Impossibile leggere il file CSV - encoding o formato non supportato', 'importate': 0}

        result['totale_righe_csv'] = len(df)
        result['colonne_csv'] = list(df.columns)

        # Mappa colonne CSV -> DB (v11.2: corretto mapping AGTIDD e AGDRIF)
        col_map = {
            'codice_cliente': ['AGCANA', 'codice_cliente', 'codice'],
            'ragione_sociale_1': ['AGRSO1', 'ragione_sociale_1', 'ragione_sociale'],
            'ragione_sociale_2': ['AGRSO2', 'ragione_sociale_2'],
            'indirizzo': ['AGINDI', 'indirizzo'],
            'cap': ['AGCAP', 'cap'],
            'localita': ['AGLOCA', 'localita', 'citta'],
            'provincia': ['AGPROV', 'provincia'],
            'partita_iva': ['AGPIVA', 'partita_iva', 'piva'],
            'email': ['AGMAIL', 'email'],
            'farmacia_categoria': ['AGCATE', 'farmacia_categoria', 'categoria'],
            'codice_farmacia': ['AGCFAR', 'codice_farmacia'],
            'farma_status': ['AGCSTA', 'farma_status', 'codice_stato'],
            'codice_pagamento': ['AGCPAG', 'codice_pagamento'],
            'min_id': ['AGTIDD', 'min_id'],
            'deposito_riferimento': ['AGDRIF', 'deposito_riferimento', 'riferimento'],
        }

        def get_col(row, field):
            for col in col_map.get(field, []):
                if col in row.index and pd.notna(row.get(col)):
                    return str(row[col]).strip()
            return ''

        # Contatori debug
        result['skip_empty_codice'] = 0

        # Import righe
        for _, row in df.iterrows():
            try:
                codice = get_col(row, 'codice_cliente')
                if not codice:
                    result['skip_empty_codice'] += 1
                    continue

                # Verifica se esiste già
                existing = db.execute(
                    "SELECT id_cliente FROM anagrafica_clienti WHERE codice_cliente = ?",
                    (codice,)
                ).fetchone()

                if existing:
                    # Update (v11.2: nomi colonne corretti, aggiorna anche data_import)
                    db.execute("""
                        UPDATE anagrafica_clienti SET
                            ragione_sociale_1 = ?,
                            ragione_sociale_2 = ?,
                            indirizzo = ?,
                            cap = ?,
                            localita = ?,
                            provincia = ?,
                            partita_iva = ?,
                            email = ?,
                            farmacia_categoria = ?,
                            codice_farmacia = ?,
                            farma_status = ?,
                            codice_pagamento = ?,
                            min_id = ?,
                            deposito_riferimento = ?,
                            data_import = CURRENT_TIMESTAMP,
                            data_aggiornamento = CURRENT_TIMESTAMP
                        WHERE codice_cliente = ?
                    """, (
                        get_col(row, 'ragione_sociale_1')[:100] or None,
                        get_col(row, 'ragione_sociale_2')[:100] or None,
                        get_col(row, 'indirizzo')[:200] or None,
                        get_col(row, 'cap')[:10] or None,
                        get_col(row, 'localita')[:100] or None,
                        get_col(row, 'provincia')[:3] or None,
                        get_col(row, 'partita_iva')[:16] or None,
                        get_col(row, 'email')[:200] or None,
                        get_col(row, 'farmacia_categoria')[:10] or None,
                        get_col(row, 'codice_farmacia')[:20] or None,
                        get_col(row, 'farma_status')[:10] or None,
                        get_col(row, 'codice_pagamento')[:10] or None,
                        get_col(row, 'min_id')[:20] or None,
                        get_col(row, 'deposito_riferimento')[:10] or None,
                        codice
                    ))
                    result['aggiornati'] += 1
                else:
                    # Insert (v11.2: nomi colonne corretti, imposta data_import)
                    db.execute("""
                        INSERT INTO anagrafica_clienti
                        (codice_cliente, ragione_sociale_1, ragione_sociale_2, indirizzo, cap,
                         localita, provincia, partita_iva, email, farmacia_categoria,
                         codice_farmacia, farma_status, codice_pagamento, min_id, deposito_riferimento,
                         data_import)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        codice,
                        get_col(row, 'ragione_sociale_1')[:100] or None,
                        get_col(row, 'ragione_sociale_2')[:100] or None,
                        get_col(row, 'indirizzo')[:200] or None,
                        get_col(row, 'cap')[:10] or None,
                        get_col(row, 'localita')[:100] or None,
                        get_col(row, 'provincia')[:3] or None,
                        get_col(row, 'partita_iva')[:16] or None,
                        get_col(row, 'email')[:200] or None,
                        get_col(row, 'farmacia_categoria')[:10] or None,
                        get_col(row, 'codice_farmacia')[:20] or None,
                        get_col(row, 'farma_status')[:10] or None,
                        get_col(row, 'codice_pagamento')[:10] or None,
                        get_col(row, 'min_id')[:20] or None,
                        get_col(row, 'deposito_riferimento')[:10] or None,
                    ))
                    result['importate'] += 1

            except Exception as e:
                result['errori'] += 1
                result['ultimo_errore'] = str(e)

        db.commit()

        # Totale in DB
        result['totale_db'] = db.execute(
            "SELECT COUNT(*) FROM anagrafica_clienti"
        ).fetchone()[0]

        log_operation('IMPORT_CLIENTI', 'ANAGRAFICA_CLIENTI', None,
                     f"Importati {result['importate']} clienti, aggiornati {result['aggiornati']} da {result['fonte']}")

        # v11.4: Revisione automatica ordini con deposito mancante
        # Dopo l'import, cerca ordini con DEP-A01 e prova a risolverli
        revisione = revisiona_ordini_deposito_mancante()
        if revisione.get('anomalie_risolte', 0) > 0:
            result['revisione_ordini'] = {
                'ordini_revisionati': revisione['ordini_revisionati'],
                'depositi_trovati': revisione['depositi_trovati'],
                'anomalie_risolte': revisione['anomalie_risolte']
            }

    except Exception as e:
        result['error'] = str(e)

    return result


def get_clienti_stats() -> Dict[str, Any]:
    """Ritorna statistiche anagrafica clienti."""
    db = get_db()

    try:
        stats = {
            'totale': db.execute(
                "SELECT COUNT(*) FROM anagrafica_clienti"
            ).fetchone()[0],
            'last_import': None,
            'filename': None
        }

        # Ultimo import
        last = db.execute("""
            SELECT data_import
            FROM anagrafica_clienti
            WHERE data_import IS NOT NULL
            ORDER BY data_import DESC
            LIMIT 1
        """).fetchone()
        if last:
            stats['last_import'] = last[0]

        return stats
    except Exception as e:
        # Tabella potrebbe non esistere
        return {'totale': 0, 'last_import': None, 'filename': None}


def clear_anagrafica_clienti() -> int:
    """Elimina tutti i clienti. Ritorna numero record eliminati."""
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM anagrafica_clienti").fetchone()[0]
    db.execute("DELETE FROM anagrafica_clienti")
    db.commit()
    log_operation('CLEAR_CLIENTI', 'ANAGRAFICA_CLIENTI', None,
                 f"Eliminati {count} clienti")
    return count


# =============================================================================
# v11.4: REVISIONE AUTOMATICA ORDINI CON DEPOSITO MANCANTE
# =============================================================================

def revisiona_ordini_deposito_mancante() -> Dict[str, Any]:
    """
    Revisiona ordini con anomalie DEP-A01 (deposito mancante) dopo import anagrafica.

    Cerca ordini in stato ANOMALIA/PENDING_REVIEW con anomalie DEP-A01 o LKP-A05 aperte,
    e prova a trovare il deposito in anagrafica_clienti usando P.IVA e/o MIN_ID.

    Logica di matching con score:
    - Match esatto su P.IVA + MIN_ID entrambi presenti → score 100
    - Match su MIN_ID esatto → score 90
    - Match su P.IVA esatta → score 80

    Se trova un cliente con deposito_riferimento e score >= 80, aggiorna l'ordine
    e risolve l'anomalia automaticamente.

    Returns:
        Dict con statistiche: ordini_revisionati, depositi_trovati, anomalie_risolte
    """
    db = get_db()

    result = {
        'ordini_revisionati': 0,
        'depositi_trovati': 0,
        'anomalie_risolte': 0,
        'errori': 0,
        'dettagli': []
    }

    try:
        # Cerca ordini con anomalie DEP-A01 o LKP-A05 aperte
        ordini = db.execute("""
            SELECT DISTINCT
                ot.id_testata,
                ot.partita_iva_estratta,
                ot.codice_ministeriale_estratto as min_id,
                ot.ragione_sociale_1,
                ot.numero_ordine_vendor,
                a.id_anomalia,
                a.codice_anomalia
            FROM ordini_testata ot
            JOIN anomalie a ON ot.id_testata = a.id_testata
            WHERE a.codice_anomalia IN ('DEP-A01', 'LKP-A05')
              AND a.stato IN ('APERTA', 'IN_GESTIONE')
              AND ot.stato IN ('ANOMALIA', 'PENDING_REVIEW')
              AND ot.deposito_riferimento IS NULL
            ORDER BY ot.id_testata
        """).fetchall()

        for ordine in ordini:
            result['ordini_revisionati'] += 1

            piva = (ordine['partita_iva_estratta'] or '').strip()
            min_id = (ordine['min_id'] or '').strip()

            if not piva and not min_id:
                continue

            # Cerca in anagrafica_clienti con scoring
            cliente = None
            score = 0

            # v11.4: Normalizzazione MIN_ID per matching (rimuovi zeri iniziali)
            min_id_norm = min_id.lstrip('0') if min_id else ''

            # 1. Match esatto su entrambi (P.IVA + MIN_ID normalizzato)
            if piva and min_id_norm:
                cliente = db.execute("""
                    SELECT deposito_riferimento, partita_iva, min_id, ragione_sociale_1
                    FROM anagrafica_clienti
                    WHERE partita_iva = %s AND LTRIM(min_id, '0') = %s
                      AND deposito_riferimento IS NOT NULL
                      AND deposito_riferimento != ''
                    LIMIT 1
                """, (piva, min_id_norm)).fetchone()
                if cliente:
                    score = 100

            # 2. Match su MIN_ID normalizzato
            if not cliente and min_id_norm:
                cliente = db.execute("""
                    SELECT deposito_riferimento, partita_iva, min_id, ragione_sociale_1
                    FROM anagrafica_clienti
                    WHERE LTRIM(min_id, '0') = %s
                      AND deposito_riferimento IS NOT NULL
                      AND deposito_riferimento != ''
                    LIMIT 1
                """, (min_id_norm,)).fetchone()
                if cliente:
                    score = 90

            # 3. Match su P.IVA esatta
            if not cliente and piva:
                cliente = db.execute("""
                    SELECT deposito_riferimento, partita_iva, min_id, ragione_sociale_1
                    FROM anagrafica_clienti
                    WHERE partita_iva = %s
                      AND deposito_riferimento IS NOT NULL
                      AND deposito_riferimento != ''
                    LIMIT 1
                """, (piva,)).fetchone()
                if cliente:
                    score = 80

            # Se trovato con score >= 80, aggiorna ordine e risolvi anomalia
            if cliente and score >= 80:
                deposito = cliente['deposito_riferimento']

                try:
                    # Aggiorna ordine con deposito
                    db.execute("""
                        UPDATE ordini_testata
                        SET deposito_riferimento = %s
                        WHERE id_testata = %s
                    """, (deposito, ordine['id_testata']))

                    result['depositi_trovati'] += 1

                    # Risolvi anomalia DEP-A01/LKP-A05
                    db.execute("""
                        UPDATE anomalie
                        SET stato = 'RISOLTA',
                            data_risoluzione = CURRENT_TIMESTAMP,
                            note_risoluzione = %s
                        WHERE id_testata = %s
                          AND codice_anomalia IN ('DEP-A01', 'LKP-A05')
                          AND stato IN ('APERTA', 'IN_GESTIONE')
                    """, (
                        f'[AUTO] Deposito {deposito} assegnato da anagrafica_clienti (score: {score}%)',
                        ordine['id_testata']
                    ))

                    result['anomalie_risolte'] += 1

                    # Approva supervisioni collegate
                    for table in ['supervisione_espositore', 'supervisione_listino',
                                  'supervisione_lookup', 'supervisione_aic', 'supervisione_prezzo']:
                        db.execute(f"""
                            UPDATE {table}
                            SET stato = 'APPROVED',
                                operatore = 'SISTEMA',
                                timestamp_decisione = CURRENT_TIMESTAMP,
                                note = COALESCE(note || ' - ', '') || '[AUTO] Risolto da import anagrafica'
                            WHERE id_testata = %s AND stato = 'PENDING'
                        """, (ordine['id_testata'],))

                    # Sblocca ordine se non ci sono altre anomalie bloccanti
                    anomalie_aperte = db.execute("""
                        SELECT COUNT(*) FROM anomalie
                        WHERE id_testata = %s
                          AND stato IN ('APERTA', 'IN_GESTIONE')
                          AND livello IN ('ERRORE', 'CRITICO')
                    """, (ordine['id_testata'],)).fetchone()[0]

                    if anomalie_aperte == 0:
                        db.execute("""
                            UPDATE ordini_testata
                            SET stato = 'ESTRATTO'
                            WHERE id_testata = %s AND stato IN ('ANOMALIA', 'PENDING_REVIEW')
                        """, (ordine['id_testata'],))

                    result['dettagli'].append({
                        'id_testata': ordine['id_testata'],
                        'numero_ordine': ordine['numero_ordine_vendor'],
                        'deposito_assegnato': deposito,
                        'score': score,
                        'match_type': 'PIVA+MIN_ID' if score == 100 else ('MIN_ID' if score == 90 else 'PIVA')
                    })

                except Exception as e:
                    result['errori'] += 1
                    result['ultimo_errore'] = str(e)

        db.commit()

        if result['anomalie_risolte'] > 0:
            log_operation('REVISIONE_DEPOSITI', 'ORDINI_TESTATA', None,
                         f"Revisionati {result['ordini_revisionati']} ordini, "
                         f"risolte {result['anomalie_risolte']} anomalie deposito")

    except Exception as e:
        result['error'] = str(e)

    return result
