/**
 * Alert per credenziali email gestite via .env
 */
import React from 'react'

export default function CredentialsAlert() {
  return (
    <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
      <div className="flex items-start gap-3">
        <div className="w-6 h-6 bg-amber-400 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
          <span className="text-white text-xs font-bold">!</span>
        </div>
        <div>
          <h4 className="font-medium text-amber-800 text-sm mb-1">
            Credenziali Protette
          </h4>
          <p className="text-xs text-amber-700">
            Le credenziali email (username/password) sono gestite tramite variabili
            d'ambiente nel file <code className="bg-amber-100 px-1 rounded">.env</code> sul
            server e non sono modificabili da questa interfaccia per motivi di sicurezza.
          </p>
          <p className="text-xs text-amber-600 mt-2">
            Variabili: <code className="bg-amber-100 px-1 rounded">IMAP_USER</code>,
            <code className="bg-amber-100 px-1 rounded ml-1">IMAP_PASSWORD</code>,
            <code className="bg-amber-100 px-1 rounded ml-1">SMTP_USER</code>,
            <code className="bg-amber-100 px-1 rounded ml-1">SMTP_PASSWORD</code>
          </p>
        </div>
      </div>
    </div>
  )
}
