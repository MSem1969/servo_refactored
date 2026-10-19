-- =============================================================================
-- v21 - Motivazione dell'archiviazione ordine
-- =============================================================================
-- L'archiviazione di un ordine richiede ora una motivazione (min. 3 caratteri),
-- salvata con chi e quando ha archiviato. Fino al 2026-10 l'archiviazione
-- sovrascriveva data_validazione/validato_da e registrava quasi sempre
-- l'operatore "admin" (default dell'endpoint).
--
-- NON si usa note_ordine: finisce nel tracciato TO_T (OrderAnnotation).
--
-- Solo colonne nuove, vuote: gli ordini gia' archiviati non vengono toccati.
-- Al ripristino dell'ordine i tre campi tornano NULL (lo storico resta
-- nell'audit, log_modifiche).
--
-- Applicare con:  psql -U servo -d servo -f v21_ordini_motivo_archiviazione.sql
-- =============================================================================

BEGIN;

ALTER TABLE public.ordini_testata ADD COLUMN IF NOT EXISTS motivo_archiviazione TEXT;
ALTER TABLE public.ordini_testata ADD COLUMN IF NOT EXISTS data_archiviazione TIMESTAMP;
ALTER TABLE public.ordini_testata ADD COLUMN IF NOT EXISTS archiviato_da VARCHAR(100);

COMMIT;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'ordini_testata'
  AND column_name IN ('motivo_archiviazione', 'data_archiviazione', 'archiviato_da')
ORDER BY column_name;
