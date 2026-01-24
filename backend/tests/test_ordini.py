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
