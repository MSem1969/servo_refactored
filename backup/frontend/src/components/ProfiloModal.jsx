/**
 * ProfiloModal.jsx - Modal per modifica profilo personale
 *
 * Permette all'utente di modificare:
 * - Nome e cognome
 * - Data di nascita
 * - Avatar (upload immagine)
 */

import React, { useState, useEffect, useRef } from 'react'
import Modal from './Modal'
import Avatar from './Avatar'
import { utentiApi } from '../api'

/**
 * Modal Profilo Personale
 *
 * @param {Object} props
 * @param {boolean} props.isOpen - Se il modal e' aperto
 * @param {Function} props.onClose - Handler chiusura
 * @param {Object} props.user - Utente corrente
 * @param {Function} props.onUpdate - Callback dopo aggiornamento (riceve utente aggiornato)
 */
export default function ProfiloModal({ isOpen, onClose, user, onUpdate }) {
  const fileInputRef = useRef(null)

  // Form state
  const [formData, setFormData] = useState({
    nome: '',
    cognome: '',
    data_nascita: '',
    avatar_base64: ''
  })
  const [previewAvatar, setPreviewAvatar] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  // Inizializza form quando si apre il modal o cambia utente
  useEffect(() => {
    if (isOpen && user) {
      setFormData({
        nome: user.nome || '',
        cognome: user.cognome || '',
        data_nascita: user.data_nascita || '',
        avatar_base64: '' // Non pre-popolare, solo se cambia
      })
      setPreviewAvatar(user.avatar_base64 || null)
      setError(null)
      setSuccess(false)
    }
  }, [isOpen, user])

  // Handler cambio input
  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    setError(null)
  }

  // Handler upload immagine
  const handleImageUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validazione tipo
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp']
    if (!allowedTypes.includes(file.type)) {
      setError('Formato non supportato. Usa JPG, PNG o WebP')
      return
    }

    // Validazione dimensione (500KB)
    if (file.size > 500 * 1024) {
      setError('Immagine troppo grande (max 500KB)')
      return
    }

    // Converti in base64
    const reader = new FileReader()
    reader.onload = (event) => {
      const base64 = event.target.result
      setFormData(prev => ({ ...prev, avatar_base64: base64 }))
      setPreviewAvatar(base64)
      setError(null)
    }
    reader.onerror = () => {
      setError('Errore durante la lettura del file')
    }
    reader.readAsDataURL(file)
  }

  // Rimuovi avatar
  const handleRemoveAvatar = () => {
    setFormData(prev => ({ ...prev, avatar_base64: '' }))
    setPreviewAvatar(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Submit form
  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(false)

    try {
      // Prepara dati da inviare (solo campi modificati)
      const updateData = {}

      if (formData.nome !== (user.nome || '')) {
        updateData.nome = formData.nome || null
      }
      if (formData.cognome !== (user.cognome || '')) {
        updateData.cognome = formData.cognome || null
      }
      if (formData.data_nascita !== (user.data_nascita || '')) {
        updateData.data_nascita = formData.data_nascita || null
      }
      // Avatar: invia solo se cambiato
      if (formData.avatar_base64 !== '') {
        updateData.avatar_base64 = formData.avatar_base64 || '' // stringa vuota = rimuovi
      }

      // Se nessun campo modificato
      if (Object.keys(updateData).length === 0) {
        setSuccess(true)
        setTimeout(() => onClose(), 1000)
        return
      }

      // Chiamata API
      const updatedUser = await utentiApi.updateProfilo(updateData)

      setSuccess(true)

      // Callback
      if (onUpdate) {
        onUpdate(updatedUser)
      }

      // Chiudi dopo breve delay
      setTimeout(() => {
        onClose()
      }, 1500)

    } catch (err) {
      console.error('Errore aggiornamento profilo:', err)
      setError(err.response?.data?.detail || 'Errore durante il salvataggio')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Il mio profilo" size="md">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Avatar Section */}
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <Avatar
              user={{ ...user, avatar_base64: previewAvatar }}
              size="xl"
              className="ring-4 ring-gray-100"
            />
            {previewAvatar && (
              <button
                type="button"
                onClick={handleRemoveAvatar}
                className="absolute -top-1 -right-1 w-6 h-6 bg-red-500 text-white rounded-full
                           flex items-center justify-center text-xs hover:bg-red-600 transition-colors"
                title="Rimuovi avatar"
              >
                x
              </button>
            )}
          </div>

          <div className="flex gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleImageUpload}
              className="hidden"
              id="avatar-upload"
            />
            <label
              htmlFor="avatar-upload"
              className="px-3 py-1.5 text-sm bg-blue-50 text-blue-600 rounded-lg cursor-pointer
                         hover:bg-blue-100 transition-colors"
            >
              Carica immagine
            </label>
            {previewAvatar && (
              <button
                type="button"
                onClick={handleRemoveAvatar}
                className="px-3 py-1.5 text-sm bg-gray-100 text-gray-600 rounded-lg
                           hover:bg-gray-200 transition-colors"
              >
                Rimuovi
              </button>
            )}
          </div>
          <p className="text-xs text-gray-500">JPG, PNG o WebP. Max 500KB.</p>
        </div>

        {/* Dati Personali */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nome
            </label>
            <input
              type="text"
              name="nome"
              value={formData.nome}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Il tuo nome"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Cognome
            </label>
            <input
              type="text"
              name="cognome"
              value={formData.cognome}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Il tuo cognome"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Data di nascita
          </label>
          <input
            type="date"
            name="data_nascita"
            value={formData.data_nascita}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Username (non modificabile) */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Username
          </label>
          <input
            type="text"
            value={user?.username || ''}
            disabled
            className="w-full px-3 py-2 border border-gray-200 rounded-lg bg-gray-100 text-gray-600"
          />
          <p className="mt-1 text-xs text-gray-400">Lo username non puo' essere modificato</p>
        </div>

        {/* Error/Success Messages */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {success && (
          <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
            Profilo aggiornato con successo!
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200
                       transition-colors disabled:opacity-50"
          >
            Annulla
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700
                       transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Salvataggio...
              </>
            ) : (
              'Salva modifiche'
            )}
          </button>
        </div>
      </form>
    </Modal>
  )
}
