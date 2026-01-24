// =============================================================================
// SERV.O v10.4 - ANOMALIE TAB COMPONENT
// =============================================================================

import React, { useMemo } from 'react';
import {
  getLivelloColor,
  getLivelloBadgeClass,
  getNormalizedLevel,
  sortAnomalieByTipo
} from '../../common';

export default function AnomalieTab({
  anomalie,
  supervisioni,
  onLoadDetail,
  onApprovaSuper,
  onRifiutaSuper
}) {
  // Ordina anomalie per tipo
  const anomalieOrdinate = useMemo(() => sortAnomalieByTipo(anomalie), [anomalie]);

  return (
    <div className="space-y-4">
      {/* Supervisioni Espositore */}
      {supervisioni.length > 0 && (
        <SupervisioniSection
          supervisioni={supervisioni}
          onApprova={onApprovaSuper}
          onRifiuta={onRifiutaSuper}
        />
      )}

      {/* Lista Anomalie */}
      {anomalieOrdinate.length === 0 ? (
        <div className="text-center py-8 text-green-600">
          <span className="text-4xl">OK</span>
          <p className="mt-2">Nessuna anomalia rilevata</p>
        </div>
      ) : (
        <div className="space-y-3">
          {anomalieOrdinate.map((anomalia) => (
            <AnomaliaCard
              key={anomalia.id_anomalia || anomalia.id}
              anomalia={anomalia}
              onLoadDetail={onLoadDetail}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Sub-component: Sezione Supervisioni
function SupervisioniSection({ supervisioni, onApprova, onRifiuta }) {
  const pendingCount = supervisioni.filter(s => s.stato === 'PENDING').length;

  return (
    <div className="mb-6">
      <h3 className="text-sm font-semibold text-purple-700 mb-3 flex items-center gap-2">
        Supervisione Espositori ({pendingCount} pending)
      </h3>
      <div className="space-y-3">
        {supervisioni.map((sup) => (
          <SupervisioneCard
            key={sup.id_supervisione}
            supervisione={sup}
            onApprova={onApprova}
            onRifiuta={onRifiuta}
          />
        ))}
      </div>
    </div>
  );
}

// Sub-component: Card Supervisione
function SupervisioneCard({ supervisione: sup, onApprova, onRifiuta }) {
  const isPending = sup.stato === 'PENDING';
  const bgClass = isPending ? 'bg-purple-50 border-purple-200' : 'bg-slate-50 border-slate-200';

  return (
    <div className={`p-4 rounded-lg border ${bgClass}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">[E]</span>
            <span className="font-semibold text-slate-800 uppercase">{sup.descrizione_espositore}</span>
            <span className="text-xs font-mono text-slate-500">({sup.codice_espositore})</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm mb-2">
            <div className="text-slate-600">
              Pezzi attesi: <span className="font-bold">{sup.pezzi_attesi}</span>
            </div>
            <div className="text-slate-600">
              Pezzi trovati: <span className={`font-bold ${sup.pezzi_trovati === sup.pezzi_attesi ? 'text-green-600' : 'text-orange-600'}`}>
                {sup.pezzi_trovati}
              </span>
            </div>
            <div className="text-slate-600">
              Valore: <span className="font-bold">EUR {sup.valore_calcolato?.toFixed(2) || '0.00'}</span>
            </div>
            <div className="text-slate-600">
              Tipo: <span className="font-bold">{sup.codice_anomalia}</span>
            </div>
          </div>

          <div className="text-xs text-slate-500">
            Pattern: <span className="font-mono">{sup.pattern_signature}</span>
            {sup.count_approvazioni !== null && (
              <span className="ml-2">({sup.count_approvazioni}/5 conferme)</span>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <StatoBadge stato={sup.stato} />

          {isPending && (
            <div className="flex flex-col gap-1 mt-2">
              <button
                onClick={() => onApprova(sup.id_supervisione)}
                className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200"
              >
                [V] Conferma
              </button>
              <button
                onClick={() => onRifiuta(sup.id_supervisione)}
                className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200"
              >
                [X] Rifiuta
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Sub-component: Card Anomalia
function AnomaliaCard({ anomalia, onLoadDetail }) {
  const isRisolta = anomalia.stato === 'risolta' || anomalia.stato === 'RISOLTA';

  return (
    <div
      className={`p-4 rounded-lg border cursor-pointer hover:shadow-md transition-shadow ${getLivelloColor(anomalia.livello)}`}
      onClick={() => onLoadDetail(anomalia.id_anomalia || anomalia.id)}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className={`px-2 py-0.5 rounded text-xs font-bold ${getLivelloBadgeClass(anomalia.livello || anomalia.severita)}`}>
              {getNormalizedLevel(anomalia)}
            </span>
            <span className="text-sm font-medium text-slate-700">
              {anomalia.tipo || anomalia.tipo_anomalia}
            </span>
          </div>
          <p className="text-sm text-slate-600">{anomalia.messaggio || anomalia.descrizione}</p>
          {anomalia.campo && (
            <p className="text-xs text-slate-500 mt-1">
              Campo: <span className="font-mono">{anomalia.campo}</span>
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded text-xs font-medium ${
            isRisolta ? 'bg-green-100 text-green-800' :
            anomalia.stato === 'ignorata' ? 'bg-slate-100 text-slate-600' :
            'bg-red-100 text-red-800'
          }`}>
            {anomalia.stato}
          </span>
        </div>
      </div>
    </div>
  );
}

// Sub-component: Badge Stato
function StatoBadge({ stato }) {
  const colorClass = stato === 'PENDING' ? 'bg-yellow-100 text-yellow-800' :
                     stato === 'APPROVATO' ? 'bg-green-100 text-green-800' :
                     stato === 'RIFIUTATO' ? 'bg-red-100 text-red-800' :
                     'bg-slate-100 text-slate-600';

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colorClass}`}>
      {stato}
    </span>
  );
}
