# =============================================================================
# SERV.O v8.1 - TEST EXPORT TRACCIATI
# =============================================================================
# Test per generazione tracciati EDI (TO_T, TO_D)
# =============================================================================

import pytest
from fastapi.testclient import TestClient


class TestGenerazioneRimossa:
    """
    Gli endpoint POST /tracciati/genera, POST /tracciati/genera/{id} e
    GET /tracciati/preview/{id} sono stati rimossi nel 2026-08: leggevano la
    vista v_dettagli_completi, inesistente in DB, e la loro contabilita' export
    divergeva da quella reale (stato ESPORTATO senza passare da VALIDATO/FTP,
    una riga esportazioni per N ordini con nomi file fittizi, q_esportata mai
    valorizzata). Nessun componente frontend li invocava.

    L'unico percorso di generazione e' POST /ordini/{id}/valida.
    """

    @pytest.mark.integration
    def test_endpoint_generazione_non_esistono(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        for metodo, url in (
            ("post", "/api/v1/tracciati/genera"),
            ("post", "/api/v1/tracciati/genera/1"),
            ("get", "/api/v1/tracciati/preview/1"),
        ):
            response = getattr(client, metodo)(url, headers=auth_headers)
            assert response.status_code == 404, f"{metodo.upper()} {url} -> {response.status_code}"

    def test_nessun_riferimento_alla_vista_inesistente(self):
        """La vista v_dettagli_completi non esiste: nessuno deve interrogarla."""
        from pathlib import Path

        sorgenti = Path(__file__).resolve().parent.parent / "app"
        colpevoli = [
            str(f.relative_to(sorgenti))
            for f in sorgenti.rglob("*.py")
            if "v_dettagli_completi" in f.read_text(encoding="utf-8").lower()
        ]
        assert not colpevoli, f"riferimenti residui alla vista: {colpevoli}"


class TestFormatoTracciati:
    """Test formato tracciati EDI."""

    def test_tracciato_to_t_format(self):
        """Verifica formato TO_T (857 caratteri)."""
        from app.services.export.formatters.to_t import generate_to_t_line
        from app.services.export.formatters.common import TO_T_LENGTH

        # Dati minimi per testata
        testata = {
            "vendor": "ANGELINI",
            "numero_ordine": "123456",
            "min_id": "TST001",
            "partita_iva": "12345678901",
            "ragione_sociale": "FARMACIA TEST",
            "indirizzo": "Via Test 1",
            "cap": "00100",
            "citta": "Roma",
            "provincia": "RM",
            "data_ordine": "2026-01-15",
            "data_consegna": "2026-01-20",
            "gg_dilazione_1": 90
        }

        line = generate_to_t_line(testata)

        # Verifica lunghezza (857 chars per TO_T)
        assert len(line) == TO_T_LENGTH, f"TO_T length should be {TO_T_LENGTH}, got {len(line)}"

        # Verifica contenuto campi principali
        assert "123456" in line  # numero_ordine
        assert "TST001" in line  # min_id

    def test_tracciato_to_d_format(self):
        """Verifica formato TO_D (344 caratteri)."""
        from app.services.export.formatters.to_d import generate_to_d_line
        from app.services.export.formatters.common import TO_D_LENGTH

        # Dati minimi per riga dettaglio
        riga = {
            "numero_ordine": "123456",
            "n_riga": 1,
            "codice_aic": "012345678",
            "q_venduta": 10,
            "q_omaggio": 0,
            "q_sconto_merce": 0,
            "data_consegna": "2026-01-20",
            "sconto_1": 0.0,
            "sconto_2": 0.0,
            "sconto_3": 0.0,
            "sconto_4": 0.0,
            "prezzo_netto": 10.00,
            "prezzo_scontare": 15.00,
            "aliquota_iva": 10.0,
            "scorporo_iva": "S",
            "prezzo_pubblico": 15.00,
            "note_allestimento": ""
        }

        line = generate_to_d_line(riga)

        # Verifica lunghezza (344 chars per TO_D)
        assert len(line) == TO_D_LENGTH, f"TO_D length should be {TO_D_LENGTH}, got {len(line)}"

        # Verifica contenuto campi principali
        assert "123456" in line  # numero_ordine
        assert "012345678" in line  # codice_aic


class TestExportValidation:
    """Test validazione campi tracciato."""

    def test_valida_campi_tracciato_valid(self, monkeypatch):
        """Validazione con dati completi."""
        from app.services.export import validators
        from app.services.export.validators import valida_campi_tracciato

        # La v12.0 ha aggiunto il controllo di coerenza ERP, che interroga
        # anagrafica_clienti: con un MIN_ID di fantasia il test fallirebbe
        # sempre. Qui si verificano i CAMPI OBBLIGATORI, non l'aggancio ERP
        # (coperto a parte), quindi il controllo viene neutralizzato.
        monkeypatch.setattr(
            validators, '_valida_coerenza_erp_export', lambda min_id, piva: None
        )

        ordine = {
            "vendor": "ANGELINI",
            "numero_ordine": "123456",
            "partita_iva": "12345678901",
            "min_id": "TST001",
            "gg_dilazione_1": 90
        }

        dettagli = [
            {
                "n_riga": 1,
                "codice_aic": "012345678",
                "q_venduta": 10,
                "prezzo_netto": 10.00
            }
        ]

        result = valida_campi_tracciato(ordine, dettagli)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_valida_campi_tracciato_missing_vendor(self):
        """Validazione con vendor mancante."""
        from app.services.export.validators import valida_campi_tracciato

        ordine = {
            "vendor": "",  # Mancante
            "numero_ordine": "123456",
            "partita_iva": "12345678901",
            "min_id": "TST001"
        }

        dettagli = [
            {"codice_aic": "012345678", "q_venduta": 10, "prezzo_netto": 10.00}
        ]

        result = valida_campi_tracciato(ordine, dettagli)

        assert result["valid"] is False
        assert any("Vendor" in err for err in result["errors"])

    def test_valida_campi_tracciato_invalid_piva(self):
        """Validazione con P.IVA non valida."""
        from app.services.export.validators import valida_campi_tracciato

        ordine = {
            "vendor": "ANGELINI",
            "numero_ordine": "123456",
            "partita_iva": "123",  # Troppo corta
            "min_id": "TST001"
        }

        dettagli = [
            {"codice_aic": "012345678", "q_venduta": 10, "prezzo_netto": 10.00}
        ]

        result = valida_campi_tracciato(ordine, dettagli)

        assert result["valid"] is False
        assert any("Partita IVA" in err for err in result["errors"])

    def test_valida_campi_tracciato_missing_aic(self):
        """Validazione con AIC mancante in dettaglio."""
        from app.services.export.validators import valida_campi_tracciato

        ordine = {
            "vendor": "ANGELINI",
            "numero_ordine": "123456",
            "partita_iva": "12345678901",
            "min_id": "TST001"
        }

        dettagli = [
            {"codice_aic": "", "q_venduta": 10, "prezzo_netto": 10.00}  # AIC mancante
        ]

        result = valida_campi_tracciato(ordine, dettagli)

        assert result["valid"] is False
        assert any("AIC" in err for err in result["errors"])


class TestExportQueries:
    """Test query per export."""

    @pytest.mark.integration
    def test_get_ordini_esportabili(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Lista ordini pronti per export."""
        response = client.get(
            "/api/v1/tracciati/esportabili",
            headers=auth_headers
        )

        # Endpoint potrebbe non esistere
        assert response.status_code in [200, 404]


class TestDataConsegnaStimata:
    """
    Data di consegna stimata quando il PDF non la contiene.

    Regola unica: data_ordine + config.GG_CONSEGNA_LAVORATIVI_DEFAULT giorni
    lavorativi (sabato/domenica esclusi, festivi non gestiti).
    """

    def test_add_business_days_salta_weekend(self):
        from datetime import date
        from app.utils.dates import add_business_days

        # Mercoledi 2026-08-12 + 3 gg lavorativi -> lunedi 2026-08-17
        # (gio 13 = 1, ven 14 = 2, sab/dom saltati, lun 17 = 3)
        assert add_business_days(date(2026, 8, 12), 3) == date(2026, 8, 17)

        # Lunedi + 3 -> giovedi (nessun weekend attraversato)
        assert add_business_days(date(2026, 8, 10), 3) == date(2026, 8, 13)

        # 5 gg lavorativi = 7 giorni solari esatti da un feriale
        assert add_business_days(date(2026, 8, 10), 5) == date(2026, 8, 17)

        # n = 0 non muove la data
        assert add_business_days(date(2026, 8, 12), 0) == date(2026, 8, 12)

    def test_add_business_days_accetta_stringhe(self):
        from datetime import date
        from app.utils.dates import add_business_days

        assert add_business_days("12/08/2026", 3) == date(2026, 8, 17)
        assert add_business_days("2026-08-12", 3) == date(2026, 8, 17)

    def test_add_business_days_input_non_validi(self):
        from app.utils.dates import add_business_days

        assert add_business_days(None, 3) is None
        assert add_business_days("", 3) is None
        assert add_business_days("non-una-data", 3) is None

    def test_to_t_est_delivery_date_da_pdf(self):
        """Se il PDF ha la data, il tracciato la riporta invariata (pos 300-309)."""
        from app.services.export.formatters.to_t import generate_to_t_line

        line = generate_to_t_line({
            "vendor": "ANGELINI",
            "numero_ordine": "123456",
            "data_ordine": "2026-08-12",
            "data_consegna": "2026-08-20",
        })
        assert line[299:309] == "20/08/2026"

    def test_to_t_est_delivery_date_stimata(self):
        """Senza data consegna: data_ordine + N giorni lavorativi, NON la data odierna."""
        from app.config import config
        from app.services.export.formatters.to_t import generate_to_t_line
        from app.utils.dates import add_business_days

        line = generate_to_t_line({
            "vendor": "DOC_GENERICI",
            "numero_ordine": "123456",
            "data_ordine": "2026-08-12",
            "data_consegna": None,
        })
        attesa = add_business_days("2026-08-12", config.GG_CONSEGNA_LAVORATIVI_DEFAULT)
        assert line[299:309] == attesa.strftime("%d/%m/%Y")

    def test_to_t_est_delivery_date_senza_data_ordine(self):
        """Ultima rete: senza data_ordine si ricade sulla data odierna."""
        from datetime import date
        from app.services.export.formatters.to_t import generate_to_t_line

        line = generate_to_t_line({"vendor": "ANGELINI", "numero_ordine": "1"})
        assert line[299:309] == date.today().strftime("%d/%m/%Y")
    def test_to_d_ext_delivery_date_legge_data_consegna_riga(self):
        """
        Regressione: il formatter leggeva solo 'data_consegna', mentre
        ORDINI_DETTAGLIO fornisce 'data_consegna_riga' -> pos 75-84 usciva vuota
        anche con il dato presente a DB.
        """
        from app.services.export.formatters.to_d import generate_to_d_line

        line = generate_to_d_line({
            "numero_ordine": "123456",
            "n_riga": 1,
            "codice_aic": "012345678",
            "q_venduta": 10,
            "data_consegna_riga": "2026-08-20",
        })
        assert line[74:84] == "20/08/2026"

    def test_to_d_ext_delivery_date_stimata(self):
        """Senza data riga: stessa stima del TO_T, a partire da data_ordine."""
        from app.config import config
        from app.services.export.formatters.to_d import generate_to_d_line
        from app.utils.dates import add_business_days

        line = generate_to_d_line({
            "numero_ordine": "123456",
            "n_riga": 1,
            "codice_aic": "012345678",
            "q_venduta": 10,
            "data_ordine": "2026-08-12",
        })
        attesa = add_business_days("2026-08-12", config.GG_CONSEGNA_LAVORATIVI_DEFAULT)
        assert line[74:84] == attesa.strftime("%d/%m/%Y")

    def test_to_t_e_to_d_concordano(self):
        """TO_T e TO_D devono stimare la stessa data per lo stesso ordine."""
        from app.services.export.formatters.to_t import generate_to_t_line
        from app.services.export.formatters.to_d import generate_to_d_line

        testata = {"vendor": "DOC_GENERICI", "numero_ordine": "1", "data_ordine": "2026-08-12"}
        riga = {"numero_ordine": "1", "n_riga": 1, "codice_aic": "012345678",
                "q_venduta": 1, "data_ordine": "2026-08-12"}

        assert generate_to_t_line(testata)[299:309] == generate_to_d_line(riga)[74:84]
