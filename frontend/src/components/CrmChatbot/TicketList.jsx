/**
 * Lista richieste (assistenza/miglioramenti) con filtri
 */
import React, { useState } from 'react'
import { useTickets, useCrmConstants, useCrmStats } from '../../hooks/useCrm'
import { Loading } from '../../common'
import TicketCard from './TicketCard'

export default function TicketList({ selectedId, onSelect }) {
  const [filters, setFilters] = useState({ stato: '', categoria: '' })
  const [search, setSearch] = useState('')

  const { data: tickets, isLoading, error } = useTickets(filters)
  const { data: constants } = useCrmConstants()
  const { data: stats } = useCrmStats()

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const filteredTickets = React.useMemo(() => {
    if (!tickets?.data) return []
    if (!search) return tickets.data
    const s = search.toLowerCase()
    return tickets.data.filter(t =>
      t.oggetto?.toLowerCase().includes(s) ||
      t.operatore_nome?.toLowerCase().includes(s) ||
      t.id_ticket?.toString() === s
    )
  }, [tickets, search])

  if (error) return <div className="p-4 text-red-600">Errore: {error.message}</div>

  const statsData = stats?.data || {}

  return (
    <div className="flex flex-col h-full">
      {/* Stats rapide */}
      <div className="p-3 bg-slate-50 border-b border-slate-200 grid grid-cols-3 gap-2">
        <div className="text-center">
          <p className="text-lg font-bold text-blue-600">{statsData.aperti || 0}</p>
          <p className="text-xs text-slate-500">Aperte</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold text-amber-600">{statsData.in_lavorazione || 0}</p>
          <p className="text-xs text-slate-500">In corso</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold text-slate-600">{statsData.chiusi || 0}</p>
          <p className="text-xs text-slate-500">Chiuse</p>
        </div>
      </div>

      {/* Filtri */}
      <div className="p-3 border-b border-slate-200 space-y-2">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Cerca richiesta..."
          className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div className="flex gap-2">
          <select
            value={filters.stato}
            onChange={(e) => handleFilterChange('stato', e.target.value)}
            className="flex-1 px-2 py-1.5 border border-slate-200 rounded text-xs"
          >
            <option value="">Tutti gli stati</option>
            {constants?.data?.stati?.map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
          <select
            value={filters.categoria}
            onChange={(e) => handleFilterChange('categoria', e.target.value)}
            className="flex-1 px-2 py-1.5 border border-slate-200 rounded text-xs"
          >
            <option value="">Tutte</option>
            {constants?.data?.categorie?.map(c => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Lista */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {isLoading ? (
          <Loading text="Caricamento..." />
        ) : filteredTickets.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            <p className="mb-2">Nessuna richiesta trovata</p>
            <p className="text-xs">Clicca "Nuovo" per creare una richiesta</p>
          </div>
        ) : (
          filteredTickets.map(ticket => (
            <TicketCard
              key={ticket.id_ticket}
              ticket={ticket}
              isSelected={selectedId === ticket.id_ticket}
              onClick={() => onSelect(ticket.id_ticket)}
            />
          ))
        )}
      </div>
    </div>
  )
}
