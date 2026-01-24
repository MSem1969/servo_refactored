-- =============================================================================
-- MIGRATION 001: Aggiunta campi profilo utente (data_nascita, avatar)
-- =============================================================================
-- Data: 2026-01-08
-- Descrizione: Aggiunge supporto per anagrafica estesa utenti con data di nascita
--              e avatar (immagine base64 per firma/etichetta)
-- =============================================================================

-- Aggiungi colonna data_nascita
ALTER TABLE operatori ADD COLUMN IF NOT EXISTS data_nascita DATE;

-- Aggiungi colonna avatar_base64 (per immagini piccole tipo firma email)
ALTER TABLE operatori ADD COLUMN IF NOT EXISTS avatar_base64 TEXT;

-- Aggiungi colonna avatar_mime_type
ALTER TABLE operatori ADD COLUMN IF NOT EXISTS avatar_mime_type VARCHAR(50) DEFAULT 'image/jpeg';

-- Commenti descrittivi
COMMENT ON COLUMN operatori.data_nascita IS 'Data di nascita utente (opzionale)';
COMMENT ON COLUMN operatori.avatar_base64 IS 'Avatar utente in formato base64 (max ~500KB)';
COMMENT ON COLUMN operatori.avatar_mime_type IS 'MIME type dell avatar (image/jpeg, image/png, image/webp)';

-- =============================================================================
-- FINE MIGRATION
-- =============================================================================
