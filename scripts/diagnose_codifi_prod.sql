-- =============================================================================
-- DIAGNOSTICA ESTRAZIONE CODIFI IN PRODUZIONE
-- =============================================================================
-- Confronta l'estrazione di un PDF CODIFI in produzione con la baseline
-- locale (mancata_estrazione.pdf, 34 ordini O-1465xx).
--
-- Uso (Coolify container DB):
--   psql -U <user> -d <db> -f diagnose_codifi_prod.sql
--   oppure copia/incolla nel client psql.
--
-- Cosa verifica:
--   1. Identifica l'acquisizione del PDF (per hash, fallback nome file)
--   2. Conta ordini estratti vs 34 attesi
--   3. Confronta righe per ordine vs baseline locale
--   4. Verifica presenza/assenza della riga REFLUZERO (AIC 983034315)
--      che era il bug noto: regex parser scartava codici che non
--      iniziano con 0
-- =============================================================================

\pset border 2
\pset format aligned
\set ON_ERROR_STOP off

-- -----------------------------------------------------------------------------
-- SEZIONE 1: Identificazione acquisizione
-- -----------------------------------------------------------------------------

\echo '== 1. ACQUISIZIONI CANDIDATE (per hash o nome file) =='

SELECT
    a.id_acquisizione,
    a.nome_file_originale,
    a.dimensione_bytes,
    a.num_ordini_estratti,
    a.stato,
    a.data_upload,
    LEFT(a.hash_file, 16) AS hash_short,
    CASE
        WHEN a.hash_file = '7137b21401a185a4760b6f2a1adb29b079952fd4d6b6c80eb024c733e3eb7d35'
            THEN 'HASH MATCH (stesso file del locale)'
        WHEN a.nome_file_originale ILIKE '%mancata_estrazione%'
            THEN 'NOME MATCH'
        WHEN a.dimensione_bytes = 105660
            THEN 'DIMENSIONE MATCH'
        ELSE 'CANDIDATO POTENZIALE'
    END AS criterio_match
FROM acquisizioni a
LEFT JOIN vendor v ON v.id_vendor = a.id_vendor
WHERE
    a.hash_file = '7137b21401a185a4760b6f2a1adb29b079952fd4d6b6c80eb024c733e3eb7d35'
    OR a.nome_file_originale ILIKE '%mancata_estrazione%'
    OR (v.codice_vendor = 'CODIFI' AND a.dimensione_bytes BETWEEN 105000 AND 106000)
ORDER BY a.data_upload DESC;

-- -----------------------------------------------------------------------------
-- SEZIONE 2: Per ogni acquisizione candidata, conteggio ordini
-- -----------------------------------------------------------------------------

\echo ''
\echo '== 2. ORDINI ESTRATTI PER OGNI ACQUISIZIONE CANDIDATA =='

SELECT
    a.id_acquisizione,
    a.nome_file_originale,
    a.num_ordini_estratti AS num_dichiarati,
    COUNT(ot.id_testata) AS num_effettivi,
    SUM(ot.righe_totali) AS righe_totali_somma,
    34 AS num_ordini_atteso_baseline,
    34 - COUNT(ot.id_testata) AS diff_vs_baseline
FROM acquisizioni a
LEFT JOIN ordini_testata ot ON ot.id_acquisizione = a.id_acquisizione
LEFT JOIN vendor v ON v.id_vendor = a.id_vendor
WHERE
    a.hash_file = '7137b21401a185a4760b6f2a1adb29b079952fd4d6b6c80eb024c733e3eb7d35'
    OR a.nome_file_originale ILIKE '%mancata_estrazione%'
    OR (v.codice_vendor = 'CODIFI' AND a.dimensione_bytes BETWEEN 105000 AND 106000)
GROUP BY a.id_acquisizione, a.nome_file_originale, a.num_ordini_estratti
ORDER BY a.id_acquisizione DESC;

-- -----------------------------------------------------------------------------
-- SEZIONE 3: Confronto righe per ordine vs baseline locale
-- -----------------------------------------------------------------------------

\echo ''
\echo '== 3. CONFRONTO RIGHE PER ORDINE (vs baseline locale, 34 ordini) =='
\echo '    (limita a tutte le acquisizioni candidate)'
\echo ''

WITH baseline_locale (numero_ordine, righe_attese) AS (
    VALUES
        ('O-146520', 20), ('O-146522', 27), ('O-146523', 23),
        ('O-146524', 41), ('O-146525', 27), ('O-146527', 23),
        ('O-146531', 12), ('O-146532', 30), ('O-146538', 29),
        ('O-146539', 28), ('O-146544', 33), ('O-146548', 22),
        ('O-146555', 12), ('O-146558', 20), ('O-146560', 21),
        ('O-146562',  9), ('O-146571', 22), ('O-146590', 31),
        ('O-146595', 12), ('O-146598', 24), ('O-146605', 34),
        ('O-146607', 28), ('O-146608', 29), ('O-146609', 25),
        ('O-146610', 37), ('O-146614', 17), ('O-146624', 20),
        ('O-146632', 21), ('O-146635', 17), ('O-146642', 20),
        ('O-146661',  1), ('O-146664', 26), ('O-146690', 17),
        ('O-146747', 25)
),
acquisizioni_target AS (
    SELECT a.id_acquisizione
    FROM acquisizioni a
    LEFT JOIN vendor v ON v.id_vendor = a.id_vendor
    WHERE
        a.hash_file = '7137b21401a185a4760b6f2a1adb29b079952fd4d6b6c80eb024c733e3eb7d35'
        OR a.nome_file_originale ILIKE '%mancata_estrazione%'
        OR (v.codice_vendor = 'CODIFI' AND a.dimensione_bytes BETWEEN 105000 AND 106000)
)
SELECT
    bl.numero_ordine,
    bl.righe_attese,
    ot.righe_totali AS righe_prod,
    (ot.righe_totali - bl.righe_attese) AS diff,
    ot.id_testata,
    ot.id_acquisizione,
    ot.stato
FROM baseline_locale bl
LEFT JOIN ordini_testata ot
    ON ot.numero_ordine_vendor = bl.numero_ordine
    AND ot.id_acquisizione IN (SELECT id_acquisizione FROM acquisizioni_target)
ORDER BY bl.numero_ordine;

-- -----------------------------------------------------------------------------
-- SEZIONE 4: Ordini attesi MANCANTI in produzione
-- -----------------------------------------------------------------------------

\echo ''
\echo '== 4. ORDINI BASELINE NON TROVATI IN PRODUZIONE =='

WITH baseline_locale (numero_ordine) AS (
    VALUES
        ('O-146520'), ('O-146522'), ('O-146523'), ('O-146524'),
        ('O-146525'), ('O-146527'), ('O-146531'), ('O-146532'),
        ('O-146538'), ('O-146539'), ('O-146544'), ('O-146548'),
        ('O-146555'), ('O-146558'), ('O-146560'), ('O-146562'),
        ('O-146571'), ('O-146590'), ('O-146595'), ('O-146598'),
        ('O-146605'), ('O-146607'), ('O-146608'), ('O-146609'),
        ('O-146610'), ('O-146614'), ('O-146624'), ('O-146632'),
        ('O-146635'), ('O-146642'), ('O-146661'), ('O-146664'),
        ('O-146690'), ('O-146747')
),
acquisizioni_target AS (
    SELECT a.id_acquisizione
    FROM acquisizioni a
    LEFT JOIN vendor v ON v.id_vendor = a.id_vendor
    WHERE
        a.hash_file = '7137b21401a185a4760b6f2a1adb29b079952fd4d6b6c80eb024c733e3eb7d35'
        OR a.nome_file_originale ILIKE '%mancata_estrazione%'
        OR (v.codice_vendor = 'CODIFI' AND a.dimensione_bytes BETWEEN 105000 AND 106000)
)
SELECT bl.numero_ordine AS ordine_mancante
FROM baseline_locale bl
WHERE NOT EXISTS (
    SELECT 1
    FROM ordini_testata ot
    WHERE ot.numero_ordine_vendor = bl.numero_ordine
      AND ot.id_acquisizione IN (SELECT id_acquisizione FROM acquisizioni_target)
)
ORDER BY bl.numero_ordine;

-- -----------------------------------------------------------------------------
-- SEZIONE 5: Verifica REFLUZERO (AIC 983034315) - bug regex CODIFI
-- -----------------------------------------------------------------------------

\echo ''
\echo '== 5. RIGA REFLUZERO (AIC 983034315) - presente nei 5 ordini? =='
\echo '   In locale (PRE-fix) era ASSENTE in:'
\echo '     O-146520, O-146524, O-146548, O-146555, O-146610'
\echo '   POST-fix locale: presente in tutti e 5'

WITH baseline_refluzero (numero_ordine) AS (
    VALUES ('O-146520'), ('O-146524'), ('O-146548'), ('O-146555'), ('O-146610')
),
acquisizioni_target AS (
    SELECT a.id_acquisizione
    FROM acquisizioni a
    LEFT JOIN vendor v ON v.id_vendor = a.id_vendor
    WHERE
        a.hash_file = '7137b21401a185a4760b6f2a1adb29b079952fd4d6b6c80eb024c733e3eb7d35'
        OR a.nome_file_originale ILIKE '%mancata_estrazione%'
        OR (v.codice_vendor = 'CODIFI' AND a.dimensione_bytes BETWEEN 105000 AND 106000)
)
SELECT
    br.numero_ordine,
    ot.id_testata,
    ot.righe_totali,
    EXISTS (
        SELECT 1 FROM ordini_dettaglio od
        WHERE od.id_testata = ot.id_testata
          AND od.codice_aic = '983034315'
    ) AS refluzero_presente
FROM baseline_refluzero br
LEFT JOIN ordini_testata ot
    ON ot.numero_ordine_vendor = br.numero_ordine
    AND ot.id_acquisizione IN (SELECT id_acquisizione FROM acquisizioni_target)
ORDER BY br.numero_ordine;

-- -----------------------------------------------------------------------------
-- SEZIONE 6: Quanti codici AIC 9-cifre NON inizianti con 0 (parafarmaci)
-- -----------------------------------------------------------------------------

\echo ''
\echo '== 6. CODICI AIC NON-0xxxxxxxx (parafarmaci) presenti nelle CODIFI =='
\echo '   In ambiente locale POST-fix: 5 occorrenze (tutte 983034315)'
\echo '   Se in produzione = 0, il bug del regex e'' presente.'

SELECT
    od.codice_aic,
    od.descrizione,
    COUNT(*) AS occorrenze,
    STRING_AGG(DISTINCT ot.numero_ordine_vendor, ', ' ORDER BY ot.numero_ordine_vendor) AS in_ordini
FROM ordini_dettaglio od
JOIN ordini_testata ot ON ot.id_testata = od.id_testata
JOIN acquisizioni a ON a.id_acquisizione = ot.id_acquisizione
JOIN vendor v ON v.id_vendor = a.id_vendor
WHERE v.codice_vendor = 'CODIFI'
  AND od.codice_aic ~ '^[1-9]\d{8}$'
  AND (
      a.hash_file = '7137b21401a185a4760b6f2a1adb29b079952fd4d6b6c80eb024c733e3eb7d35'
      OR a.nome_file_originale ILIKE '%mancata_estrazione%'
      OR a.dimensione_bytes BETWEEN 105000 AND 106000
  )
GROUP BY od.codice_aic, od.descrizione
ORDER BY occorrenze DESC, od.codice_aic;

\echo ''
\echo '== FINE DIAGNOSTICA =='
