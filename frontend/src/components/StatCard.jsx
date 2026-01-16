/**
 * StatCard Component - v6.2 Refactoring
 * Card per statistiche dashboard
 */
import React from 'react';

// Color presets per i vari tipi di stat
const colorPresets = {
  blue: { bg: 'bg-blue-100', text: 'text-blue-600' },
  green: { bg: 'bg-green-100', text: 'text-green-600' },
  amber: { bg: 'bg-amber-100', text: 'text-amber-600' },
  red: { bg: 'bg-red-100', text: 'text-red-600' },
  purple: { bg: 'bg-purple-100', text: 'text-purple-600' },
  slate: { bg: 'bg-slate-100', text: 'text-slate-600' },
  cyan: { bg: 'bg-cyan-100', text: 'text-cyan-600' },
  emerald: { bg: 'bg-emerald-100', text: 'text-emerald-600' },
  orange: { bg: 'bg-orange-100', text: 'text-orange-600' },
  indigo: { bg: 'bg-indigo-100', text: 'text-indigo-600' },
};

export function StatCard({
  label,
  value,
  icon,
  color = 'blue',
  onClick,
  className = ''
}) {
  const colors = colorPresets[color] || colorPresets.blue;

  const cardClasses = `
    bg-white p-4 rounded-xl border border-slate-200
    ${onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''}
    ${className}
  `.trim();

  return (
    <div className={cardClasses} onClick={onClick}>
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 ${colors.bg} rounded-lg flex items-center justify-center`}>
          {icon && <span className={colors.text}>{icon}</span>}
        </div>
        <div>
          <p className="text-xs text-slate-600 font-medium">{label}</p>
          <p className="text-xl font-bold text-slate-800">
            {typeof value === 'number' ? value.toLocaleString('it-IT') : value}
          </p>
        </div>
      </div>
    </div>
  );
}

// Wrapper per griglia di stat cards
export function StatCardGrid({ children, columns = 5 }) {
  const gridCols = {
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4',
    5: 'grid-cols-5',
    6: 'grid-cols-6',
  };

  return (
    <div className={`grid ${gridCols[columns] || 'grid-cols-5'} gap-4`}>
      {children}
    </div>
  );
}

export default StatCard;
