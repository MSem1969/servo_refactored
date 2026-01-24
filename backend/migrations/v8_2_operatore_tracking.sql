-- =============================================================================
-- SERV.O v8.2 - MIGRAZIONE TRACKING AZIONI OPERATORE
-- =============================================================================
-- Sistema di tracking comportamentale per analisi ML
--
-- OBIETTIVI:
-- 1. Tracciare tutte le azioni degli operatori
-- 2. Raccogliere dati per analisi pattern comportamentali
-- 3. Supportare future funzionalita ML (suggerimenti, automazioni)
--
-- ESECUZIONE:
-- psql -h localhost -U servo_user -d servo_db -f v8_2_operatore_tracking.sql
-- =============================================================================

-- =============================================================================
-- TABELLA PRINCIPALE: OPERATORE_AZIONI_LOG
-- =============================================================================

CREATE TABLE IF NOT EXISTS operatore_azioni_log (
    -- Identificatore
    id_azione SERIAL PRIMARY KEY,

    -- CHI: Operatore che ha eseguito l'azione
    id_operatore INTEGER NOT NULL,
    username VARCHAR(100) NOT NULL,
    ruolo VARCHAR(50) NOT NULL,

    -- COSA: Dettaglio azione
    sezione VARCHAR(50) NOT NULL,           -- DASHBOARD, DATABASE, REPORT, etc.
    azione VARCHAR(50) NOT NULL,            -- VIEW, FILTER, EXPORT, CONFIRM, etc.
    entita VARCHAR(100),                    -- ordine, anomalia, tracciato, etc.
    id_entita INTEGER,                      -- ID dell'entita se applicabile

    -- PARAMETRI: Filtri e opzioni usate (JSON per flessibilita)
    parametri JSONB,                        -- Filtri applicati, opzioni selezionate
    risultato JSONB,                        -- Risultato azione (count, totali, etc.)

    -- ESITO
    success BOOLEAN DEFAULT TRUE,           -- Azione completata con successo
    durata_ms INTEGER,                      -- Tempo di esecuzione in millisecondi

    -- QUANDO: Timestamp e campi derivati per analisi temporale
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    giorno_settimana INTEGER,               -- 0=Lun, 6=Dom (per pattern settimanali)
    ora_giorno INTEGER,                     -- 0-23 (per pattern giornalieri)
    settimana_anno INTEGER,                 -- 1-53 (per trend stagionali)

    -- CONTESTO: Per analisi sequenze
    session_id VARCHAR(50),                 -- Raggruppa azioni nella stessa sessione
    azione_precedente_id INTEGER,           -- FK per costruire catene di azioni

    -- CLIENT INFO
    ip_address VARCHAR(45),                 -- IPv4 o IPv6
    user_agent VARCHAR(500),                -- Browser/client info

    -- Constraint
    CONSTRAINT fk_operatore FOREIGN KEY (id_operatore)
        REFERENCES operatori(id_operatore) ON DELETE SET NULL,
    CONSTRAINT fk_azione_precedente FOREIGN KEY (azione_precedente_id)
        REFERENCES operatore_azioni_log(id_azione) ON DELETE SET NULL
);

-- =============================================================================
-- INDICI PER QUERY FREQUENTI
-- =============================================================================

-- Indice per query per operatore (analisi individuale)
CREATE INDEX IF NOT EXISTS idx_azioni_operatore
    ON operatore_azioni_log(id_operatore, timestamp DESC);

-- Indice per query per sezione (analisi per modulo)
CREATE INDEX IF NOT EXISTS idx_azioni_sezione
    ON operatore_azioni_log(sezione, timestamp DESC);

-- Indice per query per azione (analisi tipo operazione)
CREATE INDEX IF NOT EXISTS idx_azioni_tipo
    ON operatore_azioni_log(azione, timestamp DESC);

-- Indice per analisi temporale (pattern giornalieri/settimanali)
CREATE INDEX IF NOT EXISTS idx_azioni_temporale
    ON operatore_azioni_log(giorno_settimana, ora_giorno);

-- Indice per sessioni (analisi sequenze)
CREATE INDEX IF NOT EXISTS idx_azioni_sessione
    ON operatore_azioni_log(session_id, timestamp);

-- Indice per catene di azioni
CREATE INDEX IF NOT EXISTS idx_azioni_precedente
    ON operatore_azioni_log(azione_precedente_id);

-- Indice per ricerca parametri JSON (GIN per JSONB)
CREATE INDEX IF NOT EXISTS idx_azioni_parametri
    ON operatore_azioni_log USING GIN (parametri);

-- Indice per date range query
CREATE INDEX IF NOT EXISTS idx_azioni_timestamp
    ON operatore_azioni_log(timestamp DESC);

-- Indice composto per analisi comportamentale
CREATE INDEX IF NOT EXISTS idx_azioni_comportamento
    ON operatore_azioni_log(id_operatore, sezione, azione, timestamp DESC);


-- =============================================================================
-- VISTA: STATISTICHE GIORNALIERE PER OPERATORE
-- =============================================================================

CREATE OR REPLACE VIEW v_tracking_daily_stats AS
SELECT
    DATE(timestamp) AS data,
    id_operatore,
    username,
    sezione,
    azione,
    COUNT(*) AS count_azioni,
    AVG(durata_ms) AS avg_durata_ms,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) AS count_success,
    SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) AS count_error
FROM operatore_azioni_log
GROUP BY DATE(timestamp), id_operatore, username, sezione, azione
ORDER BY data DESC, id_operatore, sezione, azione;


-- =============================================================================
-- VISTA: PATTERN TEMPORALI (per analisi oraria)
-- =============================================================================

CREATE OR REPLACE VIEW v_tracking_hourly_pattern AS
SELECT
    id_operatore,
    username,
    giorno_settimana,
    ora_giorno,
    sezione,
    COUNT(*) AS count_azioni,
    ROUND(AVG(durata_ms)::numeric, 0) AS avg_durata_ms
FROM operatore_azioni_log
WHERE timestamp > CURRENT_DATE - INTERVAL '30 days'
GROUP BY id_operatore, username, giorno_settimana, ora_giorno, sezione
ORDER BY id_operatore, giorno_settimana, ora_giorno;


-- =============================================================================
-- VISTA: SEQUENZE AZIONI FREQUENTI
-- =============================================================================

CREATE OR REPLACE VIEW v_tracking_sequences AS
SELECT
    a1.sezione AS sezione_1,
    a1.azione AS azione_1,
    a2.sezione AS sezione_2,
    a2.azione AS azione_2,
    COUNT(*) AS frequenza,
    ROUND(AVG(EXTRACT(EPOCH FROM (a2.timestamp - a1.timestamp)) * 1000)::numeric, 0) AS avg_intervallo_ms
FROM operatore_azioni_log a1
JOIN operatore_azioni_log a2 ON a2.azione_precedente_id = a1.id_azione
WHERE a1.timestamp > CURRENT_DATE - INTERVAL '30 days'
GROUP BY a1.sezione, a1.azione, a2.sezione, a2.azione
HAVING COUNT(*) >= 5
ORDER BY frequenza DESC;


-- =============================================================================
-- VISTA: FILTRI REPORT PIU USATI
-- =============================================================================

CREATE OR REPLACE VIEW v_tracking_report_filters AS
SELECT
    id_operatore,
    username,
    parametri->>'vendors' AS vendors,
    parametri->>'stati' AS stati,
    parametri->>'tipo_prodotto' AS tipo_prodotto,
    parametri->>'depositi' AS depositi,
    COUNT(*) AS utilizzi,
    MAX(timestamp) AS ultimo_utilizzo
FROM operatore_azioni_log
WHERE sezione = 'REPORT'
  AND azione IN ('FILTER', 'EXPORT_EXCEL', 'PREVIEW')
  AND parametri IS NOT NULL
  AND timestamp > CURRENT_DATE - INTERVAL '90 days'
GROUP BY id_operatore, username,
         parametri->>'vendors',
         parametri->>'stati',
         parametri->>'tipo_prodotto',
         parametri->>'depositi'
HAVING COUNT(*) >= 3
ORDER BY utilizzi DESC;


-- =============================================================================
-- VISTA: RIEPILOGO ATTIVITA OPERATORI
-- =============================================================================

CREATE OR REPLACE VIEW v_tracking_operator_summary AS
SELECT
    o.id_operatore,
    o.username,
    o.ruolo,
    COUNT(DISTINCT DATE(a.timestamp)) AS giorni_attivi_30gg,
    COUNT(*) FILTER (WHERE a.timestamp > CURRENT_DATE - INTERVAL '30 days') AS azioni_30gg,
    COUNT(*) FILTER (WHERE a.timestamp > CURRENT_DATE - INTERVAL '7 days') AS azioni_7gg,
    COUNT(*) FILTER (WHERE DATE(a.timestamp) = CURRENT_DATE) AS azioni_oggi,
    MODE() WITHIN GROUP (ORDER BY a.sezione) AS sezione_preferita,
    MAX(a.timestamp) AS ultima_azione
FROM operatori o
LEFT JOIN operatore_azioni_log a ON o.id_operatore = a.id_operatore
    AND a.timestamp > CURRENT_DATE - INTERVAL '30 days'
WHERE o.attivo = TRUE
GROUP BY o.id_operatore, o.username, o.ruolo
ORDER BY azioni_30gg DESC;


-- =============================================================================
-- FUNZIONE: CLEANUP VECCHI RECORD (retention 180 giorni)
-- =============================================================================

CREATE OR REPLACE FUNCTION cleanup_tracking_log()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM operatore_azioni_log
    WHERE timestamp < CURRENT_DATE - INTERVAL '180 days';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;


-- =============================================================================
-- COMMENTI TABELLA
-- =============================================================================

COMMENT ON TABLE operatore_azioni_log IS
'Tracking comportamentale operatori per analisi ML.
Raccoglie tutte le azioni con contesto temporale e parametri.
Retention: 180 giorni (cleanup automatico).';

COMMENT ON COLUMN operatore_azioni_log.parametri IS
'Parametri/filtri usati (JSONB). Es: {"vendors": ["ANGELINI"], "stati": ["CONFERMATO"]}';

COMMENT ON COLUMN operatore_azioni_log.risultato IS
'Risultato azione (JSONB). Es: {"total_count": 150, "exported": true}';

COMMENT ON COLUMN operatore_azioni_log.session_id IS
'ID sessione per raggruppare azioni consecutive (timeout 30 min)';

COMMENT ON COLUMN operatore_azioni_log.azione_precedente_id IS
'FK alla azione precedente per costruire catene/sequenze';


-- =============================================================================
-- GRANT PERMESSI
-- =============================================================================

-- Assicura che l'utente applicativo possa scrivere
-- GRANT ALL ON operatore_azioni_log TO servo_user;
-- GRANT USAGE, SELECT ON SEQUENCE operatore_azioni_log_id_azione_seq TO servo_user;


-- =============================================================================
-- OUTPUT CONFERMA
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '=== MIGRAZIONE v8.2 TRACKING COMPLETATA ===';
    RAISE NOTICE 'Tabella: operatore_azioni_log';
    RAISE NOTICE 'Viste: v_tracking_daily_stats, v_tracking_hourly_pattern, v_tracking_sequences, v_tracking_report_filters, v_tracking_operator_summary';
    RAISE NOTICE 'Funzione: cleanup_tracking_log()';
END $$;
