/**
 * Avatar.jsx - Componente Avatar riutilizzabile
 *
 * Mostra avatar utente con fallback a iniziali colorate.
 * Supporta diverse dimensioni e può mostrare immagine base64.
 */

import React from 'react'

// Colori per fallback iniziali (basati su hash del nome)
const COLORS = [
  'bg-blue-500',
  'bg-green-500',
  'bg-yellow-500',
  'bg-red-500',
  'bg-purple-500',
  'bg-pink-500',
  'bg-indigo-500',
  'bg-teal-500',
  'bg-orange-500',
  'bg-cyan-500'
]

/**
 * Genera colore deterministico basato su stringa
 */
function getColorFromString(str) {
  if (!str) return COLORS[0]
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
  }
  return COLORS[Math.abs(hash) % COLORS.length]
}

/**
 * Estrae iniziali da nome e cognome
 */
function getInitials(nome, cognome) {
  const n = nome?.[0]?.toUpperCase() || ''
  const c = cognome?.[0]?.toUpperCase() || ''
  return n + c || '?'
}

/**
 * Componente Avatar
 *
 * @param {Object} props
 * @param {Object} props.user - Oggetto utente { nome, cognome, avatar_base64 }
 * @param {string} props.size - Dimensione: 'xs', 'sm', 'md', 'lg', 'xl' (default: 'md')
 * @param {string} props.className - Classi CSS aggiuntive
 * @param {boolean} props.showTooltip - Mostra tooltip con nome (default: false)
 * @param {Function} props.onClick - Handler click (se presente, rende cliccabile)
 */
export default function Avatar({
  user,
  size = 'md',
  className = '',
  showTooltip = false,
  onClick
}) {
  // Dimensioni per ogni size
  const sizes = {
    xs: 'w-5 h-5 text-[10px]',
    sm: 'w-6 h-6 text-xs',
    md: 'w-8 h-8 text-sm',
    lg: 'w-10 h-10 text-base',
    xl: 'w-16 h-16 text-xl'
  }

  const sizeClass = sizes[size] || sizes.md
  const fullName = `${user?.nome || ''} ${user?.cognome || ''}`.trim() || 'Utente'

  // Classi base
  const baseClasses = `
    ${sizeClass}
    rounded-full
    flex items-center justify-center
    font-medium
    select-none
    ${onClick ? 'cursor-pointer hover:opacity-80 transition-opacity' : ''}
    ${className}
  `.trim().replace(/\s+/g, ' ')

  // Se ha avatar base64, mostra immagine
  if (user?.avatar_base64) {
    return (
      <img
        src={user.avatar_base64}
        alt={fullName}
        title={showTooltip ? fullName : undefined}
        className={`${baseClasses} object-cover`}
        onClick={onClick}
      />
    )
  }

  // Fallback: iniziali con colore basato su nome
  const initials = getInitials(user?.nome, user?.cognome)
  const bgColor = getColorFromString((user?.nome || '') + (user?.cognome || ''))

  return (
    <div
      className={`${baseClasses} ${bgColor} text-white`}
      title={showTooltip ? fullName : undefined}
      onClick={onClick}
    >
      {initials}
    </div>
  )
}

/**
 * Componente AvatarWithName - Avatar con nome affiancato
 */
export function AvatarWithName({
  user,
  size = 'md',
  className = '',
  showRole = false,
  onClick
}) {
  const fullName = `${user?.nome || ''} ${user?.cognome || ''}`.trim() || user?.username || 'Utente'

  return (
    <div
      className={`flex items-center gap-2 ${onClick ? 'cursor-pointer' : ''} ${className}`}
      onClick={onClick}
    >
      <Avatar user={user} size={size} />
      <div className="min-w-0">
        <p className="font-medium text-gray-900 truncate">{fullName}</p>
        {showRole && user?.ruolo && (
          <p className="text-xs text-gray-500 capitalize">{user.ruolo}</p>
        )}
      </div>
    </div>
  )
}
