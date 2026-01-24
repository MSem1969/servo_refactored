/**
 * CRM Page - Assistenza e Proposte Miglioramento
 */
import React from 'react'
import CrmChatbot from '../components/CrmChatbot'

const CrmPage = ({ currentUser }) => {
  return (
    <div className="space-y-4">
      <CrmChatbot currentUser={currentUser} />
    </div>
  )
}

export default CrmPage
