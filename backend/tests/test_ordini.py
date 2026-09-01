# =============================================================================
# SERV.O v8.1 - TEST ORDINI
# =============================================================================
# Test per endpoint CRUD ordini
# =============================================================================

import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any


class TestListOrdini:
    """Test lista ordini."""

    def test_list_ordini(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Lista ordini con paginazione default."""
        response = client.get("/api/v1/ordini", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        # API returns 'data' array, not 'ordini'
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_list_ordini_with_pagination(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Lista ordini con paginazione custom."""
        response = client.get(
            "/api/v1/ordini",
            params={"limit": 5, "offset": 0},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 5

    def test_list_ordini_filter_by_vendor(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Lista ordini filtrati per vendor."""
        response = client.get(
            "/api/v1/ordini",
            params={"vendor": "ANGELINI"},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        for ordine in data["data"]:
            assert ordine["vendor"] == "ANGELINI"

    def test_list_ordini_filter_by_stato(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Lista ordini filtrati per stato."""
        response = client.get(
            "/api/v1/ordini",
            params={"stato": "ESTRATTO"},
            headers=auth_headers
        )

        assert response.status_code == 200


class TestGetOrdine:
    """Test recupero singolo ordine."""

    def test_get_ordine_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Ordine non esistente."""
        response = client.get(
            "/api/v1/ordini/999999999",
            headers=auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.integration
    def test_get_ordine_details(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Recupera dettagli ordine esistente."""
        # Prima ottieni lista per trovare un ID valido
        list_response = client.get(
            "/api/v1/ordini",
            params={"limit": 1},
            headers=auth_headers
        )

        if list_response.status_code != 200:
            pytest.skip("Cannot list orders")

        ordini = list_response.json().get("ordini", [])
        if not ordini:
            pytest.skip("No orders available for testing")

        ordine_id = ordini[0]["id"]

        # Recupera dettagli
        response = client.get(
            f"/api/v1/ordini/{ordine_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == ordine_id


class TestOrdineStato:
    """Test cambio stato ordine."""

    @pytest.mark.integration
    def test_update_stato_ordine(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Aggiorna stato ordine."""
        # Trova ordine in stato ESTRATTO
        list_response = client.get(
            "/api/v1/ordini",
            params={"stato": "ESTRATTO", "limit": 1},
            headers=auth_headers
        )

        if list_response.status_code != 200:
            pytest.skip("Cannot list orders")

        ordini = list_response.json().get("ordini", [])
        if not ordini:
            pytest.skip("No extracted orders available")

        ordine_id = ordini[0]["id"]

        # Tenta conferma
        response = client.post(
            f"/api/v1/ordini/{ordine_id}/conferma",
            headers=auth_headers
        )

        # Potrebbe fallire se ci sono anomalie bloccanti
        assert response.status_code in [200, 400, 409]


class TestOrdineRighe:
    """Test gestione righe ordine."""

    @pytest.mark.integration
    def test_get_righe_ordine(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Recupera righe di un ordine."""
        # Trova un ordine
        list_response = client.get(
            "/api/v1/ordini",
            params={"limit": 1},
            headers=auth_headers
        )

        if list_response.status_code != 200:
            pytest.skip("Cannot list orders")

        ordini = list_response.json().get("ordini", [])
        if not ordini:
            pytest.skip("No orders available")

        ordine_id = ordini[0]["id"]

        # Recupera righe
        response = client.get(
            f"/api/v1/ordini/{ordine_id}/righe",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "righe" in data
        assert isinstance(data["righe"], list)


class TestOrdineSearch:
    """Test ricerca ordini."""

    def test_search_ordini_by_numero(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Ricerca per numero ordine."""
        response = client.get(
            "/api/v1/ordini",
            params={"search": "TEST"},
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_search_ordini_by_farmacia(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Ricerca per nome farmacia."""
        response = client.get(
            "/api/v1/ordini",
            params={"search": "FARMACIA"},
            headers=auth_headers
        )

        assert response.status_code == 200


class TestCalcolaStatoOrdine:
    """
    Regole di _calcola_stato_ordine (funzione pura).

    Il ricalcolo cancellava lo stato ANOMALIA a ogni conferma di riga: l'ordine
    sembrava a posto ma non generava il tracciato, perche' anomalie bloccanti e
    supervisioni pending restavano aperte.
    """

    def _stats(self, totale=3, archiviato=0, confermato=0, esportato=0):
        return {'totale': totale, 'archiviato': archiviato,
                'confermato': confermato, 'esportato': esportato}

    def test_blocchi_aperti_su_stato_pre_tracciato(self):
        from app.services.orders.fulfillment import _calcola_stato_ordine

        assert _calcola_stato_ordine('ANOMALIA', self._stats(), 0,
                                     ha_blocchi_aperti=True) == 'ANOMALIA'
        assert _calcola_stato_ordine('ESTRATTO', self._stats(confermato=2), 0,
                                     ha_blocchi_aperti=True) == 'ANOMALIA'

    def test_senza_blocchi_comportamento_invariato(self):
        from app.services.orders.fulfillment import _calcola_stato_ordine

        assert _calcola_stato_ordine('ANOMALIA', self._stats(), 0) == 'ESTRATTO'
        assert _calcola_stato_ordine('ESTRATTO', self._stats(confermato=2), 0) == 'CONFERMATO'

    def test_stati_post_tracciato_non_toccati(self):
        """VALIDATO/ESPORTATO non retrocedono ad ANOMALIA: erano gia' privi di blocchi."""
        from app.services.orders.fulfillment import _calcola_stato_ordine

        for stato in ('VALIDATO', 'ESPORTATO', 'PARZ_ESPORTATO'):
            assert _calcola_stato_ordine(stato, self._stats(esportato=3), 0,
                                         ha_blocchi_aperti=True) == stato

    def test_archiviato_ed_evaso_hanno_precedenza(self):
        from app.services.orders.fulfillment import _calcola_stato_ordine

        tutte_archiviate = self._stats(totale=3, archiviato=3)
        assert _calcola_stato_ordine('ANOMALIA', tutte_archiviate, 0,
                                     ha_blocchi_aperti=True) == 'ARCHIVIATO'
        assert _calcola_stato_ordine('ANOMALIA', self._stats(), 0, ha_evasione=True,
                                     ha_blocchi_aperti=True) == 'EVASO'

    def test_ordine_senza_righe_non_e_archiviato(self):
        """
        totale == 0 significa estrazione fallita, non "tutte archiviate".

        L'ordine DOC_GENERICI 0698002291 usciva ARCHIVIATO con 0 righe: il
        ricalcolo lo chiudeva d'ufficio e ne archiviava anomalie e supervisioni,
        rendendo invisibile il fatto che il PDF non era stato letto.
        """
        from app.services.orders.fulfillment import _calcola_stato_ordine

        nessuna_riga = self._stats(totale=0)
        assert _calcola_stato_ordine('ESTRATTO', nessuna_riga, 0,
                                     ha_blocchi_aperti=True) == 'ANOMALIA'
        assert _calcola_stato_ordine('ESTRATTO', nessuna_riga, 0) == 'ESTRATTO'
        # Archiviazione manuale di un ordine vuoto: resta archiviato
        assert _calcola_stato_ordine('ARCHIVIATO', nessuna_riga, 0) == 'ARCHIVIATO'
