"""
Riprocessa tutte le acquisizioni MENARINI con l'estrattore corrente.

Serve dopo un fix dell'estrattore: gli ordini gia' in DB restano quelli
prodotti dalla versione precedente e non si aggiornano da soli.

Per ogni acquisizione: cancella supervisioni -> anomalie -> dettagli ->
testata -> acquisizione, poi rilegge il PDF da disco e lo rielabora.
E' la stessa sequenza di POST /upload/reprocess/{id}, in blocco.

    cd backend && source venv/bin/activate && python scripts/reprocess_menarini.py [--dry-run]

ATTENZIONE: cancella e ricrea gli ordini. Non usare su ordini gia' lavorati
(lookup manuale, AIC assegnati, esportazioni): il lavoro dell'operatore va perso.
Lo script si ferma se ne trova.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database_pg import get_db  # noqa: E402
from app.services.pdf_processor import process_pdf  # noqa: E402
from app import config  # noqa: E402

TABELLE_SUPERVISIONE = (
    'supervisione_aic', 'supervisione_lookup', 'supervisione_espositore',
    'supervisione_prezzo', 'supervisione_anagrafica', 'supervisione_erp',
)

VENDOR = 'MENARINI'


def acquisizioni_vendor(db, vendor):
    return db.execute("""
        SELECT DISTINCT a.id_acquisizione, a.nome_file_storage, a.percorso_storage
        FROM acquisizioni a
        JOIN ordini_testata t ON t.id_acquisizione = a.id_acquisizione
        JOIN vendor v ON v.id_vendor = t.id_vendor
        WHERE v.codice_vendor = %s
        ORDER BY a.id_acquisizione
    """, (vendor,)).fetchall()


def verifica_nessun_lavoro_manuale(db, vendor):
    """Un reprocess distrugge il lavoro dell'operatore: meglio non partire."""
    rischi = db.execute("""
        SELECT count(*) FILTER (WHERE t.stato NOT IN ('ESTRATTO', 'ANOMALIA')) AS lavorati,
               count(*) FILTER (WHERE t.lookup_method = 'MANUALE') AS lookup_manuale,
               count(*) FILTER (WHERE t.id_cliente_manuale IS NOT NULL) AS cliente_manuale,
               (SELECT count(*) FROM esportazioni_dettaglio ed
                 JOIN ordini_testata t2 ON t2.id_testata = ed.id_testata
                 JOIN vendor v2 ON v2.id_vendor = t2.id_vendor
                WHERE v2.codice_vendor = %s) AS esportazioni
        FROM ordini_testata t
        JOIN vendor v ON v.id_vendor = t.id_vendor
        WHERE v.codice_vendor = %s
    """, (vendor, vendor)).fetchone()
    problemi = {k: v for k, v in dict(rischi).items() if v}
    return problemi


def percorso_pdf(acq):
    for candidato in (acq['percorso_storage'],
                      os.path.join(config.UPLOAD_DIR, acq['nome_file_storage'] or '')):
        if candidato and os.path.exists(candidato):
            return candidato
    return None


def cancella_acquisizione(db, id_acquisizione):
    testate = db.execute(
        "SELECT id_testata FROM ordini_testata WHERE id_acquisizione = %s",
        (id_acquisizione,)
    ).fetchall()
    for t in testate:
        for tabella in TABELLE_SUPERVISIONE:
            db.execute(f"DELETE FROM {tabella} WHERE id_testata = %s", (t['id_testata'],))
        db.execute("DELETE FROM anomalie WHERE id_testata = %s", (t['id_testata'],))
        db.execute("DELETE FROM ordini_dettaglio WHERE id_testata = %s", (t['id_testata'],))
    db.execute("DELETE FROM ordini_testata WHERE id_acquisizione = %s", (id_acquisizione,))
    db.execute("DELETE FROM acquisizioni WHERE id_acquisizione = %s", (id_acquisizione,))
    db.commit()
    return len(testate)


def main():
    dry_run = '--dry-run' in sys.argv
    db = get_db()

    problemi = verifica_nessun_lavoro_manuale(db, VENDOR)
    if problemi:
        print(f"STOP: ci sono ordini {VENDOR} gia' lavorati: {problemi}")
        print("Il reprocess li distruggerebbe. Interrompo.")
        return 1

    acquisizioni = acquisizioni_vendor(db, VENDOR)
    print(f"Acquisizioni {VENDOR} da riprocessare: {len(acquisizioni)}")

    mancanti = [a['nome_file_storage'] for a in acquisizioni if not percorso_pdf(a)]
    if mancanti:
        print(f"STOP: {len(mancanti)} PDF non trovati su disco: {mancanti[:5]}")
        return 1

    if dry_run:
        for a in acquisizioni:
            print(f"  [dry-run] {a['id_acquisizione']:>4}  {a['nome_file_storage']}")
        return 0

    ok = errori = ordini = righe = 0
    for a in acquisizioni:
        pdf = percorso_pdf(a)
        nome = a['nome_file_storage']
        try:
            n_testate = cancella_acquisizione(db, a['id_acquisizione'])
            with open(pdf, 'rb') as fh:
                contenuto = fh.read()
            res = process_pdf(nome, contenuto, pdf_path=pdf, save_to_disk=False)
            stato = res.get('status')
            if stato == 'OK':
                ok += 1
                ordini += res.get('ordini', 0)
                righe += res.get('righe', 0)
            else:
                errori += 1
            print(f"  {a['id_acquisizione']:>4}  {stato:<10} "
                  f"ordini {res.get('ordini', 0):>2} righe {res.get('righe', 0):>3} "
                  f"(prima: {n_testate} ordini)  {nome[:46]}")
            for msg in res.get('anomalie', [])[:3]:
                print(f"          - {msg[:110]}")
        except Exception as exc:  # noqa: BLE001
            errori += 1
            print(f"  {a['id_acquisizione']:>4}  ERRORE     {nome[:46]}: {exc}")

    print(f"\nAcquisizioni riprocessate: {ok}/{len(acquisizioni)} (errori: {errori})")
    print(f"Ordini creati: {ordini} | righe: {righe}")
    return 0 if errori == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
