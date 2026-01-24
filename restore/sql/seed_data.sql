-- =============================================================================
-- TO_EXTRACTOR v6.2 - SEED DATA BACKUP
-- Generated: 2026-01-09 06:45:45
-- =============================================================================

-- VENDOR
INSERT INTO vendor (id_vendor, codice_vendor, ragione_sociale, partita_iva_vendor, linea_offerta, note_estrazione, attivo, data_inserimento) VALUES (1, 'ANGELINI', 'Angelini Pharma S.p.A.', NULL, NULL, 'ID MIN diretto, sconti a cascata, espositori v3.1', TRUE, '2026-01-07T20:20:00.344005') ON CONFLICT (codice_vendor) DO NOTHING;
INSERT INTO vendor (id_vendor, codice_vendor, ragione_sociale, partita_iva_vendor, linea_offerta, note_estrazione, attivo, data_inserimento) VALUES (2, 'BAYER', 'Bayer S.p.A.', NULL, NULL, 'Formato SAP', TRUE, '2026-01-07T20:20:00.344005') ON CONFLICT (codice_vendor) DO NOTHING;
INSERT INTO vendor (id_vendor, codice_vendor, ragione_sociale, partita_iva_vendor, linea_offerta, note_estrazione, attivo, data_inserimento) VALUES (3, 'CODIFI', 'Codifi S.r.l.', NULL, NULL, 'Multi-cliente', TRUE, '2026-01-07T20:20:00.344005') ON CONFLICT (codice_vendor) DO NOTHING;
INSERT INTO vendor (id_vendor, codice_vendor, ragione_sociale, partita_iva_vendor, linea_offerta, note_estrazione, attivo, data_inserimento) VALUES (4, 'CHIESI', 'Chiesi Farmaceutici S.p.A.', '02944970348', NULL, 'Escludere P.IVA vendor', TRUE, '2026-01-07T20:20:00.344005') ON CONFLICT (codice_vendor) DO NOTHING;
INSERT INTO vendor (id_vendor, codice_vendor, ragione_sociale, partita_iva_vendor, linea_offerta, note_estrazione, attivo, data_inserimento) VALUES (5, 'MENARINI', 'Menarini S.r.l.', NULL, NULL, 'Parent/Child', TRUE, '2026-01-07T20:20:00.344005') ON CONFLICT (codice_vendor) DO NOTHING;
INSERT INTO vendor (id_vendor, codice_vendor, ragione_sociale, partita_iva_vendor, linea_offerta, note_estrazione, attivo, data_inserimento) VALUES (6, 'OPELLA', 'Opella Healthcare Italy S.r.l.', NULL, NULL, 'AIC 7-9 cifre', TRUE, '2026-01-07T20:20:00.344005') ON CONFLICT (codice_vendor) DO NOTHING;
INSERT INTO vendor (id_vendor, codice_vendor, ragione_sociale, partita_iva_vendor, linea_offerta, note_estrazione, attivo, data_inserimento) VALUES (7, 'DOC_GENERICI', 'DOC Generici S.r.l.', NULL, NULL, 'Transfer Order via Grossisti, doppio indirizzo, NO prezzi', TRUE, '2026-01-07T20:20:00.344005') ON CONFLICT (codice_vendor) DO NOTHING;
INSERT INTO vendor (id_vendor, codice_vendor, ragione_sociale, partita_iva_vendor, linea_offerta, note_estrazione, attivo, data_inserimento) VALUES (8, 'GENERIC', 'Vendor Generico', NULL, NULL, 'Estrattore generico per vendor non riconosciuti', TRUE, '2026-01-07T20:20:00.344005') ON CONFLICT (codice_vendor) DO NOTHING;

-- OPERATORI
INSERT INTO operatori (id_operatore, username, nome, cognome, email, ruolo, attivo, data_creazione, created_by_operatore, data_nascita) VALUES (1, 'SYSTEM', 'Sistema', NULL, NULL, 'admin', TRUE, '2026-01-07T20:20:00.339131', NULL, NULL) ON CONFLICT (username) DO NOTHING;
INSERT INTO operatori (id_operatore, username, nome, cognome, email, ruolo, attivo, data_creazione, created_by_operatore, data_nascita) VALUES (2, 'admin', 'Admin', 'Sistema', 'admin@test.it', 'admin', TRUE, '2026-01-07T21:17:17.777344', NULL, NULL) ON CONFLICT (username) DO NOTHING;
INSERT INTO operatori (id_operatore, username, nome, cognome, email, ruolo, attivo, data_creazione, created_by_operatore, data_nascita) VALUES (4, 'stefy', 'Stefania', 'Sciarratta', 'customercare@sofad.it', 'operatore', TRUE, '2026-01-08T06:13:44.074308', 2, NULL) ON CONFLICT (username) DO NOTHING;
INSERT INTO operatori (id_operatore, username, nome, cognome, email, ruolo, attivo, data_creazione, created_by_operatore, data_nascita) VALUES (6, 'mary', 'Maria ', 'Tudisco', 'customercare@sofad.it', 'operatore', TRUE, '2026-01-08T06:17:12.938349', 2, NULL) ON CONFLICT (username) DO NOTHING;
INSERT INTO operatori (id_operatore, username, nome, cognome, email, ruolo, attivo, data_creazione, created_by_operatore, data_nascita) VALUES (7, 'francesca', 'Francesca', 'Zappala', 'segreterianetwork@sofad.it', 'supervisore', TRUE, '2026-01-08T06:17:13.147346', 2, NULL) ON CONFLICT (username) DO NOTHING;

-- CRITERI ORDINARI ESPOSITORE