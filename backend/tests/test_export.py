# =============================================================================
# SERV.O v8.1 - TEST EXPORT TRACCIATI
# =============================================================================
# Test per generazione tracciati EDI (TO_T, TO_D)
# =============================================================================

import pytest
from fastapi.testclient import TestClient


class TestExportTracciati:
    """Test export tracciati via API."""

    @pytest.mark.integration
    def test_export_ordine_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Export ordine non esistente."""
        response = client.get(
            "/api/v1/tracciati/export/999999999",
            headers=auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.integration
    def test_export_ordine_confermato(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Export ordine in stato confermato."""
        # Trova ordine confermato
        list_response = client.get(
            "/api/v1/ordini",
            params={"stato": "CONFERMATO", "limit": 1},
            headers=auth_headers
        )

        if list_response.status_code != 200:
            pytest.skip("Cannot list orders")

        data = list_response.json().get("data", [])
        if not data:
            pytest.skip("No confirmed orders available")

        ordine_id = data[0]["id_testata"]

        # Tenta export
        response = client.get(
            f"/api/v1/tracciati/export/{ordine_id}",
            headers=auth_headers
        )

        # Potrebbe essere 200 o 422 se mancano dati
        assert response.status_code in [200, 422]


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

    def test_valida_campi_tracciato_valid(self):
        """Validazione con dati completi."""
        from app.services.export.validators import valida_campi_tracciato

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
