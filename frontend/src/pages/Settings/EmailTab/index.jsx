/**
 * Email Settings Tab - Container principale
 * Gestione configurazione IMAP/SMTP per sistema email
 */
import React, { useState, useEffect } from 'react'
import { useEmailConfig, useSaveEmailConfig, useTestImap, useTestSmtp } from '../../../hooks/useEmail'
import { Button, Loading } from '../../../common'
import CredentialsAlert from './CredentialsAlert'
import ImapSection from './ImapSection'
import SmtpSection from './SmtpSection'
import EmailLogSection from './EmailLogSection'

export default function EmailTab() {
  const [activeSection, setActiveSection] = useState('smtp')
  const [localConfig, setLocalConfig] = useState(null)

  const { data: config, isLoading, error } = useEmailConfig()
  const saveMutation = useSaveEmailConfig()
  const testImapMutation = useTestImap()
  const testSmtpMutation = useTestSmtp()

  // Sync local config when data loads
  useEffect(() => {
    if (config) {
      setLocalConfig(config)
    }
  }, [config])

  const handleSave = async () => {
    try {
      await saveMutation.mutateAsync(localConfig)
      alert('Configurazione salvata con successo')
    } catch (err) {
      alert('Errore: ' + err.message)
    }
  }

  const handleTestImap = async () => {
    try {
      const result = await testImapMutation.mutateAsync()
      alert(`Test IMAP: ${result.success ? 'Connessione riuscita!' : result.error}`)
    } catch (err) {
      alert('Errore test IMAP: ' + err.message)
    }
  }

  const handleTestSmtp = async (destinatario) => {
    try {
      const result = await testSmtpMutation.mutateAsync(destinatario)
      alert(`Test SMTP: ${result.success ? 'Email inviata con successo!' : result.error}`)
    } catch (err) {
      alert('Errore test SMTP: ' + err.message)
    }
  }

  if (isLoading) return <Loading text="Caricamento configurazione email..." />
  if (error) return <div className="p-4 text-red-600">Errore: {error.message}</div>

  const sections = [
    { id: 'smtp', label: 'SMTP (Invio)', icon: '📤' },
    { id: 'imap', label: 'IMAP (Ricezione)', icon: '📥' },
    { id: 'log', label: 'Log Invii', icon: '📋' },
  ]

  return (
    <div className="p-6 space-y-6">
      {/* Alert credenziali */}
      <CredentialsAlert />

      {/* Sub-tabs */}
      <div className="flex gap-2 border-b border-slate-200 pb-2">
        {sections.map((section) => (
          <button
            key={section.id}
            onClick={() => setActiveSection(section.id)}
            className={`px-3 py-2 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
              activeSection === section.id
                ? 'bg-blue-50 text-blue-600 border-b-2 border-blue-600'
                : 'text-slate-500 hover:bg-slate-50'
            }`}
          >
            <span>{section.icon}</span>
            <span>{section.label}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="min-h-[300px]">
        {activeSection === 'smtp' && localConfig && (
          <SmtpSection
            config={localConfig}
            onChange={setLocalConfig}
            onTest={handleTestSmtp}
            testing={testSmtpMutation.isPending}
          />
        )}

        {activeSection === 'imap' && localConfig && (
          <ImapSection
            config={localConfig}
            onChange={setLocalConfig}
            onTest={handleTestImap}
            testing={testImapMutation.isPending}
          />
        )}

        {activeSection === 'log' && (
          <EmailLogSection />
        )}
      </div>

      {/* Save button (solo per config, non per log) */}
      {activeSection !== 'log' && (
        <div className="flex justify-end pt-4 border-t border-slate-200">
          <Button
            variant="primary"
            onClick={handleSave}
            loading={saveMutation.isPending}
            disabled={saveMutation.isPending}
          >
            Salva Configurazione Email
          </Button>
        </div>
      )}
    </div>
  )
}
