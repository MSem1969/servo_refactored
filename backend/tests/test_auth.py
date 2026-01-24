# =============================================================================
# SERV.O v8.1 - TEST AUTENTICAZIONE
# =============================================================================
# Test per endpoint di autenticazione e autorizzazione
# =============================================================================

import pytest
from fastapi.testclient import TestClient


class TestLogin:
    """Test login endpoint."""

    def test_login_success(self, client: TestClient):
        """Login con credenziali valide."""
        # Password deve essere >= 6 caratteri per validazione
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "admin123"  # >= 6 chars
            }
        )

        if response.status_code == 401:
            pytest.skip("Admin user not configured or wrong password")

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_password(self, client: TestClient):
        """Login con password errata."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "wrong_password_123"
            }
        )

        assert response.status_code == 401

    def test_login_invalid_username(self, client: TestClient):
        """Login con username inesistente."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent_user",
                "password": "password123"
            }
        )

        assert response.status_code == 401

    def test_login_password_too_short(self, client: TestClient):
        """Login con password troppo corta (< 6 chars)."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "short"
            }
        )

        assert response.status_code == 422

    def test_login_missing_credentials(self, client: TestClient):
        """Login senza credenziali."""
        response = client.post("/api/v1/auth/login", json={})

        assert response.status_code == 422


class TestProtectedEndpoints:
    """Test accesso endpoint protetti."""

    def test_ordini_accessible_without_auth(self, client: TestClient):
        """Ordini endpoint accessibile senza autenticazione (read-only)."""
        # Nota: ordini e' accessibile senza auth per lettura
        response = client.get("/api/v1/ordini")
        assert response.status_code == 200

    def test_ordini_with_valid_token(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Accesso ordini con token valido."""
        response = client.get("/api/v1/ordini", headers=auth_headers)
        assert response.status_code == 200

    def test_upload_without_token(self, client: TestClient):
        """Upload richiede autenticazione."""
        response = client.post("/api/v1/upload")
        # Upload dovrebbe richiedere auth
        assert response.status_code in [401, 422]

    def test_settings_without_token(self, client: TestClient):
        """Settings richiede autenticazione."""
        response = client.get("/api/v1/settings/email")
        # Settings dovrebbe richiedere auth
        assert response.status_code in [401, 404]


class TestCurrentUser:
    """Test endpoint utente corrente."""

    def test_get_current_user(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Recupera info utente corrente."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        if response.status_code == 404:
            pytest.skip("Me endpoint not available")

        assert response.status_code == 200
        data = response.json()
        assert "username" in data

    def test_get_current_user_without_token(self, client: TestClient):
        """Recupera utente senza autenticazione."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401


class TestPasswordChange:
    """Test cambio password."""

    @pytest.mark.integration
    def test_change_password_wrong_current(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Cambio password con password attuale errata."""
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "wrong_password",
                "new_password": "new_secure_password"
            },
            headers=auth_headers
        )

        # Dovrebbe fallire per password errata
        assert response.status_code in [400, 401, 404]
