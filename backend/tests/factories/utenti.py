# =============================================================================
# SERV.O v8.1 - UTENTI FACTORIES
# =============================================================================
# Factory per generazione utenti di test
# =============================================================================

import factory
from datetime import datetime


class UtenteFactory(factory.Factory):
    """
    Factory per generazione utenti.
    """

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: n + 1000)
    username = factory.Sequence(lambda n: f"test_user_{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@test.local")
    ruolo = "OPERATORE"
    attivo = True
    created_at = factory.LazyFunction(datetime.now)

    @classmethod
    def create_admin(cls) -> dict:
        """Crea utente admin."""
        return cls(
            username="test_admin",
            email="admin@test.local",
            ruolo="ADMIN"
        )

    @classmethod
    def create_operatore(cls) -> dict:
        """Crea utente operatore."""
        return cls(
            username="test_operatore",
            email="operatore@test.local",
            ruolo="OPERATORE"
        )

    @classmethod
    def create_supervisore(cls) -> dict:
        """Crea utente supervisore."""
        return cls(
            username="test_supervisore",
            email="supervisore@test.local",
            ruolo="SUPERVISORE"
        )
