# =============================================================================
# SERV.O v8.1 - ORDINI REPOSITORY
# =============================================================================
# Repository per gestione ordini
# =============================================================================

from typing import Optional, List, Dict, Any
from datetime import date

from .base import BaseRepository


class OrdiniRepository(BaseRepository[Dict[str, Any]]):
    """Repository per ordini_testata."""

    def __init__(self):
        super().__init__('ordini_testata', 'id_testata')

    def get_ordine_completo(self, id_testata: int) -> Optional[Dict[str, Any]]:
        """
        Recupera ordine con dati vendor e acquisizione.

        Args:
            id_testata: ID ordine

        Returns:
            Dict con ordine completo o None
        """
        return self._execute_one("""
            SELECT ot.*,
                   v.codice_vendor,
                   v.nome_vendor,
                   a.nome_file_originale,
                   a.data_acquisizione
            FROM ordini_testata ot
            LEFT JOIN vendor v ON ot.id_vendor = v.id_vendor
            LEFT JOIN acquisizioni a ON ot.id_acquisizione = a.id_acquisizione
            WHERE ot.id_testata = %s
        """, (id_testata,))

    def list_ordini(
        self,
        stato: str = None,
        vendor: str = None,
        data_da: date = None,
        data_a: date = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Lista ordini con filtri.

        Args:
            stato: Filtra per stato
            vendor: Filtra per vendor (codice)
            data_da: Data ordine da
            data_a: Data ordine a
            limit: Max record
            offset: Offset paginazione

        Returns:
            Lista ordini
        """
        conditions = []
        params = []

        if stato:
            conditions.append("ot.stato = %s")
            params.append(stato)

        if vendor:
            conditions.append("v.codice_vendor = %s")
            params.append(vendor)

        if data_da:
            conditions.append("ot.data_ordine >= %s")
            params.append(data_da)

        if data_a:
            conditions.append("ot.data_ordine <= %s")
            params.append(data_a)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        params.extend([limit, offset])

        return self._execute_query(f"""
            SELECT ot.*,
                   v.codice_vendor,
                   v.nome_vendor
            FROM ordini_testata ot
            LEFT JOIN vendor v ON ot.id_vendor = v.id_vendor
            WHERE {where_clause}
            ORDER BY ot.data_estrazione DESC
            LIMIT %s OFFSET %s
        """, tuple(params))

    def update_stato(self, id_testata: int, nuovo_stato: str) -> bool:
        """
        Aggiorna stato ordine.

        Args:
            id_testata: ID ordine
            nuovo_stato: Nuovo stato

        Returns:
            True se aggiornato
        """
        db = self._get_db()
        result = db.execute("""
            UPDATE ordini_testata
            SET stato = %s
            WHERE id_testata = %s
            RETURNING id_testata
        """, (nuovo_stato, id_testata)).fetchone()
        db.commit()
        return result is not None

    def count_by_stato(self) -> Dict[str, int]:
        """
        Conteggio ordini per stato.

        Returns:
            Dict {stato: count}
        """
        rows = self._execute_query("""
            SELECT stato, COUNT(*) as count
            FROM ordini_testata
            GROUP BY stato
        """)
        return {row['stato']: row['count'] for row in rows}

    def get_righe_ordine(self, id_testata: int) -> List[Dict[str, Any]]:
        """
        Recupera righe dettaglio per un ordine.

        Args:
            id_testata: ID ordine

        Returns:
            Lista righe
        """
        return self._execute_query("""
            SELECT *
            FROM ordini_dettaglio
            WHERE id_testata = %s
            ORDER BY n_riga
        """, (id_testata,))

    def get_by_numero_vendor(self, numero_ordine: str, vendor: str) -> Optional[Dict[str, Any]]:
        """
        Cerca ordine per numero vendor e codice vendor.

        Args:
            numero_ordine: Numero ordine vendor
            vendor: Codice vendor

        Returns:
            Ordine o None
        """
        return self._execute_one("""
            SELECT ot.*
            FROM ordini_testata ot
            JOIN vendor v ON ot.id_vendor = v.id_vendor
            WHERE ot.numero_ordine_vendor = %s
              AND v.codice_vendor = %s
        """, (numero_ordine, vendor))


# Singleton instance
ordini_repository = OrdiniRepository()
