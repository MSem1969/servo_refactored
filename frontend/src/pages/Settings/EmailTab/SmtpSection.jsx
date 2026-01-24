/**
 * Sezione configurazione SMTP per invio email
 * Usa struttura flat dal backend (smtp_host, smtp_port, etc.)
 */
import React, { useState } from 'react'
import { Button, StatusBadge } from '../../../common'

export default function SmtpSection({ config, onChange, onTest, testing }) {
  const [testEmail, setTestEmail] = useState('')

  const handleChange = (field, value) => {
    onChange({
      ...config,
      [field]: value
    })
  }

  const handleTest = () => {
    onTest(testEmail || null)
  }

  // La config e' flat: smtp_host, smtp_port, smtp_credentials_configured, etc.
  const isConfigured = config?.smtp_credentials_configured

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-slate-800">Configurazione SMTP</h4>
        <StatusBadge
          status={isConfigured ? 'completed' : 'pending'}
          label={isConfigured ? 'Credenziali OK' : 'Credenziali mancanti'}
          size="xs"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-slate-600 mb-1">Server SMTP</label>
          <input
            type="text"
            value={config?.smtp_host || 'smtp.gmail.com'}
            onChange={(e) => handleChange('smtp_host', e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="smtp.gmail.com"
          />
        </div>

        <div>
          <label className="block text-xs text-slate-600 mb-1">Porta</label>
          <input
            type="number"
            value={config?.smtp_port || 587}
            onChange={(e) => handleChange('smtp_port', parseInt(e.target.value))}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs text-slate-600 mb-1">Nome Mittente</label>
          <input
            type="text"
            value={config?.smtp_sender_name || ''}
            onChange={(e) => handleChange('smtp_sender_name', e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="TO Extractor"
          />
        </div>

        <div>
          <label className="block text-xs text-slate-600 mb-1">Email Mittente</label>
          <input
            type="email"
            value={config?.smtp_sender_email || ''}
            onChange={(e) => handleChange('smtp_sender_email', e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="noreply@example.com"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg cursor-pointer">
          <input
            type="checkbox"
            checked={config?.smtp_enabled !== false}
            onChange={(e) => handleChange('smtp_enabled', e.target.checked)}
            className="w-4 h-4 text-blue-600 rounded"
          />
          <span className="text-sm text-slate-700">Abilita invio email</span>
        </label>

        <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg cursor-pointer">
          <input
            type="checkbox"
            checked={config?.smtp_use_tls !== false}
            onChange={(e) => handleChange('smtp_use_tls', e.target.checked)}
            className="w-4 h-4 text-blue-600 rounded"
          />
          <span className="text-sm text-slate-700">Usa TLS</span>
        </label>
      </div>

      {/* Credenziali (solo lettura - configurate in .env) */}
      <div className="p-3 bg-slate-50 rounded-lg">
        <p className="text-xs text-slate-500 mb-2">Credenziali SMTP (configurate in .env)</p>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            {isConfigured ? (
              <span className="text-green-600 text-lg">&#10003;</span>
            ) : (
              <span className="text-red-500 text-lg">&#10007;</span>
            )}
            <span className="text-sm text-slate-700">
              {isConfigured ? 'Configurate correttamente' : 'Non configurate - modifica backend/.env'}
            </span>
          </div>
        </div>
      </div>

      {/* Notifiche Admin */}
      <div className="p-4 border border-blue-100 rounded-lg bg-blue-50/50">
        <p className="text-sm font-medium text-slate-700 mb-2">Notifiche Admin</p>
        <p className="text-xs text-slate-500 mb-3">
          Email degli admin che riceveranno notifiche per nuovi ticket di assistenza.
          Separa piu email con virgola.
        </p>
        <input
          type="text"
          value={config?.admin_notifica_email || ''}
          onChange={(e) => handleChange('admin_notifica_email', e.target.value)}
          className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="admin1@email.com, admin2@email.com"
        />
      </div>

      {/* Test Email */}
      <div className="p-4 border border-slate-200 rounded-lg">
        <p className="text-sm font-medium text-slate-700 mb-2">Invia Email di Test</p>
        <div className="flex items-center gap-3">
          <input
            type="email"
            value={testEmail}
            onChange={(e) => setTestEmail(e.target.value)}
            className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="destinatario@email.com"
          />
          <Button
            variant="secondary"
            size="sm"
            onClick={handleTest}
            loading={testing}
            disabled={testing || !isConfigured}
          >
            Invia Test
          </Button>
        </div>
        {!isConfigured && (
          <p className="text-xs text-amber-600 mt-2">
            Configura SMTP_USER e SMTP_PASSWORD in backend/.env per abilitare l'invio
          </p>
        )}
      </div>
    </div>
  )
}
