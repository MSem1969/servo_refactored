-- =============================================================================
-- SERV.O v16 - Funzione add_business_days()
-- =============================================================================
-- Serve a calcolare, lato DB, la stessa data di consegna stimata usata dal
-- backend Python (utils/dates.py::add_business_days) e dal frontend
-- (pages/Database/utils.js::addBusinessDays):
--
--     data_consegna stimata = data_ordine + N giorni lavorativi
--
-- Sabato e domenica sono saltati. Le festivita' NON sono gestite.
--
-- Prima di questa migration l'ORDER BY della lista ordini approssimava con
-- "data_ordine + INTERVAL '14 days'": corretto solo per N=10 e data_ordine
-- feriale. Con N=3 l'approssimazione non regge (3 gg lavorativi valgono 3, 4 o
-- 5 giorni solari a seconda del giorno di partenza), da cui la funzione esatta.
--
-- Applicare con:
--     psql -f backend/migrations/v16_add_business_days.sql
-- =============================================================================

-- Forma chiusa equivalente all'avanzamento giorno-per-giorno:
--   1. se la data di partenza cade nel weekend, la si normalizza al venerdi
--      precedente (avanzando un giorno alla volta, sabato e domenica non
--      vengono mai contati, quindi partire da sab/dom equivale a partire dal
--      venerdi che li precede);
--   2. ogni 5 giorni lavorativi = 7 giorni solari esatti;
--   3. il resto (n % 5) scavalca il weekend se supera il venerdi.
CREATE OR REPLACE FUNCTION add_business_days(d date, n integer)
RETURNS date
LANGUAGE sql
IMMUTABLE
AS $$
    WITH base AS (
        SELECT d - CASE EXTRACT(ISODOW FROM d)
                       WHEN 6 THEN 1   -- sabato   -> venerdi
                       WHEN 7 THEN 2   -- domenica -> venerdi
                       ELSE 0
                   END AS bd
    )
    SELECT bd
         + (n / 5) * 7
         + CASE
               WHEN n % 5 = 0 THEN 0
               WHEN EXTRACT(ISODOW FROM bd) + (n % 5) > 5 THEN (n % 5) + 2
               ELSE (n % 5)
           END
    FROM base
    WHERE d IS NOT NULL AND n IS NOT NULL;
$$;

COMMENT ON FUNCTION add_business_days(date, integer) IS
    'Aggiunge N giorni lavorativi (lun-ven, festivi non gestiti). '
    'Deve restare allineata a backend/app/utils/dates.py::add_business_days '
    'e a frontend/src/pages/Database/utils.js::addBusinessDays.';
