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

        # Mappa colonne CSV -> DB
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
            'categoria': ['AGCATE', 'categoria'],
            'codice_farmacia': ['AGCFAR', 'codice_farmacia'],
            'codice_stato': ['AGCSTA', 'codice_stato'],
            'codice_pagamento': ['AGCPAG', 'codice_pagamento'],
            'id_tipo': ['AGTIDD', 'id_tipo'],
            'riferimento': ['AGDRIF', 'riferimento'],
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
                    # Update
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
                            categoria = ?,
                            codice_farmacia = ?,
                            codice_stato = ?,
                            codice_pagamento = ?,
                            id_tipo = ?,
                            riferimento = ?,
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
                        get_col(row, 'categoria')[:10] or None,
                        get_col(row, 'codice_farmacia')[:20] or None,
                        get_col(row, 'codice_stato')[:10] or None,
                        get_col(row, 'codice_pagamento')[:10] or None,
                        get_col(row, 'id_tipo')[:20] or None,
                        get_col(row, 'riferimento')[:10] or None,
                        codice
                    ))
                    result['aggiornati'] += 1
                else:
                    # Insert
                    db.execute("""
                        INSERT INTO anagrafica_clienti
                        (codice_cliente, ragione_sociale_1, ragione_sociale_2, indirizzo, cap,
                         localita, provincia, partita_iva, email, categoria,
                         codice_farmacia, codice_stato, codice_pagamento, id_tipo, riferimento)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        get_col(row, 'categoria')[:10] or None,
                        get_col(row, 'codice_farmacia')[:20] or None,
                        get_col(row, 'codice_stato')[:10] or None,
                        get_col(row, 'codice_pagamento')[:10] or None,
                        get_col(row, 'id_tipo')[:20] or None,
                        get_col(row, 'riferimento')[:10] or None,
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
