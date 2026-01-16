# =============================================================================
# SERV.O v8.1 - BASE REPOSITORY
# =============================================================================
# Classe base per il Repository Pattern
# =============================================================================

from typing import Generic, TypeVar, Optional, List, Dict, Any
from abc import ABC, abstractmethod

from ...database_pg import get_db


T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """
    Repository base con operazioni CRUD comuni.

    Attributes:
        table_name: Nome della tabella principale
        primary_key: Nome della chiave primaria (default: 'id')
    """

    def __init__(self, table_name: str, primary_key: str = 'id'):
        self.table_name = table_name
        self.primary_key = primary_key

    def _get_db(self):
        """Ottiene connessione database."""
        return get_db()

    def get_by_id(self, id_value: int) -> Optional[Dict[str, Any]]:
        """
        Recupera record per ID.

        Args:
            id_value: Valore chiave primaria

        Returns:
            Dict con dati record o None
        """
        db = self._get_db()
        row = db.execute(
            f"SELECT * FROM {self.table_name} WHERE {self.primary_key} = %s",
            (id_value,)
        ).fetchone()
        return dict(row) if row else None

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Lista tutti i record con paginazione.

        Args:
            limit: Massimo numero record
            offset: Offset per paginazione

        Returns:
            Lista di dict
        """
        db = self._get_db()
        rows = db.execute(
            f"SELECT * FROM {self.table_name} LIMIT %s OFFSET %s",
            (limit, offset)
        ).fetchall()
        return [dict(row) for row in rows]

    def count(self, where: str = None, params: tuple = None) -> int:
        """
        Conta record con condizione opzionale.

        Args:
            where: Clausola WHERE (senza 'WHERE')
            params: Parametri per la query

        Returns:
            Conteggio record
        """
        db = self._get_db()
        query = f"SELECT COUNT(*) FROM {self.table_name}"
        if where:
            query += f" WHERE {where}"
        result = db.execute(query, params or ()).fetchone()
        return result[0] if result else 0

    def exists(self, id_value: int) -> bool:
        """Verifica se record esiste."""
        return self.get_by_id(id_value) is not None

    def delete_by_id(self, id_value: int) -> bool:
        """
        Elimina record per ID.

        Args:
            id_value: Valore chiave primaria

        Returns:
            True se eliminato
        """
        db = self._get_db()
        result = db.execute(
            f"DELETE FROM {self.table_name} WHERE {self.primary_key} = %s RETURNING {self.primary_key}",
            (id_value,)
        ).fetchone()
        db.commit()
        return result is not None

    def _execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Esegue query e ritorna lista di dict."""
        db = self._get_db()
        rows = db.execute(query, params or ()).fetchall()
        return [dict(row) for row in rows]

    def _execute_one(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """Esegue query e ritorna singolo dict."""
        db = self._get_db()
        row = db.execute(query, params or ()).fetchone()
        return dict(row) if row else None

    def _execute_scalar(self, query: str, params: tuple = None) -> Any:
        """Esegue query e ritorna valore scalare."""
        db = self._get_db()
        result = db.execute(query, params or ()).fetchone()
        return result[0] if result else None
