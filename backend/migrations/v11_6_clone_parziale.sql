-- =============================================================================
-- SERV.O v11.6 - CONSEGNE RIPARTITE (CLONE PARZIALE)
-- =============================================================================
-- Quando un ordine viene esportato parzialmente SENZA archiviare le righe
-- non evase, viene generato automaticamente un "clone parziale": una nuova
-- testata con suffisso .2/.3/... (sul numero_ordine_vendor) che contiene solo
-- le righe residue in stato ESTRATTO. Il parent resta integro con righe miste.
--
-- Modifiche:
-- 1. Colonna is_clone_parziale: discrimina i cloni dai duplicati PDF (che
--    riusano id_testata_originale)
-- 2. Indice parziale per ricerca rapida cloni di un ordine originale
-- =============================================================================

ALTER TABLE ordini_testata
ADD COLUMN IF NOT EXISTS is_clone_parziale BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_ordini_clone_parziale
ON ordini_testata(id_testata_originale)
WHERE is_clone_parziale = TRUE;

COMMENT ON COLUMN ordini_testata.is_clone_parziale IS
'TRUE se la testata e'' un clone generato da export parziale (consegna ripartita). id_testata_originale punta al parent originale (non al clone precedente nella catena).';
