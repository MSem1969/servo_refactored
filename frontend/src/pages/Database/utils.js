// =============================================================================
// SERV.O v7.0 - DATABASE PAGE UTILS
// =============================================================================
// Helper functions per componenti database
// =============================================================================

// Aggiunge giorni lavorativi ad una data
export const addBusinessDays = (date, days) => {
  const result = new Date(date);
  let addedDays = 0;

  while (addedDays < days) {
    result.setDate(result.getDate() + 1);
    const dayOfWeek = result.getDay();
    if (dayOfWeek !== 0 && dayOfWeek !== 6) {
      addedDays++;
    }
  }
  return result;
};

// Parse data consegna in formato Date
export const parseDataConsegna = (dataStr, dataOrdineStr) => {
  if (!dataStr) {
    if (dataOrdineStr) {
      const dataOrdine = new Date(dataOrdineStr);
      return addBusinessDays(dataOrdine, 10);
    }
    return new Date();
  }

  if (typeof dataStr === 'string') {
    if (dataStr.includes('/')) {
      const [day, month, year] = dataStr.split('/');
      return new Date(year, month - 1, day);
    }
    if (dataStr.includes('-')) {
      return new Date(dataStr);
    }
  }

  return new Date(dataStr);
};

// Calcola urgenza consegna
export const getUrgenza = (dataConsegnaStr, dataOrdineStr) => {
  const dataConsegna = parseDataConsegna(dataConsegnaStr, dataOrdineStr);
  const oggi = new Date();
  oggi.setHours(0, 0, 0, 0);
  dataConsegna.setHours(0, 0, 0, 0);

  const diffDays = Math.ceil((dataConsegna - oggi) / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return 'SCADUTO';
  if (diffDays <= 2) return 'URGENTE';
  return 'ORDINARIO';
};

// Formatta data per display DD/MM/YYYY
export const formatDataForDisplay = (dataStr) => {
  if (!dataStr) return '-';
  if (dataStr.includes('/')) return dataStr;
  if (dataStr.includes('-')) {
    const [anno, mese, giorno] = dataStr.split('-');
    return `${giorno}/${mese}/${anno}`;
  }
  return dataStr;
};

// Classe CSS per highlighting riga in base a urgenza
export const getRowHighlightClass = (dataConsegnaStr, dataOrdineStr) => {
  const urgenza = getUrgenza(dataConsegnaStr, dataOrdineStr);
  switch (urgenza) {
    case 'SCADUTO':
      return 'bg-red-50 border-l-4 border-l-red-500';
    case 'URGENTE':
      return 'bg-amber-50 border-l-4 border-l-amber-400';
    default:
      return '';
  }
};

// Colori per tipi anomalia
export const getTipoAnomaliaColor = (tipo) => {
  const colors = {
    'ESPOSITORE': 'bg-purple-100 text-purple-700',
    'NO_AIC': 'bg-orange-100 text-orange-700',
    'LOOKUP_FALLITO': 'bg-red-100 text-red-700',
    'DUPLICATO': 'bg-yellow-100 text-yellow-700',
    'PREZZO_ZERO': 'bg-amber-100 text-amber-700'
  };
  return colors[tipo] || 'bg-slate-100 text-slate-700';
};

// Colori per severita anomalia
export const getSeveritaColor = (severita) => {
  const colors = {
    'CRITICAL': 'bg-red-200 text-red-800',
    'ERROR': 'bg-red-100 text-red-700',
    'WARNING': 'bg-yellow-100 text-yellow-700'
  };
  return colors[severita] || 'bg-blue-100 text-blue-700';
};

// Colori per stato anomalia
export const getStatoAnomaliaColor = (stato) => {
  const colors = {
    'APERTA': 'bg-red-100 text-red-700',
    'IN_GESTIONE': 'bg-yellow-100 text-yellow-700',
    'RISOLTA': 'bg-green-100 text-green-700',
    'IGNORATA': 'bg-slate-100 text-slate-700'
  };
  return colors[stato] || 'bg-slate-100 text-slate-700';
};
