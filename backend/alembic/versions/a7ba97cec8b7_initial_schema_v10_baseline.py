"""initial_schema_v10_baseline

Revision ID: a7ba97cec8b7
Revises:
Create Date: 2026-01-17 10:39:19.579773

BASELINE MIGRATION for SERV.O v10.1

This migration represents the initial schema state (v10.1).
For existing databases, this will be stamped without execution.
For new databases, it will create the full schema.

Tables: 41 | Views: 12 | Indexes: 88
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'a7ba97cec8b7'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :name)"
    ), {"name": table_name})
    return result.scalar()


def upgrade() -> None:
    """
    Create initial schema if database is empty.
    Skip if tables already exist (baseline for existing DBs).
    """
    # Check if schema already exists by looking for core table
    if table_exists('ordini_testata'):
        print("  Schema already exists - baseline migration (no changes)")
        return

    print("  Creating initial schema v10.1...")
    conn = op.get_bind()

    # =========================================================================
    # CORE TABLES
    # =========================================================================

    # VENDOR
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS VENDOR (
            id_vendor SERIAL PRIMARY KEY,
            codice_vendor VARCHAR(20) NOT NULL UNIQUE,
            ragione_sociale VARCHAR(200),
            attivo BOOLEAN DEFAULT TRUE,
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    # ACQUISIZIONI
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ACQUISIZIONI (
            id_acquisizione SERIAL PRIMARY KEY,
            id_vendor INTEGER REFERENCES VENDOR(id_vendor),
            filename VARCHAR(255) NOT NULL,
            hash_md5 VARCHAR(32),
            data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            stato VARCHAR(20) DEFAULT 'NUOVO',
            note TEXT
        )
    """))

    # ORDINI_TESTATA
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ORDINI_TESTATA (
            id_testata SERIAL PRIMARY KEY,
            id_acquisizione INTEGER REFERENCES ACQUISIZIONI(id_acquisizione),
            numero_ordine VARCHAR(50) NOT NULL,
            data_ordine DATE,
            data_consegna DATE,
            id_vendor INTEGER REFERENCES VENDOR(id_vendor),
            min_id VARCHAR(20),
            partita_iva VARCHAR(16),
            ragione_sociale VARCHAR(200),
            indirizzo VARCHAR(200),
            cap VARCHAR(10),
            citta VARCHAR(100),
            provincia VARCHAR(5),
            stato VARCHAR(30) DEFAULT 'ESTRATTO',
            note_ordine TEXT,
            note_ddt TEXT,
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            id_farmacia INTEGER,
            tipo_lookup VARCHAR(20),
            lookup_score INTEGER,
            lookup_matches INTEGER,
            note_lookup TEXT,
            lookup_status VARCHAR(20)
        )
    """))

    # ORDINI_DETTAGLIO
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ORDINI_DETTAGLIO (
            id_dettaglio SERIAL PRIMARY KEY,
            id_testata INTEGER NOT NULL REFERENCES ORDINI_TESTATA(id_testata) ON DELETE CASCADE,
            n_riga INTEGER,
            codice_aic VARCHAR(15),
            descrizione_prodotto VARCHAR(255),
            q_venduta INTEGER DEFAULT 0,
            q_omaggio INTEGER DEFAULT 0,
            q_sconto_merce INTEGER DEFAULT 0,
            q_evasa INTEGER DEFAULT 0,
            sconto_1 DECIMAL(6,2) DEFAULT 0,
            sconto_2 DECIMAL(6,2) DEFAULT 0,
            sconto_3 DECIMAL(6,2) DEFAULT 0,
            sconto_4 DECIMAL(6,2) DEFAULT 0,
            prezzo_netto DECIMAL(10,2),
            prezzo_scontare DECIMAL(10,2),
            prezzo_pubblico DECIMAL(10,2),
            aliquota_iva DECIMAL(5,2),
            scorporo_iva VARCHAR(1) DEFAULT 'S',
            note_allestimento TEXT,
            stato_riga VARCHAR(30) DEFAULT 'ESTRATTO',
            is_espositore BOOLEAN DEFAULT FALSE,
            tipo_espositore VARCHAR(20),
            codice_espositore VARCHAR(50),
            descrizione_espositore VARCHAR(255),
            parent_espositore_id INTEGER
        )
    """))

    # OPERATORI (Auth) - MUST be before ANOMALIE (FK dependency)
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS OPERATORI (
            id_operatore SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            nome VARCHAR(100),
            cognome VARCHAR(100),
            email VARCHAR(100) UNIQUE,
            ruolo VARCHAR(20) NOT NULL DEFAULT 'operatore',
            attivo BOOLEAN DEFAULT TRUE,
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP,
            created_by_operatore INTEGER,
            disabled_at TIMESTAMP,
            disabled_by_operatore INTEGER,
            disable_reason TEXT,
            data_nascita DATE,
            avatar_base64 TEXT,
            avatar_mime_type VARCHAR(50)
        )
    """))

    # ANOMALIE
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ANOMALIE (
            id_anomalia SERIAL PRIMARY KEY,
            id_testata INTEGER REFERENCES ORDINI_TESTATA(id_testata) ON DELETE CASCADE,
            id_dettaglio INTEGER REFERENCES ORDINI_DETTAGLIO(id_dettaglio) ON DELETE CASCADE,
            id_acquisizione INTEGER REFERENCES ACQUISIZIONI(id_acquisizione) ON DELETE CASCADE,
            tipo_anomalia VARCHAR(50) NOT NULL,
            codice_anomalia VARCHAR(20),
            livello VARCHAR(20) DEFAULT 'ATTENZIONE',
            descrizione TEXT,
            valore_anomalo TEXT,
            dati_originali JSONB,
            dati_corretti JSONB,
            stato VARCHAR(20) DEFAULT 'APERTA',
            richiede_supervisione BOOLEAN DEFAULT FALSE,
            pattern_signature VARCHAR(64),
            id_operatore_gestione INTEGER REFERENCES OPERATORI(id_operatore),
            note_risoluzione TEXT,
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_risoluzione TIMESTAMP
        )
    """))

    # USER_SESSIONS
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS USER_SESSIONS (
            id_session SERIAL PRIMARY KEY,
            id_operatore INTEGER NOT NULL REFERENCES OPERATORI(id_operatore) ON DELETE CASCADE,
            token_jti VARCHAR(100) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            revoked BOOLEAN DEFAULT FALSE,
            ip_address VARCHAR(45),
            user_agent TEXT
        )
    """))

    # LOG_ATTIVITA
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS LOG_ATTIVITA (
            id_log SERIAL PRIMARY KEY,
            id_operatore INTEGER REFERENCES OPERATORI(id_operatore),
            tipo_operazione VARCHAR(50) NOT NULL,
            action_category VARCHAR(20),
            entita VARCHAR(50),
            id_entita INTEGER,
            descrizione TEXT,
            success BOOLEAN DEFAULT TRUE,
            error_message TEXT,
            ip_address VARCHAR(45),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            username_snapshot VARCHAR(50)
        )
    """))

    # =========================================================================
    # ANAGRAFICA TABLES
    # =========================================================================

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ANAGRAFICA_FARMACIE (
            id_farmacia SERIAL PRIMARY KEY,
            min_id VARCHAR(20) UNIQUE,
            partita_iva VARCHAR(16),
            ragione_sociale VARCHAR(200),
            indirizzo VARCHAR(200),
            cap VARCHAR(10),
            citta VARCHAR(100),
            provincia VARCHAR(5),
            telefono VARCHAR(20),
            email VARCHAR(100),
            data_import TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_file VARCHAR(255)
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ANAGRAFICA_PARAFARMACIE (
            id_parafarmacia SERIAL PRIMARY KEY,
            codice_sito VARCHAR(20) UNIQUE,
            partita_iva VARCHAR(16),
            sito_logistico VARCHAR(200),
            indirizzo VARCHAR(200),
            cap VARCHAR(10),
            citta VARCHAR(100),
            provincia VARCHAR(5),
            regione VARCHAR(50),
            data_import TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_file VARCHAR(255)
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ANAGRAFICA_CLIENTI (
            id_cliente SERIAL PRIMARY KEY,
            codice_cliente VARCHAR(20) UNIQUE NOT NULL,
            ragione_sociale_1 VARCHAR(100),
            ragione_sociale_2 VARCHAR(100),
            indirizzo VARCHAR(200),
            cap VARCHAR(10),
            localita VARCHAR(100),
            provincia VARCHAR(5),
            partita_iva VARCHAR(16),
            codice_fiscale VARCHAR(16),
            attivo BOOLEAN DEFAULT TRUE,
            data_import TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_file VARCHAR(255)
        )
    """))

    # =========================================================================
    # LISTINI TABLES
    # =========================================================================

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS LISTINI_VENDOR (
            id_listino SERIAL PRIMARY KEY,
            vendor VARCHAR(20) NOT NULL,
            codice_aic VARCHAR(15) NOT NULL,
            descrizione VARCHAR(255),
            prezzo_pubblico DECIMAL(10,2),
            prezzo_vendita DECIMAL(10,2),
            prezzo_netto DECIMAL(10,2),
            sconto_base DECIMAL(5,2),
            aliquota_iva DECIMAL(5,2),
            attivo BOOLEAN DEFAULT TRUE,
            data_import TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_file VARCHAR(255),
            UNIQUE(vendor, codice_aic)
        )
    """))

    # =========================================================================
    # SUPERVISION TABLES
    # =========================================================================

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS SUPERVISIONE_ESPOSITORE (
            id_supervisione SERIAL PRIMARY KEY,
            id_testata INTEGER REFERENCES ORDINI_TESTATA(id_testata) ON DELETE CASCADE,
            id_dettaglio INTEGER REFERENCES ORDINI_DETTAGLIO(id_dettaglio) ON DELETE CASCADE,
            id_anomalia INTEGER REFERENCES ANOMALIE(id_anomalia) ON DELETE CASCADE,
            vendor VARCHAR(20),
            codice_espositore VARCHAR(50),
            descrizione_espositore VARCHAR(255),
            pezzi_attesi INTEGER,
            pezzi_trovati INTEGER,
            percentuale_scostamento DECIMAL(5,2),
            fascia_scostamento VARCHAR(20),
            pattern_signature VARCHAR(64),
            pattern_approvazioni INTEGER DEFAULT 0,
            pattern_ordinario BOOLEAN DEFAULT FALSE,
            stato VARCHAR(20) DEFAULT 'PENDING',
            operatore VARCHAR(50),
            note TEXT,
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            timestamp_decisione TIMESTAMP
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS SUPERVISIONE_LISTINO (
            id_supervisione SERIAL PRIMARY KEY,
            id_testata INTEGER REFERENCES ORDINI_TESTATA(id_testata) ON DELETE CASCADE,
            id_dettaglio INTEGER REFERENCES ORDINI_DETTAGLIO(id_dettaglio) ON DELETE CASCADE,
            id_anomalia INTEGER REFERENCES ANOMALIE(id_anomalia) ON DELETE CASCADE,
            vendor VARCHAR(20),
            codice_aic VARCHAR(15),
            descrizione_prodotto VARCHAR(255),
            prezzo_estratto DECIMAL(10,2),
            prezzo_listino DECIMAL(10,2),
            differenza_percentuale DECIMAL(5,2),
            pattern_signature VARCHAR(64),
            pattern_approvazioni INTEGER DEFAULT 0,
            pattern_ordinario BOOLEAN DEFAULT FALSE,
            stato VARCHAR(20) DEFAULT 'PENDING',
            operatore VARCHAR(50),
            note TEXT,
            codice_anomalia VARCHAR(20),
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            timestamp_decisione TIMESTAMP
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS SUPERVISIONE_LOOKUP (
            id_supervisione SERIAL PRIMARY KEY,
            id_testata INTEGER REFERENCES ORDINI_TESTATA(id_testata) ON DELETE CASCADE,
            id_anomalia INTEGER REFERENCES ANOMALIE(id_anomalia) ON DELETE CASCADE,
            vendor VARCHAR(20),
            piva_estratta VARCHAR(16),
            ragione_sociale_estratta VARCHAR(200),
            indirizzo_estratto VARCHAR(200),
            lookup_score INTEGER,
            lookup_matches INTEGER,
            match_suggestions JSONB,
            pattern_signature VARCHAR(64),
            pattern_approvazioni INTEGER DEFAULT 0,
            pattern_ordinario BOOLEAN DEFAULT FALSE,
            stato VARCHAR(20) DEFAULT 'PENDING',
            operatore VARCHAR(50),
            note TEXT,
            codice_anomalia VARCHAR(20),
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            timestamp_decisione TIMESTAMP,
            id_farmacia_scelta INTEGER
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS SUPERVISIONE_AIC (
            id_supervisione SERIAL PRIMARY KEY,
            id_testata INTEGER REFERENCES ORDINI_TESTATA(id_testata) ON DELETE CASCADE,
            id_dettaglio INTEGER REFERENCES ORDINI_DETTAGLIO(id_dettaglio) ON DELETE CASCADE,
            id_anomalia INTEGER REFERENCES ANOMALIE(id_anomalia) ON DELETE CASCADE,
            vendor VARCHAR(20),
            codice_originale VARCHAR(50),
            descrizione_prodotto VARCHAR(255),
            descrizione_normalizzata VARCHAR(255),
            codice_aic_suggerito VARCHAR(15),
            confidence_score DECIMAL(5,2),
            pattern_signature VARCHAR(64),
            pattern_approvazioni INTEGER DEFAULT 0,
            pattern_ordinario BOOLEAN DEFAULT FALSE,
            stato VARCHAR(20) DEFAULT 'PENDING',
            operatore VARCHAR(50),
            note TEXT,
            codice_anomalia VARCHAR(20) DEFAULT 'AIC-A01',
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            timestamp_decisione TIMESTAMP,
            codice_aic_assegnato VARCHAR(15)
        )
    """))

    # =========================================================================
    # CRITERI ORDINARI (ML Patterns)
    # =========================================================================

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS CRITERI_ORDINARI_ESPOSITORE (
            pattern_signature VARCHAR(64) PRIMARY KEY,
            vendor VARCHAR(20),
            codice_espositore VARCHAR(50),
            descrizione_normalizzata VARCHAR(255),
            pezzi_attesi INTEGER,
            fascia_scostamento VARCHAR(20),
            count_approvazioni INTEGER DEFAULT 1,
            operatori_approvatori TEXT,
            is_ordinario BOOLEAN DEFAULT FALSE,
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_promozione TIMESTAMP,
            ultima_applicazione TIMESTAMP
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS CRITERI_ORDINARI_LISTINO (
            pattern_signature VARCHAR(64) PRIMARY KEY,
            vendor VARCHAR(20),
            codice_aic VARCHAR(15),
            descrizione_normalizzata VARCHAR(255),
            prezzo_corretto DECIMAL(10,2),
            count_approvazioni INTEGER DEFAULT 1,
            operatori_approvatori TEXT,
            is_ordinario BOOLEAN DEFAULT FALSE,
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_promozione TIMESTAMP,
            ultima_applicazione TIMESTAMP
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS CRITERI_ORDINARI_LOOKUP (
            pattern_signature VARCHAR(64) PRIMARY KEY,
            partita_iva_pattern VARCHAR(16),
            ragione_sociale_pattern VARCHAR(200),
            min_id_default VARCHAR(20),
            id_farmacia_default INTEGER,
            count_approvazioni INTEGER DEFAULT 1,
            operatori_approvatori TEXT,
            is_ordinario BOOLEAN DEFAULT FALSE,
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_promozione TIMESTAMP,
            ultima_applicazione TIMESTAMP
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS CRITERI_ORDINARI_AIC (
            pattern_signature VARCHAR(64) PRIMARY KEY,
            vendor VARCHAR(20),
            descrizione_normalizzata VARCHAR(255),
            codice_aic_default VARCHAR(15),
            count_approvazioni INTEGER DEFAULT 1,
            operatori_approvatori TEXT,
            is_ordinario BOOLEAN DEFAULT FALSE,
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_promozione TIMESTAMP,
            ultima_applicazione TIMESTAMP
        )
    """))

    # =========================================================================
    # BACKUP & SYSTEM TABLES
    # =========================================================================

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS BACKUP_METADATA (
            id_backup SERIAL PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            filepath VARCHAR(500) NOT NULL,
            size_bytes BIGINT,
            tipo VARCHAR(20) DEFAULT 'COMPLETO',
            hash_md5 VARCHAR(32),
            stato VARCHAR(20) DEFAULT 'COMPLETATO',
            note TEXT,
            id_operatore INTEGER REFERENCES OPERATORI(id_operatore),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS TRACCIATI_EXPORT (
            id_export SERIAL PRIMARY KEY,
            tipo_tracciato VARCHAR(10) NOT NULL,
            filename VARCHAR(255) NOT NULL,
            filepath VARCHAR(500),
            contenuto TEXT,
            ordini_inclusi INTEGER[],
            totale_righe INTEGER,
            id_operatore INTEGER REFERENCES OPERATORI(id_operatore),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            note TEXT
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS PERMISSIONS_MATRIX (
            id_permission SERIAL PRIMARY KEY,
            ruolo VARCHAR(20) NOT NULL,
            risorsa VARCHAR(50) NOT NULL,
            azione VARCHAR(20) NOT NULL,
            permesso BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ruolo, risorsa, azione)
        )
    """))

    # =========================================================================
    # EMAIL & CRM TABLES
    # =========================================================================

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS EMAIL_CONFIG (
            id_config SERIAL PRIMARY KEY,
            config_name VARCHAR(50) NOT NULL UNIQUE,
            imap_server VARCHAR(100),
            imap_port INTEGER DEFAULT 993,
            smtp_server VARCHAR(100),
            smtp_port INTEGER DEFAULT 587,
            email_address VARCHAR(100),
            password_encrypted TEXT,
            use_ssl BOOLEAN DEFAULT TRUE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS EMAIL_MONITORAGGIO (
            id_email SERIAL PRIMARY KEY,
            message_id VARCHAR(255) UNIQUE,
            subject VARCHAR(500),
            sender VARCHAR(200),
            received_at TIMESTAMP,
            processed_at TIMESTAMP,
            stato VARCHAR(20) DEFAULT 'NUOVO',
            has_attachments BOOLEAN DEFAULT FALSE,
            attachment_count INTEGER DEFAULT 0,
            id_acquisizione INTEGER REFERENCES ACQUISIZIONI(id_acquisizione),
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS CRM_CONTATTI (
            id_contatto SERIAL PRIMARY KEY,
            tipo VARCHAR(20) DEFAULT 'CLIENTE',
            codice VARCHAR(50),
            ragione_sociale VARCHAR(200),
            nome_referente VARCHAR(100),
            email VARCHAR(100),
            telefono VARCHAR(50),
            indirizzo VARCHAR(200),
            citta VARCHAR(100),
            provincia VARCHAR(5),
            cap VARCHAR(10),
            note TEXT,
            attivo BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """))

    # =========================================================================
    # INDEXES
    # =========================================================================

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_acquisizioni_vendor ON ACQUISIZIONI(id_vendor)",
        "CREATE INDEX IF NOT EXISTS idx_acquisizioni_stato ON ACQUISIZIONI(stato)",
        "CREATE INDEX IF NOT EXISTS idx_acquisizioni_data ON ACQUISIZIONI(data_upload)",

        "CREATE INDEX IF NOT EXISTS idx_testata_acquisizione ON ORDINI_TESTATA(id_acquisizione)",
        "CREATE INDEX IF NOT EXISTS idx_testata_vendor ON ORDINI_TESTATA(id_vendor)",
        "CREATE INDEX IF NOT EXISTS idx_testata_stato ON ORDINI_TESTATA(stato)",
        "CREATE INDEX IF NOT EXISTS idx_testata_numero ON ORDINI_TESTATA(numero_ordine)",
        "CREATE INDEX IF NOT EXISTS idx_testata_piva ON ORDINI_TESTATA(partita_iva)",
        "CREATE INDEX IF NOT EXISTS idx_testata_minid ON ORDINI_TESTATA(min_id)",
        "CREATE INDEX IF NOT EXISTS idx_testata_data ON ORDINI_TESTATA(data_ordine)",

        "CREATE INDEX IF NOT EXISTS idx_dettaglio_testata ON ORDINI_DETTAGLIO(id_testata)",
        "CREATE INDEX IF NOT EXISTS idx_dettaglio_aic ON ORDINI_DETTAGLIO(codice_aic)",
        "CREATE INDEX IF NOT EXISTS idx_dettaglio_stato ON ORDINI_DETTAGLIO(stato_riga)",
        "CREATE INDEX IF NOT EXISTS idx_dettaglio_espositore ON ORDINI_DETTAGLIO(is_espositore)",

        "CREATE INDEX IF NOT EXISTS idx_anomalie_testata ON ANOMALIE(id_testata)",
        "CREATE INDEX IF NOT EXISTS idx_anomalie_tipo ON ANOMALIE(tipo_anomalia)",
        "CREATE INDEX IF NOT EXISTS idx_anomalie_stato ON ANOMALIE(stato)",
        "CREATE INDEX IF NOT EXISTS idx_anomalie_codice ON ANOMALIE(codice_anomalia)",

        "CREATE INDEX IF NOT EXISTS idx_farmacie_piva ON ANAGRAFICA_FARMACIE(partita_iva)",
        "CREATE INDEX IF NOT EXISTS idx_farmacie_citta ON ANAGRAFICA_FARMACIE(citta)",

        "CREATE INDEX IF NOT EXISTS idx_parafarmacie_piva ON ANAGRAFICA_PARAFARMACIE(partita_iva)",

        "CREATE INDEX IF NOT EXISTS idx_listini_vendor ON LISTINI_VENDOR(vendor)",
        "CREATE INDEX IF NOT EXISTS idx_listini_aic ON LISTINI_VENDOR(codice_aic)",

        "CREATE INDEX IF NOT EXISTS idx_sup_esp_testata ON SUPERVISIONE_ESPOSITORE(id_testata)",
        "CREATE INDEX IF NOT EXISTS idx_sup_esp_stato ON SUPERVISIONE_ESPOSITORE(stato)",
        "CREATE INDEX IF NOT EXISTS idx_sup_esp_pattern ON SUPERVISIONE_ESPOSITORE(pattern_signature)",

        "CREATE INDEX IF NOT EXISTS idx_sup_lst_testata ON SUPERVISIONE_LISTINO(id_testata)",
        "CREATE INDEX IF NOT EXISTS idx_sup_lst_stato ON SUPERVISIONE_LISTINO(stato)",
        "CREATE INDEX IF NOT EXISTS idx_sup_lst_pattern ON SUPERVISIONE_LISTINO(pattern_signature)",

        "CREATE INDEX IF NOT EXISTS idx_sup_lkp_testata ON SUPERVISIONE_LOOKUP(id_testata)",
        "CREATE INDEX IF NOT EXISTS idx_sup_lkp_stato ON SUPERVISIONE_LOOKUP(stato)",

        "CREATE INDEX IF NOT EXISTS idx_sup_aic_testata ON SUPERVISIONE_AIC(id_testata)",
        "CREATE INDEX IF NOT EXISTS idx_sup_aic_stato ON SUPERVISIONE_AIC(stato)",
        "CREATE INDEX IF NOT EXISTS idx_sup_aic_pattern ON SUPERVISIONE_AIC(pattern_signature)",

        "CREATE INDEX IF NOT EXISTS idx_sessioni_operatore ON USER_SESSIONS(id_operatore)",
        "CREATE INDEX IF NOT EXISTS idx_sessioni_jti ON USER_SESSIONS(token_jti)",

        "CREATE INDEX IF NOT EXISTS idx_log_operatore ON LOG_ATTIVITA(id_operatore)",
        "CREATE INDEX IF NOT EXISTS idx_log_timestamp ON LOG_ATTIVITA(timestamp)",
    ]

    for idx_sql in indexes:
        conn.execute(text(idx_sql))

    print("  Initial schema v10.1 created successfully")


def downgrade() -> None:
    """
    Drop all tables in reverse dependency order.
    WARNING: This will destroy all data!
    """
    conn = op.get_bind()

    # Drop tables in reverse dependency order
    tables = [
        # CRM & Email
        "CRM_CONTATTI", "EMAIL_MONITORAGGIO", "EMAIL_CONFIG",
        # System
        "PERMISSIONS_MATRIX", "TRACCIATI_EXPORT", "BACKUP_METADATA",
        # Criteri ML
        "CRITERI_ORDINARI_AIC", "CRITERI_ORDINARI_LOOKUP",
        "CRITERI_ORDINARI_LISTINO", "CRITERI_ORDINARI_ESPOSITORE",
        # Supervision
        "SUPERVISIONE_AIC", "SUPERVISIONE_LOOKUP",
        "SUPERVISIONE_LISTINO", "SUPERVISIONE_ESPOSITORE",
        # Listini
        "LISTINI_VENDOR",
        # Anagrafica
        "ANAGRAFICA_CLIENTI", "ANAGRAFICA_PARAFARMACIE", "ANAGRAFICA_FARMACIE",
        # Core Auth
        "LOG_ATTIVITA", "USER_SESSIONS", "OPERATORI",
        # Core Orders
        "ANOMALIE", "ORDINI_DETTAGLIO", "ORDINI_TESTATA",
        "ACQUISIZIONI", "VENDOR",
    ]

    for table in tables:
        conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))

    print("  All tables dropped")
