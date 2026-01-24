/**
 * Widget flottante per assistenza - Accessibile da qualsiasi pagina
 */
import React, { useState, useRef } from 'react'
import { useCreateTicket, useUploadAttachment } from '../../hooks/useCrm'
import { Button } from '../../common'

const ALLOWED_TYPES = [
  'image/png', 'image/jpeg', 'image/gif',
  'application/pdf', 'text/plain'
]
const MAX_FILE_SIZE = 10 * 1024 * 1024

export default function FloatingWidget({ currentUser }) {
  const [isOpen, setIsOpen] = useState(false)
  const [form, setForm] = useState({
    categoria: 'assistenza',
    oggetto: '',
    contenuto: '',
    priorita: 'normale',
    pagina_origine: '',
    email_notifica: ''
  })
  const [files, setFiles] = useState([])
  const [success, setSuccess] = useState(false)
  const fileInputRef = useRef(null)

  const createMutation = useCreateTicket()
  const uploadMutation = useUploadAttachment()

  const handleOpen = () => {
    setIsOpen(true)
    setSuccess(false)
    // Cattura pagina corrente e email utente per notifiche
    setForm(prev => ({
      ...prev,
      pagina_origine: window.location.pathname,
      oggetto: '',
      contenuto: '',
      email_notifica: currentUser?.email || ''
    }))
  }

  const handleClose = () => {
    setIsOpen(false)
    setForm({
      categoria: 'assistenza',
      oggetto: '',
      contenuto: '',
      priorita: 'normale',
      pagina_origine: '',
      email_notifica: ''
    })
    setFiles([])
    setSuccess(false)
  }

  const handleChange = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files || [])
    const validFiles = selectedFiles.filter(file => {
      if (!ALLOWED_TYPES.includes(file.type)) return false
      if (file.size > MAX_FILE_SIZE) return false
      return true
    })
    setFiles(prev => [...prev, ...validFiles].slice(0, 3))
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!form.oggetto.trim() || !form.contenuto.trim()) {
      alert('Compila tutti i campi obbligatori')
      return
    }

    try {
      const result = await createMutation.mutateAsync(form)
      const ticketId = result.id_ticket

      // Upload allegati
      if (files.length > 0 && ticketId) {
        for (const file of files) {
          try {
            await uploadMutation.mutateAsync({ ticketId, file })
          } catch (err) {
            console.error('Errore upload:', err)
          }
        }
      }

      setSuccess(true)
      setForm({
        categoria: 'assistenza',
        oggetto: '',
        contenuto: '',
        priorita: 'normale',
        pagina_origine: '',
        email_notifica: ''
      })
      setFiles([])

      // Chiudi dopo 3 secondi
      setTimeout(() => {
        handleClose()
      }, 3000)

    } catch (err) {
      alert('Errore: ' + err.message)
    }
  }

  return (
    <>
      {/* Pulsante flottante */}
      <button
        onClick={handleOpen}
        className="fixed bottom-6 right-6 w-14 h-14 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg flex items-center justify-center text-2xl transition-all hover:scale-110 z-40"
        title="Apri assistenza"
      >
        🛠️
      </button>

      {/* Overlay */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/30 z-50 flex items-end justify-end p-4 sm:p-6">
          {/* Widget */}
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md max-h-[80vh] flex flex-col overflow-hidden animate-in">
            {/* Header */}
            <div className="bg-blue-600 text-white p-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xl">🛠️</span>
                <div>
                  <h3 className="font-semibold">Assistenza</h3>
                  <p className="text-xs text-blue-100">Come possiamo aiutarti?</p>
                </div>
              </div>
              <button
                onClick={handleClose}
                className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-blue-500 transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Content */}
            {success ? (
              <div className="p-8 text-center">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-3xl">✓</span>
                </div>
                <h4 className="text-lg font-semibold text-slate-800 mb-2">
                  Richiesta Inviata!
                </h4>
                <p className="text-sm text-slate-600">
                  Ti risponderemo il prima possibile.
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-4 space-y-4">
                {/* Tipo */}
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleChange('categoria', 'assistenza')}
                    className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                      form.categoria === 'assistenza'
                        ? 'bg-blue-100 text-blue-700 border-2 border-blue-500'
                        : 'bg-slate-100 text-slate-600 border-2 border-transparent'
                    }`}
                  >
                    🛠️ Assistenza
                  </button>
                  <button
                    type="button"
                    onClick={() => handleChange('categoria', 'miglioramento')}
                    className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                      form.categoria === 'miglioramento'
                        ? 'bg-purple-100 text-purple-700 border-2 border-purple-500'
                        : 'bg-slate-100 text-slate-600 border-2 border-transparent'
                    }`}
                  >
                    💡 Miglioramento
                  </button>
                </div>

                {/* Oggetto */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Oggetto *
                  </label>
                  <input
                    type="text"
                    value={form.oggetto}
                    onChange={(e) => handleChange('oggetto', e.target.value)}
                    placeholder={form.categoria === 'assistenza'
                      ? "Es: Errore durante l'upload"
                      : "Es: Aggiungere filtro per data"
                    }
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>

                {/* Descrizione */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Descrizione *
                  </label>
                  <textarea
                    value={form.contenuto}
                    onChange={(e) => handleChange('contenuto', e.target.value)}
                    placeholder={form.categoria === 'assistenza'
                      ? "Descrivi il problema nel dettaglio..."
                      : "Descrivi la tua proposta..."
                    }
                    rows={4}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>

                {/* Priorita (solo per assistenza) */}
                {form.categoria === 'assistenza' && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      Urgenza
                    </label>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => handleChange('priorita', 'bassa')}
                        className={`flex-1 py-1.5 px-2 rounded text-xs font-medium transition-colors ${
                          form.priorita === 'bassa'
                            ? 'bg-green-100 text-green-700 border border-green-300'
                            : 'bg-slate-50 text-slate-500 border border-slate-200'
                        }`}
                      >
                        Bassa
                      </button>
                      <button
                        type="button"
                        onClick={() => handleChange('priorita', 'normale')}
                        className={`flex-1 py-1.5 px-2 rounded text-xs font-medium transition-colors ${
                          form.priorita === 'normale'
                            ? 'bg-blue-100 text-blue-700 border border-blue-300'
                            : 'bg-slate-50 text-slate-500 border border-slate-200'
                        }`}
                      >
                        Normale
                      </button>
                      <button
                        type="button"
                        onClick={() => handleChange('priorita', 'alta')}
                        className={`flex-1 py-1.5 px-2 rounded text-xs font-medium transition-colors ${
                          form.priorita === 'alta'
                            ? 'bg-red-100 text-red-700 border border-red-300'
                            : 'bg-slate-50 text-slate-500 border border-slate-200'
                        }`}
                      >
                        Urgente
                      </button>
                    </div>
                  </div>
                )}

                {/* Allegati */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Screenshot/Allegati
                  </label>
                  <div className="border border-dashed border-slate-300 rounded-lg p-3">
                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      accept=".png,.jpg,.jpeg,.gif,.pdf,.txt"
                      onChange={handleFileSelect}
                      className="hidden"
                      id="widget-file-upload"
                    />
                    <label
                      htmlFor="widget-file-upload"
                      className="flex items-center justify-center gap-2 cursor-pointer text-slate-500 hover:text-slate-700"
                    >
                      <span>📎</span>
                      <span className="text-sm">Allega file (max 3)</span>
                    </label>
                  </div>

                  {files.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {files.map((file, index) => (
                        <div key={index} className="flex items-center justify-between p-2 bg-slate-50 rounded text-xs">
                          <span className="truncate">{file.name}</span>
                          <button
                            type="button"
                            onClick={() => removeFile(index)}
                            className="text-red-500 hover:text-red-700 ml-2"
                          >
                            ✕
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Info pagina */}
                {form.pagina_origine && (
                  <p className="text-xs text-slate-400">
                    Pagina: {form.pagina_origine}
                  </p>
                )}

                {/* Submit */}
                <Button
                  type="submit"
                  variant="primary"
                  className="w-full"
                  loading={createMutation.isPending}
                  disabled={createMutation.isPending}
                >
                  Invia Richiesta
                </Button>
              </form>
            )}

            {/* Footer */}
            <div className="px-4 py-2 bg-slate-50 border-t border-slate-200">
              <p className="text-xs text-slate-400 text-center">
                {currentUser?.username && `Connesso come ${currentUser.username}`}
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
