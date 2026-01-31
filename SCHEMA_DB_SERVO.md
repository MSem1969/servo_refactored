# SERV.O - Schema Database v11.6

> Documento generato automaticamente - Ultimo aggiornamento: 2026-01-31

## Indice

1. [Panoramica](#panoramica)
2. [Tabelle Core](#tabelle-core)
3. [Tabelle Anagrafica](#tabelle-anagrafica)
4. [Tabelle Supervisione](#tabelle-supervisione)
5. [Tabelle Criteri ML](#tabelle-criteri-ml)
6. [Tabelle Export/Tracciati](#tabelle-exporttracciati)
7. [Tabelle Email](#tabelle-email)
8. [Tabelle FTP](#tabelle-ftp)
9. [Tabelle Autenticazione](#tabelle-autenticazione)
10. [Tabelle Audit/Logging](#tabelle-auditlogging)
11. [Tabelle CRM](#tabelle-crm)
12. [Tabelle Backup](#tabelle-backup)
13. [Viste Principali](#viste-principali)
14. [Relazioni Foreign Key](#relazioni-foreign-key)

---

## Panoramica

Il database SERV.O contiene **53 tabelle** e **19 viste** organizzate nei seguenti domini funzionali:

| Dominio | Tabelle | Descrizione |
|---------|---------|-------------|
| Core | 5 | Ordini, dettagli, acquisizioni, vendor, anomalie |
| Anagrafica | 3 | Farmacie, parafarmacie, clienti |
| Supervisione | 7 | Supervisione ML per AIC, lookup, listino, espositore, prezzo |
| Criteri ML | 5 | Pattern appresi per auto-approvazione |
| Export | 4 | Esportazioni, tracciati EDI |
| Email | 3 | Configurazione IMAP/SMTP, acquisizioni email |
| FTP | 4 | Endpoint FTP, mapping vendor, log |
| Auth | 5 | Operatori, sessioni, OTP, password reset |
| Audit | 5 | Log operazioni, tracking operatore, modifiche |
| CRM | 3 | Ticket, messaggi, allegati |
| Backup | 5 | Moduli, storage, history, schedule |

---

## Tabelle Core

### acquisizioni
Storage dei file PDF caricati nel sistema.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_acquisizione | integer | NO | serial | PK |
| nome_file_originale | varchar(255) | NO | | Nome file originale |
| nome_file_storage | varchar(255) | NO | | Nome file su storage |
| percorso_storage | text | YES | | Path completo |
| hash_file | varchar(64) | YES | | SHA256 del file |
| hash_contenuto_pdf | varchar(64) | YES | | SHA256 contenuto PDF |
| dimensione_bytes | integer | YES | | Dimensione file |
| mime_type | varchar(100) | YES | 'application/pdf' | |
| id_vendor | integer | YES | | FK vendor rilevato |
| vendor_rilevato_auto | boolean | YES | true | Detection automatica |
| stato | varchar(20) | YES | 'CARICATO' | CARICATO/ELABORATO/ERRORE |
| num_ordini_estratti | integer | YES | 0 | Contatore ordini |
| messaggio_errore | text | YES | | Dettaglio errore |
| is_duplicato | boolean | YES | false | Flag duplicato |
| id_acquisizione_originale | integer | YES | | Ref acquisizione originale |
| id_operatore_upload | integer | YES | 1 | Chi ha caricato |
| data_upload | timestamp | YES | CURRENT_TIMESTAMP | |
| data_elaborazione | timestamp | YES | | |
| origine | varchar(20) | YES | 'MANUALE' | MANUALE/EMAIL/FTP |
| id_email | integer | YES | | FK email_acquisizioni |

### ordini_testata
Testata ordini estratti dai PDF.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_testata | integer | NO | serial | PK |
| id_acquisizione | integer | NO | | FK acquisizioni |
| id_vendor | integer | NO | | FK vendor |
| numero_ordine_vendor | varchar(50) | NO | | Numero ordine vendor |
| data_ordine | date | YES | | Data ordine |
| data_consegna | date | YES | | Data consegna richiesta |
| partita_iva_estratta | varchar(16) | YES | | P.IVA dal PDF |
| codice_ministeriale_estratto | varchar(9) | YES | | MIN_ID dal PDF |
| ragione_sociale_1 | varchar(100) | YES | | Ragione sociale |
| ragione_sociale_2 | varchar(100) | YES | | Ragione sociale 2 |
| indirizzo | varchar(100) | YES | | |
| cap | varchar(10) | YES | | |
| citta | varchar(100) | YES | | |
| provincia | varchar(3) | YES | | |
| nome_agente | varchar(100) | YES | | |
| gg_dilazione_1 | integer | YES | 90 | Giorni dilazione 1 |
| gg_dilazione_2 | integer | YES | | Giorni dilazione 2 |
| gg_dilazione_3 | integer | YES | | Giorni dilazione 3 |
| note_ordine | text | YES | | Note ordine |
| note_ddt | text | YES | | Note DDT |
| id_farmacia_lookup | integer | YES | | FK anagrafica_farmacie |
| id_parafarmacia_lookup | integer | YES | | FK anagrafica_parafarmacie |
| lookup_method | varchar(20) | YES | | PIVA/MIN_ID/FUZZY/MANUALE |
| lookup_source | varchar(20) | YES | 'FARMACIA' | FARMACIA/PARAFARMACIA |
| lookup_score | integer | YES | | Score 0-100 |
| chiave_univoca_ordine | varchar(64) | YES | | Hash univocità |
| is_ordine_duplicato | boolean | YES | false | |
| id_testata_originale | integer | YES | | Ref ordine originale |
| stato | varchar(20) | YES | 'ESTRATTO' | ESTRATTO/CONFERMATO/ANOMALIA/EVASO/PARZ_EVASO/ARCHIVIATO |
| data_estrazione | timestamp | YES | CURRENT_TIMESTAMP | |
| data_validazione | timestamp | YES | | |
| validato_da | varchar(50) | YES | | |
| righe_totali | integer | YES | 0 | |
| righe_confermate | integer | YES | 0 | |
| righe_in_supervisione | integer | YES | 0 | |
| data_ultimo_aggiornamento | timestamp | YES | | |
| ragione_sociale_1_estratta | varchar(100) | YES | | Valore originale |
| indirizzo_estratto | varchar(100) | YES | | Valore originale |
| cap_estratto | varchar(10) | YES | | Valore originale |
| citta_estratta | varchar(100) | YES | | Valore originale |
| provincia_estratta | varchar(3) | YES | | Valore originale |
| data_ordine_estratta | date | YES | | Valore originale |
| data_consegna_estratta | date | YES | | Valore originale |
| fonte_anagrafica | varchar(20) | YES | | Fonte dati anagrafica |
| data_modifica_anagrafica | timestamp | YES | | |
| operatore_modifica_anagrafica | varchar(100) | YES | | |
| valore_totale_netto | numeric | YES | | Totale ordine |
| deposito_riferimento | varchar(10) | YES | | Deposito di riferimento |
| id_cliente_manuale | integer | YES | | FK anagrafica_clienti |
| note_cliente_manuale | text | YES | | |

### ordini_dettaglio
Righe dettaglio degli ordini.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_dettaglio | integer | NO | serial | PK |
| id_testata | integer | NO | | FK ordini_testata |
| n_riga | integer | NO | | Numero riga progressivo |
| codice_aic | varchar(10) | YES | | Codice AIC (9 cifre) |
| codice_originale | varchar(20) | YES | | Codice dal PDF |
| codice_materiale | varchar(20) | YES | | Codice materiale SAP |
| descrizione | varchar(100) | YES | | Descrizione prodotto |
| tipo_posizione | varchar(20) | YES | '' | |
| q_venduta | integer | YES | 0 | Quantità venduta |
| q_sconto_merce | integer | YES | 0 | Quantità sconto merce |
| q_omaggio | integer | YES | 0 | Quantità omaggio |
| data_consegna_riga | date | YES | | Data consegna riga |
| sconto_1 | numeric | YES | 0 | Sconto 1 (%) |
| sconto_2 | numeric | YES | 0 | Sconto 2 (%) |
| sconto_3 | numeric | YES | 0 | Sconto 3 (%) |
| sconto_4 | numeric | YES | 0 | Sconto 4 (%) |
| prezzo_netto | numeric | YES | 0 | Prezzo netto unitario |
| prezzo_scontare | numeric | YES | 0 | Prezzo da scontare |
| prezzo_pubblico | numeric | YES | 0 | Prezzo al pubblico |
| prezzo_listino | numeric | YES | 0 | Prezzo listino |
| valore_netto | numeric | YES | 0 | Valore netto riga |
| aliquota_iva | numeric | YES | 10 | Aliquota IVA (%) |
| scorporo_iva | varchar(1) | YES | 'N' | S/N |
| note_allestimento | text | YES | | Note per allestimento |
| is_espositore | boolean | YES | false | Riga espositore parent |
| is_child | boolean | YES | false | Riga child espositore |
| is_no_aic | boolean | YES | false | Prodotto senza AIC |
| tipo_riga | varchar(20) | YES | '' | PARENT_ESPOSITORE/CHILD_ESPOSITORE |
| id_parent_espositore | integer | YES | | FK al parent |
| espositore_metadata | jsonb | YES | | Metadata espositore |
| stato_riga | varchar(20) | YES | 'ESTRATTO' | ESTRATTO/CONFERMATO/EVASO/PARZIALE/ARCHIVIATO |
| richiede_supervisione | boolean | YES | false | |
| id_supervisione | integer | YES | | |
| confermato_da | varchar(50) | YES | | |
| data_conferma | timestamp | YES | | |
| note_supervisione | text | YES | | |
| modificato_manualmente | boolean | YES | false | |
| valori_originali | jsonb | YES | | Snapshot valori originali |
| q_originale | integer | YES | 0 | Quantità originale |
| q_esportata | integer | YES | 0 | Quantità già esportata |
| q_residua | integer | YES | 0 | Quantità residua |
| num_esportazioni | integer | YES | 0 | Contatore esportazioni |
| ultima_esportazione | timestamp | YES | | |
| id_ultima_esportazione | integer | YES | | FK esportazioni |
| q_evasa | integer | YES | 0 | Quantità evasa |
| q_da_evadere | integer | YES | 0 | Quantità da evadere |
| codice_aic_inserito | text | YES | | AIC inserito manualmente |
| descrizione_estratta | varchar(200) | YES | | Descrizione originale |
| fonte_codice_aic | varchar(50) | YES | | Fonte del codice AIC |
| fonte_quantita | varchar(50) | YES | | Fonte della quantità |

### vendor
Anagrafica vendor/fornitori farmaceutici.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_vendor | integer | NO | serial | PK |
| codice_vendor | varchar(50) | NO | | Codice univoco (ANGELINI, BAYER...) |
| ragione_sociale | varchar(255) | YES | | Ragione sociale |
| partita_iva_vendor | varchar(16) | YES | | P.IVA vendor |
| linea_offerta | varchar(100) | YES | | Linea offerta |
| note_estrazione | text | YES | | Note per estrazione |
| attivo | boolean | YES | true | |
| data_inserimento | timestamp | YES | CURRENT_TIMESTAMP | |

### anomalie
Anomalie rilevate durante l'estrazione.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_anomalia | integer | NO | serial | PK |
| id_testata | integer | YES | | FK ordini_testata |
| id_dettaglio | integer | YES | | FK ordini_dettaglio |
| id_acquisizione | integer | YES | | FK acquisizioni |
| tipo_anomalia | varchar(50) | NO | | ESPOSITORE/LOOKUP/LISTINO/AIC |
| livello | varchar(20) | YES | 'ATTENZIONE' | GRAVE/ATTENZIONE |
| codice_anomalia | varchar(20) | YES | | ESP-A01, LKP-A01... |
| descrizione | text | YES | | Descrizione anomalia |
| valore_anomalo | text | YES | | Valore che ha causato anomalia |
| stato | varchar(20) | YES | 'APERTA' | APERTA/RISOLTA/IGNORATA |
| id_operatore_gestione | integer | YES | | Chi ha gestito |
| note_risoluzione | text | YES | | |
| data_rilevazione | timestamp | YES | CURRENT_TIMESTAMP | |
| data_risoluzione | timestamp | YES | | |
| richiede_supervisione | boolean | YES | false | |
| pattern_signature | varchar(100) | YES | | Signature per ML |

---

## Tabelle Anagrafica

### anagrafica_farmacie
Anagrafica farmacie dal Ministero della Salute.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_farmacia | integer | NO | serial | PK |
| min_id | varchar(9) | NO | | Codice ministeriale (UNIQUE) |
| codice_farmacia_asl | varchar(20) | YES | | Codice ASL |
| partita_iva | varchar(16) | YES | | P.IVA |
| ragione_sociale | varchar(255) | YES | | |
| indirizzo | varchar(255) | YES | | |
| cap | varchar(10) | YES | | |
| citta | varchar(100) | YES | | |
| frazione | varchar(100) | YES | | |
| provincia | varchar(3) | YES | | |
| regione | varchar(50) | YES | | |
| data_inizio_validita | date | YES | | |
| data_fine_validita | date | YES | | |
| attiva | boolean | YES | true | |
| fonte_dati | varchar(50) | YES | | MINISTERO/IMPORT |
| data_import | timestamp | YES | CURRENT_TIMESTAMP | |

### anagrafica_parafarmacie
Anagrafica parafarmacie dal Ministero.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_parafarmacia | integer | NO | serial | PK |
| codice_sito | varchar(20) | NO | | Codice sito (UNIQUE) |
| sito_logistico | varchar(255) | YES | | |
| partita_iva | varchar(16) | YES | | |
| indirizzo | varchar(255) | YES | | |
| cap | varchar(10) | YES | | |
| codice_comune | varchar(10) | YES | | |
| citta | varchar(100) | YES | | |
| codice_provincia | varchar(3) | YES | | |
| provincia | varchar(50) | YES | | |
| codice_regione | varchar(3) | YES | | |
| regione | varchar(50) | YES | | |
| data_inizio_validita | date | YES | | |
| data_fine_validita | date | YES | | |
| latitudine | numeric | YES | | |
| longitudine | numeric | YES | | |
| attiva | boolean | YES | true | |
| fonte_dati | varchar(50) | YES | | |
| data_import | timestamp | YES | CURRENT_TIMESTAMP | |

### anagrafica_clienti
Anagrafica clienti interna (import da gestionale).

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_cliente | integer | NO | serial | PK |
| codice_cliente | varchar(20) | NO | | Codice cliente interno |
| ragione_sociale_1 | varchar(100) | YES | | |
| ragione_sociale_2 | varchar(100) | YES | | |
| indirizzo | varchar(200) | YES | | |
| cap | varchar(10) | YES | | |
| localita | varchar(100) | YES | | |
| provincia | varchar(3) | YES | | |
| partita_iva | varchar(16) | YES | | |
| email | varchar(200) | YES | | |
| farmacia_categoria | varchar(10) | YES | | |
| codice_farmacia | varchar(20) | YES | | |
| farma_status | varchar(10) | YES | | |
| codice_pagamento | varchar(10) | YES | | |
| min_id | varchar(20) | YES | | Codice ministeriale |
| deposito_riferimento | varchar(10) | YES | | |
| data_import | timestamp | YES | CURRENT_TIMESTAMP | |
| data_aggiornamento | timestamp | YES | | |

---

## Tabelle Supervisione

### supervisione_unificata
Tabella unificata per tutte le supervisioni (nuova architettura).

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_supervisione | integer | NO | serial | PK |
| tipo_supervisione | varchar(20) | NO | | AIC/LOOKUP/LISTINO/ESPOSITORE/PREZZO |
| id_testata | integer | NO | | FK ordini_testata |
| id_anomalia | integer | YES | | FK anomalie |
| id_dettaglio | integer | YES | | FK ordini_dettaglio |
| codice_anomalia | varchar(20) | YES | | |
| vendor | varchar(50) | YES | | |
| pattern_signature | text | YES | | |
| stato | varchar(20) | YES | 'PENDING' | PENDING/APPROVED/REJECTED |
| operatore | varchar(100) | YES | | |
| timestamp_creazione | timestamp | YES | CURRENT_TIMESTAMP | |
| timestamp_decisione | timestamp | YES | | |
| note | text | YES | | |
| payload | jsonb | YES | '{}' | Dati specifici per tipo |

### supervisione_aic
Supervisione per anomalie codice AIC.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_supervisione | integer | NO | serial | PK |
| id_testata | integer | NO | | FK ordini_testata |
| id_anomalia | integer | YES | | FK anomalie |
| id_dettaglio | integer | YES | | FK ordini_dettaglio |
| codice_anomalia | text | NO | 'AIC-A01' | |
| vendor | text | NO | | |
| n_riga | integer | YES | | |
| descrizione_prodotto | text | YES | | |
| descrizione_normalizzata | text | YES | | Per matching |
| codice_originale | text | YES | | |
| pattern_signature | text | YES | | |
| stato | text | YES | 'PENDING' | |
| operatore | text | YES | | |
| timestamp_creazione | timestamp | YES | CURRENT_TIMESTAMP | |
| timestamp_decisione | timestamp | YES | | |
| note | text | YES | | |
| codice_aic_assegnato | text | YES | | AIC corretto |
| codice_aic_originale | text | YES | | AIC originale |
| operatore_correzione | text | YES | | |
| data_correzione | timestamp | YES | | |
| note_correzione | text | YES | | |
| operatore_approvazione | text | YES | | |
| data_approvazione | timestamp | YES | | |
| note_approvazione | text | YES | | |

### supervisione_lookup
Supervisione per anomalie lookup farmacia.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_supervisione | integer | NO | serial | PK |
| id_testata | integer | NO | | FK ordini_testata |
| id_anomalia | integer | YES | | FK anomalie |
| codice_anomalia | varchar(20) | YES | | LKP-A01/A02/A03/A04 |
| vendor | varchar(50) | YES | | |
| partita_iva_estratta | varchar(20) | YES | | |
| lookup_method | varchar(50) | YES | | |
| lookup_score | integer | YES | | |
| min_id_assegnato | varchar(20) | YES | | MIN_ID corretto |
| id_farmacia_assegnata | integer | YES | | FK anagrafica_farmacie |
| id_parafarmacia_assegnata | integer | YES | | FK anagrafica_parafarmacie |
| pattern_signature | varchar(255) | YES | | |
| stato | varchar(20) | YES | 'PENDING' | |
| operatore | varchar(100) | YES | | |
| timestamp_creazione | timestamp | YES | CURRENT_TIMESTAMP | |
| timestamp_decisione | timestamp | YES | | |
| note | text | YES | | |

### supervisione_espositore
Supervisione per anomalie espositore.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_supervisione | integer | NO | serial | PK |
| id_testata | integer | NO | | FK ordini_testata |
| id_anomalia | integer | YES | | FK anomalie |
| codice_anomalia | varchar(20) | NO | | ESP-A01...A06 |
| codice_espositore | varchar(20) | YES | | |
| descrizione_espositore | varchar(255) | YES | | |
| pezzi_attesi | integer | YES | 0 | |
| pezzi_trovati | integer | YES | 0 | |
| valore_calcolato | numeric | YES | 0 | Per chiusura MENARINI |
| pattern_signature | varchar(100) | YES | | |
| stato | varchar(20) | YES | 'PENDING' | |
| operatore | varchar(50) | YES | | |
| timestamp_creazione | timestamp | YES | CURRENT_TIMESTAMP | |
| timestamp_decisione | timestamp | YES | | |
| note | text | YES | | |
| modifiche_manuali_json | jsonb | YES | | |
| operatore_correzione | text | YES | | |
| data_correzione | timestamp | YES | | |
| note_correzione | text | YES | | |
| operatore_approvazione | text | YES | | |
| data_approvazione | timestamp | YES | | |
| note_approvazione | text | YES | | |

### supervisione_listino
Supervisione per anomalie prezzi/listino.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_supervisione | integer | NO | serial | PK |
| id_testata | integer | NO | | FK ordini_testata |
| id_dettaglio | integer | YES | | FK ordini_dettaglio |
| id_anomalia | integer | YES | | FK anomalie |
| codice_anomalia | varchar(20) | YES | | |
| vendor | varchar(50) | YES | | |
| codice_aic | varchar(20) | YES | | |
| n_riga | integer | YES | | |
| descrizione_prodotto | varchar(200) | YES | | |
| prezzo_estratto | numeric | YES | | |
| prezzo_listino | numeric | YES | | |
| prezzo_proposto | numeric | YES | | |
| pattern_signature | varchar(255) | YES | | |
| stato | varchar(20) | YES | 'PENDING' | |
| operatore | varchar(100) | YES | | |
| timestamp_creazione | timestamp | YES | CURRENT_TIMESTAMP | |
| timestamp_decisione | timestamp | YES | | |
| note | text | YES | | |
| azione | varchar(50) | YES | | USA_ESTRATTO/USA_LISTINO |
| operatore_correzione | text | YES | | |
| data_correzione | timestamp | YES | | |
| note_correzione | text | YES | | |
| operatore_approvazione | text | YES | | |
| data_approvazione | timestamp | YES | | |
| note_approvazione | text | YES | | |

### supervisione_prezzo
Supervisione per anomalie prezzo (ordine completo).

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_supervisione | integer | NO | serial | PK |
| id_testata | integer | NO | | FK ordini_testata |
| id_anomalia | integer | YES | | FK anomalie |
| codice_anomalia | text | YES | 'PRICE-A01' | |
| vendor | text | YES | | |
| numero_righe_coinvolte | integer | YES | | |
| pattern_signature | text | YES | | |
| stato | text | YES | 'PENDING' | |
| operatore | text | YES | | |
| timestamp_creazione | timestamp | YES | CURRENT_TIMESTAMP | |
| timestamp_decisione | timestamp | YES | | |
| note | text | YES | | |
| prezzi_originali | jsonb | YES | | Snapshot prezzi |
| prezzi_corretti | jsonb | YES | | Prezzi corretti |
| fonte | text | YES | 'PREZZO' | |
| operatore_correzione | text | YES | | |
| data_correzione | timestamp | YES | | |
| note_correzione | text | YES | | |
| operatore_approvazione | text | YES | | |
| data_approvazione | timestamp | YES | | |
| note_approvazione | text | YES | | |

### supervisione_anagrafica
Supervisione per anomalie anagrafica cliente.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_supervisione | integer | NO | serial | PK |
| id_testata | integer | NO | | FK ordini_testata |
| id_anomalia | integer | YES | | FK anomalie |
| codice_anomalia | text | NO | | |
| vendor | text | YES | | |
| pattern_signature | text | YES | | |
| pattern_descrizione | text | YES | | |
| piva_estratta | text | YES | | |
| min_id_estratto | text | YES | | |
| ragione_sociale_estratta | text | YES | | |
| indirizzo_estratto | text | YES | | |
| cap_estratto | text | YES | | |
| citta_estratta | text | YES | | |
| provincia_estratta | text | YES | | |
| deposito_estratto | text | YES | | |
| lookup_score | integer | YES | | |
| lookup_method | text | YES | | |
| id_farmacia_suggerita | integer | YES | | |
| piva_corretta | text | YES | | |
| min_id_corretto | text | YES | | |
| ragione_sociale_corretta | text | YES | | |
| indirizzo_corretto | text | YES | | |
| cap_corretto | text | YES | | |
| citta_corretta | text | YES | | |
| provincia_corretta | text | YES | | |
| deposito_corretto | text | YES | | |
| id_farmacia_assegnata | integer | YES | | |
| stato | text | YES | 'PENDING' | |
| operatore_correzione | text | YES | | |
| data_correzione | timestamp | YES | | |
| note_correzione | text | YES | | |
| operatore_approvazione | text | YES | | |
| data_approvazione | timestamp | YES | | |
| note_approvazione | text | YES | | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |
| updated_at | timestamp | YES | CURRENT_TIMESTAMP | |

---

## Tabelle Criteri ML

### criteri_ordinari_aic
Pattern AIC appresi per auto-approvazione.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| pattern_signature | text | NO | | PK - Signature pattern |
| pattern_descrizione | text | YES | | Descrizione leggibile |
| vendor | text | NO | | |
| descrizione_normalizzata | text | NO | | |
| count_approvazioni | integer | YES | 0 | Contatore approvazioni |
| is_ordinario | boolean | YES | false | Promosso a ordinario (>=3) |
| data_prima_occorrenza | timestamp | YES | CURRENT_TIMESTAMP | |
| data_promozione | timestamp | YES | | |
| operatori_approvatori | text | YES | | Lista operatori |
| codice_aic_default | text | YES | | AIC da usare |

### criteri_ordinari_lookup
Pattern lookup appresi.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| pattern_signature | text | NO | | PK |
| pattern_descrizione | text | YES | | |
| vendor | text | NO | | |
| codice_anomalia | text | NO | | |
| partita_iva_pattern | text | YES | | |
| count_approvazioni | integer | YES | 0 | |
| is_ordinario | boolean | YES | false | |
| data_prima_occorrenza | timestamp | YES | CURRENT_TIMESTAMP | |
| data_promozione | timestamp | YES | | |
| operatori_approvatori | text | YES | | |
| min_id_default | text | YES | | MIN_ID da usare |
| id_farmacia_default | integer | YES | | FK farmacia |

### criteri_ordinari_espositore
Pattern espositore appresi.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| pattern_signature | varchar(100) | NO | | PK |
| pattern_descrizione | text | YES | | |
| vendor | varchar(50) | NO | | |
| codice_anomalia | varchar(20) | YES | | |
| codice_espositore | varchar(20) | YES | | |
| pezzi_per_unita | integer | YES | | |
| tipo_scostamento | varchar(20) | YES | | SOTTO/SOPRA |
| fascia_scostamento | varchar(20) | YES | | |
| count_approvazioni | integer | YES | 0 | |
| is_ordinario | boolean | YES | false | |
| data_prima_occorrenza | timestamp | YES | CURRENT_TIMESTAMP | |
| data_promozione | timestamp | YES | | |
| operatori_approvatori | text | YES | | |
| descrizione_normalizzata | varchar(255) | YES | | |
| child_sequence_json | jsonb | YES | | Sequenza child attesa |
| num_child_attesi | integer | YES | 0 | |
| total_applications | integer | YES | 0 | |
| successful_applications | integer | YES | 0 | |

### criteri_ordinari_listino
Pattern listino/prezzo appresi.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| pattern_signature | text | NO | | PK |
| pattern_descrizione | text | YES | | |
| vendor | text | NO | | |
| codice_anomalia | text | NO | | |
| codice_aic | text | YES | | |
| count_approvazioni | integer | YES | 0 | |
| is_ordinario | boolean | YES | false | |
| data_prima_occorrenza | timestamp | YES | CURRENT_TIMESTAMP | |
| data_promozione | timestamp | YES | | |
| operatori_approvatori | text | YES | | |
| prezzo_netto_pattern | numeric | YES | | |
| prezzo_pubblico_pattern | numeric | YES | | |
| sconto_1_pattern | numeric | YES | | |
| sconto_2_pattern | numeric | YES | | |
| aliquota_iva_pattern | numeric | YES | | |
| azione_pattern | text | YES | | USA_ESTRATTO/USA_LISTINO |

### log_criteri_applicati
Log applicazione criteri ordinari.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_log | integer | NO | serial | PK |
| id_testata | integer | YES | | FK ordini_testata |
| id_supervisione | integer | YES | | FK supervisione |
| pattern_signature | varchar(100) | NO | | |
| azione | varchar(50) | YES | | |
| applicato_automaticamente | boolean | YES | false | |
| operatore | varchar(50) | YES | | |
| note | text | YES | | |
| timestamp | timestamp | YES | CURRENT_TIMESTAMP | |

---

## Tabelle Export/Tracciati

### esportazioni
Storico esportazioni tracciati EDI.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_esportazione | integer | NO | serial | PK |
| nome_tracciato_generato | varchar(255) | YES | | |
| data_tracciato | date | YES | | |
| nome_file_to_t | varchar(255) | YES | | File TO_T |
| nome_file_to_d | varchar(255) | YES | | File TO_D |
| num_testate | integer | YES | 0 | |
| num_dettagli | integer | YES | 0 | |
| stato | varchar(20) | YES | 'GENERATO' | GENERATO/INVIATO/ERRORE |
| note | text | YES | | |
| data_generazione | timestamp | YES | CURRENT_TIMESTAMP | |
| stato_ftp | varchar(20) | YES | 'PENDING' | PENDING/SENT/ERROR |
| data_invio_ftp | timestamp | YES | | |
| tentativi_ftp | integer | YES | 0 | |
| ultimo_errore_ftp | text | YES | | |
| ftp_path_remoto | varchar(255) | YES | | |
| ftp_file_inviati | text | YES | | Lista file inviati |

### esportazioni_dettaglio
Dettaglio ordini inclusi in esportazione.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id | integer | NO | serial | PK |
| id_esportazione | integer | NO | | FK esportazioni |
| id_testata | integer | YES | | FK ordini_testata |

### tracciati
Storico tracciati generati (CSV, altri formati).

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_tracciato | integer | NO | serial | PK |
| nome_file | varchar(255) | NO | | |
| tipo | varchar(20) | YES | 'CSV' | |
| num_righe | integer | YES | 0 | |
| id_operatore | integer | YES | | FK operatori |
| note | text | YES | | |
| data_generazione | timestamp | YES | CURRENT_TIMESTAMP | |

### tracciati_dettaglio
Dettaglio righe incluse in tracciato.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id | integer | NO | serial | PK |
| id_tracciato | integer | NO | | FK tracciati |
| id_testata | integer | YES | | FK ordini_testata |
| id_dettaglio | integer | YES | | FK ordini_dettaglio |

### listini_vendor
Listini prezzi vendor.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_listino | integer | NO | serial | PK |
| vendor | text | NO | | |
| codice_aic | text | NO | | |
| descrizione | text | YES | | |
| sconto_1 | numeric | YES | | |
| sconto_2 | numeric | YES | | |
| sconto_3 | numeric | YES | | |
| sconto_4 | numeric | YES | | |
| prezzo_netto | numeric | YES | | |
| prezzo_scontare | numeric | YES | | |
| prezzo_pubblico | numeric | YES | | |
| aliquota_iva | numeric | YES | | |
| scorporo_iva | text | YES | 'S' | |
| prezzo_csv_originale | numeric | YES | | |
| prezzo_pubblico_csv | numeric | YES | | |
| data_decorrenza | date | YES | | |
| attivo | boolean | YES | true | |
| data_import | timestamp | YES | CURRENT_TIMESTAMP | |
| fonte_file | text | YES | | Nome file importato |

---

## Tabelle Email

### email_config
Configurazione IMAP/SMTP sistema.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_config | integer | NO | serial | PK |
| imap_enabled | boolean | YES | false | |
| imap_host | varchar(100) | YES | 'imap.gmail.com' | |
| imap_port | integer | YES | 993 | |
| imap_use_ssl | boolean | YES | true | |
| imap_folder | varchar(50) | YES | 'INBOX' | |
| imap_unread_only | boolean | YES | true | |
| imap_mark_as_read | boolean | YES | true | |
| imap_apply_label | varchar(50) | YES | | |
| imap_subject_keywords | text | YES | | Keywords filtro |
| imap_sender_whitelist | text | YES | | Whitelist mittenti |
| imap_max_emails_per_run | integer | YES | 50 | |
| smtp_enabled | boolean | YES | false | |
| smtp_host | varchar(100) | YES | 'smtp.gmail.com' | |
| smtp_port | integer | YES | 587 | |
| smtp_use_tls | boolean | YES | true | |
| smtp_sender_email | varchar(100) | YES | | |
| smtp_sender_name | varchar(100) | YES | 'SERV.O Sistema' | |
| smtp_rate_limit | integer | YES | 10 | Max email/minuto |
| admin_notifica_email | text | YES | | Email admin |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |
| updated_at | timestamp | YES | CURRENT_TIMESTAMP | |
| updated_by | integer | YES | | |

### email_acquisizioni
Email processate con allegati PDF.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_email | integer | NO | serial | PK |
| message_id | varchar(255) | NO | | ID messaggio email |
| gmail_id | varchar(100) | YES | | ID Gmail |
| subject | varchar(500) | YES | | Oggetto |
| sender_email | varchar(255) | NO | | Mittente |
| sender_name | varchar(255) | YES | | Nome mittente |
| received_date | timestamp | NO | | Data ricezione |
| attachment_filename | varchar(255) | NO | | Nome allegato |
| attachment_size | integer | YES | | Dimensione |
| attachment_hash | varchar(64) | NO | | Hash allegato |
| id_acquisizione | integer | YES | | FK acquisizioni |
| stato | varchar(20) | YES | 'DA_PROCESSARE' | |
| data_elaborazione | timestamp | YES | | |
| errore_messaggio | text | YES | | |
| num_retry | integer | YES | 0 | |
| label_applicata | varchar(100) | YES | | Label Gmail |
| marcata_come_letta | boolean | YES | false | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |
| updated_at | timestamp | YES | CURRENT_TIMESTAMP | |

### email_log
Log invio email sistema.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_log | integer | NO | serial | PK |
| destinatario | varchar(255) | NO | | |
| oggetto | varchar(500) | YES | | |
| corpo | text | YES | | |
| tipo | varchar(50) | YES | 'generic' | OTP/RESET/NOTIFICA |
| stato_invio | varchar(20) | YES | 'pending' | pending/sent/failed |
| ticket_id | integer | YES | | FK crm_tickets (legacy) |
| id_ticket | integer | YES | | FK crm_tickets |
| tentativi | integer | YES | 0 | |
| ultimo_errore | text | YES | | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |
| sent_at | timestamp | YES | | |
| richiesto_da | integer | YES | | FK operatori |

---

## Tabelle FTP

### ftp_endpoints
Endpoint FTP configurati (v11.6 - password crittografate).

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id | integer | NO | serial | PK |
| nome | varchar(100) | NO | | Nome endpoint |
| descrizione | text | YES | | |
| vendor_code | varchar(50) | NO | | Codice vendor |
| deposito | varchar(10) | YES | | Codice deposito |
| ftp_host | varchar(100) | NO | | Host FTP |
| ftp_port | integer | YES | 21 | Porta |
| ftp_path | varchar(255) | NO | | Path remoto |
| ftp_username | varchar(100) | NO | | Username |
| ftp_password_encrypted | text | NO | | Password AES-256 |
| ftp_passive_mode | boolean | YES | false | Modalità passiva |
| ftp_timeout | integer | YES | 30 | Timeout secondi |
| attivo | boolean | YES | true | |
| ordine | integer | YES | 0 | Ordine visualizzazione |
| max_tentativi | integer | YES | 3 | |
| intervallo_retry_sec | integer | YES | 60 | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |
| updated_at | timestamp | YES | CURRENT_TIMESTAMP | |
| created_by | integer | YES | | FK operatori |
| updated_by | integer | YES | | FK operatori |

### ftp_config
Configurazione FTP globale (legacy).

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_config | integer | NO | serial | PK |
| ftp_enabled | boolean | YES | false | |
| ftp_host | varchar(100) | YES | | |
| ftp_port | integer | YES | 21 | |
| ftp_username | varchar(100) | YES | | |
| ftp_passive_mode | boolean | YES | false | |
| ftp_timeout | integer | YES | 30 | |
| max_tentativi | integer | YES | 3 | |
| intervallo_retry_secondi | integer | YES | 60 | |
| batch_intervallo_minuti | integer | YES | 10 | |
| batch_enabled | boolean | YES | true | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |
| updated_at | timestamp | YES | CURRENT_TIMESTAMP | |
| updated_by | varchar(100) | YES | | |

### ftp_vendor_mapping
Mapping vendor -> path FTP.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id | integer | NO | serial | PK |
| vendor_code | varchar(50) | NO | | |
| ftp_path | varchar(255) | NO | | |
| deposito | varchar(10) | YES | | |
| attivo | boolean | YES | true | |
| note | text | YES | | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |

### ftp_log
Log operazioni FTP.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id | integer | NO | serial | PK |
| id_esportazione | integer | YES | | FK esportazioni |
| id_endpoint | integer | YES | | FK ftp_endpoints |
| azione | varchar(50) | NO | | UPLOAD/DOWNLOAD/TEST |
| file_name | varchar(255) | YES | | |
| ftp_path | varchar(255) | YES | | |
| esito | varchar(20) | YES | | SUCCESS/ERROR |
| messaggio | text | YES | | |
| durata_ms | integer | YES | | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |

---

## Tabelle Autenticazione

### operatori
Utenti del sistema.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_operatore | integer | NO | serial | PK |
| username | varchar(50) | NO | | Username (UNIQUE) |
| password_hash | varchar(255) | YES | '' | Hash bcrypt |
| nome | varchar(100) | YES | | |
| cognome | varchar(100) | YES | | |
| email | varchar(255) | YES | | Email principale |
| ruolo | varchar(20) | YES | 'operatore' | admin/operatore/viewer |
| attivo | boolean | YES | true | |
| data_creazione | timestamp | YES | CURRENT_TIMESTAMP | |
| created_by_operatore | integer | YES | | |
| updated_at | timestamp | YES | | |
| last_login_at | timestamp | YES | | |
| disabled_at | timestamp | YES | | |
| disabled_by_operatore | integer | YES | | |
| disable_reason | text | YES | | |
| last_login_ip | varchar(50) | YES | | |
| data_nascita | date | YES | | |
| avatar_base64 | text | YES | | Avatar immagine |
| avatar_mime_type | varchar(50) | YES | 'image/jpeg' | |
| email_2fa | varchar(255) | YES | | Email per 2FA |
| twofa_enabled | boolean | YES | false | 2FA attivo |
| twofa_required_for | ARRAY | YES | | Operazioni che richiedono 2FA |

### user_sessions
Sessioni utente attive.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_session | integer | NO | serial | PK |
| id_operatore | integer | NO | | FK operatori |
| token_hash | varchar(255) | NO | | Hash JWT |
| created_at | timestamp | NO | CURRENT_TIMESTAMP | |
| expires_at | timestamp | NO | | |
| revoked_at | timestamp | YES | | |
| revoked_by_operatore | integer | YES | | |
| ip_address | varchar(45) | YES | | |
| user_agent | text | YES | | |

### otp_tokens
Token OTP per 2FA.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id | integer | NO | serial | PK |
| id_operatore | integer | YES | | FK operatori |
| codice | varchar(6) | NO | | Codice 6 cifre |
| tipo_operazione | varchar(50) | NO | | ftp_view_password/ftp_update... |
| riferimento_id | integer | YES | | ID risorsa (es. endpoint_id) |
| scadenza | timestamp | NO | | |
| utilizzato | boolean | YES | false | |
| ip_richiesta | varchar(45) | YES | | |
| user_agent | text | YES | | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |
| verified_at | timestamp | YES | | |

### otp_audit_log
Audit log operazioni OTP.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id | integer | NO | serial | PK |
| id_operatore | integer | YES | | FK operatori |
| tipo_operazione | varchar(50) | NO | | |
| esito | varchar(20) | NO | | SUCCESS/FAILED |
| ip_address | varchar(45) | YES | | |
| user_agent | text | YES | | |
| dettagli | text | YES | | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |

### password_reset_tokens
Token reset password.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id | integer | NO | serial | PK |
| id_operatore | integer | NO | | FK operatori |
| token_hash | varchar(255) | NO | | Hash token |
| expires_at | timestamp | NO | | |
| used_at | timestamp | YES | | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |
| ip_address | varchar(45) | YES | | |
| user_agent | text | YES | | |

---

## Tabelle Audit/Logging

### operatore_azioni_log
Tracking dettagliato azioni operatore (ML).

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_azione | integer | NO | serial | PK |
| id_operatore | integer | NO | | FK operatori |
| username | varchar(100) | NO | | Snapshot username |
| ruolo | varchar(50) | NO | | Snapshot ruolo |
| sezione | varchar(50) | NO | | Sezione app |
| azione | varchar(50) | NO | | Tipo azione |
| entita | varchar(100) | YES | | Tipo entità |
| id_entita | integer | YES | | ID entità |
| parametri | jsonb | YES | | Parametri azione |
| risultato | jsonb | YES | | Risultato |
| success | boolean | YES | true | |
| durata_ms | integer | YES | | Durata operazione |
| timestamp | timestamp | YES | CURRENT_TIMESTAMP | |
| giorno_settimana | integer | YES | | 0-6 |
| ora_giorno | integer | YES | | 0-23 |
| settimana_anno | integer | YES | | 1-53 |
| session_id | varchar(50) | YES | | ID sessione |
| azione_precedente_id | integer | YES | | FK self (sequenza) |
| ip_address | varchar(45) | YES | | |
| user_agent | varchar(500) | YES | | |

### log_operazioni
Log generico operazioni sistema.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_log | integer | NO | serial | PK |
| tipo_operazione | varchar(50) | NO | | |
| entita | varchar(50) | YES | | |
| id_entita | integer | YES | | |
| descrizione | text | YES | | |
| dati_json | jsonb | YES | | |
| id_operatore | integer | YES | | FK operatori |
| timestamp | timestamp | YES | CURRENT_TIMESTAMP | |
| action_category | varchar(50) | YES | | |
| username_snapshot | varchar(100) | YES | | |
| success | boolean | YES | true | |
| error_message | text | YES | | |
| ip_address | varchar(45) | YES | | |
| user_agent | text | YES | | |

### audit_modifiche
Audit trail modifiche campi.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_audit | integer | NO | serial | PK |
| entita | varchar(50) | NO | | Nome tabella |
| id_entita | integer | NO | | ID record |
| id_testata | integer | YES | | FK ordini_testata |
| campo_modificato | varchar(100) | NO | | Nome campo |
| valore_precedente | text | YES | | |
| valore_nuovo | text | YES | | |
| fonte_modifica | varchar(50) | NO | | MANUALE/SUPERVISIONE/SISTEMA |
| id_operatore | integer | YES | | |
| username_operatore | varchar(100) | YES | | |
| motivazione | text | YES | | |
| id_sessione | varchar(100) | YES | | |
| ip_address | varchar(50) | YES | | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |

### sessione_attivita
Tracking tempo per sezione.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id | integer | NO | serial | PK |
| id_operatore | integer | NO | | FK operatori |
| id_session | integer | YES | | FK user_sessions |
| sezione | varchar(50) | NO | | |
| ultimo_heartbeat | timestamp | NO | CURRENT_TIMESTAMP | |
| durata_secondi | integer | YES | 0 | |
| data_riferimento | date | NO | CURRENT_DATE | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |

### app_sezioni
Definizione sezioni applicazione.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| codice_sezione | varchar(50) | NO | | PK |
| nome_display | varchar(100) | NO | | |
| descrizione | text | YES | | |
| icona | varchar(50) | YES | | Nome icona |
| ordine_menu | integer | YES | 0 | |
| is_active | boolean | YES | true | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |

### permessi_ruolo
Permessi per ruolo e sezione.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_permesso | integer | NO | serial | PK |
| ruolo | varchar(20) | NO | | admin/operatore/viewer |
| codice_sezione | varchar(50) | NO | | FK app_sezioni |
| can_view | boolean | YES | false | |
| can_edit | boolean | YES | false | |
| updated_at | timestamp | YES | CURRENT_TIMESTAMP | |
| updated_by | varchar(100) | YES | | |

---

## Tabelle CRM

### crm_tickets
Ticket supporto.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_ticket | integer | NO | serial | PK |
| oggetto | varchar(255) | NO | | |
| descrizione | text | YES | | |
| stato | varchar(50) | YES | 'aperto' | aperto/in_lavorazione/chiuso |
| priorita | varchar(20) | YES | 'normale' | bassa/normale/alta/urgente |
| categoria | varchar(50) | YES | | bug/assistenza/richiesta |
| email_notifica | varchar(255) | YES | | |
| id_operatore | integer | YES | | FK operatori (creatore) |
| closed_by | integer | YES | | FK operatori |
| closed_at | timestamp | YES | | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |
| updated_at | timestamp | YES | CURRENT_TIMESTAMP | |
| pagina_origine | varchar(50) | YES | | Sezione di origine |
| pagina_dettaglio | varchar(200) | YES | | URL/dettaglio |

### crm_messaggi
Messaggi/risposte su ticket.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_messaggio | integer | NO | serial | PK |
| id_ticket | integer | NO | | FK crm_tickets |
| contenuto | text | NO | | |
| tipo | varchar(20) | YES | 'risposta' | risposta/nota_interna |
| id_operatore | integer | YES | | FK operatori |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |
| is_admin_reply | boolean | YES | false | |

### crm_allegati
Allegati a ticket/messaggi.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_allegato | integer | NO | serial | PK |
| id_ticket | integer | NO | | FK crm_tickets |
| id_messaggio | integer | YES | | FK crm_messaggi |
| nome_file | varchar(255) | NO | | |
| path_file | varchar(500) | NO | | |
| mime_type | varchar(100) | YES | | |
| dimensione | integer | YES | | |
| id_operatore | integer | YES | | FK operatori |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |

---

## Tabelle Backup

### backup_modules
Moduli backup configurabili.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_module | integer | NO | serial | PK |
| nome | varchar(50) | NO | | database/pdf/tracciati... |
| tier | integer | NO | 1 | Livello priorità |
| titolo | varchar(100) | NO | | |
| descrizione | text | YES | | |
| enabled | boolean | YES | false | |
| configured | boolean | YES | false | |
| config | jsonb | YES | '{}' | Configurazione |
| id_storage | integer | YES | | FK backup_storage |
| schedule_cron | varchar(50) | YES | | Cron expression |
| retention_days | integer | YES | 7 | |
| last_run | timestamp | YES | | |
| last_status | varchar(20) | YES | | |
| last_error | text | YES | | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |
| updated_at | timestamp | YES | | |
| updated_by | integer | YES | | |

### backup_storage
Destinazioni storage backup.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_storage | integer | NO | serial | PK |
| nome | varchar(100) | NO | | |
| tipo | varchar(20) | NO | | local/s3/ftp |
| path | text | NO | | |
| config | jsonb | YES | '{}' | Credenziali/config |
| capacity_gb | integer | YES | | |
| used_gb | integer | YES | | |
| stato | varchar(20) | YES | 'active' | |
| ultimo_check | timestamp | YES | | |
| ultimo_errore | text | YES | | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |
| created_by | integer | YES | | |
| updated_at | timestamp | YES | | |

### backup_history
Storico backup eseguiti.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_backup | integer | NO | serial | PK |
| id_module | integer | NO | | FK backup_modules |
| id_storage | integer | YES | | FK backup_storage |
| backup_type | varchar(20) | NO | | full/incremental |
| file_path | text | YES | | |
| file_name | varchar(255) | YES | | |
| file_size_bytes | bigint | YES | | |
| file_checksum | varchar(64) | YES | | |
| started_at | timestamp | NO | CURRENT_TIMESTAMP | |
| completed_at | timestamp | YES | | |
| duration_seconds | integer | YES | | |
| status | varchar(20) | NO | 'running' | running/success/failed |
| error_message | text | YES | | |
| metadata | jsonb | YES | '{}' | |
| triggered_by | varchar(50) | YES | 'scheduled' | scheduled/manual |
| operator_id | integer | YES | | |

### backup_schedules
Schedulazioni backup.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_schedule | integer | NO | serial | PK |
| id_module | integer | NO | | FK backup_modules |
| cron_expression | varchar(50) | NO | | |
| active | boolean | YES | true | |
| next_run | timestamp | YES | | |
| last_run | timestamp | YES | | |
| last_status | varchar(20) | YES | | |
| options | jsonb | YES | '{}' | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |
| updated_at | timestamp | YES | | |

### backup_operations_log
Log operazioni backup.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| id_log | integer | NO | serial | PK |
| operation | varchar(50) | NO | | backup/restore/delete |
| id_module | integer | YES | | |
| id_backup | integer | YES | | |
| details | jsonb | YES | | |
| status | varchar(20) | NO | | |
| message | text | YES | | |
| operator_id | integer | YES | | |
| created_at | timestamp | YES | CURRENT_TIMESTAMP | |

---

## Tabelle Utility

### sync_state
Stato sincronizzazione anagrafiche.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| key | varchar(50) | NO | | PK (farmacie/parafarmacie) |
| etag | varchar(100) | YES | | ETag HTTP |
| last_modified | varchar(100) | YES | | Last-Modified |
| last_sync | timestamp | YES | CURRENT_TIMESTAMP | |
| last_url | text | YES | | URL sincronizzazione |
| records_count | integer | YES | 0 | Record sincronizzati |
| extra_data | jsonb | YES | '{}' | |

### alembic_version
Versione migrazioni database.

| Colonna | Tipo | Null | Default | Descrizione |
|---------|------|------|---------|-------------|
| version_num | varchar(32) | NO | | Versione corrente |

---

## Viste Principali

### v_ordini_completi
Vista completa ordini con lookup anagrafica.

```sql
SELECT
    ot.id_testata,
    ot.id_acquisizione,
    v.codice_vendor AS vendor,
    ot.numero_ordine_vendor,
    ot.data_ordine,
    ot.data_consegna,
    ot.stato,
    -- Priorità MANUALE per i campi anagrafici
    CASE WHEN ot.lookup_method = 'MANUALE'
         THEN COALESCE(ot.codice_ministeriale_estratto, af.min_id)
         ELSE COALESCE(af.min_id, ot.codice_ministeriale_estratto)
    END AS min_id,
    -- ... altri campi con stessa logica
    a.nome_file_originale AS pdf_file
FROM ordini_testata ot
LEFT JOIN vendor v ON ot.id_vendor = v.id_vendor
LEFT JOIN anagrafica_farmacie af ON ot.id_farmacia_lookup = af.id_farmacia
LEFT JOIN acquisizioni a ON ot.id_acquisizione = a.id_acquisizione;
```

### v_supervisione_pending
Vista supervisioni espositore pending con count pattern.

```sql
SELECT
    se.*,
    ot.numero_ordine_vendor AS numero_ordine,
    ot.ragione_sociale_1 AS ragione_sociale,
    COALESCE(coe.count_approvazioni, 0) AS count_pattern,
    COALESCE(coe.is_ordinario, false) AS pattern_ordinario
FROM supervisione_espositore se
JOIN ordini_testata ot ON se.id_testata = ot.id_testata
LEFT JOIN criteri_ordinari_espositore coe ON se.pattern_signature = coe.pattern_signature
WHERE se.stato = 'PENDING';
```

### v_sync_status
Stato sincronizzazione anagrafiche.

```sql
SELECT
    key,
    last_sync,
    records_count,
    CASE
        WHEN last_sync IS NULL THEN 'MAI_SINCRONIZZATO'
        WHEN last_sync < CURRENT_TIMESTAMP - INTERVAL '7 days' THEN 'OBSOLETO'
        WHEN last_sync < CURRENT_TIMESTAMP - INTERVAL '1 day' THEN 'DA_AGGIORNARE'
        ELSE 'AGGIORNATO'
    END AS stato
FROM sync_state;
```

### Altre viste disponibili

| Vista | Descrizione |
|-------|-------------|
| v_supervisione_aic_compat | Compatibilità supervisione AIC |
| v_supervisione_lookup_compat | Compatibilità supervisione lookup |
| v_supervisione_listino_compat | Compatibilità supervisione listino |
| v_supervisione_espositore_compat | Compatibilità supervisione espositore |
| v_supervisione_prezzo_compat | Compatibilità supervisione prezzo |
| v_supervisione_grouped_pending | Supervisioni raggruppate pending |
| v_supervisione_listino_pending | Supervisioni listino pending |
| v_supervisione_lookup_pending | Supervisioni lookup pending |
| v_supervisioni_pending | Tutte le supervisioni pending |
| v_tracking_daily_stats | Statistiche tracking giornaliere |
| v_tracking_hourly_pattern | Pattern orario tracking |
| v_tracking_operator_summary | Riepilogo per operatore |
| v_tracking_report_filters | Filtri per report |
| v_tracking_sequences | Sequenze azioni |
| v_backup_dashboard | Dashboard backup |
| v_backup_history_detail | Dettaglio storico backup |

---

## Relazioni Foreign Key

```
operatore_azioni_log.id_operatore → operatori.id_operatore
operatore_azioni_log.azione_precedente_id → operatore_azioni_log.id_azione (self-reference)

supervisione_anagrafica.id_anomalia → anomalie.id_anomalia
supervisione_anagrafica.id_testata → ordini_testata.id_testata

supervisione_unificata.id_anomalia → anomalie.id_anomalia
supervisione_unificata.id_dettaglio → ordini_dettaglio.id_dettaglio
supervisione_unificata.id_testata → ordini_testata.id_testata
```

### Relazioni implicite (non FK)

```
ordini_testata.id_acquisizione → acquisizioni.id_acquisizione
ordini_testata.id_vendor → vendor.id_vendor
ordini_testata.id_farmacia_lookup → anagrafica_farmacie.id_farmacia
ordini_testata.id_parafarmacia_lookup → anagrafica_parafarmacie.id_parafarmacia

ordini_dettaglio.id_testata → ordini_testata.id_testata
ordini_dettaglio.id_parent_espositore → ordini_dettaglio.id_dettaglio (self-reference)

anomalie.id_testata → ordini_testata.id_testata
anomalie.id_dettaglio → ordini_dettaglio.id_dettaglio
anomalie.id_acquisizione → acquisizioni.id_acquisizione

supervisione_*.id_testata → ordini_testata.id_testata
supervisione_*.id_anomalia → anomalie.id_anomalia

esportazioni_dettaglio.id_esportazione → esportazioni.id_esportazione
esportazioni_dettaglio.id_testata → ordini_testata.id_testata

ftp_log.id_endpoint → ftp_endpoints.id
ftp_log.id_esportazione → esportazioni.id_esportazione

crm_messaggi.id_ticket → crm_tickets.id_ticket
crm_allegati.id_ticket → crm_tickets.id_ticket
crm_allegati.id_messaggio → crm_messaggi.id_messaggio

user_sessions.id_operatore → operatori.id_operatore
otp_tokens.id_operatore → operatori.id_operatore
password_reset_tokens.id_operatore → operatori.id_operatore
```

---

## Note Tecniche

### Convenzioni Nomi

- **id_** prefix: chiavi primarie e foreign key
- **data_** prefix: campi timestamp/date
- **is_** / **has_** prefix: campi boolean
- **_json** / **_jsonb** suffix: campi JSON
- **_hash** suffix: campi con valori hashati
- **_encrypted** suffix: campi crittografati

### Tipi Comuni

- `serial` / `integer`: ID auto-incrementanti
- `varchar(n)`: stringhe con lunghezza massima
- `text`: stringhe illimitate
- `numeric`: valori decimali (prezzi, sconti)
- `jsonb`: JSON binary (query performanti)
- `timestamp`: datetime senza timezone
- `boolean`: true/false

### Valori Default

- Timestamp: `CURRENT_TIMESTAMP`
- Boolean: `false` (sicurezza)
- Contatori: `0`
- Stati: valore iniziale (es. 'ESTRATTO', 'PENDING')
