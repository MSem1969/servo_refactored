# =============================================================================
# SERV.O v10.1 - LISTINI PARSING TESTS
# =============================================================================
# Unit tests for listini parsing functions
# =============================================================================

import pytest


class TestParseDecimalIt:
    """Test Italian decimal parsing."""

    def test_comma_decimal(self):
        """Italian format with comma."""
        from app.services.listini.parsing import parse_decimal_it

        assert parse_decimal_it('38,35') == 38.35
        assert parse_decimal_it('100,00') == 100.0
        assert parse_decimal_it('0,50') == 0.5

    def test_dot_decimal(self):
        """Standard format with dot."""
        from app.services.listini.parsing import parse_decimal_it

        assert parse_decimal_it('38.35') == 38.35

    def test_empty_returns_none(self):
        """Empty values return None."""
        from app.services.listini.parsing import parse_decimal_it

        assert parse_decimal_it('') is None
        assert parse_decimal_it('   ') is None
        assert parse_decimal_it('0') is None

    def test_invalid_returns_none(self):
        """Invalid values return None."""
        from app.services.listini.parsing import parse_decimal_it

        assert parse_decimal_it('abc') is None
        assert parse_decimal_it(None) is None


class TestParsePrezzoIntero:
    """Test integer price parsing with implicit decimals."""

    def test_two_decimals(self):
        """Standard 2 decimal places."""
        from app.services.listini.parsing import parse_prezzo_intero

        assert parse_prezzo_intero('13590', decimals=2) == 135.90
        assert parse_prezzo_intero('00013590', decimals=2) == 135.90

    def test_three_decimals(self):
        """CODIFI format with 3 decimal places."""
        from app.services.listini.parsing import parse_prezzo_intero

        assert parse_prezzo_intero('37130', decimals=3) == 37.130
        assert parse_prezzo_intero('00037130', decimals=3) == 37.130

    def test_leading_zeros_stripped(self):
        """Leading zeros should be stripped."""
        from app.services.listini.parsing import parse_prezzo_intero

        assert parse_prezzo_intero('00000100', decimals=2) == 1.0

    def test_empty_returns_none(self):
        """Empty values return None."""
        from app.services.listini.parsing import parse_prezzo_intero

        assert parse_prezzo_intero('') is None
        assert parse_prezzo_intero('0') is None


class TestParseDataYyyymmdd:
    """Test YYYYMMDD date parsing."""

    def test_valid_date(self):
        """Valid date conversion."""
        from app.services.listini.parsing import parse_data_yyyymmdd

        assert parse_data_yyyymmdd('20180206') == '2018-02-06'
        assert parse_data_yyyymmdd('20261231') == '2026-12-31'

    def test_invalid_date_returns_none(self):
        """Invalid dates return None."""
        from app.services.listini.parsing import parse_data_yyyymmdd

        assert parse_data_yyyymmdd('20181332') is None  # Invalid month/day
        assert parse_data_yyyymmdd('2018') is None  # Too short
        assert parse_data_yyyymmdd('') is None


class TestNormalizzaCodiceAic:
    """Test AIC code normalization."""

    def test_padding_to_9_digits(self):
        """Codes should be padded to 9 digits."""
        from app.services.listini.parsing import normalizza_codice_aic

        assert normalizza_codice_aic('39887070') == '039887070'
        assert normalizza_codice_aic('12345') == '000012345'

    def test_already_9_digits(self):
        """9-digit codes unchanged."""
        from app.services.listini.parsing import normalizza_codice_aic

        assert normalizza_codice_aic('012345678') == '012345678'

    def test_strips_non_numeric(self):
        """Non-numeric characters stripped."""
        from app.services.listini.parsing import normalizza_codice_aic

        assert normalizza_codice_aic('AIC-12345') == '000012345'
        assert normalizza_codice_aic(' 123 456 ') == '000123456'

    def test_empty_returns_empty(self):
        """Empty input returns empty string."""
        from app.services.listini.parsing import normalizza_codice_aic

        assert normalizza_codice_aic('') == ''
        assert normalizza_codice_aic(None) == ''


class TestScorporoIva:
    """Test VAT extraction."""

    def test_scorporo_10_percent(self):
        """Standard 10% VAT extraction."""
        from app.services.listini.parsing import scorporo_iva

        # 135.90 / 1.10 = 123.545... = 123.55 (rounded)
        result = scorporo_iva(135.90, 10)
        assert result == 123.55

    def test_scorporo_22_percent(self):
        """22% VAT extraction."""
        from app.services.listini.parsing import scorporo_iva

        # 122.00 / 1.22 = 100.0
        result = scorporo_iva(122.00, 22)
        assert result == 100.0

    def test_zero_vat(self):
        """Zero VAT."""
        from app.services.listini.parsing import scorporo_iva

        result = scorporo_iva(100.0, 0)
        assert result == 100.0

    def test_zero_price_returns_none(self):
        """Zero or negative price returns None."""
        from app.services.listini.parsing import scorporo_iva

        assert scorporo_iva(0, 10) is None
        assert scorporo_iva(-10, 10) is None


class TestCalcolaPrezzoNetto:
    """Test net price calculation with discounts."""

    def test_cascading_discounts(self):
        """Cascading discount formula."""
        from app.services.listini.parsing import calcola_prezzo_netto

        # 100 * 0.9 * 0.95 = 85.50
        result, formula = calcola_prezzo_netto(100.0, 10.0, 5.0, 0, 0, 'SCONTO_CASCATA')
        assert result == 85.50

    def test_sum_discounts(self):
        """Sum discount formula."""
        from app.services.listini.parsing import calcola_prezzo_netto

        # 100 * (1 - 0.15) = 85.00
        result, formula = calcola_prezzo_netto(100.0, 10.0, 5.0, 0, 0, 'SCONTO_SOMMA')
        assert result == 85.00

    def test_no_discounts(self):
        """No discounts applied."""
        from app.services.listini.parsing import calcola_prezzo_netto

        result, formula = calcola_prezzo_netto(100.0, 0, 0, 0, 0, 'SCONTO_CASCATA')
        assert result == 100.0

    def test_invalid_price_returns_none(self):
        """Zero/negative price returns None."""
        from app.services.listini.parsing import calcola_prezzo_netto

        result, formula = calcola_prezzo_netto(0, 10, 0, 0, 0, 'SCONTO_CASCATA')
        assert result is None

    def test_invalid_formula_returns_none(self):
        """Invalid formula returns None."""
        from app.services.listini.parsing import calcola_prezzo_netto

        result, formula = calcola_prezzo_netto(100.0, 10, 0, 0, 0, 'INVALID')
        assert result is None


class TestCeilDecimal:
    """Test ceiling decimal rounding."""

    def test_ceil_to_2_decimals(self):
        """Ceiling to 2 decimal places."""
        from app.services.listini.parsing import ceil_decimal

        assert ceil_decimal(123.541, 2) == 123.55
        assert ceil_decimal(123.001, 2) == 123.01

    def test_exact_value_unchanged(self):
        """Exact values unchanged."""
        from app.services.listini.parsing import ceil_decimal

        assert ceil_decimal(123.50, 2) == 123.50

    def test_none_returns_none(self):
        """None returns None."""
        from app.services.listini.parsing import ceil_decimal

        assert ceil_decimal(None) is None
