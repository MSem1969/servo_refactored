"""
Riprocessa le acquisizioni di un vendor con l'estrattore corrente.

Serve dopo un fix dell'estrattore: gli ordini gia' in DB restano quelli
prodotti dalla versione precedente e non si aggiornano da soli.

Per ogni acquisizione: cancella supervisioni -> anomalie -> dettagli ->
testata -> acquisizione, poi rilegge il PDF da disco e lo rielabora.
E' la stessa sequenza di POST /upload/reprocess/{id}, in blocco.

    python scripts/reprocess_vendor.py --vendor MENARINI [--dry-run]

## Il reprocess DISTRUGGE il lavoro dell'operatore

Cancella e ricrea l'ordine con un id_testata nuovo. Quello vecchio sparisce, e
con lui il lookup manuale, gli AIC assegnati in supervisione, lo stato di
conferma/evasione e il legame con le esportazioni gia' trasmesse all'ERP.

Lo script quindi SALTA le acquisizioni che hanno anche un solo ordine toccato,
e riprocessa solo le altre. Non esiste un --force: se un ordine e' stato
lavorato, la correzione va fatta a mano o non va fatta.

Un'acquisizione e' considerata intoccabile se un suo ordine ha:
  - stato diverso da ESTRATTO / ANOMALIA / ARCHIVIATO
  - lookup_method = 'MANUALE' o un cliente assegnato a mano
  - una riga in esportazioni_dettaglio (tracciato gia' emesso)
  - una supervisione decisa da un operatore (APPROVED, REJECTED, CORRETTA...)

ARCHIVIATO e' riprocessabile perche' un ordine viene archiviato anche quando
l'estrazione era sbagliata, ed e' proprio il caso che questo script serve a
recuperare. Ma attenzione: il reprocess lo riporta in vita come ESTRATTO o
ANOMALIA, quindi torna nella lista con le sue anomalie e supervisioni riaperte,
e va ri-archiviato a mano se davvero non serviva. Per lo stesso motivo le
supervisioni in stato ARCHIVED non contano come "decise": non sono un giudizio
dell'operatore, sono la conseguenza dell'archiviazione.

## In produzione

1. Il codice nuovo deve essere GIA' DEPLOYATO: il reprocess usa l'estrattore
   in esecuzione, non quello sul tuo branch.
2. Backup del database prima di partire (vedi RECOVERY.md).
3. Girare prima con --dry-run e leggere l'elenco di cosa verrebbe saltato.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database_pg import get_db  # noqa: E402
from app.services.pdf_processor import process_pdf  # noqa: E402
from app import config  # noqa: E402

# Tutte le tabelle supervisione_*: dimenticarne una lascia righe PENDING
# appese a ordini inesistenti, che continuano a contare nei totali della UI.
TABELLE_SUPERVISIONE = (
    'supervisione_aic', 'supervisione_lookup', 'supervisione_espositore',
    'supervisione_listino', 'supervisione_prezzo',
    'supervisione_anagrafica', 'supervisione_erp',
)

STATI_NON_LAVORATI = ('ESTRATTO', 'ANOMALIA', 'ARCHIVIATO')

# Stati di supervisione che NON bloccano il reprocess: in attesa di lavorazione
# o chiusi d'ufficio con l'archiviazione dell'ordine. Tutti gli altri
# (APPROVED, REJECTED, CORRETTA, ...) sono decisioni di un operatore.
STATI_SUPERVISIONE_NON_DECISI = ('PENDING', 'ARCHIVED')


def acquisizioni_vendor(db, vendor):
    return db.execute("""
        SELECT DISTINCT a.id_acquisizione, a.nome_file_storage, a.percorso_storage
        FROM acquisizioni a
        JOIN ordini_testata t ON t.id_acquisizione = a.id_acquisizione
        JOIN vendor v ON v.id_vendor = t.id_vendor
        WHERE v.codice_vendor = %s
        ORDER BY a.id_acquisizione
    """, (vendor,)).fetchall()


def motivi_intoccabile(db, id_acquisizione):
    """Perche' questa acquisizione non va riprocessata. Lista vuota = via libera."""
    riga = db.execute(f"""
        SELECT
          count(*) FILTER (WHERE t.stato NOT IN {STATI_NON_LAVORATI}) AS lavorati,
          count(*) FILTER (WHERE t.lookup_method = 'MANUALE') AS lookup_manuale,
          count(*) FILTER (WHERE t.id_cliente_manuale IS NOT NULL) AS cliente_manuale,
          count(*) FILTER (WHERE EXISTS (
              SELECT 1 FROM esportazioni_dettaglio ed WHERE ed.id_testata = t.id_testata
          )) AS esportati
        FROM ordini_testata t
        WHERE t.id_acquisizione = %s
    """, (id_acquisizione,)).fetchone()

    motivi = [f"{n} {etichetta}" for etichetta, n in dict(riga).items() if n]

    decise = 0
    for tabella in TABELLE_SUPERVISIONE:
        try:
            decise += db.execute(f"""
                SELECT count(*) FROM {tabella} s
                JOIN ordini_testata t ON t.id_testata = s.id_testata
                WHERE t.id_acquisizione = %s
                  AND s.stato NOT IN {STATI_SUPERVISIONE_NON_DECISI}
            """, (id_acquisizione,)).fetchone()[0]
        except Exception:  # noqa: BLE001 - tabella assente in DB piu' vecchi
            db.rollback()
    if decise:
        motivi.append(f"{decise} supervisioni decise")

    return motivi


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vendor', default='MENARINI', help='codice vendor (default: MENARINI)')
    parser.add_argument('--dry-run', action='store_true', help='mostra cosa farebbe, senza toccare nulla')
    args = parser.parse_args()

    vendor = args.vendor.upper()
    db = get_db()

    acquisizioni = acquisizioni_vendor(db, vendor)
    if not acquisizioni:
        print(f"Nessuna acquisizione {vendor}.")
        return 0

    lavorabili, saltate = [], []
    for acq in acquisizioni:
        motivi = motivi_intoccabile(db, acq['id_acquisizione'])
        if motivi:
            saltate.append((acq, motivi))
        elif not percorso_pdf(acq):
            saltate.append((acq, ['PDF non trovato su disco']))
        else:
            lavorabili.append(acq)

    print(f"Acquisizioni {vendor}: {len(acquisizioni)} "
          f"({len(lavorabili)} riprocessabili, {len(saltate)} saltate)\n")

    for acq, motivi in saltate:
        print(f"  SALTATA {acq['id_acquisizione']:>5}  {', '.join(motivi):<44} "
              f"{(acq['nome_file_storage'] or '')[:40]}")
    if saltate:
        print()

    if args.dry_run:
        for acq in lavorabili:
            print(f"  [dry-run] {acq['id_acquisizione']:>5}  {acq['nome_file_storage']}")
        return 0

    ok = errori = ordini = righe = 0
    for acq in lavorabili:
        pdf = percorso_pdf(acq)
        nome = acq['nome_file_storage']
        try:
            n_prima = cancella_acquisizione(db, acq['id_acquisizione'])
            with open(pdf, 'rb') as fh:
                contenuto = fh.read()
            res = process_pdf(nome, contenuto, pdf_path=pdf, save_to_disk=False)
            if res.get('status') == 'OK':
                ok += 1
                ordini += res.get('ordini', 0)
                righe += res.get('righe', 0)
            else:
                errori += 1
            print(f"  {acq['id_acquisizione']:>5}  {res.get('status'):<10} "
                  f"ordini {res.get('ordini', 0):>2} righe {res.get('righe', 0):>3} "
                  f"(prima: {n_prima} ordini)  {nome[:44]}")
        except Exception as exc:  # noqa: BLE001
            errori += 1
            print(f"  {acq['id_acquisizione']:>5}  ERRORE     {nome[:44]}: {exc}")

    print(f"\nRiprocessate: {ok}/{len(lavorabili)} (errori: {errori}) | "
          f"ordini {ordini} | righe {righe}")
    if saltate:
        print(f"Saltate {len(saltate)} acquisizioni con ordini gia' lavorati: "
              f"vanno corrette a mano o lasciate come sono.")
    return 0 if errori == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
