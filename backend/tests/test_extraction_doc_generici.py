# =============================================================================
# SERV.O - TEST ESTRAZIONE DOC_GENERICI
# =============================================================================
# La riga prodotto e' riconosciuta da AIC + quantita': classe e condizione sono
# testo libero e non devono mai far scartare la riga.
#
# Regressione reale: l'ordine 0698002291 (FARMACIA CAPUTO CROTONE) conteneva
# "902649298 EMATONIL PLUS GEL 50 ml tubo 96 3-3 TO EMATONIL". Classe "3-3" e
# condizione "TO EMATONIL" non rispettavano il pattern `[A-Z]-[A-Z]` +
# "ACCORDO TO": zero righe estratte, ordine archiviato d'ufficio, in silenzio.
# =============================================================================

from app.services.extraction.vendors.doc_generici import extract_doc_generici


HEADER = """TRANSFER ORDER Num. 0698002291 DEL 31/08/2026
Grossista SOFAD S.R.L.
Agente 10683 BELTRANO LAURA
Farmacia FARMACIA CAPUTO CROTONE SRL P.IVA 03768730792
Ind.Fiscale Via VIA ROMA 122
CAP 88900 Città CROTONE Prov. KR
Ind.Consegna Merce Via VIA ROMA 122
CAP 88900 Città CROTONE Prov. KR
Telefono Fax
COD. A.I.C. Prodotto N.pz Classe Condizione"""


def _estrai(righe_prodotto, totale=None):
    """Costruisce un PDF-testo minimale e ritorna il singolo ordine estratto."""
    corpo = [HEADER] + righe_prodotto
    if totale is not None:
        corpo.append(f"Totale: {totale}")
    corpo.append("Pagina 1 di 1")
    text = "\n".join(corpo)
    ordini = extract_doc_generici(text, text.split("\n"))
    assert len(ordini) == 1
    return ordini[0]


class TestRigaProdotto:
    """Classe e condizione non vincolano il riconoscimento della riga."""

    def test_classe_numerica_e_condizione_libera(self):
        ordine = _estrai(
            ["902649298 EMATONIL PLUS GEL 50 ml tubo 96 3-3 TO EMATONIL"],
            totale=96,
        )

        assert len(ordine["righe"]) == 1
        riga = ordine["righe"][0]
        assert riga["codice_aic"] == "902649298"
        assert riga["descrizione"] == "EMATONIL PLUS GEL 50 ml tubo"
        assert riga["q_venduta"] == 96
        assert riga["classe_farmaco"] == "3-3"
        assert riga["condizione"] == "TO EMATONIL"

    def test_formato_storico_invariato(self):
        """A-A + ACCORDO TO: il caso maggioritario non cambia."""
        ordine = _estrai(
            ["034110015 Ticlopidina DOC 250 mg 30 cpr 10 A-A ACCORDO TO"],
            totale=10,
        )

        riga = ordine["righe"][0]
        assert riga["codice_aic"] == "034110015"
        assert riga["descrizione"] == "Ticlopidina DOC 250 mg 30 cpr"
        assert riga["q_venduta"] == 10
        assert riga["classe_farmaco"] == "A-A"
        assert riga["condizione"] == "ACCORDO TO"

    def test_quantita_e_ultimo_intero_non_il_primo(self):
        """La descrizione contiene numeri: la quantita' e' l'ultimo intero isolato."""
        ordine = _estrai(
            ["047302056 Metformina DOC 1000 mg 60 cpr 15 A-A ACCORDO TO"],
            totale=15,
        )

        assert ordine["righe"][0]["q_venduta"] == 15
        assert ordine["righe"][0]["descrizione"] == "Metformina DOC 1000 mg 60 cpr"

    def test_condizione_multiparola(self):
        ordine = _estrai(
            ["034789012 MUSCORIL GEL 50 g 12 O-O TO MUSCORIL OTC"],
            totale=12,
        )

        riga = ordine["righe"][0]
        assert riga["q_venduta"] == 12
        assert riga["condizione"] == "TO MUSCORIL OTC"

    def test_riga_senza_classe_ne_condizione(self):
        ordine = _estrai(["034110015 Ticlopidina DOC 250 mg 30 cpr 10"], totale=10)

        riga = ordine["righe"][0]
        assert riga["q_venduta"] == 10
        assert riga["classe_farmaco"] == ""
        assert riga["condizione"] == ""


class TestTotaleFooter:
    """DOCGEN-A04 e' la rete di sicurezza sulla lettura delle quantita'."""

    def test_separatore_migliaia(self):
        """"Totale: 1.108" vale 1108, non 1: altrimenti A04 sparava a vuoto."""
        righe = [
            "034110015 Ticlopidina DOC 250 mg 30 cpr 1000 A-A ACCORDO TO",
            "047302056 Metformina DOC 1000 mg 60 cpr 108 A-A ACCORDO TO",
        ]
        ordine = _estrai(righe, totale="1.108")

        assert ordine["totale_pezzi_footer"] == 1108
        assert sum(r["q_venduta"] for r in ordine["righe"]) == 1108
        codici = [a["codice_anomalia"] for a in ordine["anomalie_estrazione"]]
        assert "DOCGEN-A04" not in codici

    def test_totale_incoerente_genera_anomalia(self):
        ordine = _estrai(
            ["034110015 Ticlopidina DOC 250 mg 30 cpr 10 A-A ACCORDO TO"],
            totale=99,
        )

        codici = [a["codice_anomalia"] for a in ordine["anomalie_estrazione"]]
        assert "DOCGEN-A04" in codici
