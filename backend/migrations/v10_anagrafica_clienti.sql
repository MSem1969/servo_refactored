-- =============================================================================
-- SERV.O v9.4 - MIGRAZIONE ANAGRAFICA CLIENTI
-- =============================================================================
-- Tabella esterna per anagrafiche clienti
-- NON deve essere azzerata durante RESET (come farmacie/parafarmacie)
-- =============================================================================

-- Crea tabella anagrafica_clienti
CREATE TABLE IF NOT EXISTS anagrafica_clienti (
    id_cliente SERIAL PRIMARY KEY,
    codice_cliente VARCHAR(20) NOT NULL UNIQUE,  -- AGCANA
    ragione_sociale_1 VARCHAR(100),               -- AGRSO1
    ragione_sociale_2 VARCHAR(100),               -- AGRSO2
    indirizzo VARCHAR(200),                       -- AGINDI
    cap VARCHAR(10),                              -- AGCAP
    localita VARCHAR(100),                        -- AGLOCA
    provincia VARCHAR(3),                         -- AGPROV
    partita_iva VARCHAR(16),                      -- AGPIVA
    email VARCHAR(200),                           -- AGMAIL
    categoria VARCHAR(10),                        -- AGCATE
    codice_farmacia VARCHAR(20),                  -- AGCFAR
    codice_stato VARCHAR(10),                     -- AGCSTA
    codice_pagamento VARCHAR(10),                 -- AGCPAG
    id_tipo VARCHAR(20),                          -- AGTIDD
    riferimento VARCHAR(10),                      -- AGDRIF
    data_import TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_aggiornamento TIMESTAMP
);

-- Indici per ricerche veloci
CREATE INDEX IF NOT EXISTS idx_clienti_codice ON anagrafica_clienti(codice_cliente);
CREATE INDEX IF NOT EXISTS idx_clienti_piva ON anagrafica_clienti(partita_iva);
CREATE INDEX IF NOT EXISTS idx_clienti_localita ON anagrafica_clienti(localita);
CREATE INDEX IF NOT EXISTS idx_clienti_provincia ON anagrafica_clienti(provincia);

-- Commento tabella
COMMENT ON TABLE anagrafica_clienti IS 'Anagrafica clienti esterna - NON azzerare durante RESET';
