"""
Cancella le righe supervisione_* appese a ordini che non esistono piu'.

Le lasciava indietro POST /upload/reprocess/{id}, che cancellava anomalie e
testata ma non le supervisioni. Quelle in stato PENDING continuano a contare
nei totali della UI (`SELECT COUNT(*) ... WHERE stato = 'PENDING'`), quindi
l'operatore vede lavoro che non puo' aprire.

    cd backend && source venv/bin/activate && python scripts/pulisci_supervisioni_orfane.py [--dry-run]

Salva sempre un backup JSON delle righe cancellate prima di procedere.
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database_pg import get_db  # noqa: E402


def tabelle_supervisione(db):
    righe = db.execute("""
        SELECT c.table_name
        FROM information_schema.columns c
        WHERE c.table_schema = 'public'
          AND c.table_name LIKE 'supervisione%%'
          AND c.column_name = 'id_testata'
        ORDER BY c.table_name
    """).fetchall()
    return [r['table_name'] for r in righe]


def orfane(db, tabella):
    """id_testata NULL non e' orfana: e' una supervisione non legata a un ordine."""
    return db.execute(f"""
        SELECT * FROM {tabella} s
        WHERE s.id_testata IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM ordini_testata t WHERE t.id_testata = s.id_testata)
        ORDER BY s.id_supervisione
    """).fetchall()


def serializza(riga):
    return {k: (v if isinstance(v, (int, float, bool, type(None))) else str(v))
            for k, v in dict(riga).items()}


def main():
    dry_run = '--dry-run' in sys.argv
    db = get_db()

    backup = {'quando': datetime.now().isoformat(), 'tabelle': {}}
    totale = pendenti = 0

    print(f"{'tabella':<26} {'orfane':>7} {'di cui PENDING':>15}")
    for tabella in tabelle_supervisione(db):
        righe = orfane(db, tabella)
        if not righe:
            continue
        pend = sum(1 for r in righe if dict(r).get('stato') == 'PENDING')
        totale += len(righe)
        pendenti += pend
        backup['tabelle'][tabella] = [serializza(r) for r in righe]
        print(f"{tabella:<26} {len(righe):>7} {pend:>15}")

    if not totale:
        print("\nNessuna supervisione orfana.")
        return 0

    print(f"\nTotale: {totale} righe orfane, {pendenti} in stato PENDING")

    if dry_run:
        print("[dry-run] nessuna cancellazione")
        return 0

    # Fuori dal repo: backend/backups/ e' gia' ignorata da git
    cartella = os.path.join(os.path.dirname(__file__), '..', 'backups')
    os.makedirs(cartella, exist_ok=True)
    percorso = os.path.abspath(os.path.join(
        cartella, f"supervisioni_orfane_{datetime.now():%Y%m%d_%H%M%S}.json"
    ))
    with open(percorso, 'w', encoding='utf-8') as fh:
        json.dump(backup, fh, ensure_ascii=False, indent=1)
    print(f"Backup: {percorso}")

    for tabella, righe in backup['tabelle'].items():
        ids = [r['id_supervisione'] for r in righe]
        segnaposto = ','.join(['%s'] * len(ids))
        db.execute(f"DELETE FROM {tabella} WHERE id_supervisione IN ({segnaposto})", tuple(ids))
        print(f"  cancellate {len(ids)} da {tabella}")
    db.commit()

    residue = sum(len(orfane(db, t)) for t in tabelle_supervisione(db))
    print(f"\nOrfane residue: {residue}")
    return 0 if residue == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
