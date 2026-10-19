// =============================================================================
// SERV.O - MODALE MOTIVAZIONE ARCHIVIAZIONE (2026-10)
// =============================================================================
// Archiviare un ordine richiede una motivazione (min. 3 caratteri), salvata in
// ordini_testata.motivo_archiviazione con autore e data. Usata da:
// archiviazione singola e massiva (Database) e archiviazione dell'ultima riga
// attiva (Dettaglio ordine), che archivia l'ordine.
// =============================================================================

import React, { useEffect, useState } from 'react';
import ModalBase from './ModalBase';

export const MOTIVO_ARCHIVIAZIONE_MIN = 3;
const MOTIVO_ARCHIVIAZIONE_MAX = 500;

const MotivoArchiviazioneModal = ({
  isOpen,
  onClose,
  onConfirm,
  title = 'Archiviazione ordine',
  descrizione,
  confirmText = 'Archivia',
  loading = false,
}) => {
  const [motivo, setMotivo] = useState('');

  useEffect(() => {
    if (isOpen) setMotivo('');
  }, [isOpen]);

  const motivoPulito = motivo.trim().replace(/\s+/g, ' ');
  const valido = motivoPulito.length >= MOTIVO_ARCHIVIAZIONE_MIN;

  const conferma = () => {
    if (valido && !loading) onConfirm(motivoPulito);
  };

  return (
    <ModalBase
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size="md"
      variant="warning"
      actions={{
        confirm: conferma,
        confirmText,
        confirmVariant: 'warning',
        disabled: !valido,
        loading,
      }}
    >
      {descrizione && (
        <p className="text-sm text-slate-700 whitespace-pre-line mb-3">{descrizione}</p>
      )}
      <label htmlFor="motivo-archiviazione" className="block text-sm font-medium text-slate-700 mb-1">
        Motivazione dell'archiviazione <span className="text-red-600">*</span>
      </label>
      <textarea
        id="motivo-archiviazione"
        autoFocus
        rows={3}
        maxLength={MOTIVO_ARCHIVIAZIONE_MAX}
        value={motivo}
        onChange={(e) => setMotivo(e.target.value)}
        placeholder="Es. ordine duplicato, annullato dal cliente, sostituito da altro ordine…"
        className="w-full border border-slate-300 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
      />
      <p className={`text-xs mt-1 ${valido ? 'text-slate-400' : 'text-amber-700'}`}>
        {valido
          ? `${motivo.length}/${MOTIVO_ARCHIVIAZIONE_MAX}`
          : `Obbligatoria: almeno ${MOTIVO_ARCHIVIAZIONE_MIN} caratteri`}
      </p>
      <p className="text-xs text-slate-500 mt-3">
        L'ordine passa in stato <strong>ARCHIVIATO</strong>: non verrà esportato e le sue
        anomalie aperte vengono archiviate. Si può ripristinare.
      </p>
    </ModalBase>
  );
};

export default MotivoArchiviazioneModal;
