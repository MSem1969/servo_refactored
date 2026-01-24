# =============================================================================
# SERV.O v10.1 - ANOMALIES DETECTION TESTS
# =============================================================================
# Unit tests for anomaly detection constants and helpers
# =============================================================================

import pytest


class TestAnomalyConstants:
    """Test anomaly codes and levels."""

    def test_anomaly_codes_exist(self):
        """All expected anomaly codes should be defined."""
        from app.services.anomalies.detection import ANOMALY_CODES

        expected_codes = [
            'ESP-A01', 'ESP-A02', 'ESP-A03', 'ESP-A04', 'ESP-A05', 'ESP-A06',
            'LKP-A01', 'LKP-A02', 'LKP-A03',
            'LST-A01', 'LST-A02', 'LST-A03',
            'AIC-A01', 'AIC-A02',
            'EXT-A01', 'EXT-A02',
        ]

        for code in expected_codes:
            assert code in ANOMALY_CODES, f"Missing anomaly code: {code}"

    def test_anomaly_levels_structure(self):
        """Anomaly levels should be properly structured."""
        from app.services.anomalies.detection import ANOMALY_LEVELS

        expected_levels = ['CRITICO', 'ERRORE', 'ATTENZIONE', 'INFO']

        for level in expected_levels:
            assert level in ANOMALY_LEVELS, f"Missing level: {level}"
            assert isinstance(ANOMALY_LEVELS[level], list)

    def test_blocking_anomalies_in_critical_or_error(self):
        """Blocking anomalies should be in CRITICO or ERRORE levels."""
        from app.services.anomalies.detection import ANOMALY_LEVELS, is_blocking_anomaly

        critico_codes = ANOMALY_LEVELS.get('CRITICO', [])
        errore_codes = ANOMALY_LEVELS.get('ERRORE', [])

        # All CRITICO codes should be blocking
        for code in critico_codes:
            assert is_blocking_anomaly(code), f"{code} should be blocking"

        # All ERRORE codes should be blocking
        for code in errore_codes:
            assert is_blocking_anomaly(code), f"{code} should be blocking"


class TestGetAnomalyLevel:
    """Test get_anomaly_level function."""

    def test_get_level_for_critico(self):
        """CRITICO codes should return CRITICO level."""
        from app.services.anomalies.detection import get_anomaly_level, ANOMALY_LEVELS

        for code in ANOMALY_LEVELS.get('CRITICO', []):
            assert get_anomaly_level(code) == 'CRITICO'

    def test_get_level_for_errore(self):
        """ERRORE codes should return ERRORE level."""
        from app.services.anomalies.detection import get_anomaly_level, ANOMALY_LEVELS

        for code in ANOMALY_LEVELS.get('ERRORE', []):
            assert get_anomaly_level(code) == 'ERRORE'

    def test_get_level_unknown_code(self):
        """Unknown codes should default to ATTENZIONE."""
        from app.services.anomalies.detection import get_anomaly_level

        assert get_anomaly_level('UNKNOWN-99') == 'ATTENZIONE'


class TestIsBlockingAnomaly:
    """Test is_blocking_anomaly function."""

    def test_lookup_anomalies_blocking(self):
        """LKP-A01 and LKP-A02 should be blocking."""
        from app.services.anomalies.detection import is_blocking_anomaly

        assert is_blocking_anomaly('LKP-A01') is True
        assert is_blocking_anomaly('LKP-A02') is True

    def test_lookup_warning_not_blocking(self):
        """LKP-A03 should NOT be blocking."""
        from app.services.anomalies.detection import is_blocking_anomaly

        assert is_blocking_anomaly('LKP-A03') is False

    def test_espositore_anomalies(self):
        """ESP anomalies in CRITICO/ERRORE should be blocking."""
        from app.services.anomalies.detection import is_blocking_anomaly

        # Typically blocking
        assert is_blocking_anomaly('ESP-A01') is True  # Pezzi mancanti
        assert is_blocking_anomaly('ESP-A02') is True  # Pezzi in eccesso

    def test_unknown_code_not_blocking(self):
        """Unknown codes should not be blocking."""
        from app.services.anomalies.detection import is_blocking_anomaly

        assert is_blocking_anomaly('UNKNOWN-CODE') is False
