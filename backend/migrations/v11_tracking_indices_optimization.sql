-- =============================================================================
-- SERV.O v11.0 - TRACKING INDICES OPTIMIZATION
-- =============================================================================
-- TIER 3.4: Ottimizza indici per operatore_azioni_log
--
-- PROBLEMA: Le viste usano DATE(timestamp) che non sfruttano l'indice timestamp
-- SOLUZIONE: Aggiungere indici funzionali e partial per query frequenti
--
-- ESECUZIONE:
-- psql -h localhost -U servo_user -d servo_db -f v11_tracking_indices_optimization.sql
-- =============================================================================

-- =============================================================================
-- 1. INDICE FUNZIONALE PER DATE(timestamp)
-- =============================================================================
-- Usato da: v_tracking_daily_stats
-- Query tipo: GROUP BY DATE(timestamp)

CREATE INDEX IF NOT EXISTS idx_azioni_data
    ON operatore_azioni_log (DATE(timestamp));

COMMENT ON INDEX idx_azioni_data IS
'v11.0: Indice funzionale per query aggregate per data (v_tracking_daily_stats)';


-- =============================================================================
-- 2. INDICE PARZIALE PER REPORT SECTION
-- =============================================================================
-- Usato da: v_tracking_report_filters
-- Query tipo: WHERE sezione = 'REPORT' AND azione IN (...)

CREATE INDEX IF NOT EXISTS idx_azioni_report_filters
    ON operatore_azioni_log (id_operatore, timestamp DESC)
    WHERE sezione = 'REPORT' AND azione IN ('FILTER', 'EXPORT_EXCEL', 'PREVIEW');

COMMENT ON INDEX idx_azioni_report_filters IS
'v11.0: Indice parziale per analisi filtri report (v_tracking_report_filters)';


-- =============================================================================
-- 3. INDICE PARZIALE PER ULTIMI 30 GIORNI
-- =============================================================================
-- Usato da: v_tracking_hourly_pattern, v_tracking_sequences
-- Query tipo: WHERE timestamp > CURRENT_DATE - INTERVAL '30 days'
--
-- NOTA: Questo indice richiede ricostruzione periodica (es. settimanale)
-- poiché la condizione è relativa alla data corrente.

CREATE INDEX IF NOT EXISTS idx_azioni_recenti
    ON operatore_azioni_log (id_operatore, sezione, giorno_settimana, ora_giorno)
    WHERE timestamp > NOW() - INTERVAL '30 days';

COMMENT ON INDEX idx_azioni_recenti IS
'v11.0: Indice parziale per azioni ultime 30 giorni - RICHIEDE REINDEX PERIODICO';


-- =============================================================================
-- 4. INDICE PER ANALISI SEQUENZE
-- =============================================================================
-- Usato da: v_tracking_sequences (JOIN su azione_precedente_id)
-- Ottimizza la JOIN condition

CREATE INDEX IF NOT EXISTS idx_azioni_seq_join
    ON operatore_azioni_log (azione_precedente_id, sezione, azione)
    WHERE azione_precedente_id IS NOT NULL;

COMMENT ON INDEX idx_azioni_seq_join IS
'v11.0: Indice parziale per analisi sequenze (v_tracking_sequences)';


-- =============================================================================
-- 5. INDICE PER SUCCESS RATE ANALYSIS
-- =============================================================================
-- Per query di analisi errori/successi

CREATE INDEX IF NOT EXISTS idx_azioni_success
    ON operatore_azioni_log (success, sezione, azione, timestamp DESC);

COMMENT ON INDEX idx_azioni_success IS
'v11.0: Indice per analisi success rate per sezione/azione';


-- =============================================================================
-- 6. INDICE COVERING PER OPERATOR SUMMARY
-- =============================================================================
-- Usato da: v_tracking_operator_summary
-- Include colonne selezionate per index-only scan

CREATE INDEX IF NOT EXISTS idx_azioni_operator_summary
    ON operatore_azioni_log (id_operatore, timestamp DESC)
    INCLUDE (sezione, azione);

COMMENT ON INDEX idx_azioni_operator_summary IS
'v11.0: Indice covering per summary operatore (include sezione, azione)';


-- =============================================================================
-- 7. FUNZIONE MANUTENZIONE INDICI
-- =============================================================================
-- Ricostruisce indici parziali che dipendono da date relative

CREATE OR REPLACE FUNCTION reindex_tracking_partial()
RETURNS VOID AS $$
BEGIN
    -- Ricostruisci indice parziale per ultimi 30 giorni
    REINDEX INDEX CONCURRENTLY idx_azioni_recenti;

    RAISE NOTICE 'Reindex idx_azioni_recenti completato';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION reindex_tracking_partial() IS
'v11.0: Ricostruisce indici parziali con condizioni relative a date. Eseguire settimanalmente.';


-- =============================================================================
-- 8. ANALISI STATISTICHE (per query planner)
-- =============================================================================

ANALYZE operatore_azioni_log;


-- =============================================================================
-- OUTPUT CONFERMA
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '=== MIGRAZIONE v11.0 TRACKING INDICES COMPLETATA ===';
    RAISE NOTICE 'Nuovi indici:';
    RAISE NOTICE '  - idx_azioni_data (funzionale su DATE)';
    RAISE NOTICE '  - idx_azioni_report_filters (parziale per REPORT)';
    RAISE NOTICE '  - idx_azioni_recenti (parziale 30 giorni)';
    RAISE NOTICE '  - idx_azioni_seq_join (per sequences)';
    RAISE NOTICE '  - idx_azioni_success (per analisi errori)';
    RAISE NOTICE '  - idx_azioni_operator_summary (covering index)';
    RAISE NOTICE 'Funzione: reindex_tracking_partial() per manutenzione';
END $$;
