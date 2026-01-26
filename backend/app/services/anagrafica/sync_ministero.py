# =============================================================================
# SERV.O v8.2 - SYNC ANAGRAFICA DAL MINISTERO DELLA SALUTE
# =============================================================================
# Sincronizzazione incrementale anagrafica farmacie e parafarmacie
#
# URL Farmacie:    https://www.dati.salute.gov.it/sites/default/files/opendata/FRM_FARMA_5_YYYYMMDD.json
# URL Parafarmacie: https://www.dati.salute.gov.it/sites/default/files/opendata/FRM_PFARMA_7_YYYYMMDD.json
#
# La data nel nome file corrisponde al giorno di pubblicazione.
# =============================================================================

import json
import requests
import subprocess
import shutil
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field
from enum import Enum

from ...database_pg import get_db, log_operation


# =============================================================================
# CURL FALLBACK (per ambienti con SSL issues come Codespaces)
# =============================================================================

def _curl_available() -> bool:
    """Verifica se curl è disponibile."""
    return shutil.which('curl') is not None


def _curl_head(url: str, timeout: int = 10) -> int:
    """HEAD request via curl. Ritorna status code o 0 se errore."""
    try:
        result = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', '-I', '--max-time', str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 5
        )
        return int(result.stdout.strip()) if result.returncode == 0 else 0
    except Exception:
        return 0


def _curl_download(url: str, timeout: int = 300) -> Tuple[Optional[bytes], str, str]:
    """Download via curl. Ritorna (content, etag, last_modified) o (None, '', '') se errore."""
    try:
        result = subprocess.run(
            ['curl', '-s', '-D', '-', '--max-time', str(timeout), url],
            capture_output=True, timeout=timeout + 30
        )
        if result.returncode != 0:
            return None, '', ''

        # Separa headers da content
        output = result.stdout
        header_end = output.find(b'\r\n\r\n')
        if header_end == -1:
            header_end = output.find(b'\n\n')

        if header_end == -1:
            return output, '', ''

        headers_raw = output[:header_end].decode('utf-8', errors='ignore')
        content = output[header_end + 4:]

        # Estrai ETag e Last-Modified
        etag = ''
        last_modified = ''
        for line in headers_raw.split('\n'):
            line = line.strip()
            if line.lower().startswith('etag:'):
                etag = line.split(':', 1)[1].strip()
            elif line.lower().startswith('last-modified:'):
                last_modified = line.split(':', 1)[1].strip()

        return content, etag, last_modified
    except Exception:
        return None, '', ''


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

BASE_URL = "https://www.dati.salute.gov.it/sites/default/files/opendata"

class TipoAnagrafica(Enum):
    FARMACIE = "farmacie"
    PARAFARMACIE = "parafarmacie"

# Pattern file per tipo
FILE_PATTERNS = {
    TipoAnagrafica.FARMACIE: "FRM_FARMA_5_{date}.json",
    TipoAnagrafica.PARAFARMACIE: "FRM_PFARMA_7_{date}.json"
}

# Chiavi stato sync
SYNC_STATE_KEYS = {
    TipoAnagrafica.FARMACIE: "farmacie_sync",
    TipoAnagrafica.PARAFARMACIE: "parafarmacie_sync"
}


@dataclass
class SyncResult:
    """Risultato sincronizzazione."""
    success: bool
    message: str = ""
    tipo: str = ""
    downloaded: bool = False
    nuove: int = 0
    aggiornate: int = 0
    subentri: int = 0  # Cambio P.IVA stesso codice
    chiuse: int = 0
    invariate: int = 0
    errori: int = 0
    totale_json: int = 0
    totale_db: int = 0
    etag: str = None
    url: str = None
    durata_secondi: float = 0


@dataclass
class SyncAllResult:
    """Risultato sincronizzazione completa (farmacie + parafarmacie)."""
    success: bool
    message: str
    farmacie: SyncResult = None
    parafarmacie: SyncResult = None
    durata_totale_secondi: float = 0


# =============================================================================
# GESTIONE STATO SYNC (ETag, Last-Modified)
# =============================================================================

def _ensure_sync_state_table():
    """Crea tabella sync_state se non esiste (auto-migrazione)."""
    db = get_db()
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS sync_state (
                key VARCHAR(50) PRIMARY KEY,
                etag VARCHAR(100),
                last_modified VARCHAR(100),
                last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_url TEXT,
                records_count INTEGER DEFAULT 0,
                extra_data JSONB DEFAULT '{}'::jsonb
            )
        """)
        db.commit()
    except Exception:
        pass  # Tabella già esiste o errore non critico


def get_sync_state(tipo: TipoAnagrafica) -> Dict[str, Any]:
    """Recupera stato ultima sincronizzazione per tipo."""
    db = get_db()
    key = SYNC_STATE_KEYS[tipo]

    try:
        row = db.execute("""
            SELECT etag, last_modified, last_sync, last_url, records_count
            FROM sync_state
            WHERE key = %s
        """, (key,)).fetchone()

        if row:
            return {
                'etag': row['etag'],
                'last_modified': row['last_modified'],
                'last_sync': row['last_sync'],
                'last_url': row['last_url'],
                'records_count': row['records_count']
            }
    except Exception as e:
        # Se tabella non esiste, creala
        if 'sync_state' in str(e).lower() and ('not exist' in str(e).lower() or 'does not exist' in str(e).lower()):
            _ensure_sync_state_table()

    return {
        'etag': None,
        'last_modified': None,
        'last_sync': None,
        'last_url': None,
        'records_count': 0
    }


def save_sync_state(tipo: TipoAnagrafica, etag: str, last_modified: str, url: str, records_count: int):
    """Salva stato sincronizzazione."""
    _ensure_sync_state_table()  # Auto-crea tabella se non esiste

    db = get_db()
    key = SYNC_STATE_KEYS[tipo]

    db.execute("""
        INSERT INTO sync_state (key, etag, last_modified, last_sync, last_url, records_count)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s, %s)
        ON CONFLICT (key) DO UPDATE SET
            etag = EXCLUDED.etag,
            last_modified = EXCLUDED.last_modified,
            last_sync = EXCLUDED.last_sync,
            last_url = EXCLUDED.last_url,
            records_count = EXCLUDED.records_count
    """, (key, etag, last_modified, url, records_count))
    db.commit()


# =============================================================================
# COSTRUZIONE URL
# =============================================================================

def get_url_for_date(tipo: TipoAnagrafica, target_date: date = None) -> str:
    """
    Costruisce URL per la data specificata.
    Default: data odierna.
    """
    if target_date is None:
        target_date = date.today()

    date_str = target_date.strftime("%Y%m%d")
    filename = FILE_PATTERNS[tipo].format(date=date_str)
    return f"{BASE_URL}/{filename}"


def find_latest_available_url(tipo: TipoAnagrafica, max_days_back: int = 7) -> Tuple[str, date]:
    """
    Trova l'URL più recente disponibile.
    Prova da oggi indietro fino a max_days_back giorni.
    Usa curl come fallback se requests fallisce (SSL issues).
    """
    use_curl = _curl_available()

    for days_ago in range(max_days_back + 1):
        target_date = date.today() - timedelta(days=days_ago)
        url = get_url_for_date(tipo, target_date)

        # Prima prova con requests
        try:
            response = requests.head(url, timeout=10)
            if response.status_code == 200:
                return url, target_date
        except requests.RequestException:
            # Fallback a curl se disponibile
            if use_curl:
                status = _curl_head(url, timeout=10)
                if status == 200:
                    return url, target_date
            continue

    raise ValueError(f"Nessun file {tipo.value} disponibile negli ultimi {max_days_back} giorni")


# =============================================================================
# DOWNLOAD CONDIZIONALE
# =============================================================================

def download_if_modified(url: str, saved_etag: str = None) -> Tuple[Optional[bytes], str, str, bool]:
    """
    Scarica il file solo se modificato (HTTP 304 support).
    Usa curl come fallback se requests fallisce (SSL issues).

    Returns:
        (content, new_etag, last_modified, was_downloaded)
    """
    headers = {}
    if saved_etag:
        headers['If-None-Match'] = saved_etag

    # Prima prova con requests
    try:
        response = requests.get(url, headers=headers, timeout=300)

        new_etag = response.headers.get('ETag', '')
        last_modified = response.headers.get('Last-Modified', '')

        if response.status_code == 304:
            return None, new_etag, last_modified, False

        response.raise_for_status()
        return response.content, new_etag, last_modified, True

    except requests.RequestException as e:
        # Fallback a curl se disponibile
        if _curl_available():
            content, new_etag, last_modified = _curl_download(url, timeout=300)
            if content is not None:
                return content, new_etag, last_modified, True
        # Se anche curl fallisce, rilancia l'eccezione originale
        raise e


# =============================================================================
# PARSING COMUNE
# =============================================================================

def parse_date(date_str: str) -> Optional[date]:
    """Converte data formato DD/MM/YYYY in date object."""
    if not date_str or date_str.strip() in ('-', '', 'NULL'):
        return None
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def parse_coordinate(coord_str: str) -> Optional[float]:
    """Converte coordinata (formato italiano con virgola) in float."""
    if not coord_str or coord_str.strip() in ('-', '', 'NULL'):
        return None
    try:
        return float(coord_str.strip().replace(',', '.'))
    except (ValueError, TypeError):
        return None


def normalize_piva(piva: str) -> str:
    """Normalizza P.IVA rimuovendo spazi."""
    if not piva:
        return ''
    return piva.strip().replace(' ', '')


# =============================================================================
# SYNC FARMACIE
# =============================================================================

def parse_farmacie_json(content: bytes) -> list:
    """Parsa JSON farmacie e filtra solo record attivi."""
    # Decodifica esplicita UTF-8 con gestione BOM
    text = content.decode('utf-8-sig')
    data = json.loads(text)
    return [r for r in data if r.get('data_fine_validita', '').strip() == '-']


def build_min_id(record: dict) -> str:
    """MIN_ID = cod_farmacia con padding a 9 cifre."""
    cod_farmacia = record.get('cod_farmacia', '0')
    return str(cod_farmacia).strip().zfill(9)


def sync_farmacie(
    force_download: bool = False,
    target_date: date = None,
    dry_run: bool = False
) -> SyncResult:
    """Sincronizza anagrafica farmacie dal Ministero."""
    start_time = datetime.now()
    tipo = TipoAnagrafica.FARMACIE

    # Trova URL
    try:
        if target_date:
            url = get_url_for_date(tipo, target_date)
            response = requests.head(url, timeout=10)
            if response.status_code != 200:
                return SyncResult(
                    success=False, tipo=tipo.value,
                    message=f"File non trovato per data {target_date}"
                )
        else:
            url, target_date = find_latest_available_url(tipo)
    except Exception as e:
        return SyncResult(success=False, tipo=tipo.value, message=f"Errore ricerca URL: {e}")

    # Recupera stato precedente
    state = get_sync_state(tipo)
    saved_etag = None if force_download else state.get('etag')

    # Download condizionale
    try:
        content, new_etag, last_modified, was_downloaded = download_if_modified(url, saved_etag)
    except requests.RequestException as e:
        return SyncResult(success=False, tipo=tipo.value, message=f"Errore download: {e}")

    if not was_downloaded:
        return SyncResult(
            success=True, tipo=tipo.value,
            message="File non modificato (304 Not Modified)",
            downloaded=False, etag=new_etag, url=url,
            durata_secondi=(datetime.now() - start_time).total_seconds(),
            totale_db=state.get('records_count', 0)
        )

    # Parsing
    try:
        records = parse_farmacie_json(content)
    except json.JSONDecodeError as e:
        return SyncResult(success=False, tipo=tipo.value, message=f"Errore parsing JSON: {e}")

    result = SyncResult(
        success=True, tipo=tipo.value, downloaded=True,
        totale_json=len(records), etag=new_etag, url=url
    )

    if dry_run:
        result.message = f"DRY RUN: {len(records)} farmacie attive nel JSON"
        result.durata_secondi = (datetime.now() - start_time).total_seconds()
        return result

    # Sincronizzazione DB
    db = get_db()

    # Mappa esistenti
    existing = {}
    rows = db.execute("""
        SELECT min_id, partita_iva, ragione_sociale, indirizzo, cap, citta, provincia
        FROM anagrafica_farmacie WHERE attiva = TRUE
    """).fetchall()
    for row in rows:
        existing[row['min_id']] = {
            'partita_iva': normalize_piva(row['partita_iva'] or ''),
            'ragione_sociale': (row['ragione_sociale'] or '').strip(),
            'indirizzo': (row['indirizzo'] or '').strip(),
            'cap': (row['cap'] or '').strip(),
            'citta': (row['citta'] or '').strip(),
            'provincia': (row['provincia'] or '').strip()
        }

    json_ids = set()
    fonte = f"SYNC_{target_date.strftime('%Y%m%d')}"

    for record in records:
        try:
            min_id = build_min_id(record)
            if min_id == '000000000':
                continue

            json_ids.add(min_id)

            piva = normalize_piva(record.get('p_iva', ''))
            ragione_sociale = (record.get('descrizione_farmacia', '') or '').strip()[:100]
            indirizzo = (record.get('indirizzo', '') or '').strip()[:100]
            cap = (record.get('cap', '') or '').strip()[:5]
            citta = (record.get('comune', '') or '').strip()
            provincia = (record.get('sigla_provincia', '') or '').strip()[:2]
            regione = (record.get('regione', '') or '').strip()
            cod_farmacia_asl = (record.get('cod_farmacia_asl', '') or '').strip()
            data_inizio = parse_date(record.get('data_inizio_validita', ''))

            if min_id in existing:
                old = existing[min_id]

                # Subentro (cambio P.IVA)
                if piva and old['partita_iva'] and piva != old['partita_iva']:
                    result.subentri += 1
                    log_operation('SYNC_SUBENTRO', 'ANAGRAFICA_FARMACIE', None,
                                  f"Subentro MIN_ID {min_id}: {old['partita_iva']} -> {piva}")

                changed = (
                    piva != old['partita_iva'] or
                    ragione_sociale != old['ragione_sociale'] or
                    indirizzo != old['indirizzo'] or
                    cap != old['cap'] or
                    citta != old['citta'] or
                    provincia != old['provincia']
                )

                if changed:
                    db.execute("""
                        UPDATE anagrafica_farmacie SET
                            partita_iva = %s, ragione_sociale = %s, indirizzo = %s,
                            cap = %s, citta = %s, provincia = %s, regione = %s,
                            codice_farmacia_asl = %s, data_inizio_validita = %s,
                            fonte_dati = %s, data_import = CURRENT_TIMESTAMP
                        WHERE min_id = %s
                    """, (piva, ragione_sociale, indirizzo, cap, citta, provincia,
                          regione, cod_farmacia_asl, data_inizio, fonte, min_id))
                    result.aggiornate += 1
                else:
                    result.invariate += 1
            else:
                db.execute("""
                    INSERT INTO anagrafica_farmacie
                    (min_id, partita_iva, ragione_sociale, indirizzo, cap, citta,
                     provincia, regione, codice_farmacia_asl, data_inizio_validita,
                     attiva, fonte_dati, data_import)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s, CURRENT_TIMESTAMP)
                """, (min_id, piva, ragione_sociale, indirizzo, cap, citta,
                      provincia, regione, cod_farmacia_asl, data_inizio, fonte))
                result.nuove += 1

        except Exception as e:
            result.errori += 1

    # Marca chiuse
    for min_id in existing.keys():
        if min_id not in json_ids:
            db.execute("""
                UPDATE anagrafica_farmacie
                SET attiva = FALSE, data_fine_validita = CURRENT_DATE, fonte_dati = %s
                WHERE min_id = %s AND attiva = TRUE
            """, (f"CHIUSA_{fonte}", min_id))
            result.chiuse += 1

    db.commit()
    save_sync_state(tipo, new_etag, last_modified, url, len(records))

    result.totale_db = db.execute(
        "SELECT COUNT(*) FROM anagrafica_farmacie WHERE attiva = TRUE"
    ).fetchone()[0]

    result.durata_secondi = (datetime.now() - start_time).total_seconds()
    result.message = (
        f"Farmacie: {result.nuove} nuove, {result.aggiornate} aggiornate, "
        f"{result.subentri} subentri, {result.chiuse} chiuse"
    )

    log_operation('SYNC_FARMACIE', 'ANAGRAFICA_FARMACIE', None, result.message)
    return result


# =============================================================================
# SYNC PARAFARMACIE
# =============================================================================

def parse_parafarmacie_json(content: bytes) -> list:
    """Parsa JSON parafarmacie e filtra solo record attivi."""
    # Decodifica esplicita UTF-8 con gestione BOM
    text = content.decode('utf-8-sig')
    data = json.loads(text)
    return [r for r in data if r.get('data_fine_validita', '').strip() == '-']


def sync_parafarmacie(
    force_download: bool = False,
    target_date: date = None,
    dry_run: bool = False
) -> SyncResult:
    """Sincronizza anagrafica parafarmacie dal Ministero."""
    start_time = datetime.now()
    tipo = TipoAnagrafica.PARAFARMACIE

    # Trova URL
    try:
        if target_date:
            url = get_url_for_date(tipo, target_date)
            response = requests.head(url, timeout=10)
            if response.status_code != 200:
                return SyncResult(
                    success=False, tipo=tipo.value,
                    message=f"File non trovato per data {target_date}"
                )
        else:
            url, target_date = find_latest_available_url(tipo)
    except Exception as e:
        return SyncResult(success=False, tipo=tipo.value, message=f"Errore ricerca URL: {e}")

    # Recupera stato precedente
    state = get_sync_state(tipo)
    saved_etag = None if force_download else state.get('etag')

    # Download condizionale
    try:
        content, new_etag, last_modified, was_downloaded = download_if_modified(url, saved_etag)
    except requests.RequestException as e:
        return SyncResult(success=False, tipo=tipo.value, message=f"Errore download: {e}")

    if not was_downloaded:
        return SyncResult(
            success=True, tipo=tipo.value,
            message="File non modificato (304 Not Modified)",
            downloaded=False, etag=new_etag, url=url,
            durata_secondi=(datetime.now() - start_time).total_seconds(),
            totale_db=state.get('records_count', 0)
        )

    # Parsing
    try:
        records = parse_parafarmacie_json(content)
    except json.JSONDecodeError as e:
        return SyncResult(success=False, tipo=tipo.value, message=f"Errore parsing JSON: {e}")

    result = SyncResult(
        success=True, tipo=tipo.value, downloaded=True,
        totale_json=len(records), etag=new_etag, url=url
    )

    if dry_run:
        result.message = f"DRY RUN: {len(records)} parafarmacie attive nel JSON"
        result.durata_secondi = (datetime.now() - start_time).total_seconds()
        return result

    # Sincronizzazione DB
    db = get_db()

    # Mappa esistenti
    existing = {}
    rows = db.execute("""
        SELECT codice_sito, partita_iva, sito_logistico, indirizzo, cap, citta, provincia
        FROM anagrafica_parafarmacie WHERE attiva = TRUE
    """).fetchall()
    for row in rows:
        existing[row['codice_sito']] = {
            'partita_iva': normalize_piva(row['partita_iva'] or ''),
            'sito_logistico': (row['sito_logistico'] or '').strip(),
            'indirizzo': (row['indirizzo'] or '').strip(),
            'cap': (row['cap'] or '').strip(),
            'citta': (row['citta'] or '').strip(),
            'provincia': (row['provincia'] or '').strip()
        }

    json_ids = set()
    fonte = f"SYNC_{target_date.strftime('%Y%m%d')}"

    for record in records:
        try:
            codice_sito = (record.get('codice_identificativo_sito', '') or '').strip()
            if not codice_sito:
                continue

            json_ids.add(codice_sito)

            piva = normalize_piva(record.get('partita_iva', ''))
            sito_logistico = (record.get('sito_logistico', '') or '').strip()[:100]
            indirizzo = (record.get('indirizzo', '') or '').strip()[:100]
            cap = (record.get('cap', '') or '').strip()[:5]
            citta = (record.get('comune', '') or '').strip()
            provincia = (record.get('sigla_provincia', '') or '').strip()[:2]
            regione = (record.get('regione', '') or '').strip()
            codice_comune = (record.get('codice_comune', '') or '').strip()
            codice_provincia = (record.get('codice_provincia', '') or '').strip()
            codice_regione = (record.get('codice_regione', '') or '').strip()
            data_inizio = parse_date(record.get('data_inizio_validita', ''))
            latitudine = parse_coordinate(record.get('latitudine', ''))
            longitudine = parse_coordinate(record.get('longitudine', ''))

            if codice_sito in existing:
                old = existing[codice_sito]

                # Subentro (cambio P.IVA)
                if piva and old['partita_iva'] and piva != old['partita_iva']:
                    result.subentri += 1
                    log_operation('SYNC_SUBENTRO', 'ANAGRAFICA_PARAFARMACIE', None,
                                  f"Subentro {codice_sito}: {old['partita_iva']} -> {piva}")

                changed = (
                    piva != old['partita_iva'] or
                    sito_logistico != old['sito_logistico'] or
                    indirizzo != old['indirizzo'] or
                    cap != old['cap'] or
                    citta != old['citta'] or
                    provincia != old['provincia']
                )

                if changed:
                    db.execute("""
                        UPDATE anagrafica_parafarmacie SET
                            partita_iva = %s, sito_logistico = %s, indirizzo = %s,
                            cap = %s, citta = %s, provincia = %s, regione = %s,
                            codice_comune = %s, codice_provincia = %s, codice_regione = %s,
                            data_inizio_validita = %s, latitudine = %s, longitudine = %s,
                            fonte_dati = %s, data_import = CURRENT_TIMESTAMP
                        WHERE codice_sito = %s
                    """, (piva, sito_logistico, indirizzo, cap, citta, provincia, regione,
                          codice_comune, codice_provincia, codice_regione, data_inizio,
                          latitudine, longitudine, fonte, codice_sito))
                    result.aggiornate += 1
                else:
                    result.invariate += 1
            else:
                db.execute("""
                    INSERT INTO anagrafica_parafarmacie
                    (codice_sito, partita_iva, sito_logistico, indirizzo, cap, citta,
                     provincia, regione, codice_comune, codice_provincia, codice_regione,
                     data_inizio_validita, latitudine, longitudine, attiva, fonte_dati, data_import)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s, CURRENT_TIMESTAMP)
                """, (codice_sito, piva, sito_logistico, indirizzo, cap, citta, provincia,
                      regione, codice_comune, codice_provincia, codice_regione, data_inizio,
                      latitudine, longitudine, fonte))
                result.nuove += 1

        except Exception as e:
            result.errori += 1

    # Marca chiuse
    for codice_sito in existing.keys():
        if codice_sito not in json_ids:
            db.execute("""
                UPDATE anagrafica_parafarmacie
                SET attiva = FALSE, data_fine_validita = CURRENT_DATE, fonte_dati = %s
                WHERE codice_sito = %s AND attiva = TRUE
            """, (f"CHIUSA_{fonte}", codice_sito))
            result.chiuse += 1

    db.commit()
    save_sync_state(tipo, new_etag, last_modified, url, len(records))

    result.totale_db = db.execute(
        "SELECT COUNT(*) FROM anagrafica_parafarmacie WHERE attiva = TRUE"
    ).fetchone()[0]

    result.durata_secondi = (datetime.now() - start_time).total_seconds()
    result.message = (
        f"Parafarmacie: {result.nuove} nuove, {result.aggiornate} aggiornate, "
        f"{result.subentri} subentri, {result.chiuse} chiuse"
    )

    log_operation('SYNC_PARAFARMACIE', 'ANAGRAFICA_PARAFARMACIE', None, result.message)
    return result


# =============================================================================
# SYNC COMPLETA (ENTRAMBE)
# =============================================================================

def sync_all(
    force_download: bool = False,
    target_date: date = None,
    dry_run: bool = False
) -> SyncAllResult:
    """
    Sincronizza sia farmacie che parafarmacie.

    Args:
        force_download: Ignora ETag e scarica sempre
        target_date: Data specifica (default: oggi)
        dry_run: Simula senza modificare il DB

    Returns:
        SyncAllResult con risultati per entrambe
    """
    start_time = datetime.now()

    result_farmacie = sync_farmacie(force_download, target_date, dry_run)
    result_parafarmacie = sync_parafarmacie(force_download, target_date, dry_run)

    durata_totale = (datetime.now() - start_time).total_seconds()

    success = result_farmacie.success and result_parafarmacie.success

    return SyncAllResult(
        success=success,
        message=f"Sync completata: {result_farmacie.message}; {result_parafarmacie.message}",
        farmacie=result_farmacie,
        parafarmacie=result_parafarmacie,
        durata_totale_secondi=durata_totale
    )


# =============================================================================
# UTILITIES
# =============================================================================

def check_sync_status(tipo: TipoAnagrafica = None) -> Dict[str, Any]:
    """
    Verifica stato sincronizzazione.

    Args:
        tipo: Tipo specifico o None per entrambi
    """
    def get_status_for_type(t: TipoAnagrafica) -> Dict[str, Any]:
        state = get_sync_state(t)
        try:
            url, available_date = find_latest_available_url(t)
            file_available = True
        except ValueError:
            url = None
            available_date = None
            file_available = False

        needs_update = file_available and state.get('last_url') != url

        return {
            'tipo': t.value,
            'last_sync': state.get('last_sync'),
            'last_url': state.get('last_url'),
            'last_etag': state.get('etag'),
            'records_count': state.get('records_count', 0),
            'file_available': file_available,
            'available_url': url,
            'available_date': available_date.isoformat() if available_date else None,
            'needs_update': needs_update
        }

    if tipo:
        return get_status_for_type(tipo)

    return {
        'farmacie': get_status_for_type(TipoAnagrafica.FARMACIE),
        'parafarmacie': get_status_for_type(TipoAnagrafica.PARAFARMACIE)
    }


def get_subentri_recenti(days: int = 30) -> List[Dict]:
    """Recupera subentri (cambi P.IVA) degli ultimi N giorni."""
    db = get_db()

    rows = db.execute("""
        SELECT timestamp, tabella, dettagli
        FROM log_operazioni
        WHERE operazione = 'SYNC_SUBENTRO'
        AND timestamp > CURRENT_TIMESTAMP - INTERVAL '%s days'
        ORDER BY timestamp DESC
    """, (days,)).fetchall()

    return [dict(row) for row in rows]
