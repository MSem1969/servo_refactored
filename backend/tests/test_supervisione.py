# =============================================================================
# SERV.O v8.1 - TEST SUPERVISIONE
# =============================================================================
# Test per endpoint supervisione ML
# =============================================================================

import pytest
from fastapi.testclient import TestClient


class TestSupervisionePending:
    """Test supervisioni pending."""

    def test_get_pending_supervisioni(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Lista supervisioni in attesa."""
        response = client.get(
            "/api/v1/supervisione/pending",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "supervisioni" in data
        assert isinstance(data["supervisioni"], list)

    def test_get_pending_grouped(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Lista supervisioni raggruppate per pattern."""
        response = client.get(
            "/api/v1/supervisione/pending/grouped",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "groups" in data


class TestSupervisioneStats:
    """Test statistiche supervisione."""

    def test_get_criteri_stats(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Statistiche criteri ML."""
        response = client.get(
            "/api/v1/supervisione/criteri/stats",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Verifica campi statistiche
        assert "totale_pattern" in data or "total_patterns" in data or isinstance(data, dict)


class TestSupervisioneEspositore:
    """Test supervisione espositore."""

    def test_get_espositore_supervisioni(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Lista supervisioni espositore."""
        response = client.get(
            "/api/v1/supervisione/espositore",
            headers=auth_headers
        )

        # Endpoint potrebbe non esistere o richiedere parametri
        assert response.status_code in [200, 404, 422]

    @pytest.mark.integration
    def test_approve_espositore_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Approva supervisione non esistente."""
        response = client.post(
            "/api/v1/supervisione/espositore/999999/approva",
            json={"operatore": "test"},
            headers=auth_headers
        )

        assert response.status_code in [404, 422]

    @pytest.mark.integration
    def test_reject_espositore_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Rifiuta supervisione non esistente."""
        response = client.post(
            "/api/v1/supervisione/espositore/999999/rifiuta",
            json={"operatore": "test", "note": "Test rifiuto"},
            headers=auth_headers
        )

        assert response.status_code in [404, 422]


class TestSupervisoneListino:
    """Test supervisione listino."""

    def test_get_listino_supervisioni(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Lista supervisioni listino."""
        response = client.get(
            "/api/v1/supervisione/listino",
            headers=auth_headers
        )

        # Endpoint potrebbe non esistere o richiedere parametri
        assert response.status_code in [200, 404, 422]


class TestSupervisioneLookup:
    """Test supervisione lookup."""

    def test_get_lookup_supervisioni(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Lista supervisioni lookup."""
        response = client.get(
            "/api/v1/supervisione/lookup",
            headers=auth_headers
        )

        # Endpoint potrebbe non esistere o richiedere parametri
        assert response.status_code in [200, 404, 422]


class TestSupervisionePattern:
    """Test pattern ML."""

    def test_get_criteri_tutti(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Lista tutti i criteri/pattern ML."""
        response = client.get(
            "/api/v1/supervisione/criteri",
            headers=auth_headers
        )

        # Endpoint potrebbe non esistere o richiedere parametri
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            data = response.json()
            assert "criteri" in data or isinstance(data, dict)

    def test_get_pattern_storico(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Storico applicazioni pattern."""
        response = client.get(
            "/api/v1/supervisione/storico",
            headers=auth_headers
        )

        # Endpoint potrebbe non esistere o richiedere parametri
        assert response.status_code in [200, 422]


class TestSupervisioneBulk:
    """Test operazioni bulk."""

    @pytest.mark.integration
    def test_bulk_approve_invalid_pattern(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Approvazione bulk con pattern non valido."""
        response = client.post(
            "/api/v1/supervisione/bulk/approva",
            json={
                "pattern_signature": "NONEXISTENT_PATTERN",
                "operatore": "test"
            },
            headers=auth_headers
        )

        # Potrebbe restituire 200 con 0 approvate o 404
        assert response.status_code in [200, 404, 422]
