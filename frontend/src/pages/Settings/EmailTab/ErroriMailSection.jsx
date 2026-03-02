/**
 * Sezione email in stato ERRORE con possibilità di scaricare il PDF originale
 */
import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { mailApi } from '../../../api/mail'
import { Loading } from '../../../common'

export default function ErroriMailSection() {
  const [downloading, setDownloading] = useState(null)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['mail-emails-errori'],
    queryFn: () => mailApi.getEmails({ stato: 'ERRORE', limit: 100 }),
  })

  const handleDownloadPdf = async (emailItem) => {
    setDownloading(emailItem.id_email)
    try {
      const response = await mailApi.downloadPdf(emailItem.id_email)
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = emailItem.attachment_filename || `email_${emailItem.id_email}.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      a.remove()
    } catch (err) {
      const message = err.response?.status === 404
        ? 'PDF non trovato sul server email. Potrebbe essere stato eliminato.'
        : `Errore download: ${err.message}`
      alert(message)
    } finally {
      setDownloading(null)
    }
  }

  if (isLoading) return <Loading text="Caricamento email in errore..." />
  if (error) return <div className="text-red-600 text-sm">Errore: {error.message}</div>

  const emails = data?.emails || []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium text-slate-800">Email in Errore</h4>
          <p className="text-xs text-slate-500 mt-1">
            Scarica il PDF per effettuare un upload manuale tramite il menu Upload
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
        >
          Ricarica
        </button>
      </div>

      {emails.length === 0 ? (
        <div className="p-8 text-center bg-slate-50 rounded-lg">
          <p className="text-slate-500">Nessuna email in errore</p>
        </div>
      ) : (
        <div className="border border-slate-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-3 py-2 font-medium text-slate-600">Data</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">Mittente</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">Oggetto</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">File PDF</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">Errore</th>
                <th className="text-right px-3 py-2 font-medium text-slate-600">Azioni</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {emails.map((item) => (
                <tr key={item.id_email} className="hover:bg-slate-50">
                  <td className="px-3 py-2 text-slate-600 whitespace-nowrap">
                    {item.received_date
                      ? new Date(item.received_date).toLocaleDateString('it-IT', {
                          day: '2-digit', month: '2-digit', year: 'numeric',
                          hour: '2-digit', minute: '2-digit'
                        })
                      : '-'}
                  </td>
                  <td className="px-3 py-2 text-slate-700 max-w-[160px] truncate" title={item.sender_email}>
                    {item.sender_name || item.sender_email || '-'}
                  </td>
                  <td className="px-3 py-2 text-slate-700 max-w-[200px] truncate" title={item.subject}>
                    {item.subject || '-'}
                  </td>
                  <td className="px-3 py-2 text-slate-600 max-w-[160px] truncate" title={item.attachment_filename}>
                    {item.attachment_filename || '-'}
                  </td>
                  <td className="px-3 py-2 max-w-[200px]">
                    <span className="text-red-600 text-xs truncate block" title={item.errore_messaggio}>
                      {item.errore_messaggio || 'Errore sconosciuto'}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right whitespace-nowrap">
                    <button
                      onClick={() => handleDownloadPdf(item)}
                      disabled={downloading === item.id_email}
                      className="px-2.5 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50 border border-blue-200 rounded transition-colors disabled:opacity-50"
                    >
                      {downloading === item.id_email ? 'Download...' : 'Scarica PDF'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
