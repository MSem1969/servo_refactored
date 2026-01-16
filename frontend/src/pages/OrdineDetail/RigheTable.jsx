// =============================================================================
// SERV.O v7.0 - RIGHE TABLE COMPONENT
// =============================================================================

import React from 'react';
import { calculateRigaQuantities, getStatoRigaColor, getStatoRigaLabel } from './utils';

export default function RigheTable({
  righe,
  rigaInModifica,
  formModifica,
  setFormModifica,
  stats,
  ordine,
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
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs font-medium text-slate-500 uppercase">
              <tr>
                <th className="px-3 py-3">N.</th>
                <th className="px-3 py-3">Codice AIC</th>
                <th className="px-3 py-3">Descrizione</th>
                <th className="px-3 py-3 text-center">Ordinato</th>
                <th className="px-3 py-3 text-center">Sc. Merce</th>
                <th className="px-3 py-3 text-center">Omaggio</th>
                <th className="px-3 py-3 text-center bg-green-50" title="Quantità già esportata">Evaso</th>
                <th className="px-3 py-3 text-center bg-blue-50" title="Quantità da esportare (editabile)">Da Evadere</th>
                <th className="px-3 py-3 text-center bg-orange-50" title="Rimanente da evadere">Residuo</th>
                <th className="px-3 py-3">Prezzo</th>
                <th className="px-3 py-3">Stato</th>
                <th className="px-3 py-3 text-center">Azioni</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {righe.map((riga, index) => {
                const { qOrdinata, qScontoMerce, qOmaggio, qEvasa, qDaEvadere, qResidua } = calculateRigaQuantities(riga);
                const isEditing = rigaInModifica && (rigaInModifica.id_dettaglio || rigaInModifica.id) === (riga.id_dettaglio || riga.id);

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
                      {!!(riga.is_espositore || (riga.codice_originale && riga.codice_originale !== riga.codice_aic)) && (
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
                    <td className="px-3 py-3">
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
            <h4 className="text-sm font-semibold text-slate-700 mb-2">Legenda simboli</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-slate-600">
              <div className="flex items-center gap-1"><span>🔍</span> <span>Visualizza PDF</span></div>
              <div className="flex items-center gap-1"><span>🎁</span> <span>Espositore</span></div>
              <div className="flex items-center gap-1"><span>✏️</span> <span>Modifica quantità</span></div>
              <div className="flex items-center gap-1"><span>✓</span> <span>Conferma riga</span></div>
              <div className="flex items-center gap-1"><span>↩</span> <span>Annulla conferma</span></div>
              <div className="flex items-center gap-1"><span>🔒</span> <span>Archivia (freeze)</span></div>
              <div className="flex items-center gap-1"><span>🔓</span> <span>Ripristina archiviata</span></div>
            </div>
          </div>
        </div>
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
    <div className="flex gap-1 justify-center">
      {ordine?.pdf_file && (
        <button
          onClick={onShowPdf}
          className="px-2 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded"
          title="Visualizza PDF originale"
        >
          🔍
        </button>
      )}

      {isEditing ? (
        <>
          <button
            onClick={() => onSalvaModifica(riga)}
            className="px-2 py-1 text-xs bg-green-500 hover:bg-green-600 text-white rounded"
            title="Salva"
          >
            💾
          </button>
          <button
            onClick={onChiudiModifica}
            className="px-2 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded"
            title="Annulla"
          >
            ✕
          </button>
        </>
      ) : (
        <>
          {riga.stato_riga === 'ARCHIVIATO' && (
            <button
              onClick={() => onRipristinaArchiviata(riga)}
              className="px-2 py-1 text-xs bg-blue-100 hover:bg-blue-200 text-blue-700 rounded"
              title="Ripristina riga archiviata"
            >
              🔓 Ripristina
            </button>
          )}

          {riga.stato_riga === 'EVASO' && (
            <span className="text-xs text-green-600 font-medium">Completato</span>
          )}

          {riga.stato_riga !== 'ARCHIVIATO' && riga.stato_riga !== 'EVASO' && (
            <>
              {qResidua > 0 && (
                <>
                  <button
                    onClick={() => onApriModifica(riga)}
                    className="px-2 py-1 text-xs bg-blue-100 hover:bg-blue-200 text-blue-700 rounded"
                    title="Modifica quantità da evadere"
                  >
                    ✏️
                  </button>
                  {riga.stato_riga !== 'CONFERMATO' && (
                    <button
                      onClick={() => onConfermaRiga(riga)}
                      className="px-2 py-1 text-xs bg-green-100 hover:bg-green-200 text-green-700 rounded"
                      title="Conferma tutto il residuo"
                    >
                      ✓
                    </button>
                  )}
                  {riga.stato_riga === 'CONFERMATO' && (
                    <button
                      onClick={() => onRipristinaRiga(riga)}
                      className="px-2 py-1 text-xs bg-amber-100 hover:bg-amber-200 text-amber-700 rounded"
                      title="Annulla conferma (ripristina)"
                    >
                      ↩
                    </button>
                  )}
                </>
              )}
              {qResidua <= 0 && (
                <span className="text-xs text-slate-500">Residuo esaurito</span>
              )}
              <button
                onClick={() => onArchiviaRiga(riga)}
                className="px-2 py-1 text-xs bg-slate-200 hover:bg-slate-300 text-slate-700 rounded"
                title="Archivia riga (freeze)"
              >
                🔒
              </button>
            </>
          )}
        </>
      )}
    </div>
  );
}
