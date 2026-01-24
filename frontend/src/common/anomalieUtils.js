// =============================================================================
// SERV.O v10.4 - ANOMALIE UTILS (CONDIVISO)
// =============================================================================
// Utilities unificate per visualizzazione anomalie in tutto il sistema
// =============================================================================

// Priorità tipi anomalia per ordinamento
export const TIPO_PRIORITY = {
  'aic': 1,
  'AIC': 1,
  'NO_AIC': 1,
  'prezzo': 2,
  'PREZZO_ZERO': 2,
  'listino': 3,
  'lookup': 4,
  'LOOKUP_FALLITO': 4,
  'espositore': 5,
  'ESPOSITORE': 5,
  'validazione': 6,
  'estrazione': 7,
  'DUPLICATO': 8,
  'QTA_ANOMALA': 9,
  'SCONTO_ANOMALO': 10,
};

// Ordina anomalie per tipo (priorità)
export const sortAnomalieByTipo = (items) => {
  return [...items].sort((a, b) => {
    const tipoA = (a.tipo || a.tipo_anomalia || '').toUpperCase();
    const tipoB = (b.tipo || b.tipo_anomalia || '').toUpperCase();
    const priorityA = TIPO_PRIORITY[tipoA] || 99;
    const priorityB = TIPO_PRIORITY[tipoB] || 99;
    return priorityA - priorityB;
  });
};

// Normalizza il livello/severità (unifica i campi)
export const getNormalizedLevel = (anomalia) => {
  const level = (anomalia.livello || anomalia.severita || 'INFO').toUpperCase();
  // Normalizza varianti
  if (level === 'CRITICAL' || level === 'CRITICO') return 'ERRORE';
  if (level === 'ERROR') return 'ERRORE';
  if (level === 'WARNING' || level === 'ATTENZIONE') return 'ATTENZIONE';
  if (level === 'ALTO') return 'ATTENZIONE';
  if (level === 'MEDIO') return 'ATTENZIONE';
  if (level === 'BASSO' || level === 'INFO') return 'INFO';
  return level;
};

// Colori per livello/severità anomalia (UNIFICATO)
export const getLivelloColor = (livelloRaw) => {
  const livello = (livelloRaw || '').toUpperCase();

  // ERRORE/CRITICO -> Rosso
  if (livello === 'ERRORE' || livello === 'CRITICO' || livello === 'CRITICAL' || livello === 'ERROR') {
    return 'bg-red-100 text-red-800 border-red-300';
  }
  // ATTENZIONE/WARNING/ALTO/MEDIO -> Giallo/Arancio
  if (livello === 'ATTENZIONE' || livello === 'WARNING' || livello === 'ALTO' || livello === 'MEDIO') {
    return 'bg-yellow-100 text-yellow-800 border-yellow-300';
  }
  // INFO/BASSO -> Blu
  if (livello === 'INFO' || livello === 'BASSO') {
    return 'bg-blue-100 text-blue-800 border-blue-300';
  }
  // Default
  return 'bg-slate-100 text-slate-800 border-slate-300';
};

// Badge per livello (inline styling per tabelle)
export const getLivelloBadgeClass = (livelloRaw) => {
  const livello = (livelloRaw || '').toUpperCase();

  if (livello === 'ERRORE' || livello === 'CRITICO' || livello === 'CRITICAL' || livello === 'ERROR') {
    return 'bg-red-600 text-white';
  }
  if (livello === 'ATTENZIONE' || livello === 'WARNING' || livello === 'ALTO' || livello === 'MEDIO') {
    return 'bg-yellow-200 text-yellow-800';
  }
  if (livello === 'INFO' || livello === 'BASSO') {
    return 'bg-blue-100 text-blue-800';
  }
  return 'bg-slate-200 text-slate-800';
};

// Colori per tipo anomalia
export const getTipoAnomaliaColor = (tipo) => {
  const tipoUpper = (tipo || '').toUpperCase();
  const colors = {
    'ESPOSITORE': 'bg-purple-100 text-purple-700',
    'NO_AIC': 'bg-orange-100 text-orange-700',
    'AIC': 'bg-orange-100 text-orange-700',
    'LOOKUP_FALLITO': 'bg-red-100 text-red-700',
    'LOOKUP': 'bg-red-100 text-red-700',
    'DUPLICATO': 'bg-yellow-100 text-yellow-700',
    'PREZZO_ZERO': 'bg-amber-100 text-amber-700',
    'PREZZO': 'bg-amber-100 text-amber-700',
    'LISTINO': 'bg-cyan-100 text-cyan-700',
    'QTA_ANOMALA': 'bg-pink-100 text-pink-700',
    'SCONTO_ANOMALO': 'bg-indigo-100 text-indigo-700',
    'VALIDAZIONE': 'bg-slate-100 text-slate-700',
    'ESTRAZIONE': 'bg-gray-100 text-gray-700',
  };
  return colors[tipoUpper] || 'bg-slate-100 text-slate-700';
};

// Colori per stato anomalia
export const getStatoAnomaliaColor = (stato) => {
  const statoUpper = (stato || '').toUpperCase();
  const colors = {
    'APERTA': 'bg-red-100 text-red-700',
    'IN_GESTIONE': 'bg-yellow-100 text-yellow-700',
    'RISOLTA': 'bg-green-100 text-green-700',
    'IGNORATA': 'bg-slate-100 text-slate-700'
  };
  return colors[statoUpper] || 'bg-slate-100 text-slate-700';
};

// Estrae il tipo normalizzato
export const getNormalizedTipo = (anomalia) => {
  return (anomalia.tipo || anomalia.tipo_anomalia || 'ALTRO').toUpperCase();
};

// Estrae la descrizione normalizzata
export const getNormalizedDescrizione = (anomalia) => {
  return anomalia.messaggio || anomalia.descrizione || '';
};
