# =============================================================================
# SERV.O v8.1 - TEST CONFIGURATION
# =============================================================================
# Global fixtures e configurazioni per pytest
# =============================================================================

import pytest
from fastapi.testclient import TestClient
from typing import Generator, Dict, Any
import os

# Imposta ambiente di test PRIMA di importare l'app
os.environ["TESTING"] = "true"

from app.main import app
from app.database_pg import get_db_cursor


# =============================================================================
# CLIENT FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """
    TestClient per chiamate API sincrone.
    Scope session per performance.
    """
    # TestClient di Starlette non usa 'app' come keyword argument
    c = TestClient(app)
    yield c


@pytest.fixture
def auth_headers(client: TestClient) -> Dict[str, str]:
    """
    Headers con token JWT per endpoint protetti.
    Usa credenziali di test (admin/admin123).
    """
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "admin",
            "password": "admin123"  # >= 6 chars required
        }
    )
    if response.status_code != 200:
        pytest.skip("Admin user not available for testing")

    token = response.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def operator_headers(client: TestClient) -> Dict[str, str]:
    """
    Headers con token JWT per utente operatore.
    """
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "operatore",
            "password": "operatore"
        }
    )
    if response.status_code != 200:
        pytest.skip("Operator user not available for testing")

    token = response.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest.fixture
def db_connection():
    """
    Connessione database per test diretti.
    """
    conn = get_db_connection()
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """
    Pulizia automatica dati di test dopo ogni test.
    Pattern: dati di test hanno prefisso 'TEST_'
    """
    yield

    try:
        with get_db_cursor() as cur:
            # Cleanup ordini di test
            cur.execute("""
                DELETE FROM ordini_dettaglio
                WHERE ordine_id IN (
                    SELECT id FROM ordini_testata
                    WHERE numero_ordine LIKE 'TEST_%'
                )
            """)
            cur.execute("""
                DELETE FROM anomalie
                WHERE ordine_id IN (
                    SELECT id FROM ordini_testata
                    WHERE numero_ordine LIKE 'TEST_%'
                )
            """)
            cur.execute("""
                DELETE FROM ordini_testata
                WHERE numero_ordine LIKE 'TEST_%'
            """)
    except Exception:
        # Ignora errori di cleanup
        pass


# =============================================================================
# SAMPLE DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_ordine_data() -> Dict[str, Any]:
    """
    Dati esempio per creazione ordine di test.
    """
    return {
        "numero_ordine": "TEST_001",
        "vendor": "ANGELINI",
        "data_ordine": "2026-01-15",
        "data_consegna": "2026-01-20",
        "farmacia_nome": "FARMACIA TEST",
        "farmacia_piva": "12345678901",
        "farmacia_indirizzo": "Via Test 1",
        "farmacia_cap": "00100",
        "farmacia_citta": "Roma",
        "farmacia_provincia": "RM",
        "min_id": "TST001",
        "stato": "ESTRATTO"
    }


@pytest.fixture
def sample_riga_data() -> Dict[str, Any]:
    """
    Dati esempio per riga ordine di test.
    """
    return {
        "n_riga": 1,
        "codice_aic": "012345678",
        "descrizione": "PRODOTTO TEST",
        "q_venduta": 10,
        "q_omaggio": 0,
        "q_sconto_merce": 0,
        "prezzo_pubblico": 15.50,
        "prezzo_netto": 10.00,
        "sconto_1": 10.00,
        "sconto_2": 0.00,
        "sconto_3": 0.00,
        "sconto_4": 0.00,
        "aliquota_iva": 10.00
    }


@pytest.fixture
def sample_supervisione_data() -> Dict[str, Any]:
    """
    Dati esempio per supervisione espositore.
    """
    return {
        "tipo": "ESPOSITORE",
        "stato": "PENDING",
        "pattern_signature": "TEST_PATTERN_001",
        "dettagli": {
            "parent_codice": "TEST123",
            "parent_descrizione": "ESPOSITORE TEST",
            "pezzi_attesi": 10,
            "pezzi_trovati": 8,
            "scostamento_percentuale": -20.0
        }
    }


# =============================================================================
# PDF FIXTURES
# =============================================================================

@pytest.fixture
def sample_pdf_path() -> str:
    """
    Path a PDF di test (se disponibile).
    """
    fixtures_path = os.path.join(
        os.path.dirname(__file__),
        "fixtures",
        "sample.pdf"
    )
    if not os.path.exists(fixtures_path):
        pytest.skip("Sample PDF not available")
    return fixtures_path


# =============================================================================
# MARKER CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """
    Configura marker personalizzati.
    """
    config.addinivalue_line(
        "markers", "slow: test che richiedono più tempo"
    )
    config.addinivalue_line(
        "markers", "integration: test di integrazione (richiedono DB)"
    )
    config.addinivalue_line(
        "markers", "unit: test unitari isolati"
    )
