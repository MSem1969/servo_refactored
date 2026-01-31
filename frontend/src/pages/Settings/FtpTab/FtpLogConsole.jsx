// =============================================================================
// FTP LOG CONSOLE - Dark Theme (come Upload Console)
// =============================================================================

import React, { useEffect, useRef, useState } from 'react';
import { Button } from '../../../common';
import { ftpApi } from '../../../api';

export default function FtpLogConsole({ logs, onClear }) {
  const scrollRef = useRef(null);
  const [showHistory, setShowHistory] = useState(false);
  const [historyLogs, setHistoryLogs] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Auto-scroll quando arrivano nuovi log
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  // Carica storico log dal server
  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await ftpApi.getLog(50);
      if (res.success) {
        setHistoryLogs(res.data);
        setShowHistory(true);
      }
    } catch (err) {
      console.error('Errore caricamento log:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  // Colore in base al tipo di log
  const getLogColor = (type) => {
    switch (type) {
      case 'ok':
      case 'success':
        return 'text-emerald-400';
      case 'error':
      case 'FAILED':
        return 'text-red-400';
      case 'warn':
      case 'warning':
        return 'text-yellow-400';
      case 'upload':
      case 'info':
      default:
        return 'text-slate-400';
    }
  };

  return (
    <div className="bg-slate-900 rounded-xl">
      {/* Header */}
      <div className="p-3 border-b border-slate-700 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <h3 className="font-medium text-white text-sm">Console FTP</h3>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
            <span className="text-xs text-slate-500">Live</span>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="xs"
            onClick={loadHistory}
            disabled={loadingHistory}
            className="text-slate-400 hover:text-white"
          >
            {loadingHistory ? '...' : 'Storico'}
          </Button>
          <Button
            variant="ghost"
            size="xs"
            onClick={onClear}
            className="text-slate-400 hover:text-white"
          >
            Pulisci
          </Button>
        </div>
      </div>

      {/* Log Output */}
      <div
        ref={scrollRef}
        className="p-3 font-mono text-xs h-48 overflow-y-auto"
      >
        {logs.map((log, i) => (
          <p key={i} className={`leading-relaxed ${getLogColor(log.type)}`}>
            <span className="text-slate-500">[{log.time}]</span> {log.text}
          </p>
        ))}
      </div>

      {/* History Modal */}
      {showHistory && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-900 rounded-xl shadow-xl max-w-4xl w-full mx-4 max-h-[80vh] flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-slate-700 flex justify-between items-center">
              <h3 className="font-medium text-white">Storico Log FTP (ultime 50 operazioni)</h3>
              <Button
                variant="ghost"
                size="xs"
                onClick={() => setShowHistory(false)}
                className="text-slate-400 hover:text-white"
              >
                Chiudi
              </Button>
            </div>

            {/* Table */}
            <div className="flex-1 overflow-auto p-4">
              <table className="w-full text-xs">
                <thead className="text-slate-400 border-b border-slate-700">
                  <tr>
                    <th className="text-left p-2">Timestamp</th>
                    <th className="text-left p-2">Endpoint</th>
                    <th className="text-left p-2">Operazione</th>
                    <th className="text-left p-2">File</th>
                    <th className="text-center p-2">Esito</th>
                    <th className="text-left p-2">Messaggio</th>
                  </tr>
                </thead>
                <tbody className="text-slate-300">
                  {historyLogs.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center p-8 text-slate-500">
                        Nessun log FTP disponibile
                      </td>
                    </tr>
                  ) : (
                    historyLogs.map((log) => (
                      <tr key={log.id} className="border-b border-slate-800 hover:bg-slate-800/50">
                        <td className="p-2 font-mono text-slate-400">
                          {new Date(log.timestamp).toLocaleString('it-IT')}
                        </td>
                        <td className="p-2">
                          {log.endpoint_nome || '-'}
                        </td>
                        <td className="p-2">
                          <span className="px-2 py-0.5 bg-slate-700 rounded text-slate-300">
                            {log.operazione}
                          </span>
                        </td>
                        <td className="p-2 font-mono text-slate-400 truncate max-w-[200px]">
                          {log.file_remoto || '-'}
                        </td>
                        <td className="p-2 text-center">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            log.esito === 'SUCCESS' ? 'bg-emerald-900 text-emerald-300' :
                            log.esito === 'FAILED' ? 'bg-red-900 text-red-300' :
                            'bg-slate-700 text-slate-300'
                          }`}>
                            {log.esito}
                          </span>
                        </td>
                        <td className="p-2 text-slate-400 truncate max-w-[250px]" title={log.messaggio}>
                          {log.messaggio || '-'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
