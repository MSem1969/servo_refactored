# SERV.O Recovery Scripts

Script per backup e disaster recovery del database SERV.O.

## Quick Start

```bash
# Backup completo
./backup_full.sh

# Backup solo schema (DDL)
./backup_schema.sh

# Backup dati configurazione
./backup_seed.sh

# Restore database
./restore_db.sh --input ../../../backups/full/servo_full_latest.sql

# Verifica integrità
./verify_db.sh
```

## Script Disponibili

| Script | Descrizione |
|--------|-------------|
| `backup_schema.sh` | Dump struttura DB (tabelle, indici, viste) |
| `backup_seed.sh` | Dump dati configurazione (vendor, config, etc.) |
| `backup_full.sh` | Dump completo (schema + tutti i dati) |
| `restore_db.sh` | Ripristino database da backup |
| `verify_db.sh` | Verifica integrità post-restore |

## Uso con Docker (Produzione)

```bash
# Backup da container Coolify
CONTAINER=$(docker ps -q -f name=postgres)
./backup_full.sh --docker $CONTAINER

# Restore in container
./restore_db.sh --docker $CONTAINER --input backup.sql
```

## Directory Backup

I backup vengono salvati in:
```
backend/backups/
├── schema/    # Schema DDL
├── seed/      # Dati configurazione
└── full/      # Backup completi
```

## Documentazione Completa

Vedi [RECOVERY.md](../../../RECOVERY.md) nella root del progetto per:
- Procedure dettagliate
- Scenari di recovery
- Configurazione backup periodici
- Troubleshooting
