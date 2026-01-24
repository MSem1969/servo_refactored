# =============================================================================
# SERV.O v11.0 - UNIFIED AIC SERVICE
# =============================================================================
# Servizio UNICO per tutte le operazioni su codice AIC:
# - Validazione e normalizzazione
# - Propagazione gerarchica (ORDINE, GLOBALE)
# - Creazione/Approvazione/Rifiuto supervisioni
# - Pattern ML
# - Correzione errori
#
# REFACTORING v11: Questo file sostituisce la logica duplicata presente in:
# - services/supervision/propagazione_aic.py (mantenuto per retrocompatibilità)
# - services/supervision/aic.py (logica spostata qui)
# =============================================================================

import re
import hashlib
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from ...database_pg import get_db, log_operation, log_modifica
from .constants import SOGLIA_PROMOZIONE


# =============================================================================
# ENUMS E DATA CLASSES
# =============================================================================

class LivelloPropagazione(str, Enum):
    """Livelli di propagazione AIC."""
    ORDINE = 'ORDINE'      # Tutte le righe dell'ordine con stessa descrizione
    GLOBALE = 'GLOBALE'    # Tutte le anomalie aperte stesso vendor con stessa descrizione


@dataclass
class PropagationResult:
    """Risultato di una propagazione AIC."""
    success: bool
    righe_aggiornate: int = 0
    ordini_coinvolti: List[int] = None
    descrizione_normalizzata: str = ''
    codice_aic: str = ''
    livello: str = ''
    error: str = ''

    def __post_init__(self):
        if self.ordini_coinvolti is None:
            self.ordini_coinvolti = []

    def to_dict(self) -> Dict:
        return {
            'success': self.success,
            'righe_aggiornate': self.righe_aggiornate,
            'ordini_coinvolti': self.ordini_coinvolti,
            'descrizione_normalizzata': self.descrizione_normalizzata,
            'codice_aic': self.codice_aic,
            'livello': self.livello,
            'error': self.error
        }


@dataclass
class ResolutionResult(PropagationResult):
    """Risultato di una risoluzione anomalia/supervisione."""
    anomalia_risolta: bool = False
    id_anomalia: int = None
    supervisioni_approvate: int = 0
    ml_pattern_incrementato: bool = False

    def to_dict(self) -> Dict:
        result = super().to_dict()
        result.update({
            'anomalia_risolta': self.anomalia_risolta,
            'id_anomalia': self.id_anomalia,
            'supervisioni_approvate': self.supervisioni_approvate,
            'ml_pattern_incrementato': self.ml_pattern_incrementato
        })
        return result


# =============================================================================
# VALIDAZIONE E NORMALIZZAZIONE
# =============================================================================

def valida_codice_aic(codice_aic: str) -> Tuple[bool, str]:
    """
    Valida formato codice AIC.

    Args:
        codice_aic: Codice da validare

    Returns:
        (valido, messaggio_o_codice_pulito)
        - Se valido: (True, codice_pulito)
        - Se non valido: (False, messaggio_errore)
    """
    if not codice_aic:
        return False, "Codice AIC mancante"

    codice = str(codice_aic).strip()

    if not codice.isdigit():
        return False, "Codice AIC deve contenere solo cifre"

    if len(codice) != 9:
        return False, f"Codice AIC deve essere di 9 cifre (ricevuto: {len(codice)})"

    return True, codice


def normalizza_descrizione(descrizione: str) -> str:
    """
    Normalizza descrizione per matching.
    - Uppercase
    - Rimuovi spazi multipli
    - Rimuovi caratteri speciali
    - Tronca a 50 caratteri
    """
    if not descrizione:
        return ''
    desc = ' '.join(str(descrizione).upper().split())
    desc = re.sub(r'[^\w\s]', '', desc)
    return desc[:50]


def calcola_pattern_signature(vendor: str, descrizione: str) -> str:
    """
    Calcola signature univoca per pattern AIC.
    Pattern: VENDOR|DESCRIZIONE_NORMALIZZATA

    Args:
        vendor: Codice vendor (es. MENARINI)
        descrizione: Descrizione prodotto

    Returns:
        Hash MD5 troncato a 16 caratteri
    """
    desc_norm = normalizza_descrizione(descrizione)
    raw = f"{vendor or 'UNKNOWN'}|{desc_norm}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


# =============================================================================
# AIC PROPAGATOR - CLASSE PRINCIPALE
# =============================================================================

class AICPropagator:
    """
    Classe unificata per tutte le propagazioni AIC.

    Entry point unico per:
    - Propagazione da anomalia (/anomalie/{id}/correggi-aic)
    - Propagazione da supervisione (/supervisione/aic/{id}/risolvi)
    - Propagazione bulk (/supervisione/aic/pattern/{sig}/approva-bulk)
    """

    def __init__(self):
        self.db = get_db()

    def propaga(
        self,
        id_dettaglio: int,
        codice_aic: str,
        livello: LivelloPropagazione,
        operatore: str,
        note: str = None
    ) -> PropagationResult:
        """
        Entry point unico per propagazione AIC.

        Args:
            id_dettaglio: ID riga origine
            codice_aic: Codice AIC corretto (9 cifre)
            livello: Livello di propagazione (ORDINE, GLOBALE)
            operatore: Username operatore
            note: Note opzionali

        Returns:
            PropagationResult con dettagli operazione
        """
        # Valida AIC
        valido, result = valida_codice_aic(codice_aic)
        if not valido:
            return PropagationResult(success=False, error=result)

        codice_aic = result  # Codice pulito

        # Recupera dati riga origine con vendor
        riga = self.db.execute("""
            SELECT od.id_dettaglio, od.id_testata, od.descrizione, od.codice_aic AS aic_precedente,
                   ot.numero_ordine_vendor, ot.id_vendor
            FROM ordini_dettaglio od
            JOIN ordini_testata ot ON od.id_testata = ot.id_testata
            WHERE od.id_dettaglio = %s
        """, (id_dettaglio,)).fetchone()

        if not riga:
            return PropagationResult(success=False, error=f"Riga {id_dettaglio} non trovata")

        desc_norm = normalizza_descrizione(riga['descrizione'])
        id_testata = riga['id_testata']
        id_vendor = riga['id_vendor']
        aic_precedente = riga['aic_precedente']

        try:
            if livello == LivelloPropagazione.ORDINE:
                righe_aggiornate, ordini = self._aggiorna_righe_ordine(
                    id_testata, desc_norm, codice_aic, operatore
                )
            elif livello == LivelloPropagazione.GLOBALE:
                righe_aggiornate, ordini = self._aggiorna_righe_globale(
                    desc_norm, codice_aic, operatore, id_vendor
                )
            else:
                righe_aggiornate, ordini = 0, []

            self.db.commit()

            # Log operazione
            log_operation(
                'PROPAGA_AIC',
                'ORDINI_DETTAGLIO',
                id_dettaglio,
                f"AIC {codice_aic} propagato ({livello.value}): {righe_aggiornate} righe, "
                f"{len(ordini)} ordini. Operatore: {operatore}",
                dati={
                    'codice_aic': codice_aic,
                    'aic_precedente': aic_precedente,
                    'livello': livello.value,
                    'descrizione_normalizzata': desc_norm,
                    'righe_aggiornate': righe_aggiornate,
                },
                operatore=operatore
            )

            return PropagationResult(
                success=True,
                righe_aggiornate=righe_aggiornate,
                ordini_coinvolti=list(ordini),
                descrizione_normalizzata=desc_norm,
                codice_aic=codice_aic,
                livello=livello.value
            )

        except Exception as e:
            self.db.rollback()
            return PropagationResult(success=False, error=str(e))

    def risolvi_da_anomalia(
        self,
        id_anomalia: int,
        codice_aic: str,
        livello: LivelloPropagazione,
        operatore: str,
        note: str = None
    ) -> ResolutionResult:
        """
        Risolve anomalia AIC con propagazione.

        Effetti:
        1. Propaga codice AIC secondo livello
        2. Marca anomalia come RISOLTA
        3. Chiude anomalie correlate secondo livello
        4. Aggiorna supervisioni collegate
        5. Incrementa pattern ML

        Args:
            id_anomalia: ID anomalia
            codice_aic: Codice AIC corretto
            livello: Livello propagazione
            operatore: Username operatore
            note: Note opzionali

        Returns:
            ResolutionResult con dettagli operazione
        """
        # Recupera anomalia
        anomalia = self.db.execute("""
            SELECT a.id_anomalia, a.id_testata, a.id_dettaglio, a.codice_anomalia,
                   a.stato, a.valore_anomalo, od.descrizione
            FROM anomalie a
            LEFT JOIN ordini_dettaglio od ON a.id_dettaglio = od.id_dettaglio
            WHERE a.id_anomalia = %s
        """, (id_anomalia,)).fetchone()

        if not anomalia:
            return ResolutionResult(success=False, error=f"Anomalia {id_anomalia} non trovata")

        if anomalia['stato'] == 'RISOLTA':
            return ResolutionResult(success=False, error="Anomalia già risolta")

        id_dettaglio = anomalia['id_dettaglio']
        if not id_dettaglio:
            return ResolutionResult(success=False, error="Anomalia non collegata a una riga specifica")

        # Propaga AIC
        prop_result = self.propaga(
            id_dettaglio=id_dettaglio,
            codice_aic=codice_aic,
            livello=livello,
            operatore=operatore,
            note=note
        )

        if not prop_result.success:
            return ResolutionResult(
                success=False,
                error=prop_result.error
            )

        # Marca anomalia come RISOLTA
        self.db.execute("""
            UPDATE anomalie
            SET stato = 'RISOLTA',
                data_risoluzione = CURRENT_TIMESTAMP,
                note_risoluzione = %s
            WHERE id_anomalia = %s
        """, (
            f"AIC corretto: {codice_aic} ({livello.value}). {note or ''}".strip(),
            id_anomalia
        ))

        # Chiudi anomalie correlate
        anomalie_chiuse = self._chiudi_anomalie_correlate(
            anomalia, codice_aic, livello, prop_result.descrizione_normalizzata, operatore
        )

        # Aggiorna supervisioni e ML
        sup_approvate, ml_incrementato = self._aggiorna_supervisioni_e_ml(
            anomalia, codice_aic, operatore, livello, prop_result.descrizione_normalizzata
        )

        self.db.commit()

        return ResolutionResult(
            success=True,
            righe_aggiornate=prop_result.righe_aggiornate,
            ordini_coinvolti=prop_result.ordini_coinvolti,
            descrizione_normalizzata=prop_result.descrizione_normalizzata,
            codice_aic=codice_aic,
            livello=livello.value,
            anomalia_risolta=True,
            id_anomalia=id_anomalia,
            supervisioni_approvate=sup_approvate,
            ml_pattern_incrementato=ml_incrementato
        )

    def risolvi_da_supervisione(
        self,
        id_supervisione: int,
        codice_aic: str,
        livello: LivelloPropagazione,
        operatore: str,
        note: str = None
    ) -> ResolutionResult:
        """
        Risolve supervisione AIC con propagazione.

        Args:
            id_supervisione: ID supervisione
            codice_aic: Codice AIC assegnato
            livello: Livello propagazione
            operatore: Username operatore
            note: Note opzionali

        Returns:
            ResolutionResult con dettagli operazione
        """
        # Valida AIC
        valido, result = valida_codice_aic(codice_aic)
        if not valido:
            return ResolutionResult(success=False, error=result)
        codice_aic = result

        # Recupera supervisione
        sup = self.db.execute("""
            SELECT id_supervisione, id_testata, id_dettaglio, id_anomalia,
                   pattern_signature, vendor, descrizione_normalizzata, stato
            FROM supervisione_aic
            WHERE id_supervisione = %s
        """, (id_supervisione,)).fetchone()

        if not sup:
            return ResolutionResult(success=False, error=f"Supervisione AIC {id_supervisione} non trovata")

        if sup['stato'] != 'PENDING':
            return ResolutionResult(success=False, error="Supervisione non in stato PENDING")

        righe_aggiornate = 0
        ordini_coinvolti = set()

        # Aggiorna supervisione
        self.db.execute("""
            UPDATE supervisione_aic
            SET stato = 'APPROVED',
                operatore = %s,
                timestamp_decisione = CURRENT_TIMESTAMP,
                note = %s,
                codice_aic_assegnato = %s
            WHERE id_supervisione = %s
        """, (operatore, note, codice_aic, id_supervisione))

        # Aggiorna riga specifica
        if sup['id_dettaglio']:
            self._aggiorna_riga_singola(sup['id_dettaglio'], codice_aic, operatore)
            righe_aggiornate += 1
            ordini_coinvolti.add(sup['id_testata'])

        # Propagazione
        if livello == LivelloPropagazione.ORDINE:
            count, orders = self._aggiorna_righe_ordine(
                sup['id_testata'],
                sup['descrizione_normalizzata'],
                codice_aic,
                operatore,
                exclude_dettaglio=sup['id_dettaglio']
            )
            righe_aggiornate += count
            ordini_coinvolti.update(orders)

        elif livello == LivelloPropagazione.GLOBALE:
            # Recupera id_vendor
            vendor_row = self.db.execute("""
                SELECT id_vendor FROM ordini_testata WHERE id_testata = %s
            """, (sup['id_testata'],)).fetchone()

            if vendor_row:
                count, orders = self._aggiorna_righe_globale(
                    sup['descrizione_normalizzata'],
                    codice_aic,
                    operatore,
                    vendor_row['id_vendor'],
                    exclude_dettaglio=sup['id_dettaglio']
                )
                righe_aggiornate += count
                ordini_coinvolti.update(orders)

                # Approva altre supervisioni con stesso pattern
                altre_sup = self.db.execute("""
                    UPDATE supervisione_aic
                    SET stato = 'APPROVED',
                        operatore = %s,
                        timestamp_decisione = CURRENT_TIMESTAMP,
                        note = %s,
                        codice_aic_assegnato = %s
                    WHERE pattern_signature = %s
                      AND stato = 'PENDING'
                      AND id_supervisione != %s
                    RETURNING id_supervisione, id_testata
                """, (
                    operatore,
                    f"Auto-approvato da pattern {sup['pattern_signature']}",
                    codice_aic,
                    sup['pattern_signature'],
                    id_supervisione
                )).fetchall()

                for row in altre_sup:
                    ordini_coinvolti.add(row['id_testata'])

        # Chiudi anomalie correlate
        for id_testata in ordini_coinvolti:
            self.db.execute("""
                UPDATE anomalie
                SET stato = 'RISOLTA',
                    data_risoluzione = CURRENT_TIMESTAMP,
                    note_risoluzione = %s
                WHERE id_testata = %s
                  AND codice_anomalia = 'AIC-A01'
                  AND stato IN ('APERTA', 'ERRORE', 'ATTENZIONE', 'INFO')
            """, (f"AIC assegnato: {codice_aic}", id_testata))

        # Aggiorna pattern ML
        ml_incrementato = self._registra_approvazione_pattern(
            sup['pattern_signature'], operatore, codice_aic
        )

        self.db.commit()

        # Sblocca ordini
        from .requests import sblocca_ordine_se_completo
        for id_testata in ordini_coinvolti:
            sblocca_ordine_se_completo(id_testata)

        return ResolutionResult(
            success=True,
            righe_aggiornate=righe_aggiornate,
            ordini_coinvolti=list(ordini_coinvolti),
            descrizione_normalizzata=sup['descrizione_normalizzata'],
            codice_aic=codice_aic,
            livello=livello.value,
            anomalia_risolta=True,
            supervisioni_approvate=len(altre_sup) + 1 if livello == LivelloPropagazione.GLOBALE else 1,
            ml_pattern_incrementato=ml_incrementato
        )

    def approva_bulk_pattern(
        self,
        pattern_signature: str,
        codice_aic: str,
        operatore: str,
        note: str = None
    ) -> ResolutionResult:
        """
        Approva TUTTE le supervisioni AIC pending con un dato pattern.

        Args:
            pattern_signature: Signature del pattern
            codice_aic: Codice AIC da assegnare
            operatore: Username operatore
            note: Note opzionali

        Returns:
            ResolutionResult con dettagli operazione
        """
        # Valida AIC
        valido, result = valida_codice_aic(codice_aic)
        if not valido:
            return ResolutionResult(success=False, error=result)
        codice_aic = result

        # Trova supervisioni pending
        rows = self.db.execute("""
            SELECT id_supervisione, id_testata, id_dettaglio
            FROM supervisione_aic
            WHERE pattern_signature = %s AND stato = 'PENDING'
        """, (pattern_signature,)).fetchall()

        if not rows:
            return ResolutionResult(
                success=False,
                error=f"Nessuna supervisione AIC pending per pattern {pattern_signature}"
            )

        supervisioni_approvate = 0
        ordini_coinvolti = set()
        righe_aggiornate = 0

        for row in rows:
            # Aggiorna supervisione
            self.db.execute("""
                UPDATE supervisione_aic
                SET stato = 'APPROVED',
                    operatore = %s,
                    timestamp_decisione = CURRENT_TIMESTAMP,
                    codice_aic_assegnato = %s,
                    note = %s
                WHERE id_supervisione = %s
            """, (operatore, codice_aic, f"[BULK] {note or ''}", row['id_supervisione']))

            # Aggiorna riga ordine
            if row['id_dettaglio']:
                self._aggiorna_riga_singola(row['id_dettaglio'], codice_aic, operatore, 'BULK_APPROVAL')
                righe_aggiornate += 1

            supervisioni_approvate += 1
            ordini_coinvolti.add(row['id_testata'])

            # Chiudi anomalie correlate
            self.db.execute("""
                UPDATE anomalie
                SET stato = 'RISOLTA',
                    data_risoluzione = CURRENT_TIMESTAMP,
                    note_risoluzione = %s
                WHERE id_testata = %s
                  AND codice_anomalia = 'AIC-A01'
                  AND stato IN ('APERTA', 'ERRORE', 'ATTENZIONE', 'INFO')
            """, (f"AIC assegnato: {codice_aic} [BULK]", row['id_testata']))

        # Incrementa pattern ML UNA SOLA VOLTA
        ml_incrementato = self._registra_approvazione_pattern(pattern_signature, operatore, codice_aic)

        self.db.commit()

        # Sblocca ordini
        from .requests import sblocca_ordine_se_completo
        for id_testata in ordini_coinvolti:
            sblocca_ordine_se_completo(id_testata)

        return ResolutionResult(
            success=True,
            righe_aggiornate=righe_aggiornate,
            ordini_coinvolti=list(ordini_coinvolti),
            codice_aic=codice_aic,
            livello='BULK',
            supervisioni_approvate=supervisioni_approvate,
            ml_pattern_incrementato=ml_incrementato
        )

    # =========================================================================
    # METODI PRIVATI
    # =========================================================================

    def _aggiorna_riga_singola(
        self,
        id_dettaglio: int,
        codice_aic: str,
        operatore: str,
        fonte: str = 'PROPAGAZIONE_AIC'
    ) -> int:
        """Aggiorna singola riga con audit trail."""
        row = self.db.execute("""
            SELECT codice_aic, id_testata FROM ordini_dettaglio WHERE id_dettaglio = %s
        """, (id_dettaglio,)).fetchone()

        if not row:
            return 0

        aic_precedente = row['codice_aic']
        id_testata = row['id_testata']

        self.db.execute("""
            UPDATE ordini_dettaglio SET codice_aic = %s WHERE id_dettaglio = %s
        """, (codice_aic, id_dettaglio))

        log_modifica(
            entita='ORDINI_DETTAGLIO',
            id_entita=id_dettaglio,
            campo_modificato='codice_aic',
            valore_precedente=aic_precedente,
            valore_nuovo=codice_aic,
            fonte_modifica=fonte,
            id_testata=id_testata,
            username_operatore=operatore
        )

        return 1

    def _aggiorna_righe_ordine(
        self,
        id_testata: int,
        desc_norm: str,
        codice_aic: str,
        operatore: str,
        fonte: str = 'PROPAGAZIONE_AIC_ORDINE',
        exclude_dettaglio: int = None
    ) -> Tuple[int, List[int]]:
        """
        Aggiorna righe dell'ordine con stessa descrizione normalizzata.
        Solo righe con anomalie AIC aperte.
        """
        query = """
            SELECT DISTINCT od.id_dettaglio, od.codice_aic
            FROM ordini_dettaglio od
            JOIN anomalie a ON a.id_dettaglio = od.id_dettaglio
            WHERE od.id_testata = %s
              AND UPPER(REGEXP_REPLACE(LEFT(od.descrizione, 50), '[^\\w\\s]', '', 'g')) = %s
              AND (od.codice_aic IS NULL OR od.codice_aic = '' OR od.codice_aic != %s)
              AND a.codice_anomalia = 'AIC-A01'
              AND a.stato IN ('APERTA', 'ERRORE', 'ATTENZIONE', 'INFO')
        """
        params = [id_testata, desc_norm, codice_aic]

        if exclude_dettaglio:
            query += " AND od.id_dettaglio != %s"
            params.append(exclude_dettaglio)

        righe = self.db.execute(query, params).fetchall()

        if not righe:
            return 0, []

        for riga in righe:
            self.db.execute("""
                UPDATE ordini_dettaglio SET codice_aic = %s WHERE id_dettaglio = %s
            """, (codice_aic, riga['id_dettaglio']))

            log_modifica(
                entita='ORDINI_DETTAGLIO',
                id_entita=riga['id_dettaglio'],
                campo_modificato='codice_aic',
                valore_precedente=riga['codice_aic'],
                valore_nuovo=codice_aic,
                fonte_modifica=fonte,
                id_testata=id_testata,
                username_operatore=operatore
            )

        return len(righe), [id_testata]

    def _aggiorna_righe_globale(
        self,
        desc_norm: str,
        codice_aic: str,
        operatore: str,
        id_vendor: int,
        fonte: str = 'PROPAGAZIONE_AIC_GLOBALE',
        exclude_dettaglio: int = None
    ) -> Tuple[int, List[int]]:
        """
        Aggiorna righe stesso vendor con stessa descrizione normalizzata.
        Solo righe con anomalie AIC aperte.
        """
        if not id_vendor:
            return 0, []

        query = """
            SELECT DISTINCT od.id_dettaglio, od.id_testata, od.codice_aic
            FROM ordini_dettaglio od
            JOIN ordini_testata ot ON od.id_testata = ot.id_testata
            JOIN anomalie a ON a.id_dettaglio = od.id_dettaglio
            WHERE ot.id_vendor = %s
              AND UPPER(REGEXP_REPLACE(LEFT(od.descrizione, 50), '[^\\w\\s]', '', 'g')) = %s
              AND (od.codice_aic IS NULL OR od.codice_aic = '' OR od.codice_aic != %s)
              AND a.codice_anomalia = 'AIC-A01'
              AND a.stato IN ('APERTA', 'ERRORE', 'ATTENZIONE', 'INFO')
        """
        params = [id_vendor, desc_norm, codice_aic]

        if exclude_dettaglio:
            query += " AND od.id_dettaglio != %s"
            params.append(exclude_dettaglio)

        righe = self.db.execute(query, params).fetchall()

        if not righe:
            return 0, []

        ordini_coinvolti = set()

        for riga in righe:
            self.db.execute("""
                UPDATE ordini_dettaglio SET codice_aic = %s WHERE id_dettaglio = %s
            """, (codice_aic, riga['id_dettaglio']))

            log_modifica(
                entita='ORDINI_DETTAGLIO',
                id_entita=riga['id_dettaglio'],
                campo_modificato='codice_aic',
                valore_precedente=riga['codice_aic'],
                valore_nuovo=codice_aic,
                fonte_modifica=fonte,
                id_testata=riga['id_testata'],
                username_operatore=operatore
            )

            ordini_coinvolti.add(riga['id_testata'])

        return len(righe), list(ordini_coinvolti)

    def _chiudi_anomalie_correlate(
        self,
        anomalia: Dict,
        codice_aic: str,
        livello: LivelloPropagazione,
        desc_norm: str,
        operatore: str
    ) -> int:
        """Chiude anomalie AIC correlate secondo il livello."""
        count = 0

        if livello == LivelloPropagazione.ORDINE:
            result = self.db.execute("""
                UPDATE anomalie a
                SET stato = 'RISOLTA',
                    data_risoluzione = CURRENT_TIMESTAMP,
                    note_risoluzione = %s
                FROM ordini_dettaglio od
                WHERE a.id_dettaglio = od.id_dettaglio
                  AND od.id_testata = %s
                  AND a.codice_anomalia = 'AIC-A01'
                  AND a.stato IN ('APERTA', 'ERRORE', 'ATTENZIONE', 'INFO')
                  AND UPPER(REGEXP_REPLACE(LEFT(od.descrizione, 50), '[^\\w\\s]', '', 'g')) = %s
            """, (
                f"AIC propagato: {codice_aic} [ORDINE da {operatore}]",
                anomalia['id_testata'],
                desc_norm
            ))
            count = result.rowcount if hasattr(result, 'rowcount') else 0

        elif livello == LivelloPropagazione.GLOBALE:
            vendor_row = self.db.execute("""
                SELECT id_vendor FROM ordini_testata WHERE id_testata = %s
            """, (anomalia['id_testata'],)).fetchone()

            if vendor_row:
                result = self.db.execute("""
                    UPDATE anomalie a
                    SET stato = 'RISOLTA',
                        data_risoluzione = CURRENT_TIMESTAMP,
                        note_risoluzione = %s
                    FROM ordini_dettaglio od
                    JOIN ordini_testata ot ON od.id_testata = ot.id_testata
                    WHERE a.id_dettaglio = od.id_dettaglio
                      AND ot.id_vendor = %s
                      AND a.codice_anomalia = 'AIC-A01'
                      AND a.stato IN ('APERTA', 'ERRORE', 'ATTENZIONE', 'INFO')
                      AND UPPER(REGEXP_REPLACE(LEFT(od.descrizione, 50), '[^\\w\\s]', '', 'g')) = %s
                """, (
                    f"AIC propagato: {codice_aic} [GLOBALE da {operatore}]",
                    vendor_row['id_vendor'],
                    desc_norm
                ))
                count = result.rowcount if hasattr(result, 'rowcount') else 0

        return count

    def _aggiorna_supervisioni_e_ml(
        self,
        anomalia: Dict,
        codice_aic: str,
        operatore: str,
        livello: LivelloPropagazione,
        desc_norm: str
    ) -> Tuple[int, bool]:
        """Aggiorna supervisioni collegate e pattern ML."""
        sup_approvate = 0

        # Aggiorna supervisione specifica
        result = self.db.execute("""
            UPDATE supervisione_aic
            SET stato = 'APPROVED',
                operatore = %s,
                timestamp_decisione = CURRENT_TIMESTAMP,
                codice_aic_assegnato = %s,
                note = %s
            WHERE id_anomalia = %s AND stato = 'PENDING'
        """, (operatore, codice_aic, f"Risolto da anomalie ({livello.value})", anomalia['id_anomalia']))
        sup_approvate = result.rowcount if hasattr(result, 'rowcount') else 0

        # Se GLOBALE, aggiorna tutte le supervisioni con stessa descrizione
        if livello == LivelloPropagazione.GLOBALE:
            result = self.db.execute("""
                UPDATE supervisione_aic
                SET stato = 'APPROVED',
                    operatore = %s,
                    timestamp_decisione = CURRENT_TIMESTAMP,
                    codice_aic_assegnato = %s,
                    note = %s
                WHERE descrizione_normalizzata = %s
                  AND stato = 'PENDING'
            """, (operatore, codice_aic, "Auto-approvato da propagazione GLOBALE", desc_norm))
            sup_approvate += result.rowcount if hasattr(result, 'rowcount') else 0

            # Aggiorna pattern ML per ogni vendor coinvolto
            vendors = self.db.execute("""
                SELECT DISTINCT v.codice_vendor
                FROM ordini_dettaglio od
                JOIN ordini_testata ot ON od.id_testata = ot.id_testata
                JOIN vendor v ON ot.id_vendor = v.id_vendor
                WHERE UPPER(REGEXP_REPLACE(LEFT(od.descrizione, 50), '[^\\w\\s]', '', 'g')) = %s
            """, (desc_norm,)).fetchall()

            for v in vendors:
                pattern_sig = calcola_pattern_signature(v['codice_vendor'], desc_norm)
                self._registra_approvazione_pattern(pattern_sig, operatore, codice_aic)

            return sup_approvate, len(vendors) > 0

        return sup_approvate, False

    def _registra_approvazione_pattern(
        self,
        pattern_sig: str,
        operatore: str,
        codice_aic: str
    ) -> bool:
        """
        Registra approvazione nel pattern ML AIC.
        Incrementa contatore e promuove se raggiunge soglia.
        """
        # Assicura che pattern esista
        existing = self.db.execute(
            "SELECT 1 FROM criteri_ordinari_aic WHERE pattern_signature = %s",
            (pattern_sig,)
        ).fetchone()

        if not existing:
            # Crea pattern se non esiste
            self.db.execute("""
                INSERT INTO criteri_ordinari_aic
                (pattern_signature, pattern_descrizione, codice_aic_default)
                VALUES (%s, %s, %s)
            """, (pattern_sig, f"Auto-created pattern", codice_aic))

        # Incrementa contatore
        self.db.execute("""
            UPDATE criteri_ordinari_aic
            SET count_approvazioni = count_approvazioni + 1,
                operatori_approvatori = COALESCE(operatori_approvatori || ',', '') || %s,
                codice_aic_default = COALESCE(codice_aic_default, %s)
            WHERE pattern_signature = %s
        """, (operatore, codice_aic, pattern_sig))

        # Verifica promozione
        pattern = self.db.execute("""
            SELECT count_approvazioni, is_ordinario
            FROM criteri_ordinari_aic
            WHERE pattern_signature = %s
        """, (pattern_sig,)).fetchone()

        if pattern and not pattern['is_ordinario'] and pattern['count_approvazioni'] >= SOGLIA_PROMOZIONE:
            self.db.execute("""
                UPDATE criteri_ordinari_aic
                SET is_ordinario = TRUE,
                    data_promozione = CURRENT_TIMESTAMP
                WHERE pattern_signature = %s
            """, (pattern_sig,))

            log_operation(
                'PROMOZIONE_PATTERN',
                'CRITERI_ORDINARI_AIC',
                0,
                f"Pattern {pattern_sig} promosso a ordinario dopo {SOGLIA_PROMOZIONE} approvazioni"
            )

        return True


# =============================================================================
# FUNZIONI DI UTILITÀ (per retrocompatibilità)
# =============================================================================

def propaga_aic(
    id_dettaglio: int,
    codice_aic: str,
    livello: LivelloPropagazione,
    operatore: str,
    note: str = None
) -> Dict:
    """Wrapper retrocompatibile per AICPropagator.propaga()"""
    return AICPropagator().propaga(
        id_dettaglio, codice_aic, livello, operatore, note
    ).to_dict()


def risolvi_anomalia_aic(
    id_anomalia: int,
    codice_aic: str,
    livello: LivelloPropagazione,
    operatore: str,
    note: str = None
) -> Dict:
    """Wrapper retrocompatibile per AICPropagator.risolvi_da_anomalia()"""
    return AICPropagator().risolvi_da_anomalia(
        id_anomalia, codice_aic, livello, operatore, note
    ).to_dict()


def approva_supervisione_aic(
    id_supervisione: int,
    operatore: str,
    codice_aic: str,
    livello_propagazione: str = 'GLOBALE',
    note: str = None
) -> Dict:
    """Wrapper retrocompatibile per AICPropagator.risolvi_da_supervisione()"""
    livello = LivelloPropagazione(livello_propagazione.upper())
    result = AICPropagator().risolvi_da_supervisione(
        id_supervisione, codice_aic, livello, operatore, note
    )
    # Formato risposta originale
    return {
        'approvata': result.success,
        'righe_aggiornate': result.righe_aggiornate,
        'ordini_coinvolti': result.ordini_coinvolti,
        'codice_aic': result.codice_aic,
        'success': result.success,
        'error': result.error
    }


def approva_bulk_pattern_aic(
    pattern_signature: str,
    codice_aic: str,
    operatore: str,
    note: str = None
) -> Dict:
    """Wrapper per AICPropagator.approva_bulk_pattern()"""
    return AICPropagator().approva_bulk_pattern(
        pattern_signature, codice_aic, operatore, note
    ).to_dict()


# =============================================================================
# CONTATORI
# =============================================================================

def conta_anomalie_aic_aperte() -> int:
    """Conta anomalie AIC ancora aperte."""
    db = get_db()
    row = db.execute("""
        SELECT COUNT(*) AS cnt
        FROM anomalie
        WHERE codice_anomalia = 'AIC-A01' AND stato = 'APERTA'
    """).fetchone()
    return row['cnt'] if row else 0


def conta_supervisioni_aic_pending() -> int:
    """Conta supervisioni AIC ancora pending."""
    db = get_db()
    row = db.execute("""
        SELECT COUNT(*) AS cnt
        FROM supervisione_aic
        WHERE stato = 'PENDING'
    """).fetchone()
    return row['cnt'] if row else 0
