/**
 * CRM - Assistenza e Miglioramenti
 * Container principale per gestione richieste utenti
 */
import React, { useState } from 'react'
import { Button } from '../../common'
import TicketList from './TicketList'
import TicketDetail from './TicketDetail'
import NewTicketForm from './NewTicketForm'

export default function CrmChatbot({ currentUser }) {
  const [selectedTicketId, setSelectedTicketId] = useState(null)
  const [showNewTicket, setShowNewTicket] = useState(false)

  const handleNewTicketSuccess = (ticket) => {
    setShowNewTicket(false)
    setSelectedTicketId(ticket.id_ticket)
  }

  return (
    <div className="flex h-[calc(100vh-180px)] bg-white rounded-xl border border-slate-200 overflow-hidden">
      {/* Sidebar sinistra - Lista richieste */}
      <div className="w-80 border-r border-slate-200 flex flex-col">
        <div className="p-3 border-b border-slate-200 flex items-center justify-between">
          <h2 className="font-semibold text-slate-800">Richieste</h2>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowNewTicket(true)}
          >
            + Nuova
          </Button>
        </div>
        <TicketList
          selectedId={selectedTicketId}
          onSelect={setSelectedTicketId}
        />
      </div>

      {/* Area principale - Dettaglio o nuovo ticket */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {showNewTicket ? (
          <NewTicketForm
            onSuccess={handleNewTicketSuccess}
            onCancel={() => setShowNewTicket(false)}
          />
        ) : (
          <TicketDetail
            ticketId={selectedTicketId}
            currentUserId={currentUser?.id_operatore}
          />
        )}
      </div>
    </div>
  )
}
