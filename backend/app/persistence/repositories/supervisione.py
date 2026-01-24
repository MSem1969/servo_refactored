# =============================================================================
# SERV.O v8.1 - SUPERVISIONE REPOSITORY
# =============================================================================
# Repository per gestione supervisioni
# =============================================================================

from typing import Optional, List, Dict, Any

from .base import BaseRepository


class SupervisioneEspositoreRepository(BaseRepository[Dict[str, Any]]):
    """Repository per supervisione_espositore."""

    def __init__(self):
        super().__init__('supervisione_espositore', 'id_supervisione')

    def get_pending(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Recupera supervisioni pending con dati ordine.

        Args:
            limit: Max record

        Returns:
            Lista supervisioni pending
        """
        return self._execute_query("""
            SELECT se.*,
                   ot.numero_ordine_vendor,
                   ot.ragione_sociale_1,
                   ot.data_ordine,
                   coe.count_approvazioni,
                   coe.is_ordinario
            FROM supervisione_espositore se
            JOIN ordini_testata ot ON se.id_testata = ot.id_testata
            LEFT JOIN criteri_ordinari_espositore coe ON se.pattern_signature = coe.pattern_signature
            WHERE se.stato = 'PENDING'
            ORDER BY se.timestamp_creazione DESC
            LIMIT %s
        """, (limit,))

    def count_pending(self) -> int:
        """Conta supervisioni pending."""
        return self.count("stato = 'PENDING'")

    def get_by_testata(self, id_testata: int) -> List[Dict[str, Any]]:
        """
        Recupera supervisioni per ordine.

        Args:
            id_testata: ID ordine

        Returns:
            Lista supervisioni
        """
        return self._execute_query("""
            SELECT se.*, coe.count_approvazioni, coe.is_ordinario
            FROM supervisione_espositore se
            LEFT JOIN criteri_ordinari_espositore coe ON se.pattern_signature = coe.pattern_signature
            WHERE se.id_testata = %s
            ORDER BY se.timestamp_creazione DESC
        """, (id_testata,))

    def approve(self, id_supervisione: int, operatore: str, note: str = None) -> bool:
        """
        Approva supervisione.

        Args:
            id_supervisione: ID supervisione
            operatore: Nome operatore
            note: Note opzionali

        Returns:
            True se approvata
        """
        db = self._get_db()
        result = db.execute("""
            UPDATE supervisione_espositore
            SET stato = 'APPROVED',
                operatore = %s,
                timestamp_decisione = CURRENT_TIMESTAMP,
                note = %s
            WHERE id_supervisione = %s AND stato = 'PENDING'
            RETURNING id_supervisione
        """, (operatore, note, id_supervisione)).fetchone()
        db.commit()
        return result is not None

    def reject(self, id_supervisione: int, operatore: str, note: str) -> bool:
        """
        Rifiuta supervisione.

        Args:
            id_supervisione: ID supervisione
            operatore: Nome operatore
            note: Motivazione rifiuto

        Returns:
            True se rifiutata
        """
        db = self._get_db()
        result = db.execute("""
            UPDATE supervisione_espositore
            SET stato = 'REJECTED',
                operatore = %s,
                timestamp_decisione = CURRENT_TIMESTAMP,
                note = %s
            WHERE id_supervisione = %s AND stato = 'PENDING'
            RETURNING id_supervisione
        """, (operatore, note, id_supervisione)).fetchone()
        db.commit()
        return result is not None

    def get_stats(self) -> Dict[str, int]:
        """
        Statistiche supervisioni.

        Returns:
            Dict con conteggi per stato
        """
        rows = self._execute_query("""
            SELECT stato, COUNT(*) as count
            FROM supervisione_espositore
            GROUP BY stato
        """)
        return {row['stato']: row['count'] for row in rows}


class SupervisioneListinoRepository(BaseRepository[Dict[str, Any]]):
    """Repository per supervisione_listino."""

    def __init__(self):
        super().__init__('supervisione_listino', 'id_supervisione')

    def get_pending(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Recupera supervisioni listino pending."""
        return self._execute_query("""
            SELECT sl.*,
                   ot.numero_ordine_vendor,
                   ot.ragione_sociale_1,
                   col.count_approvazioni,
                   col.is_ordinario
            FROM supervisione_listino sl
            JOIN ordini_testata ot ON sl.id_testata = ot.id_testata
            LEFT JOIN criteri_ordinari_listino col ON sl.pattern_signature = col.pattern_signature
            WHERE sl.stato = 'PENDING'
            ORDER BY sl.timestamp_creazione DESC
            LIMIT %s
        """, (limit,))

    def count_pending(self) -> int:
        """Conta supervisioni pending."""
        return self.count("stato = 'PENDING'")


class SupervisioneLookupRepository(BaseRepository[Dict[str, Any]]):
    """Repository per supervisione_lookup."""

    def __init__(self):
        super().__init__('supervisione_lookup', 'id_supervisione')

    def get_pending(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Recupera supervisioni lookup pending."""
        return self._execute_query("""
            SELECT slk.*,
                   ot.numero_ordine_vendor,
                   ot.ragione_sociale_1,
                   colk.count_approvazioni,
                   colk.is_ordinario
            FROM supervisione_lookup slk
            JOIN ordini_testata ot ON slk.id_testata = ot.id_testata
            LEFT JOIN criteri_ordinari_lookup colk ON slk.pattern_signature = colk.pattern_signature
            WHERE slk.stato = 'PENDING'
            ORDER BY slk.timestamp_creazione DESC
            LIMIT %s
        """, (limit,))

    def count_pending(self) -> int:
        """Conta supervisioni pending."""
        return self.count("stato = 'PENDING'")


# Singleton instances
supervisione_espositore_repository = SupervisioneEspositoreRepository()
supervisione_listino_repository = SupervisioneListinoRepository()
supervisione_lookup_repository = SupervisioneLookupRepository()
