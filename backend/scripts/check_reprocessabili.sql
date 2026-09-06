-- Quante acquisizioni MENARINI sono riprocessabili, senza lanciare lo script.
--
-- Stessa guardia di scripts/reprocess_vendor.py::motivi_intoccabile, in SQL:
-- serve quando si ha psql sul container del database ma non il backend, o
-- quando dal terminale remoto non si riesce a copiare l'output.
--
--   psql -U servo -d servo -f check_reprocessabili.sql
--
-- oppure, per incollare tutto in una volta:
--   docker exec -i <container> psql -U servo -d servo < check_reprocessabili.sql
--
-- E' di sola lettura: non modifica nulla.

\pset pager off

-- 1) Riga unica, pensata per essere letta o fotografata
WITH decise AS (
  SELECT id_testata FROM supervisione_aic        WHERE stato NOT IN ('PENDING','ARCHIVED')
  UNION SELECT id_testata FROM supervisione_lookup     WHERE stato NOT IN ('PENDING','ARCHIVED')
  UNION SELECT id_testata FROM supervisione_listino    WHERE stato NOT IN ('PENDING','ARCHIVED')
  UNION SELECT id_testata FROM supervisione_espositore WHERE stato NOT IN ('PENDING','ARCHIVED')
  UNION SELECT id_testata FROM supervisione_erp        WHERE stato NOT IN ('PENDING','ARCHIVED')
), acq AS (
  SELECT t.id_acquisizione,
         count(*) AS ordini,
         count(*) FILTER (
           WHERE t.stato NOT IN ('ESTRATTO','ANOMALIA','ARCHIVIATO')
              OR t.lookup_method = 'MANUALE'
              OR t.id_cliente_manuale IS NOT NULL
              OR EXISTS (SELECT 1 FROM esportazioni_dettaglio e WHERE e.id_testata = t.id_testata)
              OR EXISTS (SELECT 1 FROM decise d WHERE d.id_testata = t.id_testata)
         ) AS bloccanti
  FROM ordini_testata t
  JOIN vendor v ON v.id_vendor = t.id_vendor
  WHERE v.codice_vendor = 'MENARINI'
  GROUP BY 1
)
SELECT 'acq=' || count(*)
    || ' ok='     || count(*) FILTER (WHERE bloccanti = 0)
    || ' skip='   || count(*) FILTER (WHERE bloccanti > 0)
    || ' ordini=' || sum(ordini)
    || ' bloccanti=' || sum(bloccanti) AS riepilogo
FROM acq;

-- 2) Dettaglio dei motivi, solo se qualcosa e' bloccato
WITH decise AS (
  SELECT id_testata FROM supervisione_aic        WHERE stato NOT IN ('PENDING','ARCHIVED')
  UNION SELECT id_testata FROM supervisione_lookup     WHERE stato NOT IN ('PENDING','ARCHIVED')
  UNION SELECT id_testata FROM supervisione_listino    WHERE stato NOT IN ('PENDING','ARCHIVED')
  UNION SELECT id_testata FROM supervisione_espositore WHERE stato NOT IN ('PENDING','ARCHIVED')
  UNION SELECT id_testata FROM supervisione_erp        WHERE stato NOT IN ('PENDING','ARCHIVED')
)
SELECT t.id_acquisizione AS acq,
       count(*) FILTER (WHERE t.stato NOT IN ('ESTRATTO','ANOMALIA','ARCHIVIATO')) AS lavorati,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM esportazioni_dettaglio e WHERE e.id_testata = t.id_testata)) AS esportati,
       count(*) FILTER (WHERE t.lookup_method = 'MANUALE' OR t.id_cliente_manuale IS NOT NULL) AS manuali,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM decise d WHERE d.id_testata = t.id_testata)) AS sup_decise
FROM ordini_testata t
JOIN vendor v ON v.id_vendor = t.id_vendor
WHERE v.codice_vendor = 'MENARINI'
GROUP BY 1
HAVING count(*) FILTER (
         WHERE t.stato NOT IN ('ESTRATTO','ANOMALIA','ARCHIVIATO')
            OR t.lookup_method = 'MANUALE'
            OR t.id_cliente_manuale IS NOT NULL
            OR EXISTS (SELECT 1 FROM esportazioni_dettaglio e WHERE e.id_testata = t.id_testata)
            OR EXISTS (SELECT 1 FROM decise d WHERE d.id_testata = t.id_testata)
       ) > 0
ORDER BY 1;
