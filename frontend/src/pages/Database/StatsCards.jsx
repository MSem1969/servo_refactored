// =============================================================================
// SERV.O v7.0 - STATS CARDS COMPONENT
// =============================================================================

import React from 'react';

const StatCard = ({ icon, label, value, color = 'slate', active, onClick }) => {
  const colorClasses = {
    blue: 'bg-blue-100',
    emerald: 'bg-emerald-100',
    yellow: 'bg-yellow-100',
    green: 'bg-green-100',
    slate: 'bg-slate-100',
    red: 'bg-red-100'
  };

  const textClasses = {
    blue: 'text-slate-800',
    emerald: 'text-emerald-600',
    yellow: 'text-yellow-600',
    green: 'text-green-600',
    slate: 'text-slate-500',
    red: 'text-red-600'
  };

  return (
    <div
      onClick={onClick}
      className={`bg-white p-4 rounded-xl border-2 transition-all cursor-pointer hover:shadow-md ${
        active ? 'border-blue-500 ring-1 ring-blue-200' : 'border-slate-200 hover:border-slate-300'
      }`}
    >
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 ${colorClasses[color]} rounded-lg flex items-center justify-center`}>
          {icon}
        </div>
        <div>
          <p className="text-xs text-slate-600 font-medium">{label}</p>
          <p className={`text-xl font-bold ${textClasses[color]}`}>{value}</p>
        </div>
      </div>
    </div>
  );
};

export default function StatsCards({ stats, activeFilter = [], onStatClick }) {
  const isActive = (stato) => Array.isArray(activeFilter) && activeFilter.includes(stato);
  const allActive = Array.isArray(activeFilter) && activeFilter.length === 0;

  return (
    <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
      <StatCard icon="📋" label="Ordini" value={stats.ordini} color="blue" active={allActive} onClick={() => onStatClick('')} />
      <StatCard icon="📦" label="Evasi" value={(stats.evaso || 0) + (stats.parzEvaso || 0)} color="green" active={isActive('EVASO')} onClick={() => onStatClick('EVASO')} />
      <StatCard icon="📤" label="Esportati" value={stats.esportato || 0} color="emerald" active={isActive('ESPORTATO')} onClick={() => onStatClick('ESPORTATO')} />
      <StatCard icon="📤" label="Parz. Esportati" value={stats.parzEsportato || 0} color="yellow" active={isActive('PARZ_ESPORTATO')} onClick={() => onStatClick('PARZ_ESPORTATO')} />
      <StatCard icon="🗄️" label="Archiviati" value={stats.archiviati} color="slate" active={isActive('ARCHIVIATO')} onClick={() => onStatClick('ARCHIVIATO')} />
      <StatCard icon="⚠️" label="Anomalie Aperte" value={stats.anomalie_aperte} color="red" active={isActive('ANOMALIA')} onClick={() => onStatClick('ANOMALIA')} />
    </div>
  );
}
