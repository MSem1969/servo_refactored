/**
 * Dettaglio ticket con messaggi e allegati
 */
import React, { useState, useRef } from 'react'
import { useTicket, useTicketMessages, useAddMessage, useUpdateTicketStatus, useTicketAttachments, useUploadAttachment } from '../../hooks/useCrm'
import { crmApi } from '../../api'
import { Button, Loading } from '../../common'
import MessageThread from './MessageThread'

const STATUS_OPTIONS = [
  { value: 'aperto', label: 'Aperto' },
  { value: 'in_lavorazione', label: 'In lavorazione' },
  { value: 'chiuso', label: 'Chiuso' },
]

const CATEGORY_LABELS = {
  assistenza: 'Richiesta Assistenza',
  miglioramento: 'Proposta Miglioramento'
}

export default function TicketDetail({ ticketId, currentUserId }) {
  const [newMessage, setNewMessage] = useState('')
  const fileInputRef = useRef(null)

  const { data: ticket, isLoading: loadingTicket } = useTicket(ticketId)
  const { data: messages, isLoading: loadingMessages } = useTicketMessages(ticketId)
  const { data: attachments } = useTicketAttachments(ticketId)
  const addMessageMutation = useAddMessage()
  const updateStatusMutation = useUpdateTicketStatus()
  const uploadMutation = useUploadAttachment()

  const handleSendMessage = async () => {
    if (!newMessage.trim()) return
    try {
      await addMessageMutation.mutateAsync({
        ticketId,
        contenuto: newMessage.trim()
      })
      setNewMessage('')
    } catch (err) {
      alert('Errore invio messaggio: ' + err.message)
    }
  }

  const handleStatusChange = async (newStatus) => {
    try {
      await updateStatusMutation.mutateAsync({
        id: ticketId,
        stato: newStatus
      })
    } catch (err) {
      alert('Errore cambio stato: ' + err.message)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      await uploadMutation.mutateAsync({ ticketId, file })
    } catch (err) {
      alert('Errore upload: ' + err.message)
    }

    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleDownload = (allegato) => {
    // Usa fetch con auth header per download
    const url = crmApi.getAttachmentUrl(allegato.id_allegato)
    window.open(url, '_blank')
  }

  if (!ticketId) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        Seleziona una richiesta per visualizzarla
      </div>
    )
  }

  if (loadingTicket) return <Loading text="Caricamento..." />

  if (!ticket?.data) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        Richiesta non trovata
      </div>
    )
  }

  const ticketData = ticket.data
  const allegatiList = attachments?.data || []

  return (
    <div className="flex flex-col h-full">
      {/* Header ticket */}
      <div className="p-4 border-b border-slate-200 bg-slate-50">
        <div className="flex items-start justify-between gap-3 mb-2">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono text-slate-400">#{ticketData.id_ticket}</span>
              <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                ticketData.categoria === 'assistenza'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-purple-100 text-purple-700'
              }`}>
                {CATEGORY_LABELS[ticketData.categoria] || ticketData.categoria}
              </span>
            </div>
            <h3 className="text-lg font-semibold text-slate-800">{ticketData.oggetto}</h3>
          </div>
          <select
            value={ticketData.stato}
            onChange={(e) => handleStatusChange(e.target.value)}
            disabled={updateStatusMutation.isPending}
            className="px-3 py-1.5 border border-slate-200 rounded-lg text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {STATUS_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-4 text-xs text-slate-500">
          <span>Da: <strong className="text-slate-700">{ticketData.operatore_nome || 'Utente'}</strong></span>
          {ticketData.pagina_origine && (
            <span>Pagina: <strong className="text-slate-700">{ticketData.pagina_origine}</strong></span>
          )}
          <span>Creato: {new Date(ticketData.created_at).toLocaleDateString('it-IT')}</span>
        </div>

        {/* Allegati */}
        {allegatiList.length > 0 && (
          <div className="mt-3 p-3 bg-white rounded-lg border border-slate-200">
            <p className="text-xs text-slate-500 mb-2">Allegati ({allegatiList.length}):</p>
            <div className="flex flex-wrap gap-2">
              {allegatiList.map(allegato => (
                <button
                  key={allegato.id_allegato}
                  onClick={() => handleDownload(allegato)}
                  className="flex items-center gap-1 px-2 py-1 bg-slate-50 hover:bg-slate-100 rounded text-sm text-slate-700"
                >
                  <span>{allegato.mime_type?.startsWith('image/') ? '🖼️' : '📄'}</span>
                  <span className="truncate max-w-[150px]">{allegato.nome_originale}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Thread messaggi */}
      {loadingMessages ? (
        <div className="flex-1 flex items-center justify-center">
          <Loading text="Caricamento messaggi..." />
        </div>
      ) : (
        <MessageThread
          messages={messages?.data || []}
          currentUserId={currentUserId}
        />
      )}

      {/* Input nuovo messaggio */}
      {ticketData.stato !== 'chiuso' && (
        <div className="p-4 border-t border-slate-200 bg-white">
          <div className="flex gap-2">
            <div className="flex-1 flex gap-2">
              <textarea
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Scrivi un messaggio... (Invio per inviare)"
                rows={2}
                className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {/* Upload allegato */}
              <div className="flex flex-col gap-1">
                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="attach-file"
                />
                <label
                  htmlFor="attach-file"
                  className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded cursor-pointer self-start"
                  title="Allega file"
                >
                  📎
                </label>
              </div>
            </div>
            <Button
              variant="primary"
              onClick={handleSendMessage}
              loading={addMessageMutation.isPending}
              disabled={!newMessage.trim() || addMessageMutation.isPending}
              className="self-end"
            >
              Invia
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
