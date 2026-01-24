/**
 * Sezione configurazione IMAP per ricezione email
 * Usa struttura flat dal backend (imap_host, imap_port, etc.)
 */
import React from 'react'
import { Button, StatusBadge } from '../../../common'

export default function ImapSection({ config, onChange, onTest, testing }) {
  const handleChange = (field, value) => {
    onChange({
      ...config,
      [field]: value
    })
  }

  // La config e' flat: imap_host, imap_port, imap_credentials_configured, etc.
  const isConfigured = config?.imap_credentials_configured

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-slate-800">Configurazione IMAP</h4>
        <StatusBadge
          status={isConfigured ? 'completed' : 'pending'}
          label={isConfigured ? 'Credenziali OK' : 'Credenziali mancanti'}
          size="xs"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-slate-600 mb-1">Server IMAP</label>
          <input
            type="text"
            value={config?.imap_host || 'imap.gmail.com'}
            onChange={(e) => handleChange('imap_host', e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="imap.gmail.com"
          />
        </div>

        <div>
          <label className="block text-xs text-slate-600 mb-1">Porta</label>
          <input
            type="number"
            value={config?.imap_port || 993}
            onChange={(e) => handleChange('imap_port', parseInt(e.target.value))}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs text-slate-600 mb-1">Cartella</label>
          <input
            type="text"
            value={config?.imap_folder || 'INBOX'}
            onChange={(e) => handleChange('imap_folder', e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="INBOX"
          />
        </div>

        <div className="flex items-end gap-2">
          <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg cursor-pointer">
            <input
              type="checkbox"
              checked={config?.imap_enabled === true}
              onChange={(e) => handleChange('imap_enabled', e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="text-sm text-slate-700">Abilita monitoraggio</span>
          </label>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg cursor-pointer">
          <input
            type="checkbox"
            checked={config?.imap_use_ssl !== false}
            onChange={(e) => handleChange('imap_use_ssl', e.target.checked)}
            className="w-4 h-4 text-blue-600 rounded"
          />
          <span className="text-sm text-slate-700">Usa SSL/TLS</span>
        </label>

        <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg cursor-pointer">
          <input
            type="checkbox"
            checked={config?.imap_unread_only !== false}
            onChange={(e) => handleChange('imap_unread_only', e.target.checked)}
            className="w-4 h-4 text-blue-600 rounded"
          />
          <span className="text-sm text-slate-700">Solo non lette</span>
        </label>

        <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg cursor-pointer">
          <input
            type="checkbox"
            checked={config?.imap_mark_as_read === true}
            onChange={(e) => handleChange('imap_mark_as_read', e.target.checked)}
            className="w-4 h-4 text-blue-600 rounded"
          />
          <span className="text-sm text-slate-700">Segna come lette</span>
        </label>
      </div>

      {/* Credenziali (solo lettura - configurate in .env) */}
      <div className="p-3 bg-slate-50 rounded-lg">
        <p className="text-xs text-slate-500 mb-2">Credenziali IMAP (configurate in .env)</p>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            {isConfigured ? (
              <span className="text-green-600 text-lg">&#10003;</span>
            ) : (
              <span className="text-amber-500 text-lg">&#9888;</span>
            )}
            <span className="text-sm text-slate-700">
              {isConfigured
                ? 'Configurate correttamente'
                : 'Non configurate (opzionale - usa IMAP_USER/IMAP_PASSWORD o SMTP)'}
            </span>
          </div>
        </div>
      </div>

      <Button
        variant="secondary"
        size="sm"
        onClick={onTest}
        loading={testing}
        disabled={testing || !isConfigured}
      >
        Test Connessione IMAP
      </Button>
    </div>
  )
}
