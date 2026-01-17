# =============================================================================
# SERV.O v10.1 - LISTINI CSV IMPORT
# =============================================================================
# Import listini da file CSV
# =============================================================================

import csv
import os
from typing import Dict, Any, Tuple
from ...database_pg import get_db
from .parsing import (
    parse_decimal_it,
    parse_prezzo_intero,
    parse_data_yyyymmdd,
    normalizza_codice_aic,
    scorporo_iva,
    calcola_prezzo_netto,
)


# Mapping colonne CSV -> campi database per ogni vendor
VENDOR_CSV_MAPPINGS = {
    'CODIFI': {
        'codice_aic': 'AFCODI',
        'descrizione': 'CVDPRO',
        'sconto_1': 'CVSCO1',
        'sconto_2': 'CVSCO2',
        'prezzo_pubblico_csv': 'AFPEU1',
        'prezzo_csv_originale': 'CVPVEN',
        'aliquota_iva': 'AFAIVA',
        'data_decorrenza': 'AFDVA1',
    }
}


def import_listino_csv(
    csv_content: bytes = None,
    filepath: str = None,
    vendor: str = 'CODIFI',
    filename: str = None,
    clear_existing: bool = True,
    scorporo_iva_default: str = 'S'
) -> Tuple[bool, Dict[str, Any]]:
    """
    Importa listino da file CSV per un vendor specifico.
    I dati vengono mappati ai campi allineati al tracciato TO_D.
    """
    vendor_upper = vendor.upper()

    if vendor_upper not in VENDOR_CSV_MAPPINGS:
        return False, {
            'error': f"Vendor {vendor_upper} non supportato. Vendor disponibili: {list(VENDOR_CSV_MAPPINGS.keys())}"
        }

    if csv_content is None and filepath is None:
        return False, {'error': 'Fornire csv_content o filepath'}

    if filepath and not os.path.exists(filepath):
        return False, {'error': f"File non trovato: {filepath}"}

    mapping = VENDOR_CSV_MAPPINGS[vendor_upper]
    db = get_db()

    if filename:
        result_filename = filename
    elif filepath:
        result_filename = os.path.basename(filepath)
    else:
        result_filename = f"upload_{vendor_upper}.csv"

    result = {
        'imported': 0,
        'skipped': 0,
        'errors': [],
        'filename': result_filename
    }

    try:
        if clear_existing:
            cursor = db.execute(
                "DELETE FROM listini_vendor WHERE vendor = %s",
                (vendor_upper,)
            )
            deleted = cursor.rowcount
            db.commit()
            print(f"   Eliminate {deleted} righe esistenti per {vendor_upper}")

        if csv_content is not None:
            try:
                content_str = csv_content.decode('utf-8')
            except UnicodeDecodeError:
                content_str = csv_content.decode('latin-1', errors='replace')
            lines = content_str.splitlines()
        else:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.read().splitlines()

        if not lines:
            return False, {'error': 'File CSV vuoto'}

        sample = '\n'.join(lines[:5])
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=',;')
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = ','

        reader = csv.DictReader(lines, dialect=dialect)

        headers = reader.fieldnames or []
        required_cols = ['codice_aic', 'descrizione']
        missing = [mapping[col] for col in required_cols if mapping.get(col) and mapping[col] not in headers]
        if missing:
            return False, {
                'error': f"Colonne obbligatorie mancanti nel CSV: {missing}. Colonne trovate: {headers}"
            }

        for row_num, row in enumerate(reader, start=2):
            try:
                codice_aic_raw = row.get(mapping['codice_aic'], '').strip()
                if not codice_aic_raw:
                    result['skipped'] += 1
                    continue

                codice_aic = normalizza_codice_aic(codice_aic_raw)
                descrizione = row.get(mapping['descrizione'], '').strip()[:100]

                sconto_1_csv = parse_decimal_it(row.get(mapping.get('sconto_1', ''), ''))
                sconto_2_csv = parse_decimal_it(row.get(mapping.get('sconto_2', ''), ''))
                sconto_3_csv = parse_decimal_it(row.get(mapping.get('sconto_3', ''), ''))
                sconto_4_csv = parse_decimal_it(row.get(mapping.get('sconto_4', ''), ''))

                prezzo_pubblico_csv = parse_prezzo_intero(row.get(mapping.get('prezzo_pubblico_csv', ''), ''), decimals=3)
                prezzo_csv_originale = parse_decimal_it(row.get(mapping.get('prezzo_csv_originale', ''), ''))

                aliquota_iva_raw = row.get(mapping.get('aliquota_iva', ''), '')
                aliquota_iva = float(aliquota_iva_raw) if aliquota_iva_raw.replace('.', '').replace(',', '').isdigit() else None

                data_decorrenza = parse_data_yyyymmdd(row.get(mapping.get('data_decorrenza', ''), ''))

                if prezzo_csv_originale and prezzo_csv_originale > 0:
                    prezzo_netto = prezzo_csv_originale
                    prezzo_scontare = prezzo_csv_originale
                    prezzo_pubblico = prezzo_pubblico_csv
                    sconto_1 = 0
                    sconto_2 = 0
                    sconto_3 = 0
                    sconto_4 = 0
                    flag_scorporo = 'S'
                else:
                    prezzo_pubblico = prezzo_pubblico_csv
                    prezzo_scontare = prezzo_pubblico_csv
                    prezzo_netto = scorporo_iva(prezzo_pubblico_csv, aliquota_iva)
                    sconto_1 = sconto_1_csv
                    sconto_2 = sconto_2_csv
                    sconto_3 = sconto_3_csv
                    sconto_4 = sconto_4_csv
                    flag_scorporo = 'N'

                db.execute("""
                    INSERT INTO listini_vendor (
                        vendor, codice_aic, descrizione,
                        sconto_1, sconto_2, sconto_3, sconto_4,
                        prezzo_netto, prezzo_scontare, prezzo_pubblico,
                        aliquota_iva, scorporo_iva,
                        prezzo_csv_originale, prezzo_pubblico_csv,
                        data_decorrenza, fonte_file, attivo, data_import
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, NOW())
                    ON CONFLICT (vendor, codice_aic) DO UPDATE SET
                        descrizione = EXCLUDED.descrizione,
                        sconto_1 = EXCLUDED.sconto_1,
                        sconto_2 = EXCLUDED.sconto_2,
                        sconto_3 = EXCLUDED.sconto_3,
                        sconto_4 = EXCLUDED.sconto_4,
                        prezzo_netto = EXCLUDED.prezzo_netto,
                        prezzo_scontare = EXCLUDED.prezzo_scontare,
                        prezzo_pubblico = EXCLUDED.prezzo_pubblico,
                        aliquota_iva = EXCLUDED.aliquota_iva,
                        scorporo_iva = EXCLUDED.scorporo_iva,
                        prezzo_csv_originale = EXCLUDED.prezzo_csv_originale,
                        prezzo_pubblico_csv = EXCLUDED.prezzo_pubblico_csv,
                        data_decorrenza = EXCLUDED.data_decorrenza,
                        fonte_file = EXCLUDED.fonte_file,
                        attivo = TRUE,
                        data_import = NOW()
                """, (
                    vendor_upper, codice_aic, descrizione,
                    sconto_1, sconto_2, sconto_3, sconto_4,
                    prezzo_netto, prezzo_scontare, prezzo_pubblico,
                    aliquota_iva, flag_scorporo,
                    prezzo_csv_originale, prezzo_pubblico_csv,
                    data_decorrenza, result_filename
                ))

                result['imported'] += 1

            except Exception as e:
                result['errors'].append(f"Riga {row_num}: {str(e)}")
                result['skipped'] += 1

        db.commit()

        count = db.execute(
            "SELECT COUNT(*) FROM listini_vendor WHERE vendor = %s",
            (vendor_upper,)
        ).fetchone()[0]
        result['total_in_db'] = count

        return True, result

    except Exception as e:
        db.rollback()
        return False, {'error': f"Errore import: {str(e)}"}


def aggiorna_prezzi_netti(
    vendor: str,
    formula: str = 'SCONTO_CASCATA',
    usa_prezzo_pubblico: bool = True
) -> Dict[str, Any]:
    """
    Calcola e aggiorna prezzo_netto e prezzo_scontare per tutti i prodotti di un vendor.
    """
    db = get_db()
    vendor_upper = vendor.upper()

    rows = db.execute("""
        SELECT id_listino, prezzo_pubblico, prezzo_scontare,
               sconto_1, sconto_2, sconto_3, sconto_4
        FROM listini_vendor
        WHERE vendor = %s AND attivo = TRUE
    """, (vendor_upper,)).fetchall()

    updated = 0
    skipped = 0

    for row in rows:
        if usa_prezzo_pubblico:
            prezzo_base = row['prezzo_pubblico']
        else:
            prezzo_base = row['prezzo_scontare'] or row['prezzo_pubblico']

        prezzo_netto, formula_str = calcola_prezzo_netto(
            prezzo_base,
            row['sconto_1'],
            row['sconto_2'],
            row['sconto_3'],
            row['sconto_4'],
            formula
        )

        if prezzo_netto is not None:
            db.execute("""
                UPDATE listini_vendor
                SET prezzo_netto = %s,
                    prezzo_scontare = %s
                WHERE id_listino = %s
            """, (prezzo_netto, prezzo_base, row['id_listino']))
            updated += 1
        else:
            skipped += 1

    db.commit()

    return {
        'vendor': vendor_upper,
        'updated': updated,
        'skipped': skipped,
        'formula': formula
    }
