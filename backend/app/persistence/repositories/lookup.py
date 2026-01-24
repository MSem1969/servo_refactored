# =============================================================================
# SERV.O v11.0 - LOOKUP REPOSITORY
# =============================================================================
# Repository per anagrafica farmacie e parafarmacie
# v11.0: TIER 3.3 - Criteri importati da criteri.py (unified)
# =============================================================================

from typing import Optional, List, Dict, Any

from .base import BaseRepository
# v11.0: Import criteri from dedicated module
from .criteri import (
    CriteriOrdinariBase,
    CriteriEspositoreRepository,
    CriteriListinoRepository,
    CriteriLookupRepository,
    CriteriOrdinariFactory,
    get_criteri_espositore_repo,
    get_criteri_listino_repo,
    get_criteri_lookup_repo,
)


class FarmacieRepository(BaseRepository[Dict[str, Any]]):
    """Repository per anagrafica_farmacie."""

    def __init__(self):
        super().__init__('anagrafica_farmacie', 'id_farmacia')

    def search_by_piva(self, partita_iva: str) -> List[Dict[str, Any]]:
        """
        Cerca farmacie per partita IVA.

        Args:
            partita_iva: P.IVA da cercare

        Returns:
            Lista farmacie trovate
        """
        return self._execute_query("""
            SELECT id_farmacia, min_id, partita_iva, ragione_sociale,
                   indirizzo, cap, citta, provincia
            FROM anagrafica_farmacie
            WHERE partita_iva = %s
            ORDER BY ragione_sociale
        """, (partita_iva,))

    def search_by_min_id(self, min_id: str) -> Optional[Dict[str, Any]]:
        """
        Cerca farmacia per MIN_ID.

        Args:
            min_id: Codice ministeriale

        Returns:
            Farmacia o None
        """
        return self._execute_one("""
            SELECT id_farmacia, min_id, partita_iva, ragione_sociale,
                   indirizzo, cap, citta, provincia
            FROM anagrafica_farmacie
            WHERE min_id = %s
        """, (min_id,))

    def search_full_text(
        self,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Ricerca full-text su farmacie.

        Args:
            query: Testo da cercare
            limit: Max risultati

        Returns:
            Lista farmacie
        """
        search_pattern = f"%{query}%"
        return self._execute_query("""
            SELECT id_farmacia, min_id, partita_iva, ragione_sociale,
                   indirizzo, cap, citta, provincia
            FROM anagrafica_farmacie
            WHERE ragione_sociale ILIKE %s
               OR partita_iva LIKE %s
               OR min_id LIKE %s
               OR citta ILIKE %s
            ORDER BY ragione_sociale
            LIMIT %s
        """, (search_pattern, search_pattern, search_pattern, search_pattern, limit))

    def get_with_full_address(self, id_farmacia: int) -> Optional[Dict[str, Any]]:
        """
        Recupera farmacia con indirizzo completo.

        Args:
            id_farmacia: ID farmacia

        Returns:
            Farmacia con tutti i campi
        """
        return self._execute_one("""
            SELECT *
            FROM anagrafica_farmacie
            WHERE id_farmacia = %s
        """, (id_farmacia,))


class ParafarmacieRepository(BaseRepository[Dict[str, Any]]):
    """Repository per anagrafica_parafarmacie."""

    def __init__(self):
        super().__init__('anagrafica_parafarmacie', 'id_parafarmacia')

    def search_by_piva(self, partita_iva: str) -> List[Dict[str, Any]]:
        """
        Cerca parafarmacie per partita IVA.

        Args:
            partita_iva: P.IVA da cercare

        Returns:
            Lista parafarmacie trovate
        """
        return self._execute_query("""
            SELECT id_parafarmacia, codice_sito, partita_iva, sito_logistico,
                   indirizzo, cap, citta, provincia
            FROM anagrafica_parafarmacie
            WHERE partita_iva = %s
            ORDER BY sito_logistico
        """, (partita_iva,))

    def search_by_codice_sito(self, codice_sito: str) -> Optional[Dict[str, Any]]:
        """
        Cerca parafarmacia per codice sito.

        Args:
            codice_sito: Codice sito

        Returns:
            Parafarmacia o None
        """
        return self._execute_one("""
            SELECT id_parafarmacia, codice_sito, partita_iva, sito_logistico,
                   indirizzo, cap, citta, provincia
            FROM anagrafica_parafarmacie
            WHERE codice_sito = %s
        """, (codice_sito,))

    def search_full_text(
        self,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Ricerca full-text su parafarmacie.

        Args:
            query: Testo da cercare
            limit: Max risultati

        Returns:
            Lista parafarmacie
        """
        search_pattern = f"%{query}%"
        return self._execute_query("""
            SELECT id_parafarmacia, codice_sito, partita_iva, sito_logistico,
                   indirizzo, cap, citta, provincia
            FROM anagrafica_parafarmacie
            WHERE sito_logistico ILIKE %s
               OR partita_iva LIKE %s
               OR codice_sito LIKE %s
               OR citta ILIKE %s
            ORDER BY sito_logistico
            LIMIT %s
        """, (search_pattern, search_pattern, search_pattern, search_pattern, limit))

    def get_with_full_address(self, id_parafarmacia: int) -> Optional[Dict[str, Any]]:
        """
        Recupera parafarmacia con indirizzo completo.

        Args:
            id_parafarmacia: ID parafarmacia

        Returns:
            Parafarmacia con tutti i campi
        """
        return self._execute_one("""
            SELECT *
            FROM anagrafica_parafarmacie
            WHERE id_parafarmacia = %s
        """, (id_parafarmacia,))


# v11.0: CriteriOrdinariRepository moved to criteri.py
# Use CriteriOrdinariBase, CriteriEspositoreRepository, etc. from criteri.py

# Singleton instances
farmacie_repository = FarmacieRepository()
parafarmacie_repository = ParafarmacieRepository()

# v11.0: Use factory-managed instances from criteri.py
criteri_espositore_repository = get_criteri_espositore_repo()
criteri_listino_repository = get_criteri_listino_repo()
criteri_lookup_repository = get_criteri_lookup_repo()

# Re-export for backward compatibility
CriteriOrdinariRepository = CriteriOrdinariBase  # Alias
