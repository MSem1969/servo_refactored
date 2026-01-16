# =============================================================================
# SERV.O v9.0 - BACKUP MANAGER
# =============================================================================
# Manager centralizzato per moduli backup.
# Gestisce configurazione, esecuzione e monitoring.
# =============================================================================

import json
from typing import Dict, Any, List, Optional, Type
from datetime import datetime

from .modules.base import BackupModule, BackupResult, ModuleStatus
from .modules.wal_archive import WALArchiveModule
from .modules.full_backup import FullBackupModule


# =============================================================================
# BACKUP MANAGER
# =============================================================================

class BackupManager:
    """
    Manager centralizzato per sistema backup.

    Responsabilità:
    - Registrazione moduli disponibili
    - Caricamento configurazioni da database
    - Esecuzione backup
    - Monitoring stato
    - Gestione retention/cleanup
    """

    # Registry moduli disponibili (class references)
    AVAILABLE_MODULES: Dict[str, Type[BackupModule]] = {
        'wal_archive': WALArchiveModule,
        'full_backup': FullBackupModule,
        # Moduli futuri:
        # 'incremental': IncrementalBackupModule,
        # 'offsite_sync': OffsiteSyncModule,
        # 'cloud_backup': CloudBackupModule,
        # 'replica': ReplicaModule,
    }

    def __init__(self):
        """Inizializza manager."""
        self._modules: Dict[str, BackupModule] = {}
        self._db = None

    # =========================================================================
    # DATABASE HELPERS
    # =========================================================================

    def _get_db(self):
        """Lazy import database connection."""
        if self._db is None:
            from ...database_pg import get_db
            self._db = get_db()
        return self._db

    def _log_operation(
        self,
        operation: str,
        module_name: str = None,
        backup_id: int = None,
        status: str = 'info',
        message: str = None,
        details: Dict = None,
        operator_id: int = None
    ):
        """Registra operazione nel log."""
        db = self._get_db()
        db.execute("""
            INSERT INTO backup_operations_log
            (operation, id_module, id_backup, status, message, details, operator_id)
            VALUES (
                %s,
                (SELECT id_module FROM backup_modules WHERE nome = %s),
                %s, %s, %s, %s, %s
            )
        """, (
            operation,
            module_name,
            backup_id,
            status,
            message,
            json.dumps(details) if details else None,
            operator_id
        ))
        db.commit()

    # =========================================================================
    # MODULI - LISTA E INFO
    # =========================================================================

    def get_available_modules(self) -> List[Dict[str, Any]]:
        """
        Lista moduli disponibili con stato da database.

        Returns:
            Lista di dict con info moduli + stato configurazione
        """
        db = self._get_db()

        # Carica configurazioni da DB
        cursor = db.execute("""
            SELECT
                m.id_module,
                m.nome,
                m.tier,
                m.titolo,
                m.descrizione,
                m.enabled,
                m.configured,
                m.config,
                m.schedule_cron,
                m.retention_days,
                m.last_run,
                m.last_status,
                m.last_error,
                s.nome AS storage_nome,
                s.tipo AS storage_tipo
            FROM backup_modules m
            LEFT JOIN backup_storage s ON m.id_storage = s.id_storage
            ORDER BY m.tier
        """)
        rows = cursor.fetchall()

        modules = []
        for row in rows:
            # Istanzia modulo per ottenere metadati aggiuntivi
            module_class = self.AVAILABLE_MODULES.get(row['nome'])

            module_info = {
                'id_module': row['id_module'],
                'name': row['nome'],
                'tier': row['tier'],
                'title': row['titolo'],
                'description': row['descrizione'],
                'enabled': row['enabled'],
                'configured': row['configured'],
                'config': row['config'] or {},
                'schedule_cron': row['schedule_cron'],
                'retention_days': row['retention_days'],
                'last_run': row['last_run'].isoformat() if row['last_run'] else None,
                'last_status': row['last_status'],
                'last_error': row['last_error'],
                'storage_name': row['storage_nome'],
                'storage_type': row['storage_tipo'],
                'available': module_class is not None,
            }

            # Aggiungi metadati dal modulo se disponibile
            if module_class:
                module_info['requires_packages'] = module_class.requires_packages
                module_info['requires_sudo'] = module_class.requires_sudo

            # Determina status
            if row['enabled']:
                module_info['status'] = 'enabled'
            elif row['configured']:
                module_info['status'] = 'configured'
            else:
                module_info['status'] = 'not_configured'

            modules.append(module_info)

        return modules

    def get_module(self, module_name: str) -> Optional[BackupModule]:
        """
        Ottiene istanza modulo configurata.

        Args:
            module_name: Nome modulo

        Returns:
            Istanza BackupModule o None
        """
        if module_name not in self.AVAILABLE_MODULES:
            return None

        # Carica config da DB
        db = self._get_db()
        cursor = db.execute("""
            SELECT config, enabled, configured
            FROM backup_modules
            WHERE nome = %s
        """, (module_name,))
        row = cursor.fetchone()

        config = row['config'] if row else {}
        module = self.AVAILABLE_MODULES[module_name](config)

        if row:
            module.set_enabled(row['enabled'])
            module.set_configured(row['configured'])

        return module

    # =========================================================================
    # CONFIGURAZIONE MODULI
    # =========================================================================

    def configure_module(
        self,
        module_name: str,
        config: Dict[str, Any],
        operator_id: int = None
    ) -> Dict[str, Any]:
        """
        Configura un modulo backup.

        Args:
            module_name: Nome modulo
            config: Configurazione da applicare
            operator_id: ID operatore

        Returns:
            Dict con esito e dettagli
        """
        if module_name not in self.AVAILABLE_MODULES:
            return {
                'success': False,
                'message': f"Modulo '{module_name}' non disponibile",
                'available_modules': list(self.AVAILABLE_MODULES.keys())
            }

        # Istanzia e configura modulo
        module = self.AVAILABLE_MODULES[module_name](config)

        # Valida configurazione
        validation = module.validate_config(config)
        if not validation.valid:
            return {
                'success': False,
                'message': 'Configurazione non valida',
                'errors': validation.errors,
                'warnings': validation.warnings
            }

        # Esegui configurazione
        result = module.configure(config)

        if result.success:
            # Salva in database
            db = self._get_db()
            db.execute("""
                UPDATE backup_modules
                SET config = %s,
                    configured = TRUE,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = %s
                WHERE nome = %s
            """, (json.dumps(config), operator_id, module_name))
            db.commit()

            # Log operazione
            self._log_operation(
                'module_configure',
                module_name=module_name,
                status='success',
                message=f"Modulo {module_name} configurato",
                details=config,
                operator_id=operator_id
            )

        return {
            'success': result.success,
            'message': result.message,
            'details': result.details,
            'warnings': validation.warnings,
            'manual_steps': result.details.get('manual_steps', []),
            'requires_sudo': result.details.get('requires_sudo', False),
        }

    def enable_module(
        self,
        module_name: str,
        operator_id: int = None
    ) -> Dict[str, Any]:
        """
        Abilita modulo (dopo test).

        Args:
            module_name: Nome modulo
            operator_id: ID operatore

        Returns:
            Dict con esito
        """
        db = self._get_db()

        # Verifica che sia configurato
        cursor = db.execute("""
            SELECT configured FROM backup_modules WHERE nome = %s
        """, (module_name,))
        row = cursor.fetchone()

        if not row:
            return {'success': False, 'message': 'Modulo non trovato'}

        if not row['configured']:
            return {'success': False, 'message': 'Modulo non configurato'}

        # Abilita
        db.execute("""
            UPDATE backup_modules
            SET enabled = TRUE,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = %s
            WHERE nome = %s
        """, (operator_id, module_name))
        db.commit()

        self._log_operation(
            'module_enable',
            module_name=module_name,
            status='success',
            message=f"Modulo {module_name} abilitato",
            operator_id=operator_id
        )

        return {'success': True, 'message': f"Modulo {module_name} abilitato"}

    def disable_module(
        self,
        module_name: str,
        operator_id: int = None
    ) -> Dict[str, Any]:
        """
        Disabilita modulo.

        Args:
            module_name: Nome modulo
            operator_id: ID operatore

        Returns:
            Dict con esito
        """
        db = self._get_db()

        db.execute("""
            UPDATE backup_modules
            SET enabled = FALSE,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = %s
            WHERE nome = %s
        """, (operator_id, module_name))
        db.commit()

        self._log_operation(
            'module_disable',
            module_name=module_name,
            status='success',
            message=f"Modulo {module_name} disabilitato",
            operator_id=operator_id
        )

        return {'success': True, 'message': f"Modulo {module_name} disabilitato"}

    # =========================================================================
    # ESECUZIONE BACKUP
    # =========================================================================

    def test_module(self, module_name: str) -> Dict[str, Any]:
        """
        Testa modulo backup.

        Args:
            module_name: Nome modulo

        Returns:
            Dict con risultato test
        """
        module = self.get_module(module_name)
        if not module:
            return {'success': False, 'message': 'Modulo non trovato'}

        result = module.test()

        # Log
        self._log_operation(
            'test_run',
            module_name=module_name,
            status='success' if result.success else 'failed',
            message=result.message,
            details=result.details
        )

        return result.to_dict()

    def execute_backup(
        self,
        module_name: str,
        operator_id: int = None,
        triggered_by: str = 'manual'
    ) -> Dict[str, Any]:
        """
        Esegue backup per modulo.

        Args:
            module_name: Nome modulo
            operator_id: ID operatore (se manual)
            triggered_by: 'manual', 'scheduled', 'pre-migration'

        Returns:
            Dict con risultato backup
        """
        module = self.get_module(module_name)
        if not module:
            return {'success': False, 'message': 'Modulo non trovato'}

        db = self._get_db()

        # Mappa nome modulo a backup_type valido
        BACKUP_TYPE_MAP = {
            'wal_archive': 'wal',
            'full_backup': 'full',
            'incremental': 'incremental',
            'offsite_sync': 'sync',
            'cloud_backup': 'upload',
            'replica': 'sync',
        }
        backup_type = BACKUP_TYPE_MAP.get(module_name, 'full')

        # Crea record history
        cursor = db.execute("""
            INSERT INTO backup_history
            (id_module, backup_type, status, triggered_by, operator_id)
            VALUES (
                (SELECT id_module FROM backup_modules WHERE nome = %s),
                %s, 'running', %s, %s
            )
            RETURNING id_backup
        """, (module_name, backup_type, triggered_by, operator_id))
        backup_id = cursor.fetchone()['id_backup']
        db.commit()

        # Esegui backup
        result = module.execute()

        # Aggiorna history
        db.execute("""
            UPDATE backup_history
            SET status = %s,
                completed_at = CURRENT_TIMESTAMP,
                duration_seconds = %s,
                file_path = %s,
                file_name = %s,
                file_size_bytes = %s,
                file_checksum = %s,
                error_message = %s,
                metadata = %s
            WHERE id_backup = %s
        """, (
            'success' if result.success else 'failed',
            result.duration_seconds,
            result.file_path,
            result.file_path.split('/')[-1] if result.file_path else None,
            result.file_size_bytes,
            result.checksum,
            result.error,
            json.dumps(result.details),
            backup_id
        ))

        # Aggiorna modulo
        db.execute("""
            UPDATE backup_modules
            SET last_run = CURRENT_TIMESTAMP,
                last_status = %s,
                last_error = %s
            WHERE nome = %s
        """, (
            'success' if result.success else 'failed',
            result.error,
            module_name
        ))

        db.commit()

        # Log
        self._log_operation(
            'backup_complete' if result.success else 'backup_fail',
            module_name=module_name,
            backup_id=backup_id,
            status='success' if result.success else 'failed',
            message=result.message,
            operator_id=operator_id
        )

        response = result.to_dict()
        response['backup_id'] = backup_id
        return response

    # =========================================================================
    # CLEANUP
    # =========================================================================

    def cleanup_module(
        self,
        module_name: str,
        retention_days: int = None,
        operator_id: int = None
    ) -> Dict[str, Any]:
        """
        Esegue cleanup backup vecchi per modulo.

        Args:
            module_name: Nome modulo
            retention_days: Override retention
            operator_id: ID operatore

        Returns:
            Dict con risultato cleanup
        """
        module = self.get_module(module_name)
        if not module:
            return {'success': False, 'message': 'Modulo non trovato'}

        result = module.cleanup(retention_days)

        # Log
        self._log_operation(
            'cleanup',
            module_name=module_name,
            status='success' if result.success else 'failed',
            message=result.message,
            details=result.details,
            operator_id=operator_id
        )

        return result.to_dict()

    # =========================================================================
    # DASHBOARD E STATISTICHE
    # =========================================================================

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        Statistiche per dashboard backup.

        Returns:
            Dict con statistiche aggregate
        """
        db = self._get_db()

        # Moduli abilitati
        cursor = db.execute("""
            SELECT
                COUNT(*) FILTER (WHERE enabled) AS enabled_count,
                COUNT(*) FILTER (WHERE configured) AS configured_count,
                COUNT(*) AS total_count
            FROM backup_modules
        """)
        module_stats = cursor.fetchone()

        # Backup ultimi 7 giorni
        cursor = db.execute("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'success') AS success_count,
                COUNT(*) FILTER (WHERE status = 'failed') AS failed_count,
                COUNT(*) AS total_count,
                COALESCE(SUM(file_size_bytes), 0) AS total_bytes
            FROM backup_history
            WHERE started_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
        """)
        backup_stats = cursor.fetchone()

        # Ultimo backup per modulo
        cursor = db.execute("""
            SELECT
                m.nome,
                m.titolo,
                h.status,
                h.completed_at,
                h.file_size_bytes
            FROM backup_modules m
            LEFT JOIN LATERAL (
                SELECT status, completed_at, file_size_bytes
                FROM backup_history
                WHERE id_module = m.id_module
                ORDER BY started_at DESC
                LIMIT 1
            ) h ON true
            WHERE m.enabled = TRUE
            ORDER BY m.tier
        """)
        last_backups = [dict(row) for row in cursor.fetchall()]

        # Storage
        cursor = db.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE stato = 'active') AS active
            FROM backup_storage
        """)
        storage_stats = cursor.fetchone()

        return {
            'modules': {
                'enabled': module_stats['enabled_count'],
                'configured': module_stats['configured_count'],
                'total': module_stats['total_count'],
            },
            'backups_7d': {
                'success': backup_stats['success_count'],
                'failed': backup_stats['failed_count'],
                'total': backup_stats['total_count'],
                'total_size_mb': round(backup_stats['total_bytes'] / (1024*1024), 2) if backup_stats['total_bytes'] else 0,
            },
            'last_backups': last_backups,
            'storage': {
                'total': storage_stats['total'],
                'active': storage_stats['active'],
            },
        }

    def get_backup_history(
        self,
        module_name: str = None,
        status: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Storico backup con filtri.

        Args:
            module_name: Filtra per modulo
            status: Filtra per stato
            limit: Numero risultati
            offset: Offset paginazione

        Returns:
            Lista backup history
        """
        db = self._get_db()

        # Costruisci query
        where_clauses = []
        params = []

        if module_name:
            where_clauses.append("m.nome = %s")
            params.append(module_name)

        if status:
            where_clauses.append("h.status = %s")
            params.append(status)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        params.extend([limit, offset])

        cursor = db.execute(f"""
            SELECT
                h.id_backup,
                h.backup_type,
                h.file_name,
                h.file_size_bytes,
                h.started_at,
                h.completed_at,
                h.duration_seconds,
                h.status,
                h.error_message,
                h.triggered_by,
                m.nome AS module_name,
                m.titolo AS module_title,
                o.username AS operator
            FROM backup_history h
            JOIN backup_modules m ON h.id_module = m.id_module
            LEFT JOIN operatori o ON h.operator_id = o.id_operatore
            {where_sql}
            ORDER BY h.started_at DESC
            LIMIT %s OFFSET %s
        """, params)

        return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # STORAGE
    # =========================================================================

    def get_storage_locations(self) -> List[Dict[str, Any]]:
        """Lista storage locations configurati."""
        db = self._get_db()
        cursor = db.execute("""
            SELECT
                id_storage,
                nome,
                tipo,
                path,
                capacity_gb,
                used_gb,
                stato,
                ultimo_check,
                ultimo_errore
            FROM backup_storage
            ORDER BY tipo, nome
        """)
        return [dict(row) for row in cursor.fetchall()]

    def add_storage_location(
        self,
        name: str,
        storage_type: str,
        path: str,
        config: Dict[str, Any] = None,
        capacity_gb: int = None,
        operator_id: int = None
    ) -> Dict[str, Any]:
        """
        Aggiunge storage location.

        Args:
            name: Nome identificativo
            storage_type: 'local', 'nas', 's3', etc.
            path: Path o URL
            config: Configurazione aggiuntiva
            capacity_gb: Capacità in GB
            operator_id: ID operatore

        Returns:
            Dict con esito
        """
        db = self._get_db()

        try:
            cursor = db.execute("""
                INSERT INTO backup_storage
                (nome, tipo, path, config, capacity_gb, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id_storage
            """, (
                name,
                storage_type,
                path,
                json.dumps(config) if config else '{}',
                capacity_gb,
                operator_id
            ))
            storage_id = cursor.fetchone()['id_storage']
            db.commit()

            return {
                'success': True,
                'message': f"Storage '{name}' aggiunto",
                'id_storage': storage_id
            }

        except Exception as e:
            db.rollback()
            return {
                'success': False,
                'message': 'Errore aggiunta storage',
                'error': str(e)
            }


# =============================================================================
# SINGLETON
# =============================================================================

backup_manager = BackupManager()
