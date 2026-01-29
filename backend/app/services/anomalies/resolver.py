# =============================================================================
# SERV.O v11.0 - ANOMALIA RESOLVER (TIER 2.4)
# =============================================================================
# Servizio centralizzato per risoluzione anomalie con routing per tipo
#
# ROUTING:
# - AIC-* -> risolvi_aic (propaga AIC)
# - LKP-A05 -> risolvi_deposito (assegna deposito manuale)
# - LKP-* -> risolvi_lookup (riassegna farmacia)
# - ESP-* -> risolvi_espositore (aggiusta quantita)
# - LST-* / PRICE-* -> risolvi_listino (correggi prezzi)
# - Default -> risolvi_generico (marca come risolto)
#
# VANTAGGI:
# - Single entry point per tutti i tipi di risoluzione
# - Logica di routing centralizzata
# - Facile aggiungere nuovi tipi
# - Testing semplificato
# =============================================================================

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from ...database_pg import get_db, log_operation


class TipoRisoluzione(str, Enum):
    """Tipi di risoluzione supportati."""
    AIC = 'AIC'
    DEPOSITO = 'DEPOSITO'
    LOOKUP = 'LOOKUP'
    ESPOSITORE = 'ESPOSITORE'
    LISTINO = 'LISTINO'
    GENERICO = 'GENERICO'


@dataclass
class ResolutionParams:
    """Parametri per risoluzione anomalia."""
    operatore: str
    note: Optional[str] = None
    ruolo: str = 'operatore'
    livello_propagazione: str = 'ORDINE'

    # AIC specifici
    codice_aic: Optional[str] = None

    # Deposito specifici (LKP-A05)
    deposito_riferimento: Optional[str] = None
    id_cliente: Optional[int] = None

    # Lookup specifici (LKP-A01/A02/A03)
    tipo_entita: Optional[str] = None  # FARMACIA | PARAFARMACIA
    id_entita: Optional[int] = None

    # Espositore specifici
    q_venduta: Optional[int] = None
    q_omaggio: Optional[int] = None
    q_sconto_merce: Optional[int] = None

    # Listino specifici
    prezzo_netto: Optional[float] = None
    prezzo_pubblico: Optional[float] = None
    sconto_1: Optional[float] = None
    sconto_2: Optional[float] = None
    sconto_3: Optional[float] = None
    sconto_4: Optional[float] = None

    # Dati aggiuntivi (generico)
    dati_extra: Dict = field(default_factory=dict)


@dataclass
class ResolutionResult:
    """Risultato risoluzione."""
    success: bool
    id_anomalia: int
    tipo_risoluzione: str
    message: str
    anomalie_risolte: int = 1
    ordini_coinvolti: list = field(default_factory=list)
    righe_aggiornate: int = 0
    ml_pattern_incrementato: int = 0
    data: Dict = field(default_factory=dict)


class AnomaliaResolver:
    """
    Resolver centralizzato per anomalie.

    Usage:
        resolver = AnomaliaResolver()
        result = resolver.risolvi(
            id_anomalia=123,
            params=ResolutionParams(
                operatore='mario.rossi',
                codice_aic='012345678'
            )
        )
    """

    def __init__(self):
        self.db = None

    def risolvi(self, id_anomalia: int, params: ResolutionParams) -> ResolutionResult:
        """
        Entry point unico per risolvere qualsiasi tipo di anomalia.

        Args:
            id_anomalia: ID anomalia da risolvere
            params: Parametri di risoluzione

        Returns:
            ResolutionResult con esito operazione
        """
        self.db = get_db()

        # Recupera anomalia
        anomalia = self._get_anomalia(id_anomalia)
        if not anomalia:
            return ResolutionResult(
                success=False,
                id_anomalia=id_anomalia,
                tipo_risoluzione='UNKNOWN',
                message=f"Anomalia {id_anomalia} non trovata"
            )

        # Verifica stato
        if anomalia['stato'] == 'RISOLTA':
            return ResolutionResult(
                success=False,
                id_anomalia=id_anomalia,
                tipo_risoluzione='UNKNOWN',
                message="Anomalia gia risolta"
            )

        # =====================================================================
        # PROPAGAZIONE CENTRALIZZATA (v11.3)
        # Se livello GLOBALE o ORDINE con propagazione, usa servizio unificato
        # La propagazione chiude TUTTE le anomalie identiche, poi applica
        # eventuali correzioni dati (AIC, prezzo, etc.)
        # =====================================================================
        if params.livello_propagazione in ('GLOBALE', 'ORDINE'):
            return self._risolvi_con_propagazione(anomalia, params)

        # Routing specifico solo per risoluzione SINGOLA (senza propagazione)
        codice = anomalia.get('codice_anomalia', '') or ''

        if codice.startswith('AIC-'):
            return self._risolvi_aic(anomalia, params)

        elif codice == 'LKP-A05' or codice == 'DEP-A01' or codice.startswith('DEP-'):
            return self._risolvi_deposito(anomalia, params)

        elif codice.startswith('LKP-'):
            return self._risolvi_lookup(anomalia, params)

        elif codice.startswith('ESP-'):
            return self._risolvi_espositore(anomalia, params)

        elif codice.startswith('LST-') or codice.startswith('PRICE-'):
            return self._risolvi_listino(anomalia, params)

        else:
            return self._risolvi_generico(anomalia, params)

    def _get_anomalia(self, id_anomalia: int) -> Optional[Dict]:
        """Recupera anomalia con dati completi."""
        row = self.db.execute("""
            SELECT
                a.id_anomalia, a.id_testata, a.id_dettaglio, a.tipo_anomalia,
                a.codice_anomalia, a.livello, a.descrizione, a.valore_anomalo,
                a.stato, a.pattern_signature,
                ot.partita_iva_estratta as partita_iva,
                ot.numero_ordine_vendor,
                v.codice_vendor as vendor,
                od.codice_aic, od.descrizione as descrizione_prodotto
            FROM anomalie a
            LEFT JOIN ordini_testata ot ON a.id_testata = ot.id_testata
            LEFT JOIN vendor v ON ot.id_vendor = v.id_vendor
            LEFT JOIN ordini_dettaglio od ON a.id_dettaglio = od.id_dettaglio
            WHERE a.id_anomalia = %s
        """, (id_anomalia,)).fetchone()

        return dict(row) if row else None

    # =========================================================================
    # PROPAGAZIONE CENTRALIZZATA (v11.3)
    # =========================================================================

    def _risolvi_con_propagazione(self, anomalia: Dict, params: ResolutionParams) -> ResolutionResult:
        """
        Risolve anomalia con propagazione CENTRALIZZATA per TUTTI i tipi.

        Workflow:
        1. Trova tutte le anomalie identiche (stesso codice + stesso pattern)
        2. Applica correzioni dati a tutte le righe coinvolte
        3. Chiude tutte le anomalie identiche
        4. Sblocca tutti gli ordini coinvolti
        5. Aggiorna pattern ML

        Questo metodo unifica la logica per:
        - AIC-*: propaga codice AIC
        - LST-*/PRICE-*: propaga prezzi/sconti
        - LKP-*: propaga assegnazione farmacia
        - ESP-*: propaga correzione quantita
        - Altri: propaga solo chiusura anomalia
        """
        from .propagazione import (
            trova_anomalie_identiche,
            LivelloPropagazione,
            _approva_supervisioni_collegate,
            _incrementa_pattern_ml,
            _sblocca_ordine_se_possibile
        )

        codice = anomalia.get('codice_anomalia', '') or ''
        tipo = anomalia.get('tipo_anomalia', '') or ''

        # Determina livello propagazione
        livello = LivelloPropagazione.GLOBALE if params.livello_propagazione == 'GLOBALE' else LivelloPropagazione.ORDINE

        # Verifica permessi
        if livello == LivelloPropagazione.GLOBALE and params.ruolo not in ('admin', 'superuser', 'supervisore'):
            return ResolutionResult(
                success=False,
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione='PROPAGAZIONE',
                message=f"Ruolo {params.ruolo} non può usare propagazione GLOBALE"
            )

        try:
            # 1. Trova tutte le anomalie identiche
            anomalie_da_risolvere = trova_anomalie_identiche(anomalia['id_anomalia'], livello)

            if not anomalie_da_risolvere:
                return ResolutionResult(
                    success=False,
                    id_anomalia=anomalia['id_anomalia'],
                    tipo_risoluzione='PROPAGAZIONE',
                    message="Nessuna anomalia trovata"
                )

            anomalie_risolte = 0
            righe_aggiornate = 0
            ordini_coinvolti = set()
            supervisioni_approvate = 0

            # 2. Applica correzioni dati a TUTTE le righe coinvolte
            if self._ha_dati_correzione(params):
                for anom in anomalie_da_risolvere:
                    if anom.get('id_dettaglio'):
                        updated = self._applica_correzioni_riga(anom['id_dettaglio'], params, codice)
                        righe_aggiornate += updated

            # 3. Chiudi TUTTE le anomalie identiche
            for anom in anomalie_da_risolvere:
                if anom['stato'] in ('APERTA', 'IN_GESTIONE'):
                    self.db.execute("""
                        UPDATE anomalie
                        SET stato = 'RISOLTA',
                            data_risoluzione = CURRENT_TIMESTAMP,
                            note_risoluzione = %s
                        WHERE id_anomalia = %s
                    """, (
                        f"[{livello.value}] Operatore: {params.operatore} - {params.note or 'Risolto con propagazione'}",
                        anom['id_anomalia']
                    ))
                    anomalie_risolte += 1

                    if anom.get('id_testata'):
                        ordini_coinvolti.add(anom['id_testata'])

                    # 4. Approva supervisioni collegate
                    sup_count = _approva_supervisioni_collegate(
                        self.db, anom['id_anomalia'], params.operatore
                    )
                    supervisioni_approvate += sup_count

            # 5. Sblocca ordini coinvolti
            for id_testata in ordini_coinvolti:
                _sblocca_ordine_se_possibile(self.db, id_testata)

            # 6. Aggiorna pattern ML
            ml_incremento = 0
            if anomalie_risolte > 0:
                ml_incremento = _incrementa_pattern_ml(
                    self.db, anomalia, params.operatore, anomalie_risolte
                )

            self.db.commit()

            # Log
            log_operation(
                'RISOLVI_ANOMALIA_PROPAGAZIONE',
                'ANOMALIE',
                anomalia['id_anomalia'],
                f"[{codice}] Risolte {anomalie_risolte} anomalie ({livello.value}), "
                f"{righe_aggiornate} righe aggiornate, {len(ordini_coinvolti)} ordini",
                dati={
                    'livello': livello.value,
                    'codice_anomalia': codice,
                    'anomalie_risolte': anomalie_risolte,
                    'righe_aggiornate': righe_aggiornate,
                    'ordini_coinvolti': list(ordini_coinvolti),
                },
                operatore=params.operatore
            )

            return ResolutionResult(
                success=True,
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione=f'PROPAGAZIONE_{livello.value}',
                message=f"Risolte {anomalie_risolte} anomalie ({livello.value})",
                anomalie_risolte=anomalie_risolte,
                righe_aggiornate=righe_aggiornate,
                ordini_coinvolti=list(ordini_coinvolti),
                ml_pattern_incrementato=ml_incremento,
                data={
                    'supervisioni_approvate': supervisioni_approvate,
                    'livello': livello.value
                }
            )

        except Exception as e:
            self.db.rollback()
            return ResolutionResult(
                success=False,
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione='PROPAGAZIONE',
                message=f"Errore propagazione: {str(e)}"
            )

    def _ha_dati_correzione(self, params: ResolutionParams) -> bool:
        """Verifica se ci sono dati di correzione da applicare."""
        return any([
            params.codice_aic,
            params.prezzo_netto is not None,
            params.prezzo_pubblico is not None,
            params.sconto_1 is not None,
            params.sconto_2 is not None,
            params.sconto_3 is not None,
            params.sconto_4 is not None,
            params.q_venduta is not None,
            params.q_omaggio is not None,
            params.q_sconto_merce is not None,
        ])

    def _applica_correzioni_riga(self, id_dettaglio: int, params: ResolutionParams, codice_anomalia: str) -> int:
        """
        Applica correzioni dati a una riga ordine.

        Returns:
            1 se aggiornata, 0 altrimenti
        """
        updates = []
        values = []

        # Correzioni AIC
        if params.codice_aic:
            updates.append("codice_aic = %s")
            values.append(params.codice_aic)

        # Correzioni prezzi (LISTINO)
        if params.prezzo_netto is not None:
            updates.append("prezzo_netto = %s")
            values.append(params.prezzo_netto)

        if params.prezzo_pubblico is not None:
            updates.append("prezzo_pubblico = %s")
            values.append(params.prezzo_pubblico)

        if params.sconto_1 is not None:
            updates.append("sconto_1 = %s")
            values.append(params.sconto_1)

        if params.sconto_2 is not None:
            updates.append("sconto_2 = %s")
            values.append(params.sconto_2)

        if params.sconto_3 is not None:
            updates.append("sconto_3 = %s")
            values.append(params.sconto_3)

        if params.sconto_4 is not None:
            updates.append("sconto_4 = %s")
            values.append(params.sconto_4)

        # Correzioni quantita (ESPOSITORE)
        if params.q_venduta is not None:
            updates.append("q_venduta = %s")
            values.append(params.q_venduta)

        if params.q_omaggio is not None:
            updates.append("q_omaggio = %s")
            values.append(params.q_omaggio)

        if params.q_sconto_merce is not None:
            updates.append("q_sconto_merce = %s")
            values.append(params.q_sconto_merce)

        if not updates:
            return 0

        values.append(id_dettaglio)
        self.db.execute(f"""
            UPDATE ordini_dettaglio
            SET {', '.join(updates)}
            WHERE id_dettaglio = %s
        """, values)

        return 1

    # =========================================================================
    # RISOLUTORI SPECIFICI (per risoluzione SINGOLA senza propagazione)
    # =========================================================================

    def _risolvi_aic(self, anomalia: Dict, params: ResolutionParams) -> ResolutionResult:
        """
        Risolvi anomalia AIC assegnando codice AIC corretto.
        Delega a propagazione_aic service per logica complessa.
        """
        if not params.codice_aic:
            return ResolutionResult(
                success=False,
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione=TipoRisoluzione.AIC.value,
                message="Codice AIC richiesto per risoluzione AIC"
            )

        try:
            # v11.4: Migrato a aic_unified (refactoring)
            from ..supervision.aic_unified import propaga_aic_da_anomalia

            result = propaga_aic_da_anomalia(
                id_anomalia=anomalia['id_anomalia'],
                codice_aic=params.codice_aic,
                livello_propagazione=params.livello_propagazione,
                operatore=params.operatore,
                note=params.note
            )

            return ResolutionResult(
                success=result.get('success', False),
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione=TipoRisoluzione.AIC.value,
                message=result.get('message', 'AIC propagato'),
                righe_aggiornate=result.get('righe_aggiornate', 0),
                ordini_coinvolti=result.get('ordini_coinvolti', []),
                data=result
            )

        except Exception as e:
            return ResolutionResult(
                success=False,
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione=TipoRisoluzione.AIC.value,
                message=f"Errore risoluzione AIC: {str(e)}"
            )

    def _risolvi_deposito(self, anomalia: Dict, params: ResolutionParams) -> ResolutionResult:
        """
        Risolvi anomalia LKP-A05 assegnando deposito manuale.
        Il cliente non e in anagrafica_clienti, assegniamo deposito direttamente.
        """
        if not params.deposito_riferimento:
            return ResolutionResult(
                success=False,
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione=TipoRisoluzione.DEPOSITO.value,
                message="Deposito riferimento richiesto per LKP-A05"
            )

        id_testata = anomalia.get('id_testata')
        if not id_testata:
            return ResolutionResult(
                success=False,
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione=TipoRisoluzione.DEPOSITO.value,
                message="Anomalia non collegata a un ordine"
            )

        try:
            # Aggiorna testata con deposito manuale
            self.db.execute("""
                UPDATE ordini_testata
                SET deposito_riferimento = %s
                WHERE id_testata = %s
            """, (params.deposito_riferimento, id_testata))

            # Risolvi anomalia
            self._marca_risolta(
                anomalia['id_anomalia'],
                params.operatore,
                f"Deposito {params.deposito_riferimento} assegnato manualmente. {params.note or ''}"
            )

            # Sblocca ordine
            self._sblocca_ordine(id_testata)

            self.db.commit()

            log_operation(
                'RISOLVI_ANOMALIA_DEPOSITO',
                'ANOMALIE',
                anomalia['id_anomalia'],
                f"Deposito {params.deposito_riferimento} assegnato",
                operatore=params.operatore
            )

            return ResolutionResult(
                success=True,
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione=TipoRisoluzione.DEPOSITO.value,
                message=f"Deposito {params.deposito_riferimento} assegnato all'ordine",
                ordini_coinvolti=[id_testata],
                data={'deposito': params.deposito_riferimento}
            )

        except Exception as e:
            self.db.rollback()
            return ResolutionResult(
                success=False,
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione=TipoRisoluzione.DEPOSITO.value,
                message=f"Errore assegnazione deposito: {str(e)}"
            )

    def _risolvi_lookup(self, anomalia: Dict, params: ResolutionParams) -> ResolutionResult:
        """
        Risolvi anomalia LOOKUP riassegnando farmacia/parafarmacia.
        Delega a supervision lookup service.
        """
        if not params.tipo_entita or not params.id_entita:
            # Fallback a risoluzione generica se non ci sono parametri specifici
            return self._risolvi_generico(anomalia, params)

        try:
            from ..supervision.lookup import risolvi_supervisione_lookup

            result = risolvi_supervisione_lookup(
                id_anomalia=anomalia['id_anomalia'],
                tipo_entita=params.tipo_entita,
                id_entita=params.id_entita,
                operatore=params.operatore,
                note=params.note
            )

            return ResolutionResult(
                success=result.get('success', False),
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione=TipoRisoluzione.LOOKUP.value,
                message=result.get('message', 'Lookup risolto'),
                ordini_coinvolti=[anomalia['id_testata']] if anomalia.get('id_testata') else [],
                data=result
            )

        except Exception as e:
            return ResolutionResult(
                success=False,
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione=TipoRisoluzione.LOOKUP.value,
                message=f"Errore risoluzione lookup: {str(e)}"
            )

    def _risolvi_espositore(self, anomalia: Dict, params: ResolutionParams) -> ResolutionResult:
        """
        Risolvi anomalia ESPOSITORE aggiornando quantita.
        """
        id_dettaglio = anomalia.get('id_dettaglio')
        if not id_dettaglio:
            # Se non c'e riga, risolvi genericamente
            return self._risolvi_generico(anomalia, params)

        try:
            updates = []
            values = []

            if params.q_venduta is not None:
                updates.append("q_venduta = %s")
                values.append(params.q_venduta)

            if params.q_omaggio is not None:
                updates.append("q_omaggio = %s")
                values.append(params.q_omaggio)

            if params.q_sconto_merce is not None:
                updates.append("q_sconto_merce = %s")
                values.append(params.q_sconto_merce)

            if updates:
                values.append(id_dettaglio)
                self.db.execute(f"""
                    UPDATE ordini_dettaglio
                    SET {', '.join(updates)}
                    WHERE id_dettaglio = %s
                """, values)

            # Risolvi anomalia
            self._marca_risolta(
                anomalia['id_anomalia'],
                params.operatore,
                params.note
            )

            # Sblocca ordine
            if anomalia.get('id_testata'):
                self._sblocca_ordine(anomalia['id_testata'])

            self.db.commit()

            return ResolutionResult(
                success=True,
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione=TipoRisoluzione.ESPOSITORE.value,
                message="Espositore corretto",
                righe_aggiornate=1 if updates else 0,
                ordini_coinvolti=[anomalia['id_testata']] if anomalia.get('id_testata') else []
            )

        except Exception as e:
            self.db.rollback()
            return ResolutionResult(
                success=False,
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione=TipoRisoluzione.ESPOSITORE.value,
                message=f"Errore correzione espositore: {str(e)}"
            )

    def _risolvi_listino(self, anomalia: Dict, params: ResolutionParams) -> ResolutionResult:
        """
        Risolvi anomalia LISTINO/PREZZO correggendo prezzi/sconti.
        """
        id_dettaglio = anomalia.get('id_dettaglio')
        if not id_dettaglio:
            return self._risolvi_generico(anomalia, params)

        try:
            updates = []
            values = []

            if params.prezzo_netto is not None:
                updates.append("prezzo_netto = %s")
                values.append(params.prezzo_netto)

            if params.prezzo_pubblico is not None:
                updates.append("prezzo_pubblico = %s")
                values.append(params.prezzo_pubblico)

            if params.sconto_1 is not None:
                updates.append("sconto_1 = %s")
                values.append(params.sconto_1)

            if params.sconto_2 is not None:
                updates.append("sconto_2 = %s")
                values.append(params.sconto_2)

            if params.sconto_3 is not None:
                updates.append("sconto_3 = %s")
                values.append(params.sconto_3)

            if params.sconto_4 is not None:
                updates.append("sconto_4 = %s")
                values.append(params.sconto_4)

            if updates:
                values.append(id_dettaglio)
                self.db.execute(f"""
                    UPDATE ordini_dettaglio
                    SET {', '.join(updates)}
                    WHERE id_dettaglio = %s
                """, values)

            # Risolvi anomalia
            self._marca_risolta(
                anomalia['id_anomalia'],
                params.operatore,
                params.note
            )

            # Sblocca ordine
            if anomalia.get('id_testata'):
                self._sblocca_ordine(anomalia['id_testata'])

            self.db.commit()

            return ResolutionResult(
                success=True,
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione=TipoRisoluzione.LISTINO.value,
                message="Listino corretto",
                righe_aggiornate=1 if updates else 0,
                ordini_coinvolti=[anomalia['id_testata']] if anomalia.get('id_testata') else []
            )

        except Exception as e:
            self.db.rollback()
            return ResolutionResult(
                success=False,
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione=TipoRisoluzione.LISTINO.value,
                message=f"Errore correzione listino: {str(e)}"
            )

    def _risolvi_generico(self, anomalia: Dict, params: ResolutionParams) -> ResolutionResult:
        """
        Risoluzione generica SINGOLA - marca come risolto senza azioni specifiche.
        NOTA: La propagazione è gestita centralmente da _risolvi_con_propagazione()
        """
        try:
            # Risoluzione singola
            self._marca_risolta(
                anomalia['id_anomalia'],
                params.operatore,
                params.note
            )

            # Sblocca ordine
            if anomalia.get('id_testata'):
                self._sblocca_ordine(anomalia['id_testata'])

            self.db.commit()

            return ResolutionResult(
                success=True,
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione=TipoRisoluzione.GENERICO.value,
                message="Anomalia risolta",
                ordini_coinvolti=[anomalia['id_testata']] if anomalia.get('id_testata') else []
            )

        except Exception as e:
            self.db.rollback()
            return ResolutionResult(
                success=False,
                id_anomalia=anomalia['id_anomalia'],
                tipo_risoluzione=TipoRisoluzione.GENERICO.value,
                message=f"Errore risoluzione: {str(e)}"
            )

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _marca_risolta(self, id_anomalia: int, operatore: str, note: str = None):
        """Marca anomalia come risolta."""
        self.db.execute("""
            UPDATE anomalie
            SET stato = 'RISOLTA',
                data_risoluzione = CURRENT_TIMESTAMP,
                note_risoluzione = %s
            WHERE id_anomalia = %s
        """, (f"Operatore: {operatore} - {note or ''}", id_anomalia))

        # v11.4: Approva supervisioni collegate (inclusa prezzo)
        for table in ['supervisione_espositore', 'supervisione_listino',
                      'supervisione_lookup', 'supervisione_aic', 'supervisione_prezzo']:
            self.db.execute(f"""
                UPDATE {table}
                SET stato = 'APPROVED',
                    operatore = %s,
                    timestamp_decisione = CURRENT_TIMESTAMP,
                    note = COALESCE(note || ' - ', '') || '[AUTO] Risolto da AnomaliaResolver'
                WHERE id_anomalia = %s AND stato = 'PENDING'
            """, (operatore, id_anomalia))

    def _sblocca_ordine(self, id_testata: int):
        """Sblocca ordine se tutte anomalie risolte."""
        # Conta anomalie aperte
        anomalie = self.db.execute("""
            SELECT COUNT(*) as cnt FROM anomalie
            WHERE id_testata = %s
            AND stato IN ('APERTA', 'IN_GESTIONE')
            AND livello IN ('ERRORE', 'CRITICO')
        """, (id_testata,)).fetchone()

        # v11.4: Conta supervisioni pending (inclusa prezzo)
        sup_count = 0
        for table in ['supervisione_espositore', 'supervisione_listino',
                      'supervisione_lookup', 'supervisione_aic', 'supervisione_prezzo']:
            row = self.db.execute(f"""
                SELECT COUNT(*) as cnt FROM {table}
                WHERE id_testata = %s AND stato = 'PENDING'
            """, (id_testata,)).fetchone()
            sup_count += row['cnt'] if row else 0

        if (anomalie['cnt'] if anomalie else 0) == 0 and sup_count == 0:
            self.db.execute("""
                UPDATE ordini_testata
                SET stato = 'ESTRATTO'
                WHERE id_testata = %s AND stato IN ('ANOMALIA', 'PENDING_REVIEW')
            """, (id_testata,))


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def risolvi_anomalia(
    id_anomalia: int,
    operatore: str,
    note: str = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Funzione helper per risoluzione semplice.

    Usage:
        result = risolvi_anomalia(123, 'mario.rossi', note='Corretto')
        result = risolvi_anomalia(123, 'mario.rossi', codice_aic='012345678')
        result = risolvi_anomalia(123, 'mario.rossi', deposito_riferimento='DEP01')
    """
    params = ResolutionParams(
        operatore=operatore,
        note=note,
        **kwargs
    )

    resolver = AnomaliaResolver()
    result = resolver.risolvi(id_anomalia, params)

    return {
        'success': result.success,
        'message': result.message,
        'id_anomalia': result.id_anomalia,
        'tipo_risoluzione': result.tipo_risoluzione,
        'anomalie_risolte': result.anomalie_risolte,
        'righe_aggiornate': result.righe_aggiornate,
        'ordini_coinvolti': result.ordini_coinvolti,
        'ml_pattern_incrementato': result.ml_pattern_incrementato,
        'data': result.data
    }
