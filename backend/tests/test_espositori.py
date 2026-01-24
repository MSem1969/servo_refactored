# =============================================================================
# SERV.O v10.1 - ESPOSITORI TESTS
# =============================================================================
# Unit tests for espositore detection and models
# =============================================================================

import pytest


class TestIdentificaTipoRiga:
    """Test row type identification."""

    def test_sconto_merce(self):
        """SC.MERCE should be identified."""
        from app.services.espositori.detection import identifica_tipo_riga

        assert identifica_tipo_riga('123456789', 'Prodotto', 'SC.MERCE') == 'SCONTO_MERCE'
        assert identifica_tipo_riga('123456789', 'Prodotto', 'SCMERCE') == 'SCONTO_MERCE'

    def test_materiale_pop(self):
        """P.O.P should be identified."""
        from app.services.espositori.detection import identifica_tipo_riga

        assert identifica_tipo_riga('123456789', 'Materiale', 'P.O.P') == 'MATERIALE_POP'
        assert identifica_tipo_riga('123456789', 'Materiale', 'POP') == 'MATERIALE_POP'

    def test_angelini_parent_espositore_6_cifre(self):
        """ANGELINI: 6-digit code with XXPZ should be PARENT_ESPOSITORE."""
        from app.services.espositori.detection import identifica_tipo_riga

        result = identifica_tipo_riga('415734', 'FSTAND 24PZ PRODOTTO', '', 'ANGELINI')
        assert result == 'PARENT_ESPOSITORE'

    def test_angelini_parent_espositore_keywords(self):
        """ANGELINI: 6-digit code with keywords should be PARENT_ESPOSITORE."""
        from app.services.espositori.detection import identifica_tipo_riga

        keywords = ['BANCO', 'DBOX', 'FSTAND', 'EXPO', 'DISPLAY', 'ESPOSITORE', 'CESTA']
        for keyword in keywords:
            result = identifica_tipo_riga('123456', f'{keyword} PRODOTTO', '', 'ANGELINI')
            assert result == 'PARENT_ESPOSITORE', f"Failed for keyword: {keyword}"

    def test_angelini_promo_autonoma(self):
        """ANGELINI: 6-digit code without keywords should be PROMO_AUTONOMA."""
        from app.services.espositori.detection import identifica_tipo_riga

        result = identifica_tipo_riga('123456', 'PRODOTTO NORMALE', '', 'ANGELINI')
        assert result == 'PROMO_AUTONOMA'

    def test_menarini_parent_espositore(self):
        """MENARINI: -- code with keywords should be PARENT_ESPOSITORE."""
        from app.services.espositori.detection import identifica_tipo_riga

        result = identifica_tipo_riga('--', 'EXPO BANCO 3+3', '', 'MENARINI')
        assert result == 'PARENT_ESPOSITORE'

    def test_menarini_standard_product(self):
        """MENARINI: non-espositore should be PRODOTTO_STANDARD."""
        from app.services.espositori.detection import identifica_tipo_riga

        result = identifica_tipo_riga('943303507', 'AFTAMED GEL 10ML', '', 'MENARINI')
        assert result == 'PRODOTTO_STANDARD'

    def test_standard_product_9_digit_aic(self):
        """Standard 9-digit AIC should be PRODOTTO_STANDARD."""
        from app.services.espositori.detection import identifica_tipo_riga

        result = identifica_tipo_riga('012345678', 'PRODOTTO NORMALE', '')
        assert result == 'PRODOTTO_STANDARD'


class TestEstraiPezziEspositore:
    """Test piece extraction from description."""

    def test_fstand_pattern(self):
        """FSTAND XXPZ pattern."""
        from app.services.espositori.detection import estrai_pezzi_espositore

        pezzi, totale = estrai_pezzi_espositore('FSTAND 24PZ PRODOTTO', 2)
        assert pezzi == 24
        assert totale == 48

    def test_dbox_pattern(self):
        """DBOX XXPZ pattern."""
        from app.services.espositori.detection import estrai_pezzi_espositore

        pezzi, totale = estrai_pezzi_espositore('DBOX 12PZ', 1)
        assert pezzi == 12
        assert totale == 12

    def test_generic_pz_pattern(self):
        """Generic XXPZ pattern."""
        from app.services.espositori.detection import estrai_pezzi_espositore

        pezzi, totale = estrai_pezzi_espositore('ESPOSITORE 36 PZ', 1)
        assert pezzi == 36
        assert totale == 36

    def test_menarini_sum_pattern(self):
        """MENARINI X+Y pattern (e.g., 3+3)."""
        from app.services.espositori.detection import estrai_pezzi_espositore

        pezzi, totale = estrai_pezzi_espositore('EXPO BANCO 3+3', 1)
        assert pezzi == 6
        assert totale == 6

    def test_no_pattern_returns_none(self):
        """No pattern should return (None, None)."""
        from app.services.espositori.detection import estrai_pezzi_espositore

        pezzi, totale = estrai_pezzi_espositore('PRODOTTO NORMALE', 1)
        assert pezzi is None
        assert totale is None

    def test_empty_description(self):
        """Empty description should return (None, None)."""
        from app.services.espositori.detection import estrai_pezzi_espositore

        pezzi, totale = estrai_pezzi_espositore('', 1)
        assert pezzi is None
        assert totale is None


class TestEspositoreModel:
    """Test Espositore dataclass."""

    def test_pezzi_attesi_totali(self):
        """Test pezzi_attesi_totali calculation."""
        from app.services.espositori.models import Espositore

        esp = Espositore(
            codice_aic='',
            codice_originale='123456',
            codice_materiale='',
            descrizione='FSTAND 24PZ',
            pezzi_per_unita=24,
            quantita_parent=2
        )

        assert esp.pezzi_attesi_totali == 48

    def test_aggiungi_child(self):
        """Test adding child rows."""
        from app.services.espositori.models import Espositore, RigaChild

        esp = Espositore(
            codice_aic='',
            codice_originale='123456',
            codice_materiale='',
            descrizione='FSTAND 24PZ',
            pezzi_per_unita=24,
            quantita_parent=1
        )

        child = RigaChild(
            codice_aic='012345678',
            codice_originale='012345678',
            codice_materiale='',
            descrizione='PRODOTTO',
            quantita=10,
            prezzo_netto=5.0,
            valore_netto=50.0
        )

        esp.aggiungi_child(child)

        assert len(esp.righe_child) == 1
        assert esp.pezzi_accumulati == 10
        assert esp.valore_netto_accumulato == 50.0

    def test_espositore_vuoto_non_conta_pezzi(self):
        """Empty espositore (omaggio) should not count pieces."""
        from app.services.espositori.models import Espositore, RigaChild

        esp = Espositore(
            codice_aic='',
            codice_originale='123456',
            codice_materiale='',
            descrizione='FSTAND 24PZ',
            pezzi_per_unita=24,
            quantita_parent=1
        )

        child_vuoto = RigaChild(
            codice_aic='',
            codice_originale='--',
            codice_materiale='',
            descrizione='ESPOSITORE VUOTO',
            quantita=1,
            prezzo_netto=0.0,
            valore_netto=0.0,
            is_espositore_vuoto=True
        )

        esp.aggiungi_child(child_vuoto)

        assert esp.pezzi_accumulati == 0  # Vuoto non conta
        assert len(esp.righe_child) == 1

    def test_verifica_scostamento_zero(self):
        """Zero deviation."""
        from app.services.espositori.models import Espositore, RigaChild

        esp = Espositore(
            codice_aic='',
            codice_originale='123456',
            codice_materiale='',
            descrizione='TEST',
            pezzi_per_unita=10,
            quantita_parent=1
        )

        for i in range(10):
            esp.aggiungi_child(RigaChild(
                codice_aic=f'00000000{i}',
                codice_originale=f'00000000{i}',
                codice_materiale='',
                descrizione='PROD',
                quantita=1,
                prezzo_netto=1.0,
                valore_netto=1.0
            ))

        fascia, pct = esp.verifica_scostamento()
        assert fascia == 'ZERO'
        assert pct == 0.0

    def test_verifica_scostamento_alto(self):
        """High deviation (>20%)."""
        from app.services.espositori.models import Espositore, RigaChild

        esp = Espositore(
            codice_aic='',
            codice_originale='123456',
            codice_materiale='',
            descrizione='TEST',
            pezzi_per_unita=10,
            quantita_parent=1
        )

        # Only 5 pieces instead of 10 = -50%
        for i in range(5):
            esp.aggiungi_child(RigaChild(
                codice_aic=f'00000000{i}',
                codice_originale=f'00000000{i}',
                codice_materiale='',
                descrizione='PROD',
                quantita=1,
                prezzo_netto=1.0,
                valore_netto=1.0
            ))

        fascia, pct = esp.verifica_scostamento()
        assert fascia == 'ALTO'
        assert pct == -50.0


class TestContestoElaborazione:
    """Test ContestoElaborazione dataclass."""

    def test_default_values(self):
        """Test default initialization."""
        from app.services.espositori.models import ContestoElaborazione

        ctx = ContestoElaborazione()

        assert ctx.espositore_attivo is None
        assert ctx.righe_output == []
        assert ctx.anomalie == []
        assert ctx.contatore_righe == 0
        assert ctx.vendor == 'ANGELINI'
        assert ctx.espositori_elaborati == 0
        assert ctx.chiusure_normali == 0
        assert ctx.chiusure_forzate == 0

    def test_custom_vendor(self):
        """Test custom vendor initialization."""
        from app.services.espositori.models import ContestoElaborazione

        ctx = ContestoElaborazione(vendor='MENARINI')
        assert ctx.vendor == 'MENARINI'
