// =============================================================================
// SERV.O v7.0 - ORDINE DETAIL UTILS
// =============================================================================
// Helper functions per componenti dettaglio ordine
// =============================================================================

export const getStatoColor = (stato) => {
  const colors = {
    'nuovo': 'bg-blue-100 text-blue-800',
    'in_lavorazione': 'bg-yellow-100 text-yellow-800',
    'validato': 'bg-green-100 text-green-800',
    'esportato': 'bg-purple-100 text-purple-800',
    'errore': 'bg-red-100 text-red-800',
    'supervisione': 'bg-orange-100 text-orange-800',
    'ESTRATTO': 'bg-blue-100 text-blue-800',
    'CONFERMATO': 'bg-cyan-100 text-cyan-800',
    'ANOMALIA': 'bg-red-100 text-red-800',
    'PARZ_EVASO': 'bg-orange-100 text-orange-800',
    'EVASO': 'bg-green-100 text-green-800',
    'ARCHIVIATO': 'bg-slate-100 text-slate-600'
  };
  return colors[stato] || 'bg-slate-100 text-slate-800';
};

export const getLivelloColor = (livello) => {
  const colors = {
    'critico': 'bg-red-100 text-red-800 border-red-300',
    'alto': 'bg-orange-100 text-orange-800 border-orange-300',
    'medio': 'bg-yellow-100 text-yellow-800 border-yellow-300',
    'basso': 'bg-blue-100 text-blue-800 border-blue-300'
  };
  return colors[livello] || 'bg-slate-100 text-slate-800 border-slate-300';
};

export const getStatoRigaColor = (stato) => {
  switch (stato) {
    case 'ARCHIVIATO': return 'bg-slate-200 text-slate-700';
    case 'EVASO': return 'bg-green-100 text-green-700';
    case 'CONFERMATO': return 'bg-cyan-100 text-cyan-700';
    case 'PARZIALE': return 'bg-yellow-100 text-yellow-700';
    case 'IN_SUPERVISIONE': return 'bg-purple-100 text-purple-700';
    default: return 'bg-slate-100 text-slate-600';
  }
};

export const getStatoRigaLabel = (stato) => {
  switch (stato) {
    case 'ARCHIVIATO': return 'ARCH';
    case 'EVASO': return 'EVASO';
    case 'CONFERMATO': return 'CONF';
    case 'PARZIALE': return 'PARZ';
    case 'IN_SUPERVISIONE': return 'SUP';
    default: return 'PND';
  }
};

export const calculateRigaQuantities = (riga) => {
  const qOrdinata = riga.q_ordinata || riga.q_venduta || riga.quantita || 0;
  const qScontoMerce = riga.q_sconto_merce || 0;
  const qOmaggio = riga.q_omaggio || 0;
  const qTotale = qOrdinata + qScontoMerce + qOmaggio;
  const qEvasa = riga.q_evasa || 0;
  const qDaEvadere = riga.q_da_evadere || 0;
  const qResidua = qTotale - qEvasa;

  return {
    qOrdinata,
    qScontoMerce,
    qOmaggio,
    qTotale,
    qEvasa,
    qDaEvadere,
    qResidua
  };
};
