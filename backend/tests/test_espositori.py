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
        from app.services.espositore import identifica_tipo_riga

        assert identifica_tipo_riga('123456789', 'Prodotto', 'SC.MERCE') == 'SCONTO_MERCE'
        assert identifica_tipo_riga('123456789', 'Prodotto', 'SCMERCE') == 'SCONTO_MERCE'

    def test_materiale_pop(self):
        """P.O.P should be identified."""
        from app.services.espositore import identifica_tipo_riga

        assert identifica_tipo_riga('123456789', 'Materiale', 'P.O.P') == 'MATERIALE_POP'
        assert identifica_tipo_riga('123456789', 'Materiale', 'POP') == 'MATERIALE_POP'

    def test_angelini_parent_espositore_6_cifre(self):
        """ANGELINI: 6-digit code with XXPZ should be PARENT_ESPOSITORE."""
        from app.services.espositore import identifica_tipo_riga

        result = identifica_tipo_riga('415734', 'FSTAND 24PZ PRODOTTO', '', 'ANGELINI')
        assert result == 'PARENT_ESPOSITORE'

    def test_angelini_parent_espositore_keywords(self):
        """ANGELINI: 6-digit code with keywords should be PARENT_ESPOSITORE."""
        from app.services.espositore import identifica_tipo_riga

        keywords = ['BANCO', 'DBOX', 'FSTAND', 'EXPO', 'DISPLAY', 'ESPOSITORE', 'CESTA']
        for keyword in keywords:
            result = identifica_tipo_riga('123456', f'{keyword} PRODOTTO', '', 'ANGELINI')
            assert result == 'PARENT_ESPOSITORE', f"Failed for keyword: {keyword}"

    def test_angelini_promo_autonoma(self):
        """ANGELINI: 6-digit code without keywords should be PROMO_AUTONOMA."""
        from app.services.espositore import identifica_tipo_riga

        result = identifica_tipo_riga('123456', 'PRODOTTO NORMALE', '', 'ANGELINI')
        assert result == 'PROMO_AUTONOMA'

    def test_menarini_parent_espositore(self):
        """MENARINI: -- code with keywords should be PARENT_ESPOSITORE."""
        from app.services.espositore import identifica_tipo_riga

        result = identifica_tipo_riga('--', 'EXPO BANCO 3+3', '', 'MENARINI')
        assert result == 'PARENT_ESPOSITORE'

    def test_menarini_standard_product(self):
        """MENARINI: non-espositore should be PRODOTTO_STANDARD."""
        from app.services.espositore import identifica_tipo_riga

        result = identifica_tipo_riga('943303507', 'AFTAMED GEL 10ML', '', 'MENARINI')
        assert result == 'PRODOTTO_STANDARD'

    def test_standard_product_9_digit_aic(self):
        """Standard 9-digit AIC should be PRODOTTO_STANDARD."""
        from app.services.espositore import identifica_tipo_riga

        result = identifica_tipo_riga('012345678', 'PRODOTTO NORMALE', '')
        assert result == 'PRODOTTO_STANDARD'


class TestEstraiPezziEspositore:
    """Test piece extraction from description."""

    def test_fstand_pattern(self):
        """FSTAND XXPZ pattern."""
        from app.services.espositore import estrai_pezzi_espositore

        pezzi, totale = estrai_pezzi_espositore('FSTAND 24PZ PRODOTTO', 2)
        assert pezzi == 24
        assert totale == 48

    def test_dbox_pattern(self):
        """DBOX XXPZ pattern."""
        from app.services.espositore import estrai_pezzi_espositore

        pezzi, totale = estrai_pezzi_espositore('DBOX 12PZ', 1)
        assert pezzi == 12
        assert totale == 12

    def test_generic_pz_pattern(self):
        """Generic XXPZ pattern."""
        from app.services.espositore import estrai_pezzi_espositore

        pezzi, totale = estrai_pezzi_espositore('ESPOSITORE 36 PZ', 1)
        assert pezzi == 36
        assert totale == 36

    def test_menarini_sum_pattern(self):
        """MENARINI X+Y pattern (e.g., 3+3)."""
        from app.services.espositore import estrai_pezzi_espositore

        pezzi, totale = estrai_pezzi_espositore('EXPO BANCO 3+3', 1)
        assert pezzi == 6
        assert totale == 6

    def test_no_pattern_returns_none(self):
        """No pattern should return (None, None)."""
        from app.services.espositore import estrai_pezzi_espositore

        pezzi, totale = estrai_pezzi_espositore('PRODOTTO NORMALE', 1)
        assert pezzi is None
        assert totale is None

    def test_empty_description(self):
        """Empty description should return (None, None)."""
        from app.services.espositore import estrai_pezzi_espositore

        pezzi, totale = estrai_pezzi_espositore('', 1)
        assert pezzi is None
        assert totale is None


class TestEspositoreModel:
    """Test Espositore dataclass."""

    def test_pezzi_attesi_totali(self):
        """Test pezzi_attesi_totali calculation."""
        from app.services.espositore import Espositore

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
        from app.services.espositore import Espositore, RigaChild

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
        from app.services.espositore import Espositore, RigaChild

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
        from app.services.espositore import Espositore, RigaChild

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
        from app.services.espositore import Espositore, RigaChild

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
        from app.services.espositore import ContestoElaborazione

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
        from app.services.espositore import ContestoElaborazione

        ctx = ContestoElaborazione(vendor='MENARINI')
        assert ctx.vendor == 'MENARINI'


# =============================================================================
# MENARINI - Blocco espositore: merge parent + riga materiale
# =============================================================================
# Un espositore MENARINI occupa piu' righe di tabella: il parent ("--") porta i
# prezzi ma nessun codice, la riga materiale porta il codice ma nessun prezzo, e
# la sua posizione nel blocco e' libera. Questi test fissano l'appaiamento nelle
# tre posizioni osservate nei PDF reali.

def _riga(descrizione, cod_min, qta=1, prezzo='0,00 €', netto='0,00 €', p_netto='--'):
    """Riga della tabella prodotti MENARINI come la restituisce pdfplumber."""
    return [descrizione, cod_min, str(qta), prezzo, '--', '--', '--', p_netto, netto]


PARENT = _riga('LAILA ANSIA EXPO BANCO GIOV', '--', 1, '98,44 €', '78,75 €')
MATERIALE = _riga('LAILA EXPO BANCO GIOVANI 2026', '87AB54', 1, '0,00 €', '0,00 €', '0,00 €')
CHILD_A = _riga('LAILA 80MG 14CPR CP', '044460018', 4, '8,83 €', '28,26 €', '7,06 €')
CHILD_B = _riga('LAILA 80MG 28CPR CP', '044460020', 4, '15,78 €', '50,50 €', '12,62 €')


class TestSegmentazioneBloccoMenarini:
    """La riga materiale va appaiata al parent ovunque si trovi nel blocco."""

    def _segmenta(self, righe):
        from app.services.extraction.vendors.menarini import _segmenta_blocchi_espositore
        return _segmenta_blocchi_espositore(righe)

    def test_materiale_in_testa(self):
        blocchi, parent_di, materiali, anomalie = self._segmenta(
            [PARENT, MATERIALE, CHILD_A, CHILD_B]
        )
        assert blocchi[0]['codice'] == '87AB54'
        assert materiali == {1}
        assert parent_di == {1: 0, 2: 0, 3: 0}
        assert anomalie == []

    def test_materiale_in_mezzo(self):
        blocchi, _, materiali, anomalie = self._segmenta(
            [PARENT, CHILD_A, MATERIALE, CHILD_B]
        )
        assert blocchi[0]['codice'] == '87AB54'
        assert materiali == {2}
        assert anomalie == []

    def test_materiale_in_coda(self):
        """Caso che l'appaiamento in chiusura per valore perdeva (6/38 blocchi)."""
        blocchi, _, materiali, anomalie = self._segmenta(
            [PARENT, CHILD_A, CHILD_B, MATERIALE]
        )
        assert blocchi[0]['codice'] == '87AB54'
        assert materiali == {3}
        assert anomalie == []

    def test_due_blocchi_consecutivi(self):
        """Il blocco finisce dove ne comincia un altro."""
        parent2 = _riga('SUST BANCO 50+ FLAC 6PZ', '--', 1, '74,94 €', '54,71 €')
        materiale2 = _riga('SUSTENIUM BANCO 50+', '87AA25', 1, '0,00 €', '0,00 €', '0,00 €')
        blocchi, parent_di, materiali, anomalie = self._segmenta(
            [CHILD_A, PARENT, CHILD_B, MATERIALE, parent2, materiale2]
        )
        assert sorted(blocchi) == [1, 4]
        assert blocchi[1]['codice'] == '87AB54'
        assert blocchi[4]['codice'] == '87AA25'
        assert 0 not in parent_di  # riga prima del primo parent: autonoma
        assert materiali == {3, 5}
        assert anomalie == []

    def test_blocco_senza_materiale_genera_esp_a08(self):
        blocchi, _, materiali, anomalie = self._segmenta([PARENT, CHILD_A, CHILD_B])
        assert blocchi[0]['codice'] == ''
        assert materiali == set()
        assert len(anomalie) == 1
        assert anomalie[0]['codice_anomalia'] == 'ESP-A08'
        assert anomalie[0]['livello'] == 'ATTENZIONE'
        assert anomalie[0]['richiede_supervisione'] is False

    def test_blocco_con_due_materiali_usa_il_primo(self):
        materiale2 = _riga('ALTRO CONTENITORE', '87AB99', 1, '0,00 €', '0,00 €', '0,00 €')
        blocchi, _, materiali, anomalie = self._segmenta(
            [PARENT, MATERIALE, CHILD_A, materiale2]
        )
        assert blocchi[0]['codice'] == '87AB54'
        assert materiali == {1}
        assert len(anomalie) == 1
        assert anomalie[0]['codice_anomalia'] == 'ESP-A08'

    def test_child_con_valore_zero_non_e_materiale(self):
        """Un AIC a valore 0 e' un omaggio, non il contenitore."""
        omaggio = _riga('LAILA 80MG 14CPR CP', '044460018', 4, '0,00 €', '0,00 €', '0,00 €')
        blocchi, _, materiali, anomalie = self._segmenta([PARENT, omaggio, CHILD_A])
        assert materiali == set()
        assert anomalie[0]['codice_anomalia'] == 'ESP-A08'


class TestChiusuraBloccoMenarini:
    """La chiusura segue il blocco, il valore resta solo come verifica."""

    def _elabora(self, righe_raw):
        from app.services.espositore import elabora_righe_ordine
        return elabora_righe_ordine(righe_raw, vendor='MENARINI')

    def _parent(self, netto=78.75, pubblico=98.44, codice='87AB54'):
        return {
            'codice_originale': codice, 'codice_materiale': codice, 'codice_aic': '',
            'descrizione': 'LAILA ANSIA EXPO BANCO GIOV', 'tipo_riga': 'PARENT_ESPOSITORE',
            'quantita': 1, 'q_venduta': 1, 'prezzo_netto': netto, 'prezzo_pubblico': pubblico,
            'valore_netto': netto, 'is_espositore': True, 'is_child': False,
        }

    def _child(self, aic, quantita, netto, valore):
        return {
            'codice_originale': aic, 'codice_aic': aic, 'descrizione': f'PROD {aic}',
            'tipo_riga': 'CHILD_ESPOSITORE', '_belongs_to_parent': True, 'is_child': True,
            'quantita': quantita, 'q_venduta': quantita,
            'prezzo_netto': netto, 'valore_netto': valore,
        }

    def test_parent_conserva_codice_e_prezzi_dichiarati(self):
        ctx = self._elabora([
            self._parent(),
            self._child('044460018', 4, 7.06, 28.26),
            self._child('044460020', 4, 12.62, 50.50),
        ])
        parent = ctx.righe_output[0]
        assert parent['tipo_riga'] == 'PARENT_ESPOSITORE'
        assert parent['codice_originale'] == '87AB54'
        assert parent['codice_materiale'] == '87AB54'
        # 78,75 dichiarato, non 78,76 ricalcolato dalla somma dei child
        assert parent['prezzo_netto'] == 78.75
        assert parent['prezzo_pubblico'] == 98.44
        assert ctx.chiusure_normali == 1
        assert ctx.chiusure_forzate == 0
        assert ctx.anomalie == []

    def test_child_in_output_con_valore_dichiarato(self):
        ctx = self._elabora([
            self._parent(),
            self._child('044460018', 4, 7.06, 28.26),
            self._child('044460020', 4, 12.62, 50.50),
        ])
        child = [r for r in ctx.righe_output if r['tipo_riga'] == 'CHILD_ESPOSITORE']
        assert [c['codice_aic'] for c in child] == ['044460018', '044460020']
        assert [c['valore_netto'] for c in child] == [28.26, 50.50]

    def test_child_dopo_il_raggiungimento_del_valore_resta_nel_blocco(self):
        """Con la chiusura per valore l'ultimo child usciva dal gruppo."""
        ctx = self._elabora([
            self._parent(netto=100.00),
            self._child('044460018', 4, 24.75, 99.00),
            self._child('044460020', 1, 1.00, 1.00),
        ])
        child = [r for r in ctx.righe_output if r['tipo_riga'] == 'CHILD_ESPOSITORE']
        assert len(child) == 2
        assert ctx.anomalie == []

    def test_secondo_parent_chiude_il_primo_senza_anomalia(self):
        ctx = self._elabora([
            self._parent(),
            self._child('044460018', 4, 7.06, 28.26),
            self._child('044460020', 4, 12.62, 50.50),
            self._parent(netto=54.71, pubblico=74.94, codice='87AA25'),
            self._child('989415373', 6, 9.12, 54.71),
        ])
        parents = [r for r in ctx.righe_output if r['tipo_riga'] == 'PARENT_ESPOSITORE']
        assert [p['codice_originale'] for p in parents] == ['87AB54', '87AA25']
        assert ctx.chiusure_normali == 2
        assert ctx.chiusure_forzate == 0
        assert ctx.anomalie == []

    def test_scostamento_di_valore_genera_anomalia(self):
        ctx = self._elabora([
            self._parent(netto=100.00),
            self._child('044460018', 4, 10.0, 40.00),
        ])
        assert len(ctx.anomalie) == 1
        assert ctx.anomalie[0]['codice_anomalia'] == 'ESP-A01'

    def test_espositore_senza_child_resta_chiusura_forzata(self):
        ctx = self._elabora([self._parent()])
        assert ctx.chiusure_forzate == 1
        assert ctx.anomalie[0]['codice_anomalia'] == 'ESP-A03'


class TestScontiRigheNonEspositore:
    """
    Le righe che passano da elabora_righe_ordine devono conservare gli sconti.

    _crea_riga_output leggeva 'sconto_pct', chiave che nessun estrattore
    valorizza: in DB tutte le righe ANGELINI e MENARINI avevano sconto_1 = 0
    pur avendo sconti reali nel PDF.
    """

    def _riga_output(self, riga, vendor='ANGELINI'):
        from app.services.espositore import elabora_righe_ordine
        base = {'codice_aic': '035618026', 'codice_originale': '035618026',
                'descrizione': 'MOMENTACT 400MG 12 CPR', 'quantita': 6,
                'prezzo_netto': 6.06, 'aliquota_iva': 10}
        ctx = elabora_righe_ordine([{**base, **riga}], vendor=vendor)
        return ctx.righe_output[0]

    def test_sconto_cascata_angelini(self):
        """ANGELINI espone gli sconti come 'sconto1'..'sconto4' (es. 33,35+1)."""
        out = self._riga_output({'sconto1': 33.35, 'sconto2': 1.0})
        assert out['sconto1'] == 33.35
        assert out['sconto2'] == 1.0
        assert out['sconto3'] == 0.0
        assert out['sconto4'] == 0.0

    def test_sconto_menarini(self):
        out = self._riga_output({'sconto1': 37.0}, vendor='MENARINI')
        assert out['sconto1'] == 37.0

    def test_sconto_con_nome_cooper(self):
        """COOPER usa 'sconto_1'."""
        out = self._riga_output({'sconto_1': 60.0})
        assert out['sconto1'] == 60.0

    def test_sconto_pct_legacy(self):
        out = self._riga_output({'sconto_pct': 12.5})
        assert out['sconto1'] == 12.5

    def test_nessuno_sconto(self):
        out = self._riga_output({})
        assert out['sconto1'] == 0.0
