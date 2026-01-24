# =============================================================================
# SERV.O v8.1 - ORDINI FACTORIES
# =============================================================================
# Factory per generazione ordini e righe di test
# =============================================================================

import factory
from datetime import date, timedelta
from typing import Dict, Any


class OrdineFactory(factory.Factory):
    """
    Factory per generazione ordini testata.
    """

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: n + 10000)
    numero_ordine = factory.Sequence(lambda n: f"TEST_{n:06d}")
    vendor = factory.Iterator(["ANGELINI", "BAYER", "MENARINI", "CODIFI"])
    data_ordine = factory.LazyFunction(lambda: date.today().isoformat())
    data_consegna = factory.LazyFunction(
        lambda: (date.today() + timedelta(days=5)).isoformat()
    )

    # Dati farmacia
    farmacia_nome = factory.Sequence(lambda n: f"FARMACIA TEST {n}")
    farmacia_piva = factory.Sequence(lambda n: f"{n:011d}")
    farmacia_indirizzo = factory.Sequence(lambda n: f"Via Test {n}")
    farmacia_cap = "00100"
    farmacia_citta = "Roma"
    farmacia_provincia = "RM"
    min_id = factory.Sequence(lambda n: f"TST{n:03d}")

    # Stato
    stato = "ESTRATTO"
    note = ""

    @classmethod
    def create_batch_for_vendor(cls, vendor: str, count: int = 5) -> list:
        """Crea batch di ordini per un vendor specifico."""
        return [cls(vendor=vendor) for _ in range(count)]

    @classmethod
    def create_with_righe(cls, num_righe: int = 3) -> Dict[str, Any]:
        """Crea ordine con righe dettaglio."""
        ordine = cls()
        righe = RigaOrdineFactory.create_batch(num_righe, ordine_id=ordine["id"])
        return {
            "testata": ordine,
            "righe": righe
        }


class RigaOrdineFactory(factory.Factory):
    """
    Factory per generazione righe ordine.
    """

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: n + 100000)
    ordine_id = None
    n_riga = factory.Sequence(lambda n: n + 1)

    # Prodotto
    codice_aic = factory.Sequence(lambda n: f"{n:09d}")
    descrizione = factory.Sequence(lambda n: f"PRODOTTO TEST {n}")

    # Quantita
    q_venduta = factory.Faker("random_int", min=1, max=50)
    q_omaggio = 0
    q_sconto_merce = 0

    # Prezzi
    prezzo_pubblico = factory.Faker(
        "pydecimal", left_digits=2, right_digits=2, positive=True
    )
    prezzo_netto = factory.LazyAttribute(
        lambda obj: float(obj.prezzo_pubblico) * 0.7
    )
    prezzo_scontare = factory.LazyAttribute(
        lambda obj: float(obj.prezzo_pubblico)
    )

    # Sconti
    sconto_1 = 0.0
    sconto_2 = 0.0
    sconto_3 = 0.0
    sconto_4 = 0.0

    # IVA
    aliquota_iva = 10.0
    scorporo_iva = "S"

    # Note
    note_allestimento = ""

    @classmethod
    def create_espositore_parent(cls, ordine_id: int) -> Dict[str, Any]:
        """Crea riga parent espositore."""
        return cls(
            ordine_id=ordine_id,
            descrizione="ESPOSITORE BANCO 24PZ",
            codice_aic="500123456",
            q_venduta=1,
            prezzo_netto=50.00
        )

    @classmethod
    def create_espositore_child(
        cls,
        ordine_id: int,
        count: int = 3
    ) -> list:
        """Crea righe child espositore."""
        return [
            cls(
                ordine_id=ordine_id,
                descrizione=f"PRODOTTO CHILD {i}",
                q_venduta=8
            )
            for i in range(count)
        ]
