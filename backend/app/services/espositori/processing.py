# =============================================================================
# SERV.O v10.1 - ESPOSITORI PROCESSING
# =============================================================================
# Elaborazione righe ordine con gestione espositori
# =============================================================================

from typing import Dict, List, Optional, Tuple

from .constants import CODICI_ANOMALIA, FASCE_SUPERVISIONE_OBBLIGATORIA
from .models import RigaChild, Espositore, ContestoElaborazione
from .detection import identifica_tipo_riga, estrai_pezzi_espositore


def elabora_righe_ordine(righe_raw: List[Dict], vendor: str = 'ANGELINI') -> ContestoElaborazione:
    """
    Elaborazione completa righe ordine con gestione espositori.

    Supporta:
    - ANGELINI: chiusura su pezzi accumulati
    - MENARINI: chiusura su somma valore netto
    """
    ctx = ContestoElaborazione(vendor=vendor)

    # Per MENARINI, traccia prezzo netto parent per chiusura
    menarini_netto_parent = 0.0

    for riga in righe_raw:
        codice = riga.get('codice_originale', '')
        descrizione = riga.get('descrizione', '')
        tipo_posizione = riga.get('tipo_posizione', '')

        # Legge tipo_riga o tipo_riga_raw (per estrattori che pre-marcano)
        tipo = riga.get('tipo_riga_raw') or riga.get('tipo_riga') or identifica_tipo_riga(codice, descrizione, tipo_posizione, vendor)

        # SCONTO_MERCE: sempre autonomo
        if tipo == 'SCONTO_MERCE':
            ctx.contatore_righe += 1
            riga_output = _crea_riga_output(riga, ctx.contatore_righe, 'SCONTO_MERCE')
            riga_output['q_sconto_merce'] = riga.get('quantita', 0)
            riga_output['q_venduta'] = 0
            riga_output['richiede_supervisione'] = False
            ctx.righe_output.append(riga_output)
            continue

        # MATERIALE_POP: sempre autonomo
        if tipo == 'MATERIALE_POP':
            ctx.contatore_righe += 1
            riga_output = _crea_riga_output(riga, ctx.contatore_righe, 'MATERIALE_POP')
            riga_output['q_omaggio'] = riga.get('quantita', 0)
            riga_output['q_venduta'] = 0
            riga_output['richiede_supervisione'] = False
            ctx.righe_output.append(riga_output)
            continue

        # PARENT_ESPOSITORE: chiudi precedente, apri nuovo
        if tipo == 'PARENT_ESPOSITORE':
            if ctx.espositore_attivo:
                ctx.contatore_righe += 1
                riga_out, righe_child, anomalia = _chiudi_espositore_forzato(
                    ctx.espositore_attivo, ctx.contatore_righe, 'NUOVO_PARENT', ctx.vendor
                )
                ctx.righe_output.append(riga_out)
                ctx.righe_output.extend(righe_child)
                if anomalia:
                    ctx.anomalie.append(anomalia)
                ctx.chiusure_forzate += 1

            pezzi = riga.get('pezzi_per_unita') or estrai_pezzi_espositore(descrizione, 1)[0] or 0

            # Per MENARINI, traccia prezzo netto parent per chiusura
            if vendor.upper() == 'MENARINI':
                menarini_netto_parent = float(riga.get('prezzo_netto', 0) or riga.get('prezzo_netto_parent', 0) or 0)

            ctx.espositore_attivo = Espositore(
                codice_aic=riga.get('codice_aic', ''),
                codice_originale=codice,
                codice_materiale=riga.get('codice_materiale', ''),
                descrizione=descrizione,
                pezzi_per_unita=pezzi,
                quantita_parent=riga.get('quantita', 0) or riga.get('q_venduta', 0) or 1,
                aliquota_iva=riga.get('aliquota_iva', 10),
                n_riga=ctx.contatore_righe + 1,
            )
            ctx.espositori_elaborati += 1
            continue

        # PRODOTTO_STANDARD o PROMO_AUTONOMA
        if tipo in ['PRODOTTO_STANDARD', 'PROMO_AUTONOMA', 'CHILD_ESPOSITORE']:
            # Per MENARINI, verifica che la riga sia effettivamente un child
            should_add_to_parent = False
            if ctx.espositore_attivo:
                if vendor.upper() == 'MENARINI':
                    # Per MENARINI: aggiungi SOLO se l'estrattore ha marcato come child
                    is_marked_child = riga.get('is_child', False) or riga.get('_belongs_to_parent', False)
                    is_child_type = tipo == 'CHILD_ESPOSITORE'
                    should_add_to_parent = is_marked_child or is_child_type
                else:
                    # Per altri vendor (ANGELINI): aggiungi tutte le righe dopo il parent
                    should_add_to_parent = True

            # Per MENARINI, se c'è un espositore attivo ma questa riga NON è un child,
            # chiudi l'espositore forzatamente (la riga interrompe la sequenza)
            if ctx.espositore_attivo and not should_add_to_parent and vendor.upper() == 'MENARINI':
                ctx.contatore_righe += 1
                riga_out, righe_child, anomalia = _chiudi_espositore_forzato(
                    ctx.espositore_attivo, ctx.contatore_righe, 'RIGA_NON_CHILD', ctx.vendor
                )
                ctx.righe_output.append(riga_out)
                ctx.righe_output.extend(righe_child)
                if anomalia:
                    ctx.anomalie.append(anomalia)
                ctx.chiusure_forzate += 1
                ctx.espositore_attivo = None
                menarini_netto_parent = 0.0

            if should_add_to_parent:
                # Per MENARINI usa valore_netto dal PDF (Totale Netto)
                # Per altri vendor calcola prezzo_netto × quantità
                child_quantita = int(riga.get('quantita', 0) or riga.get('q_venduta', 0) or 0)
                child_prezzo = float(riga.get('prezzo_netto', 0) or 0)
                # Usa valore_netto se presente (MENARINI), altrimenti calcola
                child_valore_calcolato = float(riga.get('valore_netto', 0) or 0)
                if child_valore_calcolato == 0:
                    child_valore_calcolato = child_prezzo * child_quantita

                # Rileva espositore vuoto (omaggio contenitore MENARINI)
                is_espositore_vuoto = riga.get('is_espositore_vuoto', False)
                # Backup detection: se non ha AIC e prezzo 0, è probabile espositore vuoto
                if not is_espositore_vuoto and not riga.get('codice_aic') and child_prezzo == 0:
                    is_espositore_vuoto = True

                child = RigaChild(
                    codice_aic=riga.get('codice_aic', ''),
                    codice_originale=codice,
                    codice_materiale=riga.get('codice_materiale', ''),
                    descrizione=descrizione,
                    quantita=child_quantita,
                    prezzo_netto=child_prezzo,
                    valore_netto=child_valore_calcolato,
                    aliquota_iva=float(riga.get('aliquota_iva', 10) or 10),
                    n_riga_originale=ctx.contatore_righe + 1,
                    is_espositore_vuoto=is_espositore_vuoto,
                )
                ctx.espositore_attivo.aggiungi_child(child)

                # Logica chiusura differenziata per vendor
                should_close = False
                if vendor.upper() == 'MENARINI':
                    # MENARINI: chiudi quando somma netto child >= netto parent
                    if menarini_netto_parent > 0:
                        diff = ctx.espositore_attivo.valore_netto_accumulato - menarini_netto_parent
                        tolleranza = menarini_netto_parent * 0.05  # 5% di tolleranza
                        if diff >= -tolleranza:
                            should_close = True

                    # Fallback - se abbiamo pezzi_per_unita e li abbiamo raggiunti
                    if not should_close and ctx.espositore_attivo.pezzi_per_unita:
                        pezzi_attesi = ctx.espositore_attivo.pezzi_per_unita * ctx.espositore_attivo.quantita_parent
                        if ctx.espositore_attivo.pezzi_accumulati >= pezzi_attesi:
                            should_close = True

                    # Safety - se abbiamo già molti child (>20) e il valore è vicino (entro 20%)
                    if not should_close and len(ctx.espositore_attivo.righe_child) > 20:
                        if menarini_netto_parent > 0:
                            ratio = ctx.espositore_attivo.valore_netto_accumulato / menarini_netto_parent
                            if ratio >= 0.80:  # Almeno 80% del valore
                                should_close = True
                else:
                    # ANGELINI e altri: chiudi quando pezzi accumulati >= pezzi attesi
                    if ctx.espositore_attivo.pezzi_accumulati >= ctx.espositore_attivo.pezzi_attesi_totali:
                        should_close = True

                if should_close:
                    ctx.contatore_righe += 1
                    riga_out, righe_child, anomalia = _chiudi_espositore_normale(
                        ctx.espositore_attivo, ctx.contatore_righe, ctx.vendor
                    )
                    ctx.righe_output.append(riga_out)
                    ctx.righe_output.extend(righe_child)
                    if anomalia:
                        ctx.anomalie.append(anomalia)
                    ctx.espositore_attivo = None
                    ctx.chiusure_normali += 1
                    menarini_netto_parent = 0.0
                continue

            ctx.contatore_righe += 1
            riga_output = _crea_riga_output(riga, ctx.contatore_righe, tipo)
            riga_output['richiede_supervisione'] = False
            ctx.righe_output.append(riga_output)
            continue

    # Fine documento: chiudi espositore residuo
    if ctx.espositore_attivo:
        ctx.contatore_righe += 1
        motivo = 'SENZA_CHILD' if len(ctx.espositore_attivo.righe_child) == 0 else 'FINE_DOCUMENTO'
        riga_out, righe_child, anomalia = _chiudi_espositore_forzato(
            ctx.espositore_attivo, ctx.contatore_righe, motivo, ctx.vendor
        )
        ctx.righe_output.append(riga_out)
        ctx.righe_output.extend(righe_child)
        if anomalia:
            ctx.anomalie.append(anomalia)
        ctx.chiusure_forzate += 1
        ctx.espositore_attivo = None

    return ctx


def _chiudi_espositore(
    esp: Espositore,
    n_riga: int,
    vendor: str,
    forzato: bool = False,
    motivo: str = ''
) -> Tuple[Dict, List[Dict], Optional[Dict]]:
    """
    Chiude espositore (unificata normale + forzato).
    """
    prezzo_calcolato = esp.calcola_prezzo_netto_parent()
    fascia, scostamento_pct = esp.verifica_scostamento()

    # Richiede supervisione: sempre se forzato, altrimenti solo per fasce critiche
    richiede_supervisione = True if forzato or fascia in FASCE_SUPERVISIONE_OBBLIGATORIA else False

    # Riga parent output
    riga_output = {
        'n_riga': n_riga,
        'codice_aic': esp.codice_aic,
        'codice_originale': esp.codice_originale,
        'codice_materiale': esp.codice_materiale,
        'descrizione': esp.descrizione,
        'q_venduta': esp.quantita_parent,
        'q_omaggio': 0,
        'q_sconto_merce': 0,
        'prezzo_netto': prezzo_calcolato,
        'prezzo_pubblico': 0,
        'aliquota_iva': esp.aliquota_iva,
        'valore_netto': esp.valore_netto_accumulato,
        'is_espositore': 1,
        'is_child': 0,
        'tipo_riga': 'PARENT_ESPOSITORE',
        'espositore_metadata': esp.genera_metadata_json('FORZATA' if forzato else 'NORMALE', motivo),
        'richiede_supervisione': richiede_supervisione,
        'stato_riga': 'ESTRATTO',
        '_id_parent_placeholder': True,
    }

    # Genera righe child (logica unificata)
    righe_child = _genera_righe_child(esp, n_riga)

    # Genera anomalia se necessario
    anomalia = _genera_anomalia_espositore(
        esp, fascia, scostamento_pct, vendor,
        forzato, motivo, richiede_supervisione
    )

    return riga_output, righe_child, anomalia


def _genera_righe_child(esp: Espositore, n_riga: int) -> List[Dict]:
    """Genera righe child per un espositore."""
    righe_child = []
    for idx, child in enumerate(esp.righe_child):
        child_valore = child.prezzo_netto * child.quantita
        righe_child.append({
            'n_riga': n_riga + 0.001 * (idx + 1),
            'codice_aic': child.codice_aic,
            'codice_originale': child.codice_originale,
            'codice_materiale': child.codice_materiale,
            'descrizione': child.descrizione,
            'q_venduta': child.quantita,
            'q_omaggio': 0,
            'q_sconto_merce': 0,
            'prezzo_netto': child.prezzo_netto,
            'prezzo_pubblico': 0,
            'aliquota_iva': child.aliquota_iva,
            'valore_netto': child_valore,
            'is_espositore': 0,
            'is_child': 1,
            'tipo_riga': 'CHILD_ESPOSITORE',
            'richiede_supervisione': False,
            'stato_riga': 'ESTRATTO',
            '_belongs_to_parent': True,
        })
    return righe_child


def _genera_anomalia_espositore(
    esp: Espositore,
    fascia: str,
    scostamento_pct: float,
    vendor: str,
    forzato: bool,
    motivo: str,
    richiede_supervisione: bool
) -> Optional[Dict]:
    """Genera anomalia per espositore se necessario."""
    # Prima di generare anomalia, verifica se esiste pattern ordinario
    if not forzato or fascia not in FASCE_SUPERVISIONE_OBBLIGATORIA:
        try:
            from ..ml_pattern_matching import verifica_pattern_ordinario_per_espositore

            child_estratti = [
                {
                    'aic': c.codice_aic,
                    'codice': c.codice_originale,
                    'quantita': c.quantita
                }
                for c in esp.righe_child
            ]

            is_ordinario, similarity = verifica_pattern_ordinario_per_espositore(
                vendor=vendor,
                codice_espositore=esp.codice_originale,
                descrizione_espositore=esp.descrizione,
                child_estratti=child_estratti
            )

            if is_ordinario and similarity and similarity >= 80:
                return None

        except Exception:
            pass

    # Determina se serve anomalia e quale codice
    if forzato:
        if motivo == 'SENZA_CHILD' or len(esp.righe_child) == 0:
            codice_anom = 'ESP-A03'
        elif motivo == 'NUOVO_PARENT':
            codice_anom = 'ESP-A04'
        elif motivo == 'RIGA_NON_CHILD':
            codice_anom = 'ESP-A07'
        else:
            codice_anom = 'ESP-A05'
        livello = 'ERRORE'
        pattern_suffix = motivo
        desc_extra = ''
    elif esp.pezzi_accumulati != esp.pezzi_attesi_totali:
        codice_anom = 'ESP-A01' if esp.pezzi_accumulati < esp.pezzi_attesi_totali else 'ESP-A02'
        livello = 'ERRORE' if fascia in FASCE_SUPERVISIONE_OBBLIGATORIA else 'ATTENZIONE'
        pattern_suffix = fascia
        desc_extra = f' ({scostamento_pct:+.1f}%)'
    else:
        return None

    # Genera descrizione child per supervisione
    child_desc_parts = []
    for c in esp.righe_child[:5]:
        desc_short = c.descrizione[:15] if c.descrizione else c.codice_originale
        child_desc_parts.append(f"{c.codice_originale} {desc_short} x{c.quantita}")
    child_desc = ", ".join(child_desc_parts)
    if len(esp.righe_child) > 5:
        child_desc += f" (+{len(esp.righe_child) - 5} altri)"

    descrizione_base = f"{CODICI_ANOMALIA[codice_anom]}: attesi {esp.pezzi_attesi_totali}, trovati {esp.pezzi_accumulati}{desc_extra}"
    if child_desc:
        descrizione_completa = f"{descrizione_base}\nChild: {child_desc}"
    else:
        descrizione_completa = descrizione_base

    return {
        'tipo_anomalia': 'ESPOSITORE',
        'livello': livello,
        'codice_anomalia': codice_anom,
        'descrizione': descrizione_completa,
        'valore_anomalo': f"{esp.codice_originale}: {esp.descrizione}",
        'richiede_supervisione': richiede_supervisione,
        'espositore_codice': esp.codice_originale,
        'espositore_descrizione': esp.descrizione,
        'pezzi_attesi': esp.pezzi_attesi_totali,
        'pezzi_trovati': esp.pezzi_accumulati,
        'valore_netto_child': round(esp.valore_netto_accumulato, 2),
        'fascia_scostamento': fascia,
        'motivo_chiusura': motivo if forzato else '',
        'pattern_signature': f"{vendor}_{codice_anom}_{esp.codice_originale}_{pattern_suffix}",
        'child_dettaglio': [
            {'codice': c.codice_originale, 'descrizione': c.descrizione[:20], 'quantita': c.quantita}
            for c in esp.righe_child
        ],
    }


def _chiudi_espositore_normale(esp: Espositore, n_riga: int, vendor: str) -> Tuple[Dict, List[Dict], Optional[Dict]]:
    """Wrapper compatibilità: chiusura normale."""
    return _chiudi_espositore(esp, n_riga, vendor, forzato=False)


def _chiudi_espositore_forzato(esp: Espositore, n_riga: int, motivo: str, vendor: str) -> Tuple[Dict, List[Dict], Dict]:
    """Wrapper compatibilità: chiusura forzata."""
    return _chiudi_espositore(esp, n_riga, vendor, forzato=True, motivo=motivo)


def _crea_riga_output(riga: Dict, n_riga: int, tipo_riga: str) -> Dict:
    """Crea riga output formattata."""
    return {
        'n_riga': n_riga,
        'codice_aic': riga.get('codice_aic', ''),
        'codice_originale': riga.get('codice_originale', ''),
        'codice_materiale': riga.get('codice_materiale', ''),
        'descrizione': riga.get('descrizione', ''),
        'tipo_posizione': riga.get('tipo_posizione', ''),
        'q_venduta': int(riga.get('quantita', 0) or 0),
        'q_omaggio': 0,
        'q_sconto_merce': 0,
        'prezzo_listino': float(riga.get('prezzo_listino', 0) or 0),
        'prezzo_netto': float(riga.get('prezzo_netto', 0) or 0),
        'prezzo_pubblico': float(riga.get('prezzo_pubblico', 0) or 0),
        'sconto_1': float(riga.get('sconto_pct', 0) or 0),
        'aliquota_iva': float(riga.get('aliquota_iva', 10) or 10),
        'valore_netto': float(riga.get('valore_netto', 0) or 0),
        'is_espositore': 0,
        'is_child': 0,
        'tipo_riga': tipo_riga,
        'richiede_supervisione': False,
        'stato_riga': 'ESTRATTO',
    }


def valuta_espositori_con_ml(
    ctx: ContestoElaborazione,
    id_testata: int,
    vendor: str
) -> ContestoElaborazione:
    """
    Valuta espositori elaborati con sistema ML.

    Chiamata dopo elabora_righe_ordine() per confrontare ogni espositore
    con i pattern appresi.
    """
    from ..ml_pattern_matching import valuta_espositore_con_ml as ml_valuta

    # Verifica se ci sono anomalie espositore da valutare
    anomalie_espositore = [
        a for a in ctx.anomalie
        if a.get('tipo_anomalia') == 'ESPOSITORE'
        and a.get('codice_anomalia') in ('ESP-A01', 'ESP-A02', 'ESP-A03', 'ESP-A04', 'ESP-A05')
    ]

    if not anomalie_espositore:
        return ctx

    # Per ogni anomalia, cerca pattern ML
    for anomalia in anomalie_espositore:
        codice_esp = anomalia.get('espositore_codice', '')
        if not codice_esp:
            continue

        # Trova la riga parent corrispondente
        parent_row = next(
            (r for r in ctx.righe_output
             if r.get('codice_originale') == codice_esp
             and r.get('is_espositore') == 1),
            None
        )

        if not parent_row:
            continue

        # Trova i child di questo parent
        child_rows = [
            r for r in ctx.righe_output
            if r.get('_belongs_to_parent')
            and r.get('is_child') == 1
        ]

        # Prepara lista child per confronto ML
        child_estratti = [
            {
                'aic': r.get('codice_aic', ''),
                'codice': r.get('codice_originale', ''),
                'descrizione': r.get('descrizione', ''),
                'quantita': r.get('q_venduta', 0)
            }
            for r in child_rows
        ]

        # Valuta con ML
        decision, anomalia_ml = ml_valuta(
            id_testata=id_testata,
            id_dettaglio=0,
            vendor=vendor,
            codice_espositore=codice_esp,
            descrizione_espositore=parent_row.get('descrizione', ''),
            child_estratti=child_estratti
        )

        # Gestisci decisione ML
        if decision == 'APPLY_ML':
            anomalia['ml_decision'] = 'APPLY_ML'
            anomalia['richiede_supervisione'] = False
            anomalia['livello'] = 'INFO'
            anomalia['descrizione'] += ' [ML: pattern applicato automaticamente]'

        elif decision == 'APPLY_WARNING':
            anomalia['ml_decision'] = 'APPLY_WARNING'
            anomalia['richiede_supervisione'] = False
            anomalia['livello'] = 'ATTENZIONE'
            anomalia['descrizione'] += ' [ML: pattern applicato con warning]'

        elif decision == 'SEND_SUPERVISION' and anomalia_ml:
            ctx.anomalie.append(anomalia_ml)
            anomalia['ml_decision'] = 'SEND_SUPERVISION'
            anomalia['descrizione'] += ' [ML: conflitto rilevato]'

    return ctx
