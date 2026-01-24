/**
 * Thread messaggi di un ticket
 */
import React, { useRef, useEffect } from 'react'

export default function MessageThread({ messages = [], currentUserId }) {
  const bottomRef = useRef(null)

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const formatTime = (dateStr) => {
    if (!dateStr) return ''
    return new Date(dateStr).toLocaleString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400 text-sm">
        Nessun messaggio in questo ticket
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((msg) => {
        const isOwn = msg.autore_id === currentUserId
        const isSystem = msg.tipo === 'sistema'

        if (isSystem) {
          return (
            <div key={msg.id} className="flex justify-center">
              <div className="px-3 py-1 bg-slate-100 rounded-full text-xs text-slate-500">
                {msg.contenuto}
              </div>
            </div>
          )
        }

        return (
          <div
            key={msg.id}
            className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[75%] rounded-lg p-3 ${
                isOwn
                  ? 'bg-blue-500 text-white'
                  : 'bg-slate-100 text-slate-800'
              }`}
            >
              {!isOwn && (
                <p className={`text-xs font-medium mb-1 ${isOwn ? 'text-blue-100' : 'text-slate-500'}`}>
                  {msg.autore_nome || 'Operatore'}
                </p>
              )}
              <p className="text-sm whitespace-pre-wrap">{msg.contenuto}</p>
              <p className={`text-xs mt-1 ${isOwn ? 'text-blue-200' : 'text-slate-400'}`}>
                {formatTime(msg.created_at)}
              </p>
            </div>
          </div>
        )
      })}
      <div ref={bottomRef} />
    </div>
  )
}
