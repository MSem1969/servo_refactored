-- =============================================================================
-- v20 - Stato FTP BLOCCATO
-- =============================================================================
-- Tra la generazione del tracciato e l'invio FTP (batch ogni 10 minuti)
-- l'ordine puo' essere archiviato o finire in ANOMALIA. Il sender inviava
-- comunque, perche' controllava solo stato_ftp. Ora ricontrolla l'ordine e,
-- se e' bloccato, mette l'esportazione in BLOCCATO con il motivo in
-- ultimo_errore_ftp, invece di trasmetterla.
--
-- Un'esportazione BLOCCATO si ritrasmette con Invia (pagina Tracciati):
-- il sender ricontrolla l'ordine e la blocca di nuovo se il blocco persiste.
--
-- Applicare con:  psql -U servo -d servo -f v20_stato_ftp_bloccato.sql
-- =============================================================================

BEGIN;

ALTER TABLE public.esportazioni DROP CONSTRAINT IF EXISTS esportazioni_stato_ftp_check;

ALTER TABLE public.esportazioni
    ADD CONSTRAINT esportazioni_stato_ftp_check
    CHECK (stato_ftp IN (
        'PENDING', 'SENDING', 'SENT', 'RETRY', 'FAILED',
        'SKIPPED', 'ALERT_SENT', 'SUPERSEDED', 'BLOCCATO'
    ));

COMMIT;

SELECT conname, pg_get_constraintdef(oid) AS def
FROM pg_constraint
WHERE conrelid = 'public.esportazioni'::regclass
  AND conname = 'esportazioni_stato_ftp_check';
