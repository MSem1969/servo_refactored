#!/usr/bin/env python3
# =============================================================================
# SERV.O v9.4 - IMPORT ANAGRAFICA CLIENTI
# =============================================================================
# Script per importare anagrafiche clienti da file CSV
# Formati accettati:
# - CSV con intestazione: AGCANA,AGRSO1,AGRSO2,AGINDI,AGCAP,AGLOCA,AGPROV,AGPIVA,AGMAIL,AGCATE,AGCFAR,AGCSTA,AGCPAG,AGTIDD,AGDRIF
# - estrazione ERP ANAG_TOT_V_*.csv: senza intestazione, separatore ';', stesso ordine
# =============================================================================

import csv
import sys
import os
from datetime import datetime

# Aggiungi path per import moduli app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database_pg import get_db
from app.services.anagrafica.legacy import _leggi_tracciato_clienti_erp


def import_clienti(csv_path: str, truncate: bool = False) -> dict:
    """
    Importa anagrafiche clienti da file CSV.

    Args:
        csv_path: Percorso file CSV
        truncate: Se True, svuota la tabella prima dell'import

    Returns:
        Dict con statistiche: {totale, inseriti, aggiornati, errori}
    """
    db = get_db()

    stats = {
        'totale': 0,
        'inseriti': 0,
        'aggiornati': 0,
        'errori': 0,
        'errori_dettaglio': []
    }

    if truncate:
        print("Svuotamento tabella anagrafica_clienti...")
        db.execute("TRUNCATE TABLE anagrafica_clienti RESTART IDENTITY")
        db.commit()

    # Mapping colonne CSV -> DB
    col_mapping = {
        'AGCANA': 'codice_cliente',
        'AGRSO1': 'ragione_sociale_1',
        'AGRSO2': 'ragione_sociale_2',
        'AGINDI': 'indirizzo',
        'AGCAP': 'cap',
        'AGLOCA': 'localita',
        'AGPROV': 'provincia',
        'AGPIVA': 'partita_iva',
        'AGMAIL': 'email',
        'AGCATE': 'farmacia_categoria',
        'AGCFAR': 'codice_farmacia',
        'AGCSTA': 'farma_status',
        'AGCPAG': 'codice_pagamento',
        'AGTIDD': 'min_id',
        'AGDRIF': 'deposito_riferimento',
    }

    print(f"Lettura file: {csv_path}")

    with open(csv_path, 'rb') as f:
        erp = _leggi_tracciato_clienti_erp(f.read())

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        if erp is not None:
            reader, prima_riga = erp[0].to_dict('records'), 1
        else:
            reader, prima_riga = csv.DictReader(f), 2  # Start 2 per header

        for row_num, row in enumerate(reader, start=prima_riga):
            stats['totale'] += 1

            try:
                # Estrai codice cliente (obbligatorio)
                codice = row.get('AGCANA', '').strip()
                if not codice:
                    stats['errori'] += 1
                    stats['errori_dettaglio'].append(f"Riga {row_num}: codice cliente vuoto")
                    continue

                # Prepara dati per insert/update
                data = {}
                for csv_col, db_col in col_mapping.items():
                    val = row.get(csv_col, '').strip()
                    data[db_col] = val if val else None

                # Verifica se esiste già
                existing = db.execute(
                    "SELECT id_cliente FROM anagrafica_clienti WHERE codice_cliente = %s",
                    (codice,)
                ).fetchone()

                if existing:
                    # Update
                    set_clause = ", ".join([f"{k} = %s" for k in data.keys() if k != 'codice_cliente'])
                    set_clause += ", data_aggiornamento = CURRENT_TIMESTAMP"
                    values = [v for k, v in data.items() if k != 'codice_cliente']
                    values.append(codice)

                    db.execute(f"""
                        UPDATE anagrafica_clienti
                        SET {set_clause}
                        WHERE codice_cliente = %s
                    """, values)
                    stats['aggiornati'] += 1
                else:
                    # Insert
                    cols = ", ".join(data.keys())
                    placeholders = ", ".join(["%s"] * len(data))
                    values = list(data.values())

                    db.execute(f"""
                        INSERT INTO anagrafica_clienti ({cols})
                        VALUES ({placeholders})
                    """, values)
                    stats['inseriti'] += 1

                # Commit ogni 1000 record
                if stats['totale'] % 1000 == 0:
                    db.commit()
                    print(f"  Processati {stats['totale']} record...")

            except Exception as e:
                stats['errori'] += 1
                stats['errori_dettaglio'].append(f"Riga {row_num}: {str(e)}")

    db.commit()

    print(f"\nImport completato:")
    print(f"  Totale righe: {stats['totale']}")
    print(f"  Inseriti: {stats['inseriti']}")
    print(f"  Aggiornati: {stats['aggiornati']}")
    print(f"  Errori: {stats['errori']}")

    if stats['errori_dettaglio'] and len(stats['errori_dettaglio']) <= 10:
        print("\nDettaglio errori:")
        for err in stats['errori_dettaglio']:
            print(f"  - {err}")

    return stats


def get_clienti_count() -> int:
    """Ritorna il numero di clienti in anagrafica."""
    db = get_db()
    result = db.execute("SELECT COUNT(*) FROM anagrafica_clienti").fetchone()
    return result[0] if result else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python import_clienti.py <file.csv> [--truncate]")
        print("  --truncate: Svuota la tabella prima dell'import")
        sys.exit(1)

    csv_path = sys.argv[1]
    truncate = '--truncate' in sys.argv

    if not os.path.exists(csv_path):
        print(f"Errore: File non trovato: {csv_path}")
        sys.exit(1)

    import_clienti(csv_path, truncate)
