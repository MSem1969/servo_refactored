// =============================================================================
// SERV.O v11.3 - RIGHE TABLE COMPONENT
// =============================================================================
// v11.3: Sort state lifted to parent (persists across reloads and tab changes)
// =============================================================================

import React, { useMemo } from 'react';
import { calculateRigaQuantities, getStatoRigaColor, getStatoRigaLabel } from './utils';
import { parseDataConsegna } from '../Database/utils';

// Componente intestazione colonna ordinabile
function SortableHeader({ label, field, sortField, sortDirection, onSort, className = '' }) {
  const isActive = sortField === field;
  return (
    <th
      className={`px-3 py-3 cursor-pointer hover:bg-slate-100 select-none ${className}`}
      onClick={() => onSort(field)}
    >
      <div className="flex items-center gap-1">
        {label}
        <span className={`text-xs ${isActive ? 'text-blue-600' : 'text-slate-300'}`}>
          {isActive ? (sortDirection === 'asc' ? '▲' : '▼') : '⇅'}
        </span>
      </div>
    </th>
  );
}

export default function RigheTable({
  righe,
  rigaInModifica,
  formModifica,
  setFormModifica,
  stats,
  ordine,
  // v11.3: Sort state from parent (persists across reloads)
  sortField = 'n_riga',
  sortDirection = 'asc',
  onSort,
  onShowPdf,
  onApriModifica,
  onSalvaModifica,
  onChiudiModifica,
  onConfermaRiga,
  onRipristinaRiga,
  onArchiviaRiga,
  onRipristinaArchiviata,
  onConfermaTutto,
  onRipristinaTutto,
  onValidaOrdine
}) {
  // v11.3: Sort handler from parent
  const handleSort = onSort;

  // Ordina le righe
  const sortedRighe = useMemo(() => {
    if (!righe || righe.length === 0) return [];

    return [...righe].sort((a, b) => {
      let aVal, bVal;

      // Calcola quantità per campi derivati
      const aQty = calculateRigaQuantities(a);
      const bQty = calculateRigaQuantities(b);

      switch (sortField) {
        case 'n_riga':
          aVal = a.n_riga || 0;
          bVal = b.n_riga || 0;
          break;
        case 'codice_aic':
          aVal = a.codice_aic || a.codice_prodotto || '';
          bVal = b.codice_aic || b.codice_prodotto || '';
          break;
        case 'descrizione':
          aVal = a.descrizione_prodotto || a.descrizione || '';
          bVal = b.descrizione_prodotto || b.descrizione || '';
          break;
        case 'q_ordinata':
          aVal = aQty.qOrdinata;
          bVal = bQty.qOrdinata;
          break;
        case 'q_sconto_merce':
          aVal = aQty.qScontoMerce;
          bVal = bQty.qScontoMerce;
          break;
        case 'q_omaggio':
          aVal = aQty.qOmaggio;
          bVal = bQty.qOmaggio;
          break;
        case 'q_evasa':
          aVal = aQty.qEvasa;
          bVal = bQty.qEvasa;
          break;
        case 'q_da_evadere':
          aVal = aQty.qDaEvadere;
          bVal = bQty.qDaEvadere;
          break;
        case 'q_residua':
          aVal = aQty.qResidua;
          bVal = bQty.qResidua;
          break;
        case 'prezzo_netto':
          aVal = parseFloat(a.prezzo_netto) || 0;
          bVal = parseFloat(b.prezzo_netto) || 0;
          break;
        case 'data_consegna':
          aVal = a.data_consegna || ordine?.data_consegna || '';
          bVal = b.data_consegna || ordine?.data_consegna || '';
          break;
        case 'stato_riga':
          aVal = a.stato_riga || '';
          bVal = b.stato_riga || '';
          break;
        default:
          aVal = 0;
          bVal = 0;
      }

      // Confronto
      if (typeof aVal === 'string') {
        const cmp = aVal.localeCompare(bVal, 'it');
        return sortDirection === 'asc' ? cmp : -cmp;
      } else {
        const cmp = aVal - bVal;
        return sortDirection === 'asc' ? cmp : -cmp;
      }
    });
  }, [righe, sortField, sortDirection, ordine]);

  return (
    <div className="p-4">
      {/* Riepilogo e azioni in blocco */}
      <div className="flex justify-between items-center mb-4">
        <div className="text-sm text-slate-500 flex flex-wrap gap-x-3">
          <span>{stats.totaleRighe} righe totali</span>
          <span className="text-green-600">{stats.totaleEvase} evase</span>
          <span className="text-blue-600 font-medium">{stats.totaleDaEvadere} da evadere</span>
          <span className="text-orange-600">{stats.totaleResiduo} residuo</span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onConfermaTutto}
            disabled={righe.length === 0 || stats.tutteEvase}
            className="px-4 py-2 bg-green-500 hover:bg-green-600 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium"
            title="Imposta Da Evadere = Residuo per tutte le righe"
          >
            ✓ Conferma Tutto
          </button>
          <button
            onClick={onRipristinaTutto}
            disabled={righe.length === 0 || !stats.haRigheConfermate}
            className="px-4 py-2 bg-orange-500 hover:bg-orange-600 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium"
            title="Annulla conferma per tutte le righe"
          >
            ↩ Ripristina Tutto
          </button>
        </div>
      </div>

      {/* Tabella */}
      {righe.length === 0 ? (
        <div className="text-center py-8 text-slate-500">
          <div className="text-4xl mb-2">📦</div>
          <p>Nessuna riga per questo ordine</p>
        </div>
      ) : (
        <>
          {/* Hint scroll orizzontale */}
          <div className="mb-2 text-xs text-slate-500 flex items-center gap-2">
            <span>⬅️ Scorri orizzontalmente per vedere tutte le colonne ➡️</span>
            <span className="text-blue-600">| Colonna "Azioni" (ottimizzata verticalmente) sempre visibile a destra</span>
          </div>
          <div className="overflow-x-auto relative">
          <table className="w-full text-sm relative">
            <thead className="bg-slate-50 text-left text-xs font-medium text-slate-500 uppercase">
              <tr>
                <SortableHeader label="N." field="n_riga" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} />
                <SortableHeader label="Codice AIC" field="codice_aic" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} />
                <SortableHeader label="Descrizione" field="descrizione" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} />
                <SortableHeader label="Ordinato" field="q_ordinata" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} className="text-center" />
                <SortableHeader label="Sc. Merce" field="q_sconto_merce" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} className="text-center" />
                <SortableHeader label="Omaggio" field="q_omaggio" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} className="text-center" />
                <SortableHeader label="Evaso" field="q_evasa" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} className="text-center bg-green-50" />
                <SortableHeader label="Da Evadere" field="q_da_evadere" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} className="text-center bg-blue-50" />
                <SortableHeader label="Residuo" field="q_residua" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} className="text-center bg-orange-50" />
                <SortableHeader label="Prezzo" field="prezzo_netto" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} />
                <SortableHeader label="Consegna" field="data_consegna" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} />
                <SortableHeader label="Stato" field="stato_riga" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} />
                <th className="px-3 py-3 text-center bg-slate-50 sticky right-0 shadow-[-2px_0_4px_rgba(0,0,0,0.1)] min-w-[110px] z-10">
                  Azioni
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {sortedRighe.map((riga, index) => {
                const { qOrdinata, qScontoMerce, qOmaggio, qEvasa, qDaEvadere, qResidua } = calculateRigaQuantities(riga);
                const isEditing = rigaInModifica && (rigaInModifica.id_dettaglio || rigaInModifica.id) === (riga.id_dettaglio || riga.id);

                const bgClass = riga.is_espositore ? 'bg-purple-50' : 'bg-white';

                return (
                  <tr key={riga.id_dettaglio || riga.id || index} className={`hover:bg-slate-50 ${riga.is_espositore ? 'bg-purple-50' : ''}`}>
                    <td className="px-3 py-3 text-slate-500">{riga.n_riga || index + 1}</td>
                    <td className="px-3 py-3">
                      <div className="font-mono text-xs">{riga.codice_aic || riga.codice_prodotto || '-'}</div>
                      {riga.codice_originale && riga.codice_originale !== riga.codice_aic && (
                        <div className="text-xs text-slate-400">{riga.codice_originale}</div>
                      )}
                    </td>
                    <td className="px-3 py-3 uppercase">
                      {/* v11.2: Mostra emoji solo per veri espositori, non per differenze AIC (padding OPELLA) */}
                      {!!riga.is_espositore && (
                        <span className="mr-1" title="Espositore">🎁</span>
                      )}
                      {riga.descrizione_prodotto || riga.descrizione || '-'}
                    </td>
                    <td className="px-3 py-3 text-center font-medium">{qOrdinata}</td>
                    <td className="px-3 py-3 text-center">
                      {qScontoMerce > 0 ? (
                        <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-xs">{qScontoMerce}</span>
                      ) : '-'}
                    </td>
                    <td className="px-3 py-3 text-center">
                      {qOmaggio > 0 ? (
                        <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">{qOmaggio}</span>
                      ) : '-'}
                    </td>
                    <td className="px-3 py-3 text-center bg-green-50/50">
                      <span className={qEvasa > 0 ? 'text-green-600 font-medium' : 'text-slate-400'}>{qEvasa}</span>
                    </td>
                    <td className="px-3 py-3 text-center bg-blue-50/50">
                      {isEditing ? (
                        <input
                          type="number"
                          min="0"
                          max={qResidua}
                          value={formModifica.q_da_evadere}
                          onChange={(e) => setFormModifica(f => ({ ...f, q_da_evadere: parseInt(e.target.value) || 0 }))}
                          onFocus={(e) => e.target.select()}
                          className="w-16 px-2 py-1 border border-blue-400 rounded text-center text-sm bg-white"
                          autoFocus
                        />
                      ) : (
                        <span className={qDaEvadere > 0 ? 'text-blue-600 font-bold' : 'text-slate-400'}>
                          {qDaEvadere > 0 ? qDaEvadere : '-'}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-center bg-orange-50/50">
                      {qResidua > 0 ? (
                        <span className="text-orange-600 font-medium">{qResidua}</span>
                      ) : (
                        <span className="text-green-600">-</span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-right">
                      {riga.prezzo_netto ? `€ ${parseFloat(riga.prezzo_netto).toFixed(2)}` : '-'}
                    </td>
                    <td className="px-3 py-3 text-center text-xs">
                      {/* Data consegna: riga, altrimenti testata, altrimenti stima
                          data_ordine + N giorni lavorativi (stessa regola della lista
                          ordini e del tracciato). La stima e' marcata con "~". */}
                      {(() => {
                        let dataConsegna = riga.data_consegna || ordine?.data_consegna;
                        if (!dataConsegna) {
                          if (!ordine?.data_ordine) return '-';
                          // Costruzione locale: toISOString() sposterebbe di un giorno
                          // (mezzanotte locale -> giorno precedente in UTC).
                          const s = parseDataConsegna(null, ordine.data_ordine);
                          const gg = String(s.getDate()).padStart(2, '0');
                          const mm = String(s.getMonth() + 1).padStart(2, '0');
                          return `~${gg}/${mm}/${String(s.getFullYear()).slice(2)}`;
                        }
                        try {
                          // Parsing diretto per formato ISO YYYY-MM-DD (evita shift timezone)
                          if (/^\d{4}-\d{2}-\d{2}$/.test(dataConsegna)) {
                            const [y, m, d] = dataConsegna.split('-');
                            return `${d}/${m}/${y.slice(2)}`;
                          }
                          const date = new Date(dataConsegna);
                          return date.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: '2-digit' });
                        } catch {
                          return dataConsegna;
                        }
                      })()}
                    </td>
                    <td className="px-3 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getStatoRigaColor(riga.stato_riga)}`}>
                        {riga.stato_riga === 'ARCHIVIATO' ? '🔒 ARCH' :
                         riga.stato_riga === 'EVASO' ? '✓ EVASO' :
                         riga.stato_riga === 'CONFERMATO' ? 'CONF' :
                         riga.stato_riga === 'PARZIALE' ? 'PARZ' :
                         riga.stato_riga === 'IN_SUPERVISIONE' ? 'SUP' :
                         'PND'}
                      </span>
                    </td>
                    <td className={`px-3 py-3 ${bgClass} sticky right-0 shadow-[-2px_0_4px_rgba(0,0,0,0.05)] min-w-[110px] z-10`}>
                      <RigaActions
                        riga={riga}
                        isEditing={isEditing}
                        qResidua={qResidua}
                        ordine={ordine}
                        onShowPdf={onShowPdf}
                        onApriModifica={onApriModifica}
                        onSalvaModifica={onSalvaModifica}
                        onChiudiModifica={onChiudiModifica}
                        onConfermaRiga={onConfermaRiga}
                        onRipristinaRiga={onRipristinaRiga}
                        onArchiviaRiga={onArchiviaRiga}
                        onRipristinaArchiviata={onRipristinaArchiviata}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {/* Leggenda simboli */}
          <div className="mt-4 p-3 bg-slate-50 rounded-lg border border-slate-200">
            <h4 className="text-sm font-semibold text-slate-700 mb-2">Legenda azioni</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-slate-600">
              <div className="flex items-center gap-1"><span>🔍 PDF</span> <span>Visualizza ordine</span></div>
              <div className="flex items-center gap-1"><span>✏️ Modifica</span> <span>Cambia quantità</span></div>
              <div className="flex items-center gap-1"><span>✓ Conferma</span> <span>Conferma riga</span></div>
              <div className="flex items-center gap-1"><span>↩ Ripristina</span> <span>Annulla conferma</span></div>
              <div className="flex items-center gap-1"><span>🔒 Archivia</span> <span>Blocca riga</span></div>
              <div className="flex items-center gap-1"><span>🔓 Ripristina</span> <span>Sblocca archiviata</span></div>
              <div className="flex items-center gap-1"><span>💾 Salva</span> <span>Salva modifiche</span></div>
              <div className="flex items-center gap-1"><span>🎁</span> <span>Riga espositore</span></div>
            </div>
          </div>
        </div>
        </>
      )}

      {/* Pulsanti in fondo */}
      {righe.length > 0 && (
        <div className="mt-4 flex justify-between border-t border-slate-200 pt-4">
          <button
            onClick={onValidaOrdine}
            disabled={righe.length === 0}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium"
            title="Genera tracciato con le quantità 'Da Evadere'"
          >
            📤 Genera Tracciato
          </button>
          <div className="flex gap-2">
            <button
              onClick={onConfermaTutto}
              disabled={righe.length === 0 || stats.tutteEvase}
              className="px-4 py-2 bg-green-500 hover:bg-green-600 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium"
            >
              ✓ Conferma Tutto
            </button>
            <button
              onClick={onRipristinaTutto}
              disabled={righe.length === 0 || !stats.haRigheConfermate}
              className="px-4 py-2 bg-orange-500 hover:bg-orange-600 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium"
            >
              ↩ Ripristina Tutto
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// Sub-component per azioni riga
function RigaActions({
  riga,
  isEditing,
  qResidua,
  ordine,
  onShowPdf,
  onApriModifica,
  onSalvaModifica,
  onChiudiModifica,
  onConfermaRiga,
  onRipristinaRiga,
  onArchiviaRiga,
  onRipristinaArchiviata
}) {
  return (
    <div className="flex flex-col gap-1 items-center">
      {ordine?.pdf_file && (
        <button
          onClick={onShowPdf}
          className="w-full px-2 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded whitespace-nowrap"
          title="Visualizza PDF originale"
        >
          🔍 PDF
        </button>
      )}

      {isEditing ? (
        <>
          <button
            onClick={() => onSalvaModifica(riga)}
            className="w-full px-2 py-1 text-xs bg-green-500 hover:bg-green-600 text-white rounded whitespace-nowrap"
            title="Salva"
          >
            💾 Salva
          </button>
          <button
            onClick={onChiudiModifica}
            className="w-full px-2 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded whitespace-nowrap"
            title="Annulla"
          >
            ✕ Annulla
          </button>
        </>
      ) : (
        <>
          {riga.stato_riga === 'ARCHIVIATO' && (
            <button
              onClick={() => onRipristinaArchiviata(riga)}
              className="w-full px-2 py-1 text-xs bg-blue-100 hover:bg-blue-200 text-blue-700 rounded whitespace-nowrap"
              title="Ripristina riga archiviata"
            >
              🔓 Ripristina
            </button>
          )}

          {riga.stato_riga === 'EVASO' && (
            <>
              <span className="text-xs text-green-600 font-medium">✓ Completato</span>
              <button
                onClick={() => onRipristinaRiga(riga)}
                className="w-full px-2 py-1 text-xs bg-amber-100 hover:bg-amber-200 text-amber-700 rounded whitespace-nowrap"
                title="Hard Reset: azzera q_evasa e riporta a ESTRATTO"
              >
                ↩ Ripristina
              </button>
            </>
          )}

          {riga.stato_riga !== 'ARCHIVIATO' && riga.stato_riga !== 'EVASO' && (
            <>
              {qResidua > 0 && (
                <>
                  <button
                    onClick={() => onApriModifica(riga)}
                    className="w-full px-2 py-1 text-xs bg-blue-100 hover:bg-blue-200 text-blue-700 rounded whitespace-nowrap"
                    title="Modifica quantità da evadere"
                  >
                    ✏️ Modifica
                  </button>
                  {riga.stato_riga !== 'CONFERMATO' && (
                    <button
                      onClick={() => onConfermaRiga(riga)}
                      className="w-full px-2 py-1 text-xs bg-green-100 hover:bg-green-200 text-green-700 rounded whitespace-nowrap"
                      title="Conferma tutto il residuo"
                    >
                      ✓ Conferma
                    </button>
                  )}
                  {riga.stato_riga === 'CONFERMATO' && (
                    <button
                      onClick={() => onRipristinaRiga(riga)}
                      className="w-full px-2 py-1 text-xs bg-amber-100 hover:bg-amber-200 text-amber-700 rounded whitespace-nowrap"
                      title="Annulla conferma (ripristina)"
                    >
                      ↩ Ripristina
                    </button>
                  )}
                </>
              )}
              {qResidua <= 0 && (
                <span className="text-xs text-slate-500 text-center">Residuo esaurito</span>
              )}
              <button
                onClick={() => onArchiviaRiga(riga)}
                className="w-full px-2 py-1 text-xs bg-slate-200 hover:bg-slate-300 text-slate-700 rounded whitespace-nowrap"
                title="Archivia riga (freeze)"
              >
                🔒 Archivia
              </button>
            </>
          )}
        </>
      )}
    </div>
  );
}
