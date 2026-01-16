# =============================================================================
# TO_EXTRACTOR v6.2 - DATABASE MANAGER (PostgreSQL)
# =============================================================================
# Migrazione da SQLite a PostgreSQL per supporto multiutenza
# Layer di compatibilita per mantenere stessa interfaccia di database.py
# =============================================================================

import os
import re
import json
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, RealDictRow

from .config import config


# =============================================================================
# CONNECTION POOL
# =============================================================================

_pool: Optional[pool.ThreadedConnectionPool] = None


def init_pool():
    """Inizializza il connection pool PostgreSQL."""
    global _pool
    if _pool is not None:
        return

    _pool = pool.ThreadedConnectionPool(
        minconn=2,
        maxconn=20,
        host=config.PG_HOST,
        port=config.PG_PORT,
        database=config.PG_DATABASE,
        user=config.PG_USER,
        password=config.PG_PASSWORD
    )
    print(f"   PostgreSQL pool: {config.PG_HOST}:{config.PG_PORT}/{config.PG_DATABASE}")


def close_pool():
    """Chiude il connection pool."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


# =============================================================================
# WRAPPER COMPATIBILITA SQLITE
# =============================================================================

class PostgreSQLConnection:
    """
    Wrapper che simula l'interfaccia sqlite3.Connection per PostgreSQL.
    Permette di usare lo stesso codice scritto per SQLite.
    """

    def __init__(self, conn):
        self._conn = conn
        self._cursor = None

    def execute(self, sql: str, params: tuple = None):
        """
        Esegue una query SQL.
        Converte automaticamente ? in %s per compatibilita SQLite.
        """
        # Converti placeholder da ? a %s
        pg_sql = self._convert_sql(sql)

        # Crea cursor con risultati come dizionari
        cursor = self._conn.cursor(cursor_factory=RealDictCursor)

        # Per INSERT, aggiungi RETURNING per ottenere lastrowid
        # Ma NON per INSERT ... ON CONFLICT (upsert)
        is_insert = pg_sql.strip().upper().startswith('INSERT')
        has_on_conflict = 'ON CONFLICT' in pg_sql.upper()
        has_returning = 'RETURNING' in pg_sql.upper()
        auto_returning = False

        if is_insert and not has_returning and not has_on_conflict:
            # Trova la tabella per determinare la colonna ID
            pg_sql = pg_sql.rstrip(';').rstrip() + ' RETURNING *'
            auto_returning = True

        try:
            if params:
                cursor.execute(pg_sql, params)
            else:
                cursor.execute(pg_sql)
        except Exception as e:
            cursor.close()
            # Rollback per evitare "transaction aborted" sui prossimi comandi
            try:
                self._conn.rollback()
            except:
                pass
            raise e

        # Per INSERT con RETURNING auto-aggiunto, recupera lastrowid e consuma il risultato
        # Se RETURNING era già presente nella query originale, NON consumare il risultato
        wrapped = PostgreSQLCursor(cursor)
        if is_insert and auto_returning:
            try:
                row = cursor.fetchone()
                if row:
                    # Prendi il primo campo (tipicamente l'ID)
                    first_key = list(row.keys())[0]
                    wrapped.lastrowid = row[first_key]
            except:
                pass

        return wrapped

    def executemany(self, sql: str, params_list: list):
        """Esegue la stessa query con parametri multipli."""
        pg_sql = self._convert_sql(sql)
        cursor = self._conn.cursor(cursor_factory=RealDictCursor)

        try:
            cursor.executemany(pg_sql, params_list)
        except Exception as e:
            cursor.close()
            try:
                self._conn.rollback()
            except:
                pass
            raise e

        return PostgreSQLCursor(cursor)

    def executescript(self, script: str):
        """Esegue uno script SQL (multiple statements)."""
        cursor = self._conn.cursor()
        try:
            cursor.execute(script)
        finally:
            cursor.close()

    def commit(self):
        """Commit della transazione."""
        self._conn.commit()

    def rollback(self):
        """Rollback della transazione."""
        self._conn.rollback()

    def cursor(self):
        """Ritorna un cursor."""
        return self._conn.cursor(cursor_factory=RealDictCursor)

    def close(self):
        """Rilascia la connessione al pool."""
        if _pool is not None:
            _pool.putconn(self._conn)

    def _convert_sql(self, sql: str) -> str:
        """
        Converte SQL da sintassi SQLite a PostgreSQL.
        - ? -> %s (placeholder)
        - datetime('now') -> CURRENT_TIMESTAMP
        - date('now') -> CURRENT_DATE
        - date('now', '-N days') -> CURRENT_DATE - INTERVAL 'N days'
        - date(column) -> column::date
        """
        # Placeholder ? -> %s
        result = sql.replace('?', '%s')

        # datetime('now') -> CURRENT_TIMESTAMP
        result = re.sub(r"datetime\s*\(\s*'now'\s*\)", 'CURRENT_TIMESTAMP', result, flags=re.IGNORECASE)

        # date('now', '-N days') -> CURRENT_DATE - INTERVAL 'N days'
        def convert_date_offset(match):
            offset = match.group(1)  # es: "-7 days"
            # Rimuovi il segno meno e converti
            if offset.startswith('-'):
                return f"CURRENT_DATE - INTERVAL '{offset[1:]}'"
            else:
                return f"CURRENT_DATE + INTERVAL '{offset}'"
        result = re.sub(r"date\s*\(\s*'now'\s*,\s*'([^']+)'\s*\)", convert_date_offset, result, flags=re.IGNORECASE)

        # date('now') -> CURRENT_DATE (senza offset)
        result = re.sub(r"date\s*\(\s*'now'\s*\)", 'CURRENT_DATE', result, flags=re.IGNORECASE)

        # date(column_name) -> column_name::date (solo per colonne, non per stringhe)
        # Attenzione: questo pattern è rischioso, lo applichiamo solo per colonne comuni
        result = re.sub(r"date\s*\(\s*(data_\w+|timestamp|created_at|updated_at|received_date)\s*\)",
                       r'\1::date', result, flags=re.IGNORECASE)

        # datetime(column_name) -> column_name (PostgreSQL timestamps sono già comparabili)
        result = re.sub(r"datetime\s*\(\s*(\w+)\s*\)", r'\1', result, flags=re.IGNORECASE)

        return result


class HybridRow(dict):
    """
    Riga che supporta sia accesso per chiave (row['col']) che per indice (row[0]).
    Necessario per compatibilità SQLite -> PostgreSQL.
    """
    def __init__(self, data):
        super().__init__(data)
        self._keys = list(data.keys())
        self._values = list(data.values())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


class PostgreSQLCursor:
    """
    Wrapper per cursor PostgreSQL che simula sqlite3.Cursor.
    Supporta accesso a risultati come dizionari (row['campo']) e per indice (row[0]).
    """

    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None
        self.rowcount = cursor.rowcount

    def fetchone(self):
        """Ritorna una riga come HybridRow (dict + index access)."""
        row = self._cursor.fetchone()
        if row is None:
            return None
        return HybridRow(row)

    def fetchall(self):
        """Ritorna tutte le righe come lista di HybridRow."""
        rows = self._cursor.fetchall()
        return [HybridRow(row) for row in rows]

    def fetchmany(self, size=None):
        """Ritorna N righe."""
        if size:
            return self._cursor.fetchmany(size)
        return self._cursor.fetchmany()

    def close(self):
        """Chiude il cursor."""
        self._cursor.close()

    def __iter__(self):
        return iter(self._cursor)


# =============================================================================
# CONNESSIONE DATABASE (Compatibile con SQLite interface)
# =============================================================================

_connection: Optional[PostgreSQLConnection] = None


def get_db() -> PostgreSQLConnection:
    """
    Ritorna connessione al database (compatibile con sqlite3.Connection).
    Usa un wrapper che simula l'interfaccia SQLite.
    """
    global _connection

    if _pool is None:
        init_pool()

    if _connection is None:
        raw_conn = _pool.getconn()
        raw_conn.autocommit = False
        _connection = PostgreSQLConnection(raw_conn)

    return _connection


@contextmanager
def get_db_cursor():
    """Context manager per cursor con commit/rollback automatico."""
    db = get_db()
    cursor = db.cursor()
    try:
        yield cursor
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        cursor.close()


def close_db():
    """Chiude la connessione e rilascia al pool."""
    global _connection
    if _connection is not None:
        try:
            _connection._conn.rollback()  # Rollback eventuali transazioni pendenti
        except:
            pass
        _connection.close()
        _connection = None


# =============================================================================
# INIZIALIZZAZIONE DATABASE
# =============================================================================

def init_database(force_reset: bool = False) -> PostgreSQLConnection:
    """Inizializza il database PostgreSQL."""
    global _connection

    init_pool()

    # Prendi connessione temporanea per verifiche
    raw_conn = _pool.getconn()
    try:
        cur = raw_conn.cursor(cursor_factory=RealDictCursor)

        # Verifica se le tabelle esistono
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'vendor'
            )
        """)
        tables_exist = cur.fetchone()['exists']

        if not tables_exist:
            print("   Schema PostgreSQL non trovato - eseguire create_schema.sql")
        else:
            print(f"   Database PostgreSQL connesso: {config.PG_DATABASE}")

        cur.close()
        raw_conn.commit()
    finally:
        _pool.putconn(raw_conn)

    # Inizializza connessione wrapper
    db = get_db()

    # Statistiche
    stats = get_stats()
    print(f"   Farmacie: {stats['farmacie']:,} | Parafarmacie: {stats['parafarmacie']:,} | Ordini: {stats['ordini']:,}")

    return db


# =============================================================================
# FUNZIONI UTILITA (stessa interfaccia di database.py)
# =============================================================================

def get_vendor_id(codice_vendor: str) -> Optional[int]:
    """Ritorna ID vendor dato il codice."""
    db = get_db()
    row = db.execute(
        "SELECT id_vendor FROM vendor WHERE codice_vendor = %s",
        (codice_vendor.upper(),)
    ).fetchone()
    return row['id_vendor'] if row else None


def get_vendor_by_id(id_vendor: int) -> Optional[Dict[str, Any]]:
    """Ritorna dati vendor dato l'ID."""
    db = get_db()
    row = db.execute("SELECT * FROM vendor WHERE id_vendor = %s", (id_vendor,)).fetchone()
    return dict(row) if row else None


def get_all_vendors() -> List[Dict[str, Any]]:
    """Ritorna tutti i vendor attivi."""
    db = get_db()
    rows = db.execute("SELECT * FROM vendor WHERE attivo = TRUE ORDER BY codice_vendor").fetchall()
    return [dict(row) for row in rows]


def get_stats() -> Dict[str, Any]:
    """Ritorna statistiche database."""
    db = get_db()

    stats = {
        'farmacie': db.execute("SELECT COUNT(*) AS cnt FROM anagrafica_farmacie").fetchone()['cnt'],
        'parafarmacie': db.execute("SELECT COUNT(*) AS cnt FROM anagrafica_parafarmacie").fetchone()['cnt'],
        'ordini': db.execute("SELECT COUNT(*) AS cnt FROM ordini_testata").fetchone()['cnt'],
        'dettagli': db.execute("SELECT COUNT(*) AS cnt FROM ordini_dettaglio").fetchone()['cnt'],
        'anomalie_aperte': db.execute("SELECT COUNT(*) AS cnt FROM anomalie WHERE stato IN ('APERTA', 'IN_GESTIONE')").fetchone()['cnt'],
        'pdf_elaborati': db.execute("SELECT COUNT(*) AS cnt FROM acquisizioni WHERE stato = 'ELABORATO'").fetchone()['cnt'],
        'pdf_oggi': db.execute("SELECT COUNT(*) AS cnt FROM acquisizioni WHERE DATE(data_upload) = CURRENT_DATE").fetchone()['cnt'],
        'righe_da_confermare': db.execute("SELECT COUNT(*) AS cnt FROM ordini_dettaglio WHERE stato_riga = 'ESTRATTO'").fetchone()['cnt'],
        'righe_in_supervisione': db.execute("SELECT COUNT(*) AS cnt FROM ordini_dettaglio WHERE stato_riga = 'IN_SUPERVISIONE'").fetchone()['cnt'],
    }

    return stats


def get_vendor_stats() -> List[Dict[str, Any]]:
    """Ritorna statistiche per vendor."""
    db = get_db()
    rows = db.execute('''
        SELECT
            v.codice_vendor AS vendor,
            COUNT(DISTINCT ot.id_testata) AS ordini,
            COUNT(od.id_dettaglio) AS righe
        FROM vendor v
        LEFT JOIN ordini_testata ot ON v.id_vendor = ot.id_vendor
        LEFT JOIN ordini_dettaglio od ON ot.id_testata = od.id_testata
        WHERE v.attivo = TRUE
        GROUP BY v.id_vendor, v.codice_vendor
        ORDER BY v.codice_vendor
    ''').fetchall()
    return [dict(row) for row in rows]


def get_operatore_id_by_username(username: str) -> Optional[int]:
    """
    Recupera l'ID operatore dal username.

    Args:
        username: Nome utente

    Returns:
        ID operatore o None se non trovato
    """
    if not username:
        return None
    db = get_db()
    row = db.execute(
        "SELECT id_operatore FROM operatori WHERE username = %s",
        (username,)
    ).fetchone()
    return row['id_operatore'] if row else None


def log_operation(tipo: str, entita: str = None, id_entita: int = None,
                  descrizione: str = None, dati: Dict = None,
                  id_operatore: int = None, operatore: str = None):
    """
    Registra operazione nel log.

    Args:
        tipo: Tipo operazione (es. UPDATE_STATO, REGISTRA_EVASIONE, etc.)
        entita: Tabella/entità coinvolta
        id_entita: ID dell'entità
        descrizione: Descrizione operazione
        dati: Dati aggiuntivi JSON
        id_operatore: ID operatore che ha eseguito l'operazione
        operatore: Username operatore (alternativa a id_operatore, verrà convertito)
    """
    # Se passato username invece di ID, recupera l'ID
    if id_operatore is None and operatore:
        id_operatore = get_operatore_id_by_username(operatore)

    db = get_db()
    db.execute('''
        INSERT INTO log_operazioni (tipo_operazione, entita, id_entita, descrizione, dati_json, id_operatore)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (tipo, entita, id_entita, descrizione, json.dumps(dati) if dati else None, id_operatore))
    db.commit()


def get_supervisione_pending() -> List[Dict[str, Any]]:
    """Ritorna supervisioni in attesa."""
    db = get_db()
    rows = db.execute("SELECT * FROM v_supervisione_pending").fetchall()
    return [dict(row) for row in rows]


def get_supervisione_by_testata(id_testata: int) -> List[Dict[str, Any]]:
    """Ritorna supervisioni per testata."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM supervisione_espositore WHERE id_testata = %s",
        (id_testata,)
    ).fetchall()
    return [dict(row) for row in rows]


def count_supervisioni_pending() -> int:
    """Conta supervisioni in attesa."""
    db = get_db()
    return db.execute("SELECT COUNT(*) AS cnt FROM supervisione_espositore WHERE stato = 'PENDING'").fetchone()['cnt']


def get_criterio_by_pattern(pattern_signature: str) -> Optional[Dict[str, Any]]:
    """Ritorna criterio per pattern signature."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM criteri_ordinari_espositore WHERE pattern_signature = %s",
        (pattern_signature,)
    ).fetchone()
    return dict(row) if row else None


def get_criteri_ordinari() -> List[Dict[str, Any]]:
    """Ritorna criteri ordinari."""
    db = get_db()
    rows = db.execute("""
        SELECT * FROM criteri_ordinari_espositore
        WHERE is_ordinario = TRUE
        ORDER BY data_promozione DESC
    """).fetchall()
    return [dict(row) for row in rows]


def get_criteri_stats() -> Dict[str, Any]:
    """Ritorna statistiche criteri."""
    db = get_db()

    stats = {
        'totale_pattern': db.execute("SELECT COUNT(*) AS cnt FROM criteri_ordinari_espositore").fetchone()['cnt'],
        'pattern_ordinari': db.execute("SELECT COUNT(*) AS cnt FROM criteri_ordinari_espositore WHERE is_ordinario = TRUE").fetchone()['cnt'],
        'pattern_in_apprendimento': db.execute("""
            SELECT COUNT(*) AS cnt FROM criteri_ordinari_espositore
            WHERE is_ordinario = FALSE AND count_approvazioni > 0
        """).fetchone()['cnt'],
        'applicazioni_automatiche_oggi': db.execute("""
            SELECT COUNT(*) AS cnt FROM log_criteri_applicati
            WHERE DATE(timestamp) = CURRENT_DATE AND applicato_automaticamente = TRUE
        """).fetchone()['cnt'],
    }

    return stats
