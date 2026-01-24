-- =============================================================================
-- SERV.O v7.0 - COLONNE ESTRATTE ORDINI_TESTATA
-- =============================================================================
-- Aggiunge colonne per preservare i valori originali estratti dal PDF
-- Questi valori rimangono immutabili anche dopo lookup/modifica manuale
-- =============================================================================

-- Colonne estratte (immutabili - valori originali dal PDF)
ALTER TABLE ordini_testata ADD COLUMN IF NOT EXISTS ragione_sociale_1_estratta VARCHAR(100);
ALTER TABLE ordini_testata ADD COLUMN IF NOT EXISTS indirizzo_estratto VARCHAR(100);
ALTER TABLE ordini_testata ADD COLUMN IF NOT EXISTS cap_estratto VARCHAR(10);
ALTER TABLE ordini_testata ADD COLUMN IF NOT EXISTS citta_estratta VARCHAR(100);
ALTER TABLE ordini_testata ADD COLUMN IF NOT EXISTS provincia_estratta VARCHAR(3);
ALTER TABLE ordini_testata ADD COLUMN IF NOT EXISTS data_ordine_estratta DATE;
ALTER TABLE ordini_testata ADD COLUMN IF NOT EXISTS data_consegna_estratta DATE;

-- Fonte anagrafica (FARMACIA, PARAFARMACIA, MANUALE)
ALTER TABLE ordini_testata ADD COLUMN IF NOT EXISTS fonte_anagrafica VARCHAR(20);

-- Popola le colonne estratte con i valori attuali per ordini esistenti
UPDATE ordini_testata
SET ragione_sociale_1_estratta = ragione_sociale_1,
    indirizzo_estratto = indirizzo,
    cap_estratto = cap,
    citta_estratta = citta,
    provincia_estratta = provincia,
    data_ordine_estratta = data_ordine,
    data_consegna_estratta = data_consegna
WHERE ragione_sociale_1_estratta IS NULL;

-- Verifica
SELECT 'Colonne aggiunte:' AS info;
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'ordini_testata'
  AND column_name LIKE '%_estratt%'
ORDER BY ordinal_position;
