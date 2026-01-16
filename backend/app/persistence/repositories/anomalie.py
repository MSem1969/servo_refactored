# =============================================================================
# SERV.O v8.1 - ANOMALIE REPOSITORY
# =============================================================================
# Repository per gestione anomalie
# =============================================================================

from typing import Optional, List, Dict, Any

from .base import BaseRepository


class AnomalieRepository(BaseRepository[Dict[str, Any]]):
    """Repository per anomalie."""

    def __init__(self):
        super().__init__('anomalie', 'id_anomalia')

    def list_with_filters(
        self,
        tipo: str = None,
        livello: str = None,
        stato: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Lista anomalie con filtri.

        Args:
            tipo: Tipo anomalia
            livello: INFO, ATTENZIONE, ERRORE, CRITICO
            stato: APERTA, IN_GESTIONE, RISOLTA, IGNORATA
            limit: Max record
            offset: Offset paginazione

        Returns:
            Dict con anomalie, totale, limit, offset
        """
        conditions = []
        params = []

        if tipo:
            conditions.append("tipo_anomalia = %s")
            params.append(tipo)

        if livello:
            conditions.append("livello = %s")
            params.append(livello)

        if stato:
            conditions.append("an.stato = %s")
            params.append(stato)
        else:
            conditions.append("an.stato IN ('APERTA', 'IN_GESTIONE')")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Count
        totale = self._execute_scalar(f"""
            SELECT COUNT(*) FROM anomalie an
            LEFT JOIN ordini_testata ot ON an.id_testata = ot.id_testata
            WHERE {where_clause}
        """, tuple(params))

        # Query con join
        params.extend([limit, offset])
        rows = self._execute_query(f"""
            SELECT
                an.*,
                v.codice_vendor as vendor,
                ot.numero_ordine_vendor as numero_ordine,
                a.nome_file_originale as pdf_file
            FROM anomalie an
            LEFT JOIN ordini_testata ot ON an.id_testata = ot.id_testata
            LEFT JOIN vendor v ON ot.id_vendor = v.id_vendor
            LEFT JOIN acquisizioni a ON COALESCE(an.id_acquisizione, ot.id_acquisizione) = a.id_acquisizione
            WHERE {where_clause}
            ORDER BY
                CASE an.livello
                    WHEN 'CRITICO' THEN 1
                    WHEN 'ERRORE' THEN 2
                    WHEN 'ATTENZIONE' THEN 3
                    ELSE 4
                END,
                an.data_rilevazione DESC
            LIMIT %s OFFSET %s
        """, tuple(params))

        return {
            'anomalie': rows,
            'totale': totale or 0,
            'limit': limit,
            'offset': offset
        }

    def get_by_ordine(self, id_testata: int) -> List[Dict[str, Any]]:
        """
        Recupera anomalie di un ordine.

        Args:
            id_testata: ID ordine

        Returns:
            Lista anomalie
        """
        return self._execute_query("""
            SELECT * FROM anomalie
            WHERE id_testata = %s
            ORDER BY data_rilevazione DESC
        """, (id_testata,))

    def get_critiche(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Recupera anomalie critiche/errore aperte.

        Args:
            limit: Max record

        Returns:
            Lista anomalie critiche
        """
        return self._execute_query("""
            SELECT
                an.*,
                v.codice_vendor as vendor,
                ot.numero_ordine_vendor as numero_ordine
            FROM anomalie an
            LEFT JOIN ordini_testata ot ON an.id_testata = ot.id_testata
            LEFT JOIN vendor v ON ot.id_vendor = v.id_vendor
            WHERE an.stato IN ('APERTA', 'IN_GESTIONE')
            AND an.livello IN ('CRITICO', 'ERRORE')
            ORDER BY
                CASE an.livello WHEN 'CRITICO' THEN 1 ELSE 2 END,
                an.data_rilevazione DESC
            LIMIT %s
        """, (limit,))

    def update_stato(self, id_anomalia: int, nuovo_stato: str, note: str = None) -> bool:
        """
        Aggiorna stato anomalia.

        Args:
            id_anomalia: ID anomalia
            nuovo_stato: APERTA, IN_GESTIONE, RISOLTA, IGNORATA
            note: Note opzionali

        Returns:
            True se aggiornata
        """
        stati_validi = ['APERTA', 'IN_GESTIONE', 'RISOLTA', 'IGNORATA']
        if nuovo_stato not in stati_validi:
            return False

        db = self._get_db()

        if nuovo_stato in ('RISOLTA', 'IGNORATA'):
            db.execute("""
                UPDATE anomalie
                SET stato = %s,
                    data_risoluzione = CURRENT_TIMESTAMP,
                    note_risoluzione = %s
                WHERE id_anomalia = %s
            """, (nuovo_stato, note, id_anomalia))
        else:
            db.execute(
                "UPDATE anomalie SET stato = %s WHERE id_anomalia = %s",
                (nuovo_stato, id_anomalia)
            )

        db.commit()
        return True

    def create(
        self,
        id_testata: int = None,
        id_dettaglio: int = None,
        id_acquisizione: int = None,
        tipo: str = 'ALTRO',
        livello: str = 'ATTENZIONE',
        descrizione: str = '',
        valore_anomalo: str = None
    ) -> int:
        """
        Crea nuova anomalia.

        Args:
            id_testata: ID ordine
            id_dettaglio: ID riga dettaglio
            id_acquisizione: ID acquisizione
            tipo: Tipo anomalia
            livello: Livello anomalia
            descrizione: Descrizione
            valore_anomalo: Valore anomalo

        Returns:
            ID nuova anomalia
        """
        db = self._get_db()

        cursor = db.execute("""
            INSERT INTO anomalie
            (id_testata, id_dettaglio, id_acquisizione, tipo_anomalia,
             livello, descrizione, valore_anomalo, stato)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'APERTA')
            RETURNING id_anomalia
        """, (id_testata, id_dettaglio, id_acquisizione, tipo,
              livello, descrizione, valore_anomalo))

        result = cursor.fetchone()
        db.commit()
        return result[0] if result else None

    def count_by_stato(self) -> Dict[str, int]:
        """
        Conteggio anomalie per stato.

        Returns:
            Dict {stato: count}
        """
        rows = self._execute_query("""
            SELECT stato, COUNT(*) as count
            FROM anomalie
            GROUP BY stato
        """)
        return {row['stato']: row['count'] for row in rows}

    def count_by_livello(self) -> Dict[str, int]:
        """
        Conteggio anomalie per livello.

        Returns:
            Dict {livello: count}
        """
        rows = self._execute_query("""
            SELECT livello, COUNT(*) as count
            FROM anomalie
            WHERE stato IN ('APERTA', 'IN_GESTIONE')
            GROUP BY livello
        """)
        return {row['livello']: row['count'] for row in rows}


# Singleton instance
anomalie_repository = AnomalieRepository()
