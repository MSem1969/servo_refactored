/**
 * Card singolo ticket (assistenza/miglioramento) nella lista
 */
import React from 'react'

const STATUS_STYLES = {
  aperto: { bg: 'bg-blue-100', text: 'text-blue-700', dot: 'bg-blue-500' },
  in_lavorazione: { bg: 'bg-amber-100', text: 'text-amber-700', dot: 'bg-amber-500' },
  chiuso: { bg: 'bg-slate-100', text: 'text-slate-700', dot: 'bg-slate-500' },
}

const PRIORITY_STYLES = {
  bassa: { icon: '🟢', label: 'Bassa' },
  normale: { icon: '🟡', label: 'Normale' },
  alta: { icon: '🔴', label: 'Alta' },
}

const CATEGORY_ICONS = {
  assistenza: '🛠️',
  miglioramento: '💡'
}

export default function TicketCard({ ticket, onClick, isSelected }) {
  const status = STATUS_STYLES[ticket.stato] || STATUS_STYLES.aperto
  const priority = PRIORITY_STYLES[ticket.priorita] || PRIORITY_STYLES.normale
  const categoryIcon = CATEGORY_ICONS[ticket.categoria] || '📋'

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now - date
    const hours = Math.floor(diff / (1000 * 60 * 60))

    if (hours < 1) return 'Adesso'
    if (hours < 24) return `${hours}h fa`
    if (hours < 48) return 'Ieri'
    return date.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' })
  }

  return (
    <div
      onClick={onClick}
      className={`p-3 border rounded-lg cursor-pointer transition-all ${
        isSelected
          ? 'border-blue-500 bg-blue-50 shadow-sm'
          : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span title={ticket.categoria === 'assistenza' ? 'Assistenza' : 'Miglioramento'}>
            {categoryIcon}
          </span>
          <div className={`w-2 h-2 rounded-full ${status.dot}`} />
          <span className="text-xs font-mono text-slate-500">#{ticket.id_ticket}</span>
        </div>
        <span className="text-xs text-slate-400">{formatDate(ticket.updated_at)}</span>
      </div>

      <h4 className="text-sm font-medium text-slate-800 mb-1 line-clamp-2">
        {ticket.oggetto}
      </h4>

      <p className="text-xs text-slate-500 mb-2">
        da: {ticket.operatore_nome || 'Utente'}
      </p>

      <div className="flex items-center justify-between">
        <span className={`px-2 py-0.5 text-xs font-medium rounded ${status.bg} ${status.text}`}>
          {ticket.stato?.replace('_', ' ')}
        </span>
        <span className="text-xs" title={priority.label}>{priority.icon}</span>
      </div>

      {ticket.num_messaggi > 0 && (
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center gap-1 text-xs text-slate-400">
          <span>💬</span>
          <span>{ticket.num_messaggi} messaggi</span>
        </div>
      )}
    </div>
  )
}
