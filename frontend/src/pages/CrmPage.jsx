/**
 * CRM Page - Assistenza e Proposte Miglioramento
 */
import React from 'react'
import CrmChatbot from '../components/CrmChatbot'

const CrmPage = ({ currentUser }) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Assistenza</h1>
          <p className="text-sm text-slate-600">
            Richieste di assistenza e proposte di miglioramento
          </p>
        </div>
      </div>

      <CrmChatbot currentUser={currentUser} />
    </div>
  )
}

export default CrmPage
