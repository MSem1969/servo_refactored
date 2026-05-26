# =============================================================================
# SERV.O - TEST RIEMISSIONE TRACCIATO
# =============================================================================
# Test unitari per la logica di edit + riemissione del tracciato:
#  - _apply_export_suffix(force=...) con casi base / clone parziale / riemissione
#  - sostituzione del numero ordine in TO_T (pos 11-40) e TO_D (pos 1-30, multi-riga)
#  - normalizzazione CRLF
# =============================================================================

import pytest

from app.services.export.generator import _apply_export_suffix
from app.services.export.riemissione import (
    _replace_order_number_to_t,
    _replace_order_number_to_d,
    _normalize_crlf,
    TO_T_ORDER_START,
    TO_T_ORDER_END,
    TO_D_ORDER_START,
    TO_D_ORDER_END,
)


# ---------------------------------------------------------------------------
# Mock db per _apply_export_suffix
# ---------------------------------------------------------------------------

class _MockCursor:
    def __init__(self, count):
        self._count = count

    def fetchone(self):
        return (self._count,)


class _MockDb:
    """db.execute(...).fetchone()[0] → count."""
    def __init__(self, count):
        self._count = count

    def execute(self, *_args, **_kwargs):
        return _MockCursor(self._count)


# ---------------------------------------------------------------------------
# _apply_export_suffix
# ---------------------------------------------------------------------------

class TestApplyExportSuffix:
    def test_export_normale_no_punto(self):
        """Ordine base: applica suffisso .N."""
        db = _MockDb(count=0)  # nessuna esportazione precedente -> .1
        assert _apply_export_suffix("ORD001", db, 42) == "ORD001.1"

    def test_export_normale_con_punto_invariato(self):
        """Clone parziale (numero gia' suffissato): non tocca il numero."""
        db = _MockDb(count=5)
        # Senza force=True, un numero con punto viene restituito invariato
        assert _apply_export_suffix("ORD001.2", db, 42) == "ORD001.2"

    def test_export_normale_counter_incrementa(self):
        """Counter da esportazioni_dettaglio + 1."""
        db = _MockDb(count=2)  # gia' 2 esportazioni -> nuovo suffisso .3
        assert _apply_export_suffix("ORD001", db, 42) == "ORD001.3"

    def test_riemissione_force_su_numero_base(self):
        """force=True: applica sempre il tail."""
        db = _MockDb(count=1)  # 1 esportazione (originale) -> nuovo .2
        assert _apply_export_suffix("ORD001", db, 42, force=True) == "ORD001.2"

    def test_riemissione_force_su_clone_parziale(self):
        """force=True su numero gia' suffissato (clone): aggiunge tail ulteriore."""
        db = _MockDb(count=1)
        # Clone ORD001.2 riemesso 1 volta -> ORD001.2.2
        assert _apply_export_suffix("ORD001.2", db, 42, force=True) == "ORD001.2.2"

    def test_riemissione_force_counter_multiplo(self):
        """Riemissione multipla: counter cresce."""
        db = _MockDb(count=3)
        assert _apply_export_suffix("ORD001", db, 42, force=True) == "ORD001.4"


# ---------------------------------------------------------------------------
# Sostituzione numero ordine TO_T
# ---------------------------------------------------------------------------

class TestReplaceOrderNumberToT:
    def _make_line(self, numero):
        """Costruisce una riga TO_T di 869 char con numero in pos 11-40."""
        vendor = "HAL_FARVI ".ljust(10)
        numero_field = numero.ljust(30)[:30]
        # Riempio il resto con spazi fino a 869
        tail = " " * (869 - 10 - 30)
        line = vendor + numero_field + tail
        assert len(line) == 869
        return line

    def test_sostituzione_mantiene_lunghezza(self):
        original = self._make_line("ORD001.1")
        out = _replace_order_number_to_t(original + "\r\n", "ORD001.2")
        first_line = out.split("\r\n")[0]
        assert len(first_line) == 869
        # Il numero nuovo deve essere alla posizione corretta
        assert first_line[TO_T_ORDER_START:TO_T_ORDER_END].strip() == "ORD001.2"

    def test_sostituzione_numero_corto(self):
        original = self._make_line("ORD001.1")
        out = _replace_order_number_to_t(original, "X")
        first_line = out.split("\r\n")[0]
        # Numero corto -> padded a 30 char
        assert first_line[TO_T_ORDER_START:TO_T_ORDER_END] == "X".ljust(30)
        assert len(first_line) == 869

    def test_sostituzione_non_tocca_altri_campi(self):
        original = self._make_line("ORD001.1")
        out = _replace_order_number_to_t(original, "ORD001.2")
        first_line = out.split("\r\n")[0]
        # Vendor (pos 1-10) preservato
        assert first_line[:10] == "HAL_FARVI "
        # Resto della riga preservato
        assert first_line[TO_T_ORDER_END:] == original[TO_T_ORDER_END:]

    def test_riga_troppo_corta_solleva(self):
        with pytest.raises(ValueError):
            _replace_order_number_to_t("riga troppo corta", "ORD001.1")


# ---------------------------------------------------------------------------
# Sostituzione numero ordine TO_D
# ---------------------------------------------------------------------------

class TestReplaceOrderNumberToD:
    def _make_line(self, numero, payload="X" * 200):
        """Costruisce una riga TO_D con numero in pos 1-30."""
        numero_field = numero.ljust(30)[:30]
        line = numero_field + payload
        return line

    def test_sostituzione_su_singola_riga(self):
        original = self._make_line("ORD001.1") + "\r\n"
        out = _replace_order_number_to_d(original, "ORD001.2")
        line = out.split("\r\n")[0]
        assert line[TO_D_ORDER_START:TO_D_ORDER_END].rstrip() == "ORD001.2"
        # Payload preservato
        assert line[TO_D_ORDER_END:] == "X" * 200

    def test_sostituzione_su_piu_righe(self):
        l1 = self._make_line("ORD001.1", payload="A" * 200)
        l2 = self._make_line("ORD001.1", payload="B" * 200)
        l3 = self._make_line("ORD001.1", payload="C" * 200)
        content = "\r\n".join([l1, l2, l3]) + "\r\n"
        out = _replace_order_number_to_d(content, "ORD001.2")
        lines = [l for l in out.split("\r\n") if l]
        assert len(lines) == 3
        for i, line in enumerate(lines):
            assert line[TO_D_ORDER_START:TO_D_ORDER_END].rstrip() == "ORD001.2"
        # Payload preservato per ogni riga
        assert lines[0][TO_D_ORDER_END:] == "A" * 200
        assert lines[1][TO_D_ORDER_END:] == "B" * 200
        assert lines[2][TO_D_ORDER_END:] == "C" * 200

    def test_righe_vuote_preservate(self):
        l1 = self._make_line("ORD001.1")
        content = l1 + "\r\n\r\n"  # riga vuota finale
        out = _replace_order_number_to_d(content, "ORD001.2")
        # Riga vuota mantenuta
        assert out.endswith("\r\n")

    def test_riga_troppo_corta_solleva(self):
        # Numero ordine + meno di 30 char totali
        with pytest.raises(ValueError):
            _replace_order_number_to_d("abc", "ORD001.1")


# ---------------------------------------------------------------------------
# Normalizzazione CRLF
# ---------------------------------------------------------------------------

class TestNormalizeCRLF:
    def test_lf_to_crlf(self):
        assert _normalize_crlf("a\nb\nc") == "a\r\nb\r\nc"

    def test_cr_solo_to_crlf(self):
        assert _normalize_crlf("a\rb\rc") == "a\r\nb\r\nc"

    def test_crlf_invariato(self):
        assert _normalize_crlf("a\r\nb\r\nc") == "a\r\nb\r\nc"

    def test_mix(self):
        assert _normalize_crlf("a\r\nb\nc\rd") == "a\r\nb\r\nc\r\nd"
