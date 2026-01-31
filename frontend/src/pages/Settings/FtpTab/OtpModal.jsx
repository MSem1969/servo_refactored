// =============================================================================
// OTP VERIFICATION MODAL
// =============================================================================

import React, { useState, useEffect, useRef } from 'react';
import { Button } from '../../../common';

export default function OtpModal({ operation, onVerify, onCancel }) {
  const [code, setCode] = useState(['', '', '', '', '', '']);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [countdown, setCountdown] = useState(operation?.scadenza || 300);
  const inputRefs = useRef([]);

  // Countdown timer
  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Focus primo input
  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  // Gestione input
  const handleChange = (index, value) => {
    if (!/^\d*$/.test(value)) return; // Solo numeri

    const newCode = [...code];
    newCode[index] = value.slice(-1);
    setCode(newCode);
    setError(null);

    // Auto-focus next
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  // Gestione backspace
  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  // Gestione paste
  const handlePaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pasted.length === 6) {
      setCode(pasted.split(''));
      inputRefs.current[5]?.focus();
    }
  };

  // Verifica
  const handleVerify = async () => {
    const fullCode = code.join('');
    if (fullCode.length !== 6) {
      setError('Inserisci il codice completo (6 cifre)');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await onVerify(fullCode);
    } catch (err) {
      setError(err.response?.data?.detail || err.response?.data?.error || 'Codice non valido');
      setCode(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  // Format countdown
  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const operationLabels = {
    FTP_VIEW_PASSWORD: 'visualizzare la password',
    FTP_EDIT: 'modificare la configurazione'
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="p-6 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
              <span className="text-2xl">🔐</span>
            </div>
            <div>
              <h3 className="font-semibold text-slate-800">Verifica 2FA</h3>
              <p className="text-sm text-slate-500">
                Per {operationLabels[operation.type] || operation.type}
              </p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          <p className="text-sm text-slate-600 mb-4">
            Inserisci il codice OTP inviato alla tua email per <strong>{operation.endpointName}</strong>
          </p>

          {/* OTP Input */}
          <div className="flex justify-center gap-2 mb-4">
            {code.map((digit, i) => (
              <input
                key={i}
                ref={el => inputRefs.current[i] = el}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleChange(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                onPaste={handlePaste}
                className={`w-12 h-14 text-center text-2xl font-mono font-bold border-2 rounded-lg
                  ${error ? 'border-red-300 bg-red-50' : 'border-slate-300'}
                  focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none
                  transition-colors`}
                disabled={loading || countdown === 0}
              />
            ))}
          </div>

          {/* Error */}
          {error && (
            <div className="text-center text-sm text-red-600 mb-4">
              {error}
            </div>
          )}

          {/* Countdown */}
          <div className="text-center mb-4">
            {countdown > 0 ? (
              <span className={`text-sm ${countdown < 60 ? 'text-amber-600 font-medium' : 'text-slate-500'}`}>
                Codice valido per {formatTime(countdown)}
              </span>
            ) : (
              <span className="text-sm text-red-600 font-medium">
                Codice scaduto. Richiedi un nuovo codice.
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end gap-3">
          <Button variant="secondary" onClick={onCancel} disabled={loading}>
            Annulla
          </Button>
          <Button
            variant="primary"
            onClick={handleVerify}
            disabled={loading || countdown === 0 || code.some(d => !d)}
            loading={loading}
          >
            Verifica
          </Button>
        </div>
      </div>
    </div>
  );
}
