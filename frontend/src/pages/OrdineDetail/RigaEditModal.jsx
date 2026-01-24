// =============================================================================
// SERV.O v11.0 - RIGA EDIT MODAL COMPONENT
// =============================================================================
// v11.0: Usa ModalBase per coerenza UI (TIER 2.2)
// v11.0: Usa RigaEditForm estratto (TIER 3.1)
// =============================================================================

import React from 'react';
import { ModalBase, RigaEditForm } from '../../common';

export default function RigaEditModal({
  riga,
  formModifica,
  setFormModifica,
  onSave,
  onClose
}) {
  if (!riga) return null;

  // Handler per onChange compatibile con RigaEditForm
  const handleFormChange = (newData) => {
    setFormModifica(newData);
  };

  return (
    <ModalBase
      isOpen={!!riga}
      onClose={onClose}
      title={`Modifica Riga #${riga.n_riga}`}
      size="md"
      variant="primary"
      actions={{
        confirm: () => onSave(riga),
        confirmText: 'Salva Modifiche',
        confirmVariant: 'primary',
      }}
    >
      <RigaEditForm
        formData={formModifica}
        onChange={handleFormChange}
        riga={riga}
        variant="full"
        showSconti={true}
        showDaEvadere={true}
        showTotals={true}
      />
    </ModalBase>
  );
}
