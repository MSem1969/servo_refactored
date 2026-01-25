// =============================================================================
// VENDOR BADGE COMPONENT
// =============================================================================
// Badge colorato per identificare fornitori farmaceutici
// Colori specifici per brand recognition
// =============================================================================

import React from 'react';

/**
 * Componente VendorBadge per fornitori farmaceutici
 * 
 * LOGICA IMPLEMENTATIVA:
 * - Ogni vendor ha colori brand specifici
 * - Gestione vendor sconosciuti con fallback
 * - Dimensioni responsive
 * - Acronimi per spazi ridotti
 * 
 * INTERRELAZIONI:
 * - Usato in: DatabasePage, DashboardPage, OrderDetailPage, SupervisionePage
 * - Sostituisce: tutti gli span vendor sparsi nel codice
 * 
 * @param {string} vendor - Nome vendor (ANGELINI, BAYER, etc.)
 * @param {boolean} showAcronym - Mostra solo acronimo (per spazi stretti)
 * @param {string} size - Dimensione (xs, sm, md)
 * @param {string} className - Classi aggiuntive
 */
const VendorBadge = ({ 
  vendor, 
  showAcronym = false, 
  size = 'sm',
  className = '' 
}) => {
  
  // Configurazione vendor con: colori, nome completo, acronimo
  // v6.2: Aggiunto DOC_GENERICI
  const vendorConfig = {
    ANGELINI: {
      bg: 'bg-blue-100',
      text: 'text-blue-700',
      border: 'border-blue-200',
      name: 'Angelini',
      acronym: 'ANG',
      icon: '🏥'
    },
    BAYER: {
      bg: 'bg-amber-100',
      text: 'text-amber-700',
      border: 'border-amber-200',
      name: 'Bayer',
      acronym: 'BAY',
      icon: '🌿'
    },
    CODIFI: {
      bg: 'bg-emerald-100',
      text: 'text-emerald-700',
      border: 'border-emerald-200',
      name: 'Codifi',
      acronym: 'COD',
      icon: '💊'
    },
    CHIESI: {
      bg: 'bg-purple-100',
      text: 'text-purple-700',
      border: 'border-purple-200',
      name: 'Chiesi',
      acronym: 'CHI',
      icon: '🫁'
    },
    MENARINI: {
      bg: 'bg-pink-100',
      text: 'text-pink-700',
      border: 'border-pink-200',
      name: 'Menarini',
      acronym: 'MEN',
      icon: '❤️'
    },
    OPELLA: {
      bg: 'bg-indigo-100',
      text: 'text-indigo-700',
      border: 'border-indigo-200',
      name: 'Opella',
      acronym: 'OPE',
      icon: '⚡'
    },
    DOC_GENERICI: {
      bg: 'bg-gray-100',
      text: 'text-gray-700',
      border: 'border-gray-300',
      name: 'DOC Generici',
      acronym: 'DOC',
      icon: '📦'
    },
    COOPER: {
      bg: 'bg-teal-100',
      text: 'text-teal-700',
      border: 'border-teal-200',
      name: 'Cooper',
      acronym: 'COP',
      icon: '🧴'
    },
    RECKITT: {
      bg: 'bg-rose-100',
      text: 'text-rose-700',
      border: 'border-rose-200',
      name: 'Reckitt',
      acronym: 'REC',
      icon: '💗'
    }
  };
  
  // Dimensioni badge
  const sizeClasses = {
    xs: 'px-1.5 py-0.5 text-xs',
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
  };
  
  // Configurazione per vendor corrente (con fallback)
  const config = vendorConfig[vendor?.toUpperCase()] || {
    bg: 'bg-slate-100',
    text: 'text-slate-700',
    border: 'border-slate-200',
    name: vendor || 'Sconosciuto',
    acronym: vendor?.substring(0, 3) || 'N/A',
    icon: '❓'
  };
  
  // Label da mostrare: acronimo o nome completo
  const displayLabel = showAcronym ? config.acronym : config.name;
  
  // Classi CSS finali
  const finalClasses = [
    'font-medium',
    'rounded',
    'inline-flex',
    'items-center',
    'gap-1',
    'border',
    'whitespace-nowrap',
    config.bg,
    config.text,
    config.border,
    sizeClasses[size] || sizeClasses.sm,
    className
  ].join(' ');
  
  return (
    <span 
      className={finalClasses}
      title={showAcronym ? config.name : `${config.name} - ${vendor}`}
    >
      {/* Icona vendor (opzionale, solo per size md+) */}
      {size !== 'xs' && (
        <span className="leading-none">{config.icon}</span>
      )}
      
      {/* Label vendor */}
      <span>{displayLabel}</span>
    </span>
  );
};

// Utility per ottenere lista vendor supportati
// v11.2: Lista aggiornata vendor abilitati + COOPER + RECKITT
VendorBadge.getSupportedVendors = () => {
  return ['DOC_GENERICI', 'CODIFI', 'COOPER', 'MENARINI', 'OPELLA', 'CHIESI', 'ANGELINI', 'BAYER', 'RECKITT'];
};

// Utility per verificare se vendor è supportato
VendorBadge.isSupported = (vendor) => {
  const supported = ['DOC_GENERICI', 'CODIFI', 'COOPER', 'MENARINI', 'OPELLA', 'CHIESI', 'ANGELINI', 'BAYER', 'RECKITT'];
  return supported.includes(vendor?.toUpperCase());
};

export { VendorBadge };
export default VendorBadge;
