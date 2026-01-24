-- =============================================================================
-- MIGRAZIONE v10.1: Aggiunge colonne mancanti a crm_tickets
-- =============================================================================
-- Problema: Le colonne pagina_origine e pagina_dettaglio non esistono
-- Soluzione: Aggiungerle se non presenti
-- =============================================================================

-- Verifica e aggiungi colonna pagina_origine
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'crm_tickets' AND column_name = 'pagina_origine'
    ) THEN
        ALTER TABLE crm_tickets ADD COLUMN pagina_origine VARCHAR(50);
        RAISE NOTICE 'Colonna pagina_origine aggiunta a crm_tickets';
    ELSE
        RAISE NOTICE 'Colonna pagina_origine già esistente';
    END IF;
END $$;

-- Verifica e aggiungi colonna pagina_dettaglio
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'crm_tickets' AND column_name = 'pagina_dettaglio'
    ) THEN
        ALTER TABLE crm_tickets ADD COLUMN pagina_dettaglio VARCHAR(200);
        RAISE NOTICE 'Colonna pagina_dettaglio aggiunta a crm_tickets';
    ELSE
        RAISE NOTICE 'Colonna pagina_dettaglio già esistente';
    END IF;
END $$;

-- Commenti
COMMENT ON COLUMN crm_tickets.pagina_origine IS 'Pagina da cui è stato aperto il ticket (es: dashboard, ordine-detail)';
COMMENT ON COLUMN crm_tickets.pagina_dettaglio IS 'Dettaglio contesto (es: Ordine #12345)';
