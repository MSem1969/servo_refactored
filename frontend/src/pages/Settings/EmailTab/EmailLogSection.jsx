/**
 * Sezione log email inviate
 */
import React from 'react'
import { useEmailLog, useRetryEmail } from '../../../hooks/useEmail'
import { StatusBadge, Loading } from '../../../common'

const STATUS_COLORS = {
  sent: { bg: 'bg-emerald-100', text: 'text-emerald-700', label: 'Inviata' },
  failed: { bg: 'bg-red-100', text: 'text-red-700', label: 'Fallita' },
  pending: { bg: 'bg-amber-100', text: 'text-amber-700', label: 'In coda' },
  retry: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Retry' },
}

export default function EmailLogSection() {
  const { data: logs, isLoading, error } = useEmailLog({ limit: 50 })
  const retryMutation = useRetryEmail()

  const handleRetry = async (logId) => {
    try {
      await retryMutation.mutateAsync(logId)
      alert('Email reinviata con successo')
    } catch (err) {
      alert('Errore: ' + err.message)
    }
  }

  if (isLoading) return <Loading text="Caricamento log..." />
  if (error) return <div className="text-red-600 text-sm">Errore: {error.message}</div>

  const items = logs?.items || []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-slate-800">Log Email Inviate</h4>
        <span className="text-xs text-slate-500">{items.length} email</span>
      </div>

      {items.length === 0 ? (
        <div className="p-8 text-center bg-slate-50 rounded-lg">
          <p className="text-slate-500">Nessuna email inviata</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {items.map((log) => {
            const status = STATUS_COLORS[log.stato] || STATUS_COLORS.pending
            return (
              <div
                key={log.id}
                className="p-3 border border-slate-200 rounded-lg hover:bg-slate-50"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 text-xs font-medium rounded ${status.bg} ${status.text}`}>
                        {status.label}
                      </span>
                      <span className="text-xs text-slate-400">
                        {new Date(log.created_at).toLocaleString('it-IT')}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-slate-800 truncate">
                      {log.oggetto}
                    </p>
                    <p className="text-xs text-slate-500 truncate">
                      A: {log.destinatario}
                    </p>
                    {log.errore && (
                      <p className="text-xs text-red-600 mt-1 truncate">
                        Errore: {log.errore}
                      </p>
                    )}
                  </div>
                  {log.stato === 'failed' && (
                    <button
                      onClick={() => handleRetry(log.id)}
                      disabled={retryMutation.isPending}
                      className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                    >
                      Riprova
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
