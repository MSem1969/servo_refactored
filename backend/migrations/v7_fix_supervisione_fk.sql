-- =============================================================================
-- SERV.O v7.0 - FIX FK supervisione_listino.id_dettaglio
-- =============================================================================
-- Modifica il vincolo FK per permettere ON DELETE SET NULL
-- Questo permette l'eliminazione di righe ordine mantenendo lo storico supervisione
-- =============================================================================

-- 1. Rimuovi vincolo esistente (se esiste)
ALTER TABLE supervisione_listino
DROP CONSTRAINT IF EXISTS supervisione_listino_id_dettaglio_fkey;

-- 2. Ricrea con ON DELETE SET NULL
ALTER TABLE supervisione_listino
ADD CONSTRAINT supervisione_listino_id_dettaglio_fkey
FOREIGN KEY (id_dettaglio)
REFERENCES ordini_dettaglio(id_dettaglio)
ON DELETE SET NULL;

-- 3. Verifica
SELECT 'Vincolo ricreato:' AS info;
SELECT conname, confdeltype
FROM pg_constraint
WHERE conname = 'supervisione_listino_id_dettaglio_fkey';
-- confdeltype: 'n' = SET NULL, 'c' = CASCADE, 'a' = NO ACTION
