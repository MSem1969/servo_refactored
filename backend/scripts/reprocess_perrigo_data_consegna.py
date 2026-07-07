#!/usr/bin/env python3
"""
Rielaborazione data di consegna ordini PERRIGO
==============================================

Corregge la `data_consegna` (testata) e la `data_consegna_riga` (dettaglio)
degli ordini PERRIGO gia' presenti in DB, ri-estraendola dal PDF originale con
l'estrattore corretto (fix underscore separatore + confine blocco).

Contesto: prima del fix, il regex "Data di consegna : DD.MM.YYYY" non matchava
mai (la riga cade su un separatore del PDF e pdfplumber intercala i caratteri
con underscore), quindi la data restava vuota e a valle coincideva con la data
ordine / data odierna.

COSA TOCCA (solo campi data):
  - ordini_testata.data_consegna
  - ordini_dettaglio.data_consegna_riga
NON tocca: quantita', prezzi, stati, lookup, esportazioni, evasioni.

E' idempotente: aggiorna solo le righe la cui data differisce dal valore
ri-estratto; rieseguirlo non produce ulteriori modifiche.

Uso (da backend/, con venv attivo):
  python scripts/reprocess_perrigo_data_consegna.py                 # DRY-RUN (default)
  python scripts/reprocess_perrigo_data_consegna.py --apply         # scrive su DB
  python scripts/reprocess_perrigo_data_consegna.py --apply --operatore mario.rossi
  python scripts/reprocess_perrigo_data_consegna.py --id-testata 174 # un solo ordine

Gli ordini gia' ESPORTATO/EVASO vengono aggiornati come richiesto, ma il
tracciato eventualmente gia' inviato mantiene la data vecchia: vengono elencati
a fine run come "DA RIEMETTERE" per un'eventuale riemissione manuale.
"""

import argparse
import os
import sys
from datetime import datetime

# Rende importabile il package `app` (questo script sta in backend/scripts/)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pdfplumber  # noqa: E402

from app.database_pg import get_db, get_operatore_id_by_username  # noqa: E402
from app.services.extraction.vendors.perrigo import extract_perrigo  # noqa: E402
from app.services.pdf_processor import _convert_date_to_iso  # noqa: E402

try:
    from app.services.pdf_processor import _fix_encoding_manual
except Exception:  # pragma: no cover
    def _fix_encoding_manual(t):
        return t

try:
    import ftfy
    _FTFY = True
except Exception:  # pragma: no cover
    _FTFY = False

STATI_ESPORTATI = {'ESPORTATO', 'PARZ_ESPORTATO', 'EVASO', 'PARZ_EVASO'}


def estrai_testo(pdf_path: str) -> str:
    """Ricostruisce il testo come fa pdf_processor (x_tolerance=5, y_tolerance=3)."""
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(x_tolerance=5, y_tolerance=3) or ""
            if _FTFY:
                page_text = ftfy.fix_text(page_text)
            page_text = _fix_encoding_manual(page_text)
            parts.append(page_text)
    return "\n".join(parts) + "\n"


def date_estratte(pdf_path: str, numero_ordine: str):
    """
    Ritorna (testata_iso, mappa_codice->iso, distinct_iso, trovate).
    testata_iso: data di consegna della testata (prima referenza).
    mappa: codice(aic/originale) -> data iso, per il caso multi-data.
    """
    text = estrai_testo(pdf_path)
    orders = extract_perrigo(text, text.split("\n"), pdf_path)

    order = None
    for o in orders:
        if str(o.get('numero_ordine', '')).strip() == str(numero_ordine).strip():
            order = o
            break
    if order is None and len(orders) == 1:
        order = orders[0]
    if order is None:
        return None, {}, [], False

    righe = order.get('righe', [])
    mappa = {}
    distinct = []
    for r in righe:
        it = r.get('data_consegna')
        if not it:
            continue
        iso = _convert_date_to_iso(it)
        if not iso:
            continue
        if iso not in distinct:
            distinct.append(iso)
        for key in (r.get('codice_aic'), r.get('codice_originale')):
            if key:
                mappa[str(key)] = iso

    testata_it = order.get('data_consegna') or (righe[0].get('data_consegna') if righe else '')
    testata_iso = _convert_date_to_iso(testata_it) if testata_it else (distinct[0] if distinct else None)
    return testata_iso, mappa, distinct, bool(distinct)


def scrivi_backup(cur, orders, path: str) -> int:
    """
    Scrive un file SQL di rollback con i valori ATTUALI di data_consegna
    (testata) e data_consegna_riga (dettaglio) per gli ordini in scope.
    Rieseguendo quel file si ripristina lo stato precedente alla correzione.
    Ritorna il numero di UPDATE generati.
    """
    n = 0
    righe = [
        f"-- Backup rollback PERRIGO data_consegna - generato {datetime.now().isoformat(timespec='seconds')}",
        "-- Ripristina i valori PRECEDENTI alla correzione. Eseguire con: psql ... -f <questo file>",
        "BEGIN;",
    ]
    for o in orders:
        idt = o['id_testata']
        cur.execute("SELECT to_char(data_consegna,'YYYY-MM-DD') d FROM ordini_testata WHERE id_testata=%s", (idt,))
        d = dict(cur.fetchall()[0])['d']
        val = f"DATE '{d}'" if d else "NULL"
        righe.append(f"UPDATE ordini_testata SET data_consegna = {val} WHERE id_testata = {idt};")
        n += 1
        cur.execute("""SELECT id_dettaglio, to_char(data_consegna_riga,'YYYY-MM-DD') d
                       FROM ordini_dettaglio WHERE id_testata=%s ORDER BY id_dettaglio""", (idt,))
        for rr in [dict(x) for x in cur.fetchall()]:
            val = f"DATE '{rr['d']}'" if rr['d'] else "NULL"
            righe.append(f"UPDATE ordini_dettaglio SET data_consegna_riga = {val} WHERE id_dettaglio = {rr['id_dettaglio']};")
            n += 1
    righe.append("COMMIT;")
    with open(path, 'w') as f:
        f.write("\n".join(righe) + "\n")
    return n


def main():
    ap = argparse.ArgumentParser(description="Rielabora data_consegna ordini PERRIGO")
    ap.add_argument('--apply', action='store_true', help='Scrive le modifiche (default: dry-run)')
    ap.add_argument('--operatore', default='system', help='Username per audit log (default: system)')
    ap.add_argument('--id-testata', type=int, default=None, help='Limita a un singolo id_testata')
    ap.add_argument('--backup', nargs='?', const='', default=None,
                    help='Scrive un file SQL di rollback prima di modificare. Opzionale il path; '
                         'senza valore usa perrigo_data_consegna_backup_<timestamp>.sql')
    args = ap.parse_args()

    conn = get_db()
    cur = conn.cursor()

    filtro = "AND t.id_testata = %s" if args.id_testata else ""
    params = [args.id_testata] if args.id_testata else []
    cur.execute(f"""
        SELECT t.id_testata, t.numero_ordine_vendor, t.stato, t.data_consegna,
               a.percorso_storage
        FROM ordini_testata t
        JOIN vendor v ON v.id_vendor = t.id_vendor
        LEFT JOIN acquisizioni a ON a.id_acquisizione = t.id_acquisizione
        WHERE v.codice_vendor = 'PERRIGO' {filtro}
        ORDER BY t.id_testata
    """, params)
    orders = [dict(r) for r in cur.fetchall()]

    print(f"{'=' * 78}")
    print(f"REPROCESS PERRIGO data_consegna  |  MODE={'APPLY' if args.apply else 'DRY-RUN'}"
          f"  |  ordini={len(orders)}")
    print(f"{'=' * 78}")

    # Backup di rollback PRIMA di qualunque scrittura
    if args.backup is not None and orders:
        bkp_path = args.backup or f"perrigo_data_consegna_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        n_bkp = scrivi_backup(cur, orders, bkp_path)
        print(f"Backup rollback scritto in: {os.path.abspath(bkp_path)}  ({n_bkp} UPDATE, {len(orders)} ordini)\n")

    tot_testate = 0
    tot_righe = 0
    da_riemettere = []
    saltati = []

    for o in orders:
        idt = o['id_testata']
        num = o['numero_ordine_vendor']
        stato = o['stato']
        path = o['percorso_storage']

        if not (path and os.path.exists(path)):
            saltati.append((idt, num, 'PDF mancante'))
            print(f"  [SKIP] id={idt} ord={num}: PDF non trovato ({path})")
            continue

        try:
            testata_iso, mappa, distinct, trovate = date_estratte(path, num)
        except Exception as e:
            saltati.append((idt, num, f'errore estrazione: {e}'))
            print(f"  [SKIP] id={idt} ord={num}: errore estrazione {e}")
            continue

        if not trovate or not testata_iso:
            saltati.append((idt, num, 'data non estratta'))
            print(f"  [SKIP] id={idt} ord={num}: data di consegna non estratta")
            continue

        multi = len(distinct) > 1

        # --- Testata ---
        cur.execute("SELECT to_char(data_consegna,'YYYY-MM-DD') d FROM ordini_testata WHERE id_testata=%s", (idt,))
        old_testata = dict(cur.fetchall()[0])['d']
        testata_change = (old_testata != testata_iso)

        # --- Dettaglio: quante righe cambierebbero ---
        if not multi:
            cur.execute("""
                SELECT count(*) c FROM ordini_dettaglio
                WHERE id_testata=%s AND data_consegna_riga IS DISTINCT FROM %s
            """, (idt, testata_iso))
            n_righe_change = dict(cur.fetchall()[0])['c']
        else:
            # multi-data: conteggio per riga tramite mappa codice->data (fallback testata)
            cur.execute("""SELECT id_dettaglio, codice_aic, codice_originale,
                                  to_char(data_consegna_riga,'YYYY-MM-DD') d
                           FROM ordini_dettaglio WHERE id_testata=%s""", (idt,))
            n_righe_change = 0
            for rr in [dict(x) for x in cur.fetchall()]:
                new = mappa.get(str(rr['codice_aic'])) or mappa.get(str(rr['codice_originale'])) or testata_iso
                if rr['d'] != new:
                    n_righe_change += 1

        flag = ''
        if multi:
            flag += f"  [MULTI-DATA {distinct}]"
        if stato in STATI_ESPORTATI:
            flag += f"  [{stato} -> DA RIEMETTERE]"
            da_riemettere.append((idt, num, stato))

        print(f"  id={idt} ord={num} stato={stato}: testata {old_testata} -> {testata_iso}"
              f" ({'MODIFICA' if testata_change else 'invariata'}), righe da aggiornare={n_righe_change}{flag}")

        if args.apply:
            if testata_change:
                cur.execute("UPDATE ordini_testata SET data_consegna=%s WHERE id_testata=%s",
                            (testata_iso, idt))
            if not multi:
                cur.execute("""
                    UPDATE ordini_dettaglio SET data_consegna_riga=%s
                    WHERE id_testata=%s AND data_consegna_riga IS DISTINCT FROM %s
                """, (testata_iso, idt, testata_iso))
            else:
                cur.execute("""SELECT id_dettaglio, codice_aic, codice_originale,
                                      to_char(data_consegna_riga,'YYYY-MM-DD') d
                               FROM ordini_dettaglio WHERE id_testata=%s""", (idt,))
                for rr in [dict(x) for x in cur.fetchall()]:
                    new = mappa.get(str(rr['codice_aic'])) or mappa.get(str(rr['codice_originale'])) or testata_iso
                    if rr['d'] != new:
                        cur.execute("UPDATE ordini_dettaglio SET data_consegna_riga=%s WHERE id_dettaglio=%s",
                                    (new, rr['id_dettaglio']))

        if testata_change:
            tot_testate += 1
        tot_righe += n_righe_change

    if args.apply:
        conn.commit()
        _audit(conn, args.operatore, tot_testate, tot_righe)
        print(f"\nCOMMIT OK. Testate modificate={tot_testate}, righe modificate={tot_righe}")
    else:
        conn.rollback()
        print(f"\nDRY-RUN (nessuna scrittura). Testate da modificare={tot_testate}, "
              f"righe da modificare={tot_righe}")
        print("Rilancia con --apply per applicare.")

    if da_riemettere:
        print("\n--- ORDINI GIA' ESPORTATI/EVASI (data corretta in DB, tracciato da riemettere) ---")
        for idt, num, st in da_riemettere:
            print(f"  id={idt} ord={num} stato={st}")

    if saltati:
        print("\n--- SALTATI ---")
        for idt, num, motivo in saltati:
            print(f"  id={idt} ord={num}: {motivo}")

    cur.close()


def _audit(conn, operatore, n_testate, n_righe):
    """Audit best-effort: non deve mai far fallire la correzione dati."""
    try:
        id_op = get_operatore_id_by_username(operatore)
        if not id_op:
            print(f"  (audit log saltato: operatore '{operatore}' non in tabella operatori; "
                  f"i dati sono comunque aggiornati)")
            return
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO operatore_azioni_log
              (id_operatore, username, ruolo, sezione, azione, entita, parametri, success, timestamp)
            VALUES (%s, %s, %s, 'DATABASE', 'REPROCESS_DATA_CONSEGNA', 'ordini_perrigo',
                    %s::jsonb, TRUE, NOW())
        """, (id_op, operatore, 'system',
              '{"vendor":"PERRIGO","testate":%d,"righe":%d}' % (n_testate, n_righe)))
        conn.commit()
        cur.close()
    except Exception as e:
        conn.rollback()
        print(f"  (audit log non registrato: {e})")


if __name__ == '__main__':
    main()
