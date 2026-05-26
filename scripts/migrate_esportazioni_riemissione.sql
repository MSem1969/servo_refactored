-- =============================================================================
-- MIGRAZIONE: Edit + Riemissione tracciato
-- =============================================================================
-- Aggiunge supporto per riemissione di un tracciato dopo edit manuale:
--  - is_riemissione      : flag che identifica le esportazioni riemesse
--  - riemessa_da_id      : link all'esportazione originale (parent)
--  - data_riemissione    : timestamp della riemissione (popolato sull'originale)
--  - note_riemissione    : annotazione libera (motivo correzione)
-- Estende inoltre i valori validi di stato_ftp includendo 'SUPERSEDED'
-- (stato finale dell'esportazione originale dopo che è stata sostituita).
-- =============================================================================

BEGIN;

-- 1. Nuove colonne su esportazioni
ALTER TABLE public.esportazioni
    ADD COLUMN IF NOT EXISTS is_riemissione   boolean DEFAULT false NOT NULL,
    ADD COLUMN IF NOT EXISTS riemessa_da_id   integer,
    ADD COLUMN IF NOT EXISTS data_riemissione timestamp without time zone,
    ADD COLUMN IF NOT EXISTS note_riemissione text;

-- 2. PRIMARY KEY su id_esportazione (storicamente mancante: necessaria per la FK self-referential)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.esportazioni'::regclass
          AND contype = 'p'
    ) THEN
        ALTER TABLE public.esportazioni
            ADD CONSTRAINT esportazioni_pkey PRIMARY KEY (id_esportazione);
    END IF;
END$$;

-- 3. FK verso esportazione originale (parent → child)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'esportazioni_riemessa_da_fk'
    ) THEN
        ALTER TABLE public.esportazioni
            ADD CONSTRAINT esportazioni_riemessa_da_fk
            FOREIGN KEY (riemessa_da_id)
            REFERENCES public.esportazioni(id_esportazione)
            ON DELETE SET NULL;
    END IF;
END$$;

-- 4. Indici per ricerche frequenti (lista riemissioni di un'esportazione)
CREATE INDEX IF NOT EXISTS idx_esportazioni_riemessa_da
    ON public.esportazioni(riemessa_da_id)
    WHERE riemessa_da_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_esportazioni_is_riemissione
    ON public.esportazioni(is_riemissione)
    WHERE is_riemissione = true;

-- 5. CHECK constraint su stato_ftp (include SUPERSEDED)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'esportazioni_stato_ftp_check'
    ) THEN
        ALTER TABLE public.esportazioni DROP CONSTRAINT esportazioni_stato_ftp_check;
    END IF;

    ALTER TABLE public.esportazioni
        ADD CONSTRAINT esportazioni_stato_ftp_check
        CHECK (stato_ftp IN (
            'PENDING', 'SENDING', 'SENT', 'RETRY', 'FAILED',
            'SKIPPED', 'ALERT_SENT', 'SUPERSEDED'
        ));
END$$;

COMMIT;

-- =============================================================================
-- VERIFICA POST-MIGRAZIONE
-- =============================================================================
SELECT 'POST MIGRAZIONE' AS fase;

SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'esportazioni'
  AND column_name IN ('is_riemissione', 'riemessa_da_id', 'data_riemissione', 'note_riemissione')
ORDER BY column_name;

SELECT conname, pg_get_constraintdef(oid) AS def
FROM pg_constraint
WHERE conrelid = 'public.esportazioni'::regclass
  AND conname IN ('esportazioni_riemessa_da_fk', 'esportazioni_stato_ftp_check');
