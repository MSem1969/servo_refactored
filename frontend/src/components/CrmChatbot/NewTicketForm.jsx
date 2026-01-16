/**
 * Form per creare un nuovo ticket (assistenza/miglioramento)
 * Con supporto per allegati
 */
import React, { useState, useRef } from 'react'
import { useCreateTicket, useCrmConstants, useUploadAttachment } from '../../hooks/useCrm'
import { Button } from '../../common'

const INITIAL_FORM = {
  oggetto: '',
  contenuto: '',
  categoria: 'assistenza',
  priorita: 'normale',
  pagina_origine: window.location.pathname,
}

// Formati file permessi
const ALLOWED_TYPES = [
  'image/png', 'image/jpeg', 'image/gif',
  'application/pdf',
  'text/plain',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
]
const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10 MB
const MAX_FILES = 5

export default function NewTicketForm({ onSuccess, onCancel }) {
  const [form, setForm] = useState(INITIAL_FORM)
  const [files, setFiles] = useState([])
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef(null)

  const { data: constants } = useCrmConstants()
  const createMutation = useCreateTicket()
  const uploadMutation = useUploadAttachment()

  const handleChange = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files || [])

    // Validazione
    const validFiles = selectedFiles.filter(file => {
      if (!ALLOWED_TYPES.includes(file.type)) {
        alert(`Formato non supportato: ${file.name}`)
        return false
      }
      if (file.size > MAX_FILE_SIZE) {
        alert(`File troppo grande: ${file.name} (max 10 MB)`)
        return false
      }
      return true
    })

    // Max 5 file
    const newFiles = [...files, ...validFiles].slice(0, MAX_FILES)
    setFiles(newFiles)

    // Reset input
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!form.oggetto.trim()) {
      alert('Inserisci un oggetto per la richiesta')
      return
    }
    if (!form.contenuto.trim()) {
      alert('Inserisci una descrizione della richiesta')
      return
    }

    try {
      // 1. Crea ticket
      const result = await createMutation.mutateAsync(form)
      const ticketId = result.id_ticket

      // 2. Upload allegati (se presenti)
      if (files.length > 0 && ticketId) {
        setUploading(true)
        for (const file of files) {
          try {
            await uploadMutation.mutateAsync({ ticketId, file })
          } catch (err) {
            console.error('Errore upload:', err)
          }
        }
        setUploading(false)
      }

      setForm(INITIAL_FORM)
      setFiles([])
      onSuccess?.(result)

    } catch (err) {
      alert('Errore creazione ticket: ' + err.message)
    }
  }

  const categorie = constants?.data?.categorie || [
    { value: 'assistenza', label: 'Richiesta Assistenza' },
    { value: 'miglioramento', label: 'Proposta Miglioramento' }
  ]

  const prioritaOptions = constants?.data?.priorita || [
    { value: 'bassa', label: 'Bassa' },
    { value: 'normale', label: 'Normale' },
    { value: 'alta', label: 'Alta' }
  ]

  return (
    <form onSubmit={handleSubmit} className="p-4 space-y-4">
      <h3 className="text-lg font-semibold text-slate-800">Nuova Richiesta</h3>

      {/* Tipo richiesta */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Tipo Richiesta *
          </label>
          <select
            value={form.categoria}
            onChange={(e) => handleChange('categoria', e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {categorie.map(cat => (
              <option key={cat.value} value={cat.value}>{cat.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Priorita
          </label>
          <select
            value={form.priorita}
            onChange={(e) => handleChange('priorita', e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {prioritaOptions.map(p => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </div>
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
          placeholder="Breve descrizione della richiesta"
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
            ? "Descrivi il problema riscontrato, includendo eventuali messaggi di errore..."
            : "Descrivi la funzionalita o il miglioramento che vorresti..."
          }
          rows={5}
          className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          required
        />
      </div>

      {/* Allegati */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Allegati (opzionale)
        </label>
        <div className="border-2 border-dashed border-slate-200 rounded-lg p-4">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".png,.jpg,.jpeg,.gif,.pdf,.txt,.doc,.docx,.xls,.xlsx"
            onChange={handleFileSelect}
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className="flex flex-col items-center justify-center cursor-pointer text-slate-500 hover:text-slate-700"
          >
            <span className="text-2xl mb-1">📎</span>
            <span className="text-sm">Clicca per allegare file</span>
            <span className="text-xs text-slate-400 mt-1">
              PNG, JPG, PDF, TXT, DOC, XLS (max 10 MB, max 5 file)
            </span>
          </label>
        </div>

        {/* Lista file selezionati */}
        {files.length > 0 && (
          <div className="mt-2 space-y-1">
            {files.map((file, index) => (
              <div key={index} className="flex items-center justify-between p-2 bg-slate-50 rounded text-sm">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="flex-shrink-0">
                    {file.type.startsWith('image/') ? '🖼️' : '📄'}
                  </span>
                  <span className="truncate">{file.name}</span>
                  <span className="text-xs text-slate-400 flex-shrink-0">
                    ({(file.size / 1024).toFixed(0)} KB)
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => removeFile(index)}
                  className="text-red-500 hover:text-red-700 p-1"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pulsanti */}
      <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
        {onCancel && (
          <Button type="button" variant="secondary" onClick={onCancel}>
            Annulla
          </Button>
        )}
        <Button
          type="submit"
          variant="primary"
          loading={createMutation.isPending || uploading}
          disabled={createMutation.isPending || uploading}
        >
          {uploading ? 'Caricamento allegati...' : 'Invia Richiesta'}
        </Button>
      </div>
    </form>
  )
}
