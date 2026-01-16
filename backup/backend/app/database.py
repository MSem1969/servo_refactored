# =============================================================================
# TO_EXTRACTOR v6.1 - DATABASE MANAGER
# =============================================================================
# Schema: 15 tabelle + 5 viste
# Aggiornamento: Gestione conferma righe e workflow supervisione
# =============================================================================

import sqlite3
import os
import json
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from .config import config


# =============================================================================
# CONNESSIONE DATABASE
# =============================================================================

_connection: Optional[sqlite3.Connection] = None


def get_db() -> sqlite3.Connection:
    """Ritorna connessione al database (singleton)."""
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(
            config.DB_PATH,
            check_same_thread=False
        )
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA foreign_keys = ON")
        _connection.execute("PRAGMA journal_mode = WAL")
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
    """Chiude connessione database."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


# =============================================================================
# SCHEMA DDL v6.1
# =============================================================================

def get_ddl_script() -> str:
    """Ritorna lo script DDL completo per creare il database."""
    return '''
-- TO_EXTRACTOR DDL SQLite v6.1
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS OPERATORI (
    id_operatore INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT DEFAULT '',
    nome TEXT,
    cognome TEXT,
    email TEXT UNIQUE,
    ruolo TEXT DEFAULT 'operatore' CHECK (ruolo IN ('admin','operatore','supervisore','readonly')),
    attivo INTEGER DEFAULT 1,
    data_creazione TEXT DEFAULT (datetime('now')),
    created_by_operatore INTEGER REFERENCES OPERATORI(id_operatore),
    updated_at TEXT,
    last_login_at TEXT,
    disabled_at TEXT,
    disabled_by_operatore INTEGER REFERENCES OPERATORI(id_operatore),
    disable_reason TEXT
);
INSERT OR IGNORE INTO OPERATORI (id_operatore, username, nome, ruolo)
VALUES (1, 'SYSTEM', 'Sistema', 'admin');

CREATE TABLE IF NOT EXISTS USER_SESSIONS (
    id_session INTEGER PRIMARY KEY AUTOINCREMENT,
    id_operatore INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT DEFAULT (datetime('now')) NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    revoked_by_operatore INTEGER,
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (id_operatore) REFERENCES OPERATORI(id_operatore),
    FOREIGN KEY (revoked_by_operatore) REFERENCES OPERATORI(id_operatore)
);
CREATE INDEX IF NOT EXISTS idx_sessions_operatore ON USER_SESSIONS(id_operatore);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON USER_SESSIONS(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON USER_SESSIONS(expires_at);

CREATE TABLE IF NOT EXISTS VENDOR (
    id_vendor INTEGER PRIMARY KEY AUTOINCREMENT,
    codice_vendor TEXT NOT NULL UNIQUE,
    ragione_sociale TEXT,
    partita_iva_vendor TEXT,
    linea_offerta TEXT,
    note_estrazione TEXT,
    attivo INTEGER DEFAULT 1,
    data_inserimento TEXT DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO VENDOR (codice_vendor, ragione_sociale, partita_iva_vendor, note_estrazione) VALUES
    ('ANGELINI', 'Angelini Pharma S.p.A.', NULL, 'ID MIN diretto, sconti a cascata, espositori v3.1'),
    ('BAYER', 'Bayer S.p.A.', NULL, 'Formato SAP'),
    ('CODIFI', 'Codifi S.r.l.', NULL, 'Multi-cliente'),
    ('CHIESI', 'Chiesi Farmaceutici S.p.A.', '02944970348', 'Escludere P.IVA vendor'),
    ('MENARINI', 'Menarini S.r.l.', NULL, 'Parent/Child'),
    ('OPELLA', 'Opella Healthcare Italy S.r.l.', NULL, 'AIC 7-9 cifre'),
    ('DOC_GENERICI', 'DOC Generici S.r.l.', NULL, 'Transfer Order via Grossisti, doppio indirizzo, NO prezzi'),
    ('GENERIC', 'Vendor Generico', NULL, 'Estrattore generico per vendor non riconosciuti');

CREATE TABLE IF NOT EXISTS ANAGRAFICA_FARMACIE (
    id_farmacia INTEGER PRIMARY KEY AUTOINCREMENT,
    min_id TEXT NOT NULL UNIQUE,
    codice_farmacia_asl TEXT,
    partita_iva TEXT,
    ragione_sociale TEXT,
    indirizzo TEXT,
    cap TEXT,
    citta TEXT,
    frazione TEXT,
    provincia TEXT,
    regione TEXT,
    data_inizio_validita TEXT,
    data_fine_validita TEXT,
    attiva INTEGER DEFAULT 1,
    fonte_dati TEXT,
    data_import TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_farmacie_min_id ON ANAGRAFICA_FARMACIE(min_id);
CREATE INDEX IF NOT EXISTS idx_farmacie_piva ON ANAGRAFICA_FARMACIE(partita_iva);

CREATE TABLE IF NOT EXISTS ANAGRAFICA_PARAFARMACIE (
    id_parafarmacia INTEGER PRIMARY KEY AUTOINCREMENT,
    codice_sito TEXT NOT NULL UNIQUE,
    sito_logistico TEXT,
    partita_iva TEXT,
    indirizzo TEXT,
    cap TEXT,
    codice_comune TEXT,
    citta TEXT,
    codice_provincia TEXT,
    provincia TEXT,
    codice_regione TEXT,
    regione TEXT,
    data_inizio_validita TEXT,
    data_fine_validita TEXT,
    latitudine TEXT,
    longitudine TEXT,
    attiva INTEGER DEFAULT 1,
    fonte_dati TEXT,
    data_import TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_parafarm_codice ON ANAGRAFICA_PARAFARMACIE(codice_sito);
CREATE INDEX IF NOT EXISTS idx_parafarm_piva ON ANAGRAFICA_PARAFARMACIE(partita_iva);

CREATE TABLE IF NOT EXISTS ACQUISIZIONI (
    id_acquisizione INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_file_originale TEXT NOT NULL,
    nome_file_storage TEXT NOT NULL,
    percorso_storage TEXT,
    hash_file TEXT,
    hash_contenuto_pdf TEXT,
    dimensione_bytes INTEGER,
    mime_type TEXT DEFAULT 'application/pdf',
    id_vendor INTEGER REFERENCES VENDOR(id_vendor),
    vendor_rilevato_auto INTEGER DEFAULT 1,
    stato TEXT DEFAULT 'CARICATO' CHECK (stato IN ('CARICATO','IN_ELABORAZIONE','ELABORATO','ERRORE','SCARTATO')),
    num_ordini_estratti INTEGER DEFAULT 0,
    messaggio_errore TEXT,
    is_duplicato INTEGER DEFAULT 0,
    id_acquisizione_originale INTEGER REFERENCES ACQUISIZIONI(id_acquisizione),
    id_operatore_upload INTEGER DEFAULT 1,
    data_upload TEXT DEFAULT (datetime('now')),
    data_elaborazione TEXT
);
CREATE INDEX IF NOT EXISTS idx_acquisizioni_hash ON ACQUISIZIONI(hash_file);
CREATE INDEX IF NOT EXISTS idx_acquisizioni_stato ON ACQUISIZIONI(stato);

CREATE TABLE IF NOT EXISTS ORDINI_TESTATA (
    id_testata INTEGER PRIMARY KEY AUTOINCREMENT,
    id_acquisizione INTEGER NOT NULL REFERENCES ACQUISIZIONI(id_acquisizione),
    id_vendor INTEGER NOT NULL REFERENCES VENDOR(id_vendor),
    numero_ordine_vendor TEXT NOT NULL,
    data_ordine TEXT,
    data_consegna TEXT,
    partita_iva_estratta TEXT,
    codice_ministeriale_estratto TEXT,
    ragione_sociale_1 TEXT,
    ragione_sociale_2 TEXT,
    indirizzo TEXT,
    cap TEXT,
    citta TEXT,
    provincia TEXT,
    nome_agente TEXT,
    gg_dilazione_1 INTEGER DEFAULT 90,
    gg_dilazione_2 INTEGER,
    gg_dilazione_3 INTEGER,
    note_ordine TEXT,
    note_ddt TEXT,
    id_farmacia_lookup INTEGER REFERENCES ANAGRAFICA_FARMACIE(id_farmacia),
    id_parafarmacia_lookup INTEGER REFERENCES ANAGRAFICA_PARAFARMACIE(id_parafarmacia),
    lookup_method TEXT,
    lookup_source TEXT DEFAULT 'FARMACIA',
    lookup_score INTEGER,
    chiave_univoca_ordine TEXT UNIQUE,
    is_ordine_duplicato INTEGER DEFAULT 0,
    id_testata_originale INTEGER REFERENCES ORDINI_TESTATA(id_testata),
    stato TEXT DEFAULT 'ESTRATTO',
    data_estrazione TEXT DEFAULT (datetime('now')),
    data_validazione TEXT,
    validato_da TEXT,
    righe_totali INTEGER DEFAULT 0,
    righe_confermate INTEGER DEFAULT 0,
    righe_in_supervisione INTEGER DEFAULT 0,
    data_ultimo_aggiornamento TEXT
);
CREATE INDEX IF NOT EXISTS idx_testata_acquisizione ON ORDINI_TESTATA(id_acquisizione);
CREATE INDEX IF NOT EXISTS idx_testata_vendor ON ORDINI_TESTATA(id_vendor);
CREATE INDEX IF NOT EXISTS idx_testata_stato ON ORDINI_TESTATA(stato);

CREATE TABLE IF NOT EXISTS ORDINI_DETTAGLIO (
    id_dettaglio INTEGER PRIMARY KEY AUTOINCREMENT,
    id_testata INTEGER NOT NULL REFERENCES ORDINI_TESTATA(id_testata) ON DELETE CASCADE,
    n_riga INTEGER NOT NULL,
    codice_aic TEXT,
    codice_originale TEXT,
    codice_materiale TEXT,
    descrizione TEXT,
    tipo_posizione TEXT DEFAULT '',
    q_venduta INTEGER DEFAULT 0,
    q_sconto_merce INTEGER DEFAULT 0,
    q_omaggio INTEGER DEFAULT 0,
    data_consegna_riga TEXT,
    sconto_1 REAL DEFAULT 0,
    sconto_2 REAL DEFAULT 0,
    sconto_3 REAL DEFAULT 0,
    sconto_4 REAL DEFAULT 0,
    prezzo_netto REAL DEFAULT 0,
    prezzo_scontare REAL DEFAULT 0,
    prezzo_pubblico REAL DEFAULT 0,
    prezzo_listino REAL DEFAULT 0,
    valore_netto REAL DEFAULT 0,
    aliquota_iva REAL DEFAULT 10,
    scorporo_iva TEXT DEFAULT 'N',
    note_allestimento TEXT,
    is_espositore INTEGER DEFAULT 0,
    is_child INTEGER DEFAULT 0,
    is_no_aic INTEGER DEFAULT 0,
    tipo_riga TEXT DEFAULT '',
    id_parent_espositore INTEGER,
    espositore_metadata TEXT,
    -- Campi stato e supervisione
    stato_riga TEXT DEFAULT 'ESTRATTO',
    richiede_supervisione INTEGER DEFAULT 0,
    id_supervisione INTEGER,
    confermato_da TEXT,
    data_conferma TEXT,
    note_supervisione TEXT,
    modificato_manualmente INTEGER DEFAULT 0,
    valori_originali TEXT,
    -- v6.1.2: Campi per gestione esportazioni parziali
    q_originale INTEGER DEFAULT 0,           -- Quantità originale dal PDF
    q_esportata INTEGER DEFAULT 0,           -- Quantità già inclusa in tracciati
    q_residua INTEGER DEFAULT 0,             -- Quantità ancora da esportare
    num_esportazioni INTEGER DEFAULT 0,      -- Contatore esportazioni riga
    ultima_esportazione TEXT,                -- Data ultima esportazione
    id_ultima_esportazione INTEGER           -- FK a ESPORTAZIONI
);
CREATE INDEX IF NOT EXISTS idx_dettaglio_testata ON ORDINI_DETTAGLIO(id_testata);
CREATE INDEX IF NOT EXISTS idx_dettaglio_aic ON ORDINI_DETTAGLIO(codice_aic);
CREATE INDEX IF NOT EXISTS idx_dettaglio_stato ON ORDINI_DETTAGLIO(stato_riga);

CREATE TABLE IF NOT EXISTS ANOMALIE (
    id_anomalia INTEGER PRIMARY KEY AUTOINCREMENT,
    id_testata INTEGER REFERENCES ORDINI_TESTATA(id_testata) ON DELETE CASCADE,
    id_dettaglio INTEGER REFERENCES ORDINI_DETTAGLIO(id_dettaglio) ON DELETE CASCADE,
    id_acquisizione INTEGER REFERENCES ACQUISIZIONI(id_acquisizione),
    tipo_anomalia TEXT NOT NULL,
    livello TEXT DEFAULT 'ATTENZIONE',
    codice_anomalia TEXT,
    descrizione TEXT,
    valore_anomalo TEXT,
    stato TEXT DEFAULT 'APERTA',
    id_operatore_gestione INTEGER REFERENCES OPERATORI(id_operatore),
    note_risoluzione TEXT,
    data_rilevazione TEXT DEFAULT (datetime('now')),
    data_risoluzione TEXT,
    richiede_supervisione INTEGER DEFAULT 0,
    pattern_signature TEXT
);
CREATE INDEX IF NOT EXISTS idx_anomalie_tipo ON ANOMALIE(tipo_anomalia, stato);
CREATE INDEX IF NOT EXISTS idx_anomalie_testata ON ANOMALIE(id_testata);

CREATE TABLE IF NOT EXISTS SUPERVISIONE_ESPOSITORE (
    id_supervisione INTEGER PRIMARY KEY AUTOINCREMENT,
    id_testata INTEGER NOT NULL REFERENCES ORDINI_TESTATA(id_testata) ON DELETE CASCADE,
    id_anomalia INTEGER REFERENCES ANOMALIE(id_anomalia) ON DELETE SET NULL,
    codice_anomalia TEXT NOT NULL,
    codice_espositore TEXT,
    descrizione_espositore TEXT,
    pezzi_attesi INTEGER DEFAULT 0,
    pezzi_trovati INTEGER DEFAULT 0,
    valore_calcolato REAL DEFAULT 0,
    pattern_signature TEXT,
    stato TEXT DEFAULT 'PENDING',
    operatore TEXT,
    timestamp_creazione TEXT DEFAULT (datetime('now')),
    timestamp_decisione TEXT,
    note TEXT,
    modifiche_manuali_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_supervisione_testata ON SUPERVISIONE_ESPOSITORE(id_testata);
CREATE INDEX IF NOT EXISTS idx_supervisione_stato ON SUPERVISIONE_ESPOSITORE(stato);

CREATE TABLE IF NOT EXISTS CRITERI_ORDINARI_ESPOSITORE (
    pattern_signature TEXT PRIMARY KEY,
    pattern_descrizione TEXT,
    vendor TEXT NOT NULL,
    codice_anomalia TEXT NOT NULL,
    codice_espositore TEXT,
    pezzi_per_unita INTEGER,
    tipo_scostamento TEXT,
    fascia_scostamento TEXT,
    count_approvazioni INTEGER DEFAULT 0,
    is_ordinario INTEGER DEFAULT 0,
    data_prima_occorrenza TEXT DEFAULT (datetime('now')),
    data_promozione TEXT,
    operatori_approvatori TEXT
);

CREATE TABLE IF NOT EXISTS LOG_CRITERI_APPLICATI (
    id_log INTEGER PRIMARY KEY AUTOINCREMENT,
    id_testata INTEGER REFERENCES ORDINI_TESTATA(id_testata) ON DELETE SET NULL,
    id_supervisione INTEGER,
    pattern_signature TEXT NOT NULL,
    azione TEXT,
    applicato_automaticamente INTEGER DEFAULT 0,
    operatore TEXT,
    note TEXT,
    timestamp TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS TRACCIATI (
    id_tracciato INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_file TEXT NOT NULL,
    tipo TEXT DEFAULT 'CSV',
    num_righe INTEGER DEFAULT 0,
    id_operatore INTEGER REFERENCES OPERATORI(id_operatore),
    note TEXT,
    data_generazione TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS TRACCIATI_DETTAGLIO (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_tracciato INTEGER NOT NULL REFERENCES TRACCIATI(id_tracciato) ON DELETE CASCADE,
    id_testata INTEGER REFERENCES ORDINI_TESTATA(id_testata),
    id_dettaglio INTEGER REFERENCES ORDINI_DETTAGLIO(id_dettaglio)
);

CREATE TABLE IF NOT EXISTS LOG_OPERAZIONI (
    id_log INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_operazione TEXT NOT NULL,
    entita TEXT,
    id_entita INTEGER,
    descrizione TEXT,
    dati_json TEXT,
    id_operatore INTEGER REFERENCES OPERATORI(id_operatore),
    timestamp TEXT DEFAULT (datetime('now'))
);

-- Tabella per tracciare le esportazioni tracciati
CREATE TABLE IF NOT EXISTS ESPORTAZIONI (
    id_esportazione INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_tracciato_generato TEXT,
    data_tracciato TEXT,
    nome_file_to_t TEXT,
    nome_file_to_d TEXT,
    num_testate INTEGER DEFAULT 0,
    num_dettagli INTEGER DEFAULT 0,
    stato TEXT DEFAULT 'GENERATO',
    note TEXT,
    data_generazione TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ESPORTAZIONI_DETTAGLIO (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_esportazione INTEGER NOT NULL REFERENCES ESPORTAZIONI(id_esportazione) ON DELETE CASCADE,
    id_testata INTEGER REFERENCES ORDINI_TESTATA(id_testata)
);
CREATE INDEX IF NOT EXISTS idx_esportazioni_det ON ESPORTAZIONI_DETTAGLIO(id_esportazione);

CREATE VIEW IF NOT EXISTS V_ORDINI_COMPLETI AS
SELECT 
    ot.id_testata,
    v.codice_vendor AS vendor,
    ot.numero_ordine_vendor AS numero_ordine,
    ot.data_ordine,
    ot.data_consegna,
    ot.ragione_sociale_1 AS ragione_sociale,
    ot.indirizzo,
    ot.cap,
    ot.citta,
    ot.provincia,
    ot.partita_iva_estratta AS partita_iva,
    ot.codice_ministeriale_estratto AS codice_ministeriale,
    ot.codice_ministeriale_estratto AS min_id,
    ot.lookup_method,
    ot.lookup_score,
    ot.stato,
    ot.data_estrazione,
    ot.data_validazione,
    ot.validato_da,
    ot.righe_totali,
    ot.righe_confermate,
    ot.righe_in_supervisione,
    ot.id_farmacia_lookup,
    ot.id_parafarmacia_lookup,
    f.min_id AS anag_min_id,
    p.codice_sito AS anag_codice_sito,
    a.nome_file_originale AS pdf_file,
    a.data_upload,
    COUNT(od.id_dettaglio) AS num_righe_calc,
    SUM(CASE WHEN od.is_espositore = 1 THEN 1 ELSE 0 END) AS num_espositori
FROM ORDINI_TESTATA ot
JOIN VENDOR v ON ot.id_vendor = v.id_vendor
JOIN ACQUISIZIONI a ON ot.id_acquisizione = a.id_acquisizione
LEFT JOIN ANAGRAFICA_FARMACIE f ON ot.id_farmacia_lookup = f.id_farmacia
LEFT JOIN ANAGRAFICA_PARAFARMACIE p ON ot.id_parafarmacia_lookup = p.id_parafarmacia
LEFT JOIN ORDINI_DETTAGLIO od ON ot.id_testata = od.id_testata
GROUP BY ot.id_testata;

-- Vista dettagli completi per generazione tracciato
CREATE VIEW IF NOT EXISTS V_DETTAGLI_COMPLETI AS
SELECT 
    od.id_dettaglio,
    od.id_testata,
    od.n_riga,
    od.codice_aic,
    od.codice_originale,
    od.codice_materiale,
    od.descrizione,
    od.tipo_posizione,
    od.q_venduta,
    od.q_sconto_merce,
    od.q_omaggio,
    od.data_consegna_riga,
    od.sconto_1,
    od.sconto_2,
    od.sconto_3,
    od.sconto_4,
    od.prezzo_netto,
    od.prezzo_pubblico,
    od.prezzo_listino,
    od.valore_netto,
    od.aliquota_iva,
    od.is_espositore,
    od.is_child,
    od.is_no_aic,
    od.tipo_riga,
    od.id_parent_espositore,
    od.espositore_metadata,
    od.stato_riga,
    od.richiede_supervisione,
    od.id_supervisione,
    od.confermato_da,
    od.data_conferma,
    od.note_supervisione,
    od.modificato_manualmente,
    -- v6.1.2: Campi esportazione parziale
    od.q_originale,
    od.q_esportata,
    od.q_residua,
    od.num_esportazioni,
    od.ultima_esportazione,
    od.id_ultima_esportazione,
    ot.numero_ordine_vendor AS numero_ordine,
    v.codice_vendor AS vendor
FROM ORDINI_DETTAGLIO od
JOIN ORDINI_TESTATA ot ON od.id_testata = ot.id_testata
JOIN VENDOR v ON ot.id_vendor = v.id_vendor;

-- v6.1.2: Vista righe esportabili (confermate con quantità da esportare)
CREATE VIEW IF NOT EXISTS V_RIGHE_ESPORTABILI AS
SELECT 
    od.id_dettaglio,
    od.id_testata,
    od.n_riga,
    od.codice_aic,
    od.descrizione,
    od.q_venduta,
    od.q_originale,
    od.q_esportata,
    od.q_residua,
    od.stato_riga,
    od.is_child,
    od.num_esportazioni,
    ot.numero_ordine_vendor AS numero_ordine,
    v.codice_vendor AS vendor,
    ot.ragione_sociale_1 AS ragione_sociale
FROM ORDINI_DETTAGLIO od
JOIN ORDINI_TESTATA ot ON od.id_testata = ot.id_testata
JOIN VENDOR v ON ot.id_vendor = v.id_vendor
WHERE od.stato_riga IN ('CONFERMATO', 'PARZIALMENTE_ESP')
  AND od.is_child = 0
  AND (od.q_residua > 0 OR (od.q_residua = 0 AND od.num_esportazioni = 0));

CREATE VIEW IF NOT EXISTS V_SUPERVISIONE_PENDING AS
SELECT 
    se.id_supervisione,
    se.id_testata,
    se.codice_anomalia,
    se.codice_espositore,
    se.descrizione_espositore,
    se.pezzi_attesi,
    se.pezzi_trovati,
    se.valore_calcolato,
    se.pattern_signature,
    se.stato,
    se.timestamp_creazione,
    ot.numero_ordine_vendor AS numero_ordine,
    v.codice_vendor AS vendor,
    ot.ragione_sociale_1 AS ragione_sociale,
    ot.citta,
    a.nome_file_originale AS pdf_file,
    COALESCE(coe.count_approvazioni, 0) AS count_pattern,
    COALESCE(coe.is_ordinario, 0) AS pattern_ordinario
FROM SUPERVISIONE_ESPOSITORE se
JOIN ORDINI_TESTATA ot ON se.id_testata = ot.id_testata
JOIN VENDOR v ON ot.id_vendor = v.id_vendor
JOIN ACQUISIZIONI a ON ot.id_acquisizione = a.id_acquisizione
LEFT JOIN CRITERI_ORDINARI_ESPOSITORE coe ON se.pattern_signature = coe.pattern_signature
WHERE se.stato = 'PENDING'
ORDER BY se.timestamp_creazione DESC;

CREATE VIEW IF NOT EXISTS V_RIGHE_CONFERMABILI AS
SELECT 
    od.id_dettaglio, od.id_testata, od.n_riga, od.codice_aic, od.descrizione,
    od.q_venduta, od.prezzo_netto, od.tipo_riga, od.stato_riga, od.richiede_supervisione,
    ot.numero_ordine_vendor, v.codice_vendor AS vendor
FROM ORDINI_DETTAGLIO od
JOIN ORDINI_TESTATA ot ON od.id_testata = ot.id_testata
JOIN VENDOR v ON ot.id_vendor = v.id_vendor
WHERE od.stato_riga = 'ESTRATTO' AND NOT od.richiede_supervisione;

CREATE VIEW IF NOT EXISTS V_RIGHE_IN_SUPERVISIONE AS
SELECT 
    od.id_dettaglio, od.id_testata, od.n_riga, od.codice_aic, od.descrizione,
    od.tipo_riga, od.stato_riga, od.id_supervisione,
    se.stato AS stato_supervisione, se.codice_anomalia,
    ot.numero_ordine_vendor, v.codice_vendor AS vendor
FROM ORDINI_DETTAGLIO od
JOIN ORDINI_TESTATA ot ON od.id_testata = ot.id_testata
JOIN VENDOR v ON ot.id_vendor = v.id_vendor
LEFT JOIN SUPERVISIONE_ESPOSITORE se ON od.id_supervisione = se.id_supervisione
WHERE od.richiede_supervisione AND od.stato_riga IN ('ESTRATTO', 'IN_SUPERVISIONE');
'''


# =============================================================================
# INIZIALIZZAZIONE DATABASE
# =============================================================================

def init_database(force_reset: bool = False) -> sqlite3.Connection:
    global _connection

    if force_reset and os.path.exists(config.DB_PATH):
        close_db()
        os.remove(config.DB_PATH)
        print(f"🗑️ Database {config.DB_PATH} eliminato")

    db = get_db()

    tables = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='VENDOR'"
    ).fetchall()

    if not tables:
        db.executescript(get_ddl_script())
        db.commit()
        print("✅ Schema database v6.1 creato")
    else:
        _apply_migrations(db)
        _apply_email_migrations(db)
        print(f"✅ Database connesso: {config.DB_PATH}")

    stats = get_stats()
    print(
        f"   📊 Farmacie: {stats['farmacie']:,} | Parafarmacie: {stats['parafarmacie']:,} | Ordini: {stats['ordini']:,}")

    return db


def _apply_migrations(db: sqlite3.Connection) -> None:
    # Migrazione ORDINI_DETTAGLIO v6.1
    columns = db.execute("PRAGMA table_info(ORDINI_DETTAGLIO)").fetchall()
    col_names = [c[1] for c in columns]

    if 'stato_riga' not in col_names:
        print("📦 Applicando migrazione v6.1...")
        migrations = [
            "ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN stato_riga TEXT DEFAULT 'ESTRATTO'",
            "ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN richiede_supervisione INTEGER DEFAULT 0",
            "ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN id_supervisione INTEGER",
            "ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN confermato_da TEXT",
            "ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN data_conferma TEXT",
            "ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN note_supervisione TEXT",
            "ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN modificato_manualmente INTEGER DEFAULT 0",
            "ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN valori_originali TEXT",
            "ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN codice_materiale TEXT",
            "ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN tipo_posizione TEXT DEFAULT ''",
            "ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN prezzo_listino REAL DEFAULT 0",
            "ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN valore_netto REAL DEFAULT 0",
            "ALTER TABLE ORDINI_TESTATA ADD COLUMN righe_totali INTEGER DEFAULT 0",
            "ALTER TABLE ORDINI_TESTATA ADD COLUMN righe_confermate INTEGER DEFAULT 0",
            "ALTER TABLE ORDINI_TESTATA ADD COLUMN righe_in_supervisione INTEGER DEFAULT 0",
            "ALTER TABLE ORDINI_TESTATA ADD COLUMN data_ultimo_aggiornamento TEXT",
        ]
        for sql in migrations:
            try:
                db.execute(sql)
            except sqlite3.OperationalError:
                pass
        db.commit()
        print("   ✅ Migrazione v6.1 completata")

    # Migrazione OPERATORI v6.2 - colonne mancanti per auth
    op_columns = db.execute("PRAGMA table_info(OPERATORI)").fetchall()
    op_col_names = [c[1] for c in op_columns]

    op_missing_cols = {
        'created_by_operatore': 'INTEGER',
        'updated_at': 'TEXT',
        'last_login_at': 'TEXT',
        'disabled_at': 'TEXT',
        'disabled_by_operatore': 'INTEGER',
        'disable_reason': 'TEXT',
    }

    op_migrations = []
    for col, col_type in op_missing_cols.items():
        if col not in op_col_names:
            op_migrations.append(f"ALTER TABLE OPERATORI ADD COLUMN {col} {col_type}")

    if op_migrations:
        print(f"📦 Applicando migrazione OPERATORI v6.2 ({len(op_migrations)} colonne)...")
        for sql in op_migrations:
            try:
                db.execute(sql)
                print(f"   ✅ {sql.split('ADD COLUMN')[1].split()[0]}")
            except sqlite3.OperationalError as e:
                print(f"   ⚠️ {e}")
        db.commit()

    # Migrazione ANOMALIE v6.2 - colonne mancanti
    anom_columns = db.execute("PRAGMA table_info(ANOMALIE)").fetchall()
    anom_col_names = [c[1] for c in anom_columns]

    anom_missing_cols = {
        'note_risoluzione': 'TEXT',
        'data_risoluzione': 'TEXT',
        'id_operatore_gestione': 'INTEGER',
        'richiede_supervisione': 'INTEGER DEFAULT 0',
        'pattern_signature': 'TEXT',
        'codice_anomalia': 'TEXT',
    }

    anom_migrations = []
    for col, col_type in anom_missing_cols.items():
        if col not in anom_col_names:
            anom_migrations.append(f"ALTER TABLE ANOMALIE ADD COLUMN {col} {col_type}")

    if anom_migrations:
        print(f"📦 Applicando migrazione ANOMALIE v6.2 ({len(anom_migrations)} colonne)...")
        for sql in anom_migrations:
            try:
                db.execute(sql)
                print(f"   ✅ {sql.split('ADD COLUMN')[1].split()[0]}")
            except sqlite3.OperationalError as e:
                print(f"   ⚠️ {e}")
        db.commit()

    # Migrazione ANAGRAFICA_FARMACIE v6.2 - colonne mancanti
    farm_columns = db.execute("PRAGMA table_info(ANAGRAFICA_FARMACIE)").fetchall()
    farm_col_names = [c[1] for c in farm_columns]

    # Tutte le colonne che potrebbero mancare
    farm_missing_cols = {
        'regione': 'TEXT',
        'frazione': 'TEXT',
        'codice_farmacia_asl': 'TEXT',
        'data_inizio_validita': 'TEXT',
        'data_fine_validita': 'TEXT',
        'attiva': 'INTEGER DEFAULT 1',
        'fonte_dati': 'TEXT',
        'data_import': 'TEXT',
    }

    farm_migrations = []
    for col, col_type in farm_missing_cols.items():
        if col not in farm_col_names:
            farm_migrations.append(f"ALTER TABLE ANAGRAFICA_FARMACIE ADD COLUMN {col} {col_type}")

    if farm_migrations:
        print(f"📦 Applicando migrazione ANAGRAFICA_FARMACIE v6.2 ({len(farm_migrations)} colonne)...")
        for sql in farm_migrations:
            try:
                db.execute(sql)
            except sqlite3.OperationalError:
                pass
        db.commit()
        print("   ✅ Migrazione ANAGRAFICA_FARMACIE completata")

    # Migrazione ANAGRAFICA_PARAFARMACIE v6.2 - colonne mancanti
    para_columns = db.execute("PRAGMA table_info(ANAGRAFICA_PARAFARMACIE)").fetchall()
    para_col_names = [c[1] for c in para_columns]

    # Se manca codice_sito (colonna chiave), ricrea la tabella
    if 'codice_sito' not in para_col_names:
        print("📦 ANAGRAFICA_PARAFARMACIE: colonna codice_sito mancante, ricreazione tabella...")
        db.execute("DROP TABLE IF EXISTS ANAGRAFICA_PARAFARMACIE")
        db.execute("""
            CREATE TABLE ANAGRAFICA_PARAFARMACIE (
                id_parafarmacia INTEGER PRIMARY KEY AUTOINCREMENT,
                codice_sito TEXT NOT NULL UNIQUE,
                sito_logistico TEXT,
                partita_iva TEXT,
                indirizzo TEXT,
                cap TEXT,
                codice_comune TEXT,
                citta TEXT,
                codice_provincia TEXT,
                provincia TEXT,
                codice_regione TEXT,
                regione TEXT,
                data_inizio_validita TEXT,
                data_fine_validita TEXT,
                latitudine TEXT,
                longitudine TEXT,
                attiva INTEGER DEFAULT 1,
                fonte_dati TEXT,
                data_import TEXT DEFAULT (datetime('now'))
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_parafarm_codice ON ANAGRAFICA_PARAFARMACIE(codice_sito)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_parafarm_piva ON ANAGRAFICA_PARAFARMACIE(partita_iva)")
        db.commit()
        print("   ✅ Tabella ANAGRAFICA_PARAFARMACIE ricreata")
    else:
        # Tutte le colonne che potrebbero mancare (oltre codice_sito)
        para_missing_cols = {
            'regione': 'TEXT',
            'codice_comune': 'TEXT',
            'codice_provincia': 'TEXT',
            'codice_regione': 'TEXT',
            'latitudine': 'TEXT',
            'longitudine': 'TEXT',
            'data_inizio_validita': 'TEXT',
            'data_fine_validita': 'TEXT',
            'attiva': 'INTEGER DEFAULT 1',
            'fonte_dati': 'TEXT',
            'data_import': 'TEXT',
        }

        para_migrations = []
        for col, col_type in para_missing_cols.items():
            if col not in para_col_names:
                para_migrations.append(f"ALTER TABLE ANAGRAFICA_PARAFARMACIE ADD COLUMN {col} {col_type}")

        if para_migrations:
            print(f"📦 Applicando migrazione ANAGRAFICA_PARAFARMACIE v6.2 ({len(para_migrations)} colonne)...")
            for sql in para_migrations:
                try:
                    db.execute(sql)
                except sqlite3.OperationalError:
                    pass
            db.commit()
            print("   ✅ Migrazione ANAGRAFICA_PARAFARMACIE completata")

    # Migrazione v6.2: Ricrea vista V_ORDINI_COMPLETI se usa p.min_id (errore)
    try:
        # Verifica se la vista esiste e ha il problema
        view_sql = db.execute(
            "SELECT sql FROM sqlite_master WHERE type='view' AND name='V_ORDINI_COMPLETI'"
        ).fetchone()

        if view_sql and 'p.min_id' in (view_sql[0] or ''):
            print("📦 Migrazione V_ORDINI_COMPLETI: correzione p.min_id → p.codice_sito...")
            db.execute("DROP VIEW IF EXISTS V_ORDINI_COMPLETI")
            db.execute("""
                CREATE VIEW V_ORDINI_COMPLETI AS
                SELECT
                    ot.id_testata,
                    v.codice_vendor AS vendor,
                    ot.numero_ordine_vendor AS numero_ordine,
                    ot.data_ordine,
                    ot.data_consegna,
                    ot.ragione_sociale_1 AS ragione_sociale,
                    ot.indirizzo,
                    ot.cap,
                    ot.citta,
                    ot.provincia,
                    ot.partita_iva_estratta AS partita_iva,
                    ot.codice_ministeriale_estratto AS codice_ministeriale,
                    ot.codice_ministeriale_estratto AS min_id,
                    ot.lookup_method,
                    ot.lookup_score,
                    ot.stato,
                    ot.data_estrazione,
                    ot.data_validazione,
                    ot.validato_da,
                    ot.righe_totali,
                    ot.righe_confermate,
                    ot.righe_in_supervisione,
                    ot.id_farmacia_lookup,
                    ot.id_parafarmacia_lookup,
                    f.min_id AS anag_min_id,
                    p.codice_sito AS anag_codice_sito,
                    a.nome_file_originale AS pdf_file,
                    a.data_upload,
                    COUNT(od.id_dettaglio) AS num_righe_calc,
                    SUM(CASE WHEN od.is_espositore = 1 THEN 1 ELSE 0 END) AS num_espositori
                FROM ORDINI_TESTATA ot
                JOIN VENDOR v ON ot.id_vendor = v.id_vendor
                JOIN ACQUISIZIONI a ON ot.id_acquisizione = a.id_acquisizione
                LEFT JOIN ANAGRAFICA_FARMACIE f ON ot.id_farmacia_lookup = f.id_farmacia
                LEFT JOIN ANAGRAFICA_PARAFARMACIE p ON ot.id_parafarmacia_lookup = p.id_parafarmacia
                LEFT JOIN ORDINI_DETTAGLIO od ON ot.id_testata = od.id_testata
                GROUP BY ot.id_testata
            """)
            db.commit()
            print("   ✅ Vista V_ORDINI_COMPLETI corretta")
    except Exception as e:
        print(f"   ⚠️ Errore migrazione vista: {e}")

    # Migrazione v6.2: Aggiungi vendor mancanti (DOC_GENERICI, GENERIC)
    try:
        # Usa INSERT OR IGNORE per evitare errori su constraint
        db.execute("INSERT OR IGNORE INTO VENDOR (codice, ragione_sociale, formato_pdf, attivo) VALUES ('DOC_GENERICI', 'DOC Generici S.r.l.', 'Transfer Order', 1)")
        db.execute("INSERT OR IGNORE INTO VENDOR (codice, ragione_sociale, formato_pdf, attivo) VALUES ('GENERIC', 'Vendor Generico', 'Generico', 1)")
        db.commit()
        print("   ✅ Vendor DOC_GENERICI e GENERIC verificati")
    except:
        # Prova schema alternativo
        try:
            db.execute("INSERT OR IGNORE INTO VENDOR (codice_vendor, ragione_sociale) VALUES ('DOC_GENERICI', 'DOC Generici S.r.l.')")
            db.execute("INSERT OR IGNORE INTO VENDOR (codice_vendor, ragione_sociale) VALUES ('GENERIC', 'Vendor Generico')")
            db.commit()
            print("   ✅ Vendor DOC_GENERICI e GENERIC verificati (schema alt)")
        except Exception as e:
            print(f"   ⚠️ Skip migrazione vendor: {e}")


def _apply_email_migrations(db: sqlite3.Connection) -> None:
    """Applica migrazioni per supporto Gmail (v6.2)"""

    # Verifica se EMAIL_ACQUISIZIONI esiste
    tables = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='EMAIL_ACQUISIZIONI'"
    ).fetchall()

    if not tables:
        print("📧 Applicando migrazione Gmail (v6.2)...")

        # Crea tabella EMAIL_ACQUISIZIONI
        db.execute("""
            CREATE TABLE EMAIL_ACQUISIZIONI (
                id_email INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE NOT NULL,
                gmail_id TEXT,
                subject TEXT,
                sender_email TEXT NOT NULL,
                sender_name TEXT,
                received_date TEXT NOT NULL,
                attachment_filename TEXT NOT NULL,
                attachment_size INTEGER,
                attachment_hash TEXT NOT NULL,
                id_acquisizione INTEGER REFERENCES ACQUISIZIONI(id_acquisizione),
                stato TEXT DEFAULT 'DA_PROCESSARE' 
                    CHECK (stato IN ('DA_PROCESSARE','PROCESSATA','ERRORE','DUPLICATO')),
                data_elaborazione TEXT,
                errore_messaggio TEXT,
                num_retry INTEGER DEFAULT 0,
                label_applicata TEXT,
                marcata_come_letta INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Crea indici
        db.execute(
            "CREATE INDEX idx_email_message_id ON EMAIL_ACQUISIZIONI(message_id)")
        db.execute(
            "CREATE INDEX idx_email_hash ON EMAIL_ACQUISIZIONI(attachment_hash)")
        db.execute("CREATE INDEX idx_email_stato ON EMAIL_ACQUISIZIONI(stato)")

        # Aggiungi colonne a ACQUISIZIONI
        try:
            db.execute(
                "ALTER TABLE ACQUISIZIONI ADD COLUMN origine TEXT DEFAULT 'MANUALE'")
        except sqlite3.OperationalError:
            pass

        try:
            db.execute(
                "ALTER TABLE ACQUISIZIONI ADD COLUMN id_email INTEGER REFERENCES EMAIL_ACQUISIZIONI(id_email)")
        except sqlite3.OperationalError:
            pass

        db.commit()
        print("   ✅ Migrazione Gmail completata")


def _apply_email_migrations(db: sqlite3.Connection) -> None:
    """Applica migrazioni per supporto Gmail (v6.2)"""

    # Verifica se EMAIL_ACQUISIZIONI esiste
    tables = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='EMAIL_ACQUISIZIONI'"
    ).fetchall()

    if not tables:
        print("📧 Applicando migrazione Gmail (v6.2)...")

        # Crea tabella EMAIL_ACQUISIZIONI
        db.execute("""
            CREATE TABLE EMAIL_ACQUISIZIONI (
                id_email INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE NOT NULL,
                gmail_id TEXT,
                subject TEXT,
                sender_email TEXT NOT NULL,
                sender_name TEXT,
                received_date TEXT NOT NULL,
                attachment_filename TEXT NOT NULL,
                attachment_size INTEGER,
                attachment_hash TEXT NOT NULL,
                id_acquisizione INTEGER REFERENCES ACQUISIZIONI(id_acquisizione),
                stato TEXT DEFAULT 'DA_PROCESSARE' 
                    CHECK (stato IN ('DA_PROCESSARE','PROCESSATA','ERRORE','DUPLICATO')),
                data_elaborazione TEXT,
                errore_messaggio TEXT,
                num_retry INTEGER DEFAULT 0,
                label_applicata TEXT,
                marcata_come_letta INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Crea indici
        db.execute(
            "CREATE INDEX idx_email_message_id ON EMAIL_ACQUISIZIONI(message_id)")
        db.execute(
            "CREATE INDEX idx_email_hash ON EMAIL_ACQUISIZIONI(attachment_hash)")
        db.execute("CREATE INDEX idx_email_stato ON EMAIL_ACQUISIZIONI(stato)")

        # Aggiungi colonne a ACQUISIZIONI
        try:
            db.execute(
                "ALTER TABLE ACQUISIZIONI ADD COLUMN origine TEXT DEFAULT 'MANUALE'")
        except sqlite3.OperationalError:
            pass  # Colonna già esistente

        try:
            db.execute(
                "ALTER TABLE ACQUISIZIONI ADD COLUMN id_email INTEGER REFERENCES EMAIL_ACQUISIZIONI(id_email)")
        except sqlite3.OperationalError:
            pass

        db.commit()
        print("   ✅ Migrazione Gmail completata")

# =============================================================================
# FUNZIONI UTILITÀ
# =============================================================================


def get_vendor_id(codice_vendor: str) -> Optional[int]:
    db = get_db()
    row = db.execute("SELECT id_vendor FROM VENDOR WHERE codice_vendor = ?",
                     (codice_vendor.upper(),)).fetchone()
    return row['id_vendor'] if row else None


def get_vendor_by_id(id_vendor: int) -> Optional[Dict[str, Any]]:
    db = get_db()
    row = db.execute("SELECT * FROM VENDOR WHERE id_vendor = ?",
                     (id_vendor,)).fetchone()
    return dict(row) if row else None


def get_all_vendors() -> List[Dict[str, Any]]:
    db = get_db()
    rows = db.execute(
        "SELECT * FROM VENDOR WHERE attivo = 1 ORDER BY codice_vendor").fetchall()
    return [dict(row) for row in rows]


def get_stats() -> Dict[str, Any]:
    db = get_db()
    return {
        'farmacie': db.execute("SELECT COUNT(*) FROM ANAGRAFICA_FARMACIE").fetchone()[0],
        'parafarmacie': db.execute("SELECT COUNT(*) FROM ANAGRAFICA_PARAFARMACIE").fetchone()[0],
        'ordini': db.execute("SELECT COUNT(*) FROM ORDINI_TESTATA").fetchone()[0],
        'dettagli': db.execute("SELECT COUNT(*) FROM ORDINI_DETTAGLIO").fetchone()[0],
        'anomalie_aperte': db.execute("SELECT COUNT(*) FROM ANOMALIE WHERE stato IN ('APERTA', 'IN_GESTIONE')").fetchone()[0],
        'pdf_elaborati': db.execute("SELECT COUNT(*) FROM ACQUISIZIONI WHERE stato = 'ELABORATO'").fetchone()[0],
        'pdf_oggi': db.execute("SELECT COUNT(*) FROM ACQUISIZIONI WHERE date(data_upload) = date('now')").fetchone()[0],
        'righe_da_confermare': db.execute("SELECT COUNT(*) FROM ORDINI_DETTAGLIO WHERE stato_riga = 'ESTRATTO'").fetchone()[0],
        'righe_in_supervisione': db.execute("SELECT COUNT(*) FROM ORDINI_DETTAGLIO WHERE stato_riga = 'IN_SUPERVISIONE'").fetchone()[0],
    }


def get_vendor_stats() -> List[Dict[str, Any]]:
    db = get_db()
    rows = db.execute('''
        SELECT v.codice_vendor AS vendor, COUNT(DISTINCT ot.id_testata) AS ordini, COUNT(od.id_dettaglio) AS righe
        FROM VENDOR v
        LEFT JOIN ORDINI_TESTATA ot ON v.id_vendor = ot.id_vendor
        LEFT JOIN ORDINI_DETTAGLIO od ON ot.id_testata = od.id_testata
        WHERE v.attivo = 1 GROUP BY v.id_vendor ORDER BY v.codice_vendor
    ''').fetchall()
    return [dict(row) for row in rows]


def log_operation(tipo: str, entita: str = None, id_entita: int = None, descrizione: str = None, dati: Dict = None):
    db = get_db()
    db.execute('''INSERT INTO LOG_OPERAZIONI (tipo_operazione, entita, id_entita, descrizione, dati_json) VALUES (?, ?, ?, ?, ?)''',
               (tipo, entita, id_entita, descrizione, json.dumps(dati) if dati else None))
    db.commit()


def get_supervisione_pending() -> List[Dict[str, Any]]:
    db = get_db()
    rows = db.execute("SELECT * FROM V_SUPERVISIONE_PENDING").fetchall()
    return [dict(row) for row in rows]


def get_supervisione_by_testata(id_testata: int) -> List[Dict[str, Any]]:
    db = get_db()
    rows = db.execute(
        "SELECT * FROM SUPERVISIONE_ESPOSITORE WHERE id_testata = ?", (id_testata,)).fetchall()
    return [dict(row) for row in rows]


def count_supervisioni_pending() -> int:
    db = get_db()
    return db.execute("SELECT COUNT(*) FROM SUPERVISIONE_ESPOSITORE WHERE stato = 'PENDING'").fetchone()[0]


def get_criterio_by_pattern(pattern_signature: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    row = db.execute("SELECT * FROM CRITERI_ORDINARI_ESPOSITORE WHERE pattern_signature = ?",
                     (pattern_signature,)).fetchone()
    return dict(row) if row else None


def get_criteri_ordinari() -> List[Dict[str, Any]]:
    db = get_db()
    rows = db.execute(
        "SELECT * FROM CRITERI_ORDINARI_ESPOSITORE WHERE is_ordinario = 1 ORDER BY data_promozione DESC").fetchall()
    return [dict(row) for row in rows]


def get_criteri_stats() -> Dict[str, Any]:
    db = get_db()
    return {
        'totale_pattern': db.execute("SELECT COUNT(*) FROM CRITERI_ORDINARI_ESPOSITORE").fetchone()[0],
        'pattern_ordinari': db.execute("SELECT COUNT(*) FROM CRITERI_ORDINARI_ESPOSITORE WHERE is_ordinario = 1").fetchone()[0],
        'pattern_in_apprendimento': db.execute("SELECT COUNT(*) FROM CRITERI_ORDINARI_ESPOSITORE WHERE is_ordinario = 0 AND count_approvazioni > 0").fetchone()[0],
        'applicazioni_automatiche_oggi': db.execute("SELECT COUNT(*) FROM LOG_CRITERI_APPLICATI WHERE date(timestamp) = date('now') AND applicato_automaticamente = 1").fetchone()[0],
    }
