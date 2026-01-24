# =============================================================================
# SERV.O v11.0 - CRITERI ORDINARI REPOSITORY
# =============================================================================
# Repository per gestione criteri ML (pattern ordinari)
# v11.0: TIER 3.3 - Base class unificata per ridurre duplicazione
# =============================================================================

from typing import Dict, Any, List, Optional
from .base import BaseRepository


class CriteriOrdinariBase(BaseRepository[Dict[str, Any]]):
    """
    Base class unificata per tutti i repository criteri ordinari.
    Fornisce metodi comuni: get_by_pattern, get_ordinari, increment_approvazioni,
    promuovi_a_ordinario, reset_pattern, get_stats.

    Subclasses devono solo definire:
    - table_name (nel costruttore)
    - metodi specifici per quel tipo di criterio
    """

    def get_by_pattern(self, pattern_signature: str) -> Optional[Dict[str, Any]]:
        """Recupera criterio per pattern signature."""
        return self._execute_one(
            f"SELECT * FROM {self.table_name} WHERE pattern_signature = %s",
            (pattern_signature,)
        )

    def get_ordinari(self) -> List[Dict[str, Any]]:
        """Lista criteri promossi a ordinari."""
        return self._execute_query(
            f"SELECT * FROM {self.table_name} WHERE is_ordinario = TRUE ORDER BY data_promozione DESC"
        )

    def get_in_apprendimento(self) -> List[Dict[str, Any]]:
        """Lista criteri in fase di apprendimento."""
        return self._execute_query(
            f"SELECT * FROM {self.table_name} WHERE is_ordinario = FALSE ORDER BY count_approvazioni DESC"
        )

    def increment_approvazioni(self, pattern_signature: str, operatore: str) -> bool:
        """Incrementa contatore approvazioni."""
        db = self._get_db()
        result = db.execute(f"""
            UPDATE {self.table_name}
            SET count_approvazioni = count_approvazioni + 1,
                operatori_approvatori = COALESCE(operatori_approvatori || ',', '') || %s
            WHERE pattern_signature = %s
            RETURNING pattern_signature
        """, (operatore, pattern_signature)).fetchone()
        db.commit()
        return result is not None

    def promuovi_a_ordinario(self, pattern_signature: str) -> bool:
        """Promuove pattern a ordinario."""
        db = self._get_db()
        result = db.execute(f"""
            UPDATE {self.table_name}
            SET is_ordinario = TRUE, data_promozione = NOW()
            WHERE pattern_signature = %s
            RETURNING pattern_signature
        """, (pattern_signature,)).fetchone()
        db.commit()
        return result is not None

    def reset_pattern(self, pattern_signature: str) -> bool:
        """Reset pattern (non più ordinario)."""
        db = self._get_db()
        result = db.execute(f"""
            UPDATE {self.table_name}
            SET is_ordinario = FALSE, count_approvazioni = 0
            WHERE pattern_signature = %s
            RETURNING pattern_signature
        """, (pattern_signature,)).fetchone()
        db.commit()
        return result is not None

    def get_stats(self) -> Dict[str, Any]:
        """Statistiche criteri."""
        return {
            'totale': self._execute_scalar(f"SELECT COUNT(*) FROM {self.table_name}"),
            'ordinari': self._execute_scalar(f"SELECT COUNT(*) FROM {self.table_name} WHERE is_ordinario = TRUE"),
            'in_apprendimento': self._execute_scalar(f"SELECT COUNT(*) FROM {self.table_name} WHERE is_ordinario = FALSE"),
        }


class CriteriEspositoreRepository(CriteriOrdinariBase):
    """Repository per criteri_ordinari_espositore."""

    def __init__(self):
        super().__init__('criteri_ordinari_espositore', 'pattern_signature')

    def get_by_vendor(self, vendor: str) -> List[Dict[str, Any]]:
        """Lista criteri per vendor."""
        return self._execute_query(
            "SELECT * FROM criteri_ordinari_espositore WHERE vendor = %s ORDER BY count_approvazioni DESC",
            (vendor,)
        )


class CriteriListinoRepository(CriteriOrdinariBase):
    """Repository per criteri_ordinari_listino."""

    def __init__(self):
        super().__init__('criteri_ordinari_listino', 'pattern_signature')

    def get_by_aic(self, codice_aic: str) -> List[Dict[str, Any]]:
        """Lista criteri per codice AIC."""
        return self._execute_query(
            "SELECT * FROM criteri_ordinari_listino WHERE codice_aic = %s",
            (codice_aic,)
        )


class CriteriLookupRepository(CriteriOrdinariBase):
    """Repository per criteri_ordinari_lookup."""

    def __init__(self):
        super().__init__('criteri_ordinari_lookup', 'pattern_signature')

    def get_by_piva(self, partita_iva: str) -> List[Dict[str, Any]]:
        """Lista criteri per partita IVA pattern."""
        return self._execute_query(
            "SELECT * FROM criteri_ordinari_lookup WHERE partita_iva_pattern = %s",
            (partita_iva,)
        )

    def set_default_farmacia(self, pattern_signature: str, min_id: str, id_farmacia: int) -> bool:
        """Imposta farmacia default per pattern."""
        db = self._get_db()
        result = db.execute("""
            UPDATE criteri_ordinari_lookup
            SET min_id_default = %s, id_farmacia_default = %s
            WHERE pattern_signature = %s
            RETURNING pattern_signature
        """, (min_id, id_farmacia, pattern_signature)).fetchone()
        db.commit()
        return result is not None


class CriteriAicRepository(CriteriOrdinariBase):
    """Repository per criteri_ordinari_aic."""

    def __init__(self):
        super().__init__('criteri_ordinari_aic', 'pattern_signature')

    def get_by_vendor_descrizione(self, vendor: str, descrizione_normalizzata: str) -> Optional[Dict[str, Any]]:
        """Cerca criterio per vendor e descrizione normalizzata."""
        return self._execute_one(
            "SELECT * FROM criteri_ordinari_aic WHERE vendor = %s AND descrizione_normalizzata = %s",
            (vendor, descrizione_normalizzata)
        )

    def set_default_aic(self, pattern_signature: str, codice_aic: str) -> bool:
        """Imposta AIC default per pattern."""
        db = self._get_db()
        result = db.execute("""
            UPDATE criteri_ordinari_aic
            SET codice_aic_default = %s
            WHERE pattern_signature = %s
            RETURNING pattern_signature
        """, (codice_aic, pattern_signature)).fetchone()
        db.commit()
        return result is not None


# =============================================================================
# FACTORY FOR UNIFIED ACCESS (v11.0 TIER 3.3)
# =============================================================================

class CriteriOrdinariFactory:
    """
    Factory per accesso unificato ai repository criteri ordinari.
    Permette di ottenere il repository corretto in base al tipo.
    """

    _repos = {
        'espositore': None,
        'listino': None,
        'lookup': None,
        'aic': None,
    }

    @classmethod
    def get(cls, tipo: str) -> CriteriOrdinariBase:
        """
        Ottiene repository per tipo.

        Args:
            tipo: 'espositore', 'listino', 'lookup', 'aic'

        Returns:
            Repository specifico
        """
        if tipo not in cls._repos:
            raise ValueError(f"Tipo criterio non valido: {tipo}. Usa: {list(cls._repos.keys())}")

        if cls._repos[tipo] is None:
            if tipo == 'espositore':
                cls._repos[tipo] = CriteriEspositoreRepository()
            elif tipo == 'listino':
                cls._repos[tipo] = CriteriListinoRepository()
            elif tipo == 'lookup':
                cls._repos[tipo] = CriteriLookupRepository()
            elif tipo == 'aic':
                cls._repos[tipo] = CriteriAicRepository()

        return cls._repos[tipo]

    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """Statistiche aggregate per tutti i tipi di criteri."""
        return {
            tipo: cls.get(tipo).get_stats()
            for tipo in cls._repos.keys()
        }


# =============================================================================
# REPOSITORY INSTANCES (Singleton-like) - Backward compatibility
# =============================================================================

def get_criteri_espositore_repo() -> CriteriEspositoreRepository:
    """Get or create CriteriEspositoreRepository instance."""
    return CriteriOrdinariFactory.get('espositore')


def get_criteri_listino_repo() -> CriteriListinoRepository:
    """Get or create CriteriListinoRepository instance."""
    return CriteriOrdinariFactory.get('listino')


def get_criteri_lookup_repo() -> CriteriLookupRepository:
    """Get or create CriteriLookupRepository instance."""
    return CriteriOrdinariFactory.get('lookup')


def get_criteri_aic_repo() -> CriteriAicRepository:
    """Get or create CriteriAicRepository instance."""
    return CriteriOrdinariFactory.get('aic')
