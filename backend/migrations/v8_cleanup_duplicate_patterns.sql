-- =============================================================================
-- SERV.O v8.1 - PULIZIA PATTERN DUPLICATI LISTINO
-- =============================================================================
-- Rimuove pattern duplicati per stesso AIC/vendor mantenendo quello con più approvazioni
-- =============================================================================

-- 1. Visualizza pattern duplicati per AIC/vendor (per verifica)
SELECT
    codice_aic,
    vendor,
    COUNT(*) AS num_patterns,
    STRING_AGG(pattern_signature, ', ') AS signatures,
    STRING_AGG(pattern_descrizione, ' | ') AS descrizioni,
    MAX(count_approvazioni) AS max_approvazioni,
    BOOL_OR(is_ordinario) AS any_ordinario
FROM criteri_ordinari_listino
WHERE codice_aic IS NOT NULL
GROUP BY codice_aic, vendor
HAVING COUNT(*) > 1;

-- 2. Per ogni gruppo di duplicati, tieni solo quello con più approvazioni
-- Prima identifichiamo i pattern da mantenere (quello con max approvazioni per ogni AIC/vendor)
WITH ranked_patterns AS (
    SELECT
        pattern_signature,
        codice_aic,
        vendor,
        count_approvazioni,
        is_ordinario,
        ROW_NUMBER() OVER (
            PARTITION BY codice_aic, vendor
            ORDER BY count_approvazioni DESC, is_ordinario DESC, pattern_signature
        ) AS rn
    FROM criteri_ordinari_listino
    WHERE codice_aic IS NOT NULL
),
patterns_to_delete AS (
    SELECT pattern_signature
    FROM ranked_patterns
    WHERE rn > 1
)
-- Elimina i duplicati (commentato per sicurezza - eseguire manualmente dopo verifica)
-- DELETE FROM criteri_ordinari_listino
-- WHERE pattern_signature IN (SELECT pattern_signature FROM patterns_to_delete);

-- 3. Mostra pattern che verranno eliminati
SELECT 'PATTERN DA ELIMINARE:' AS info;
SELECT
    col.pattern_signature,
    col.codice_aic,
    col.vendor,
    col.pattern_descrizione,
    col.count_approvazioni,
    col.is_ordinario
FROM criteri_ordinari_listino col
WHERE col.pattern_signature IN (
    SELECT pattern_signature
    FROM (
        SELECT
            pattern_signature,
            ROW_NUMBER() OVER (
                PARTITION BY codice_aic, vendor
                ORDER BY count_approvazioni DESC, is_ordinario DESC, pattern_signature
            ) AS rn
        FROM criteri_ordinari_listino
        WHERE codice_aic IS NOT NULL
    ) ranked
    WHERE rn > 1
);

-- 4. Mostra pattern che verranno mantenuti
SELECT 'PATTERN DA MANTENERE:' AS info;
SELECT
    col.pattern_signature,
    col.codice_aic,
    col.vendor,
    col.pattern_descrizione,
    col.count_approvazioni,
    col.is_ordinario
FROM criteri_ordinari_listino col
WHERE col.pattern_signature IN (
    SELECT pattern_signature
    FROM (
        SELECT
            pattern_signature,
            ROW_NUMBER() OVER (
                PARTITION BY codice_aic, vendor
                ORDER BY count_approvazioni DESC, is_ordinario DESC, pattern_signature
            ) AS rn
        FROM criteri_ordinari_listino
        WHERE codice_aic IS NOT NULL
    ) ranked
    WHERE rn = 1
);
