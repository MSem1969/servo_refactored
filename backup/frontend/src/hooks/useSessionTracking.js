/**
 * Hook per tracking tempo sessione per sezione
 * Invia heartbeat ogni 60 secondi al backend
 */
import { useEffect, useRef } from 'react';
import { produttivitaApi } from '../api';

const HEARTBEAT_INTERVAL = 60000; // 60 secondi

export function useSessionTracking(sezione) {
  const intervalRef = useRef(null);
  const lastSezioneRef = useRef(null);

  useEffect(() => {
    // Se la sezione è cambiata, invia subito un heartbeat
    if (sezione && sezione !== lastSezioneRef.current) {
      lastSezioneRef.current = sezione;

      // Invia heartbeat iniziale
      produttivitaApi.heartbeat(sezione).catch(err => {
        console.warn('Heartbeat iniziale fallito:', err);
      });
    }

    // Setup intervallo heartbeat
    if (sezione) {
      intervalRef.current = setInterval(() => {
        produttivitaApi.heartbeat(sezione).catch(err => {
          console.warn('Heartbeat fallito:', err);
        });
      }, HEARTBEAT_INTERVAL);
    }

    // Cleanup su cambio sezione o unmount
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [sezione]);

  // Heartbeat su beforeunload (chiusura tab)
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (lastSezioneRef.current) {
        // Usa sendBeacon per garantire l'invio anche alla chiusura
        const token = localStorage.getItem('authToken');
        if (token) {
          navigator.sendBeacon(
            '/api/v1/produttivita/heartbeat',
            JSON.stringify({ sezione: lastSezioneRef.current })
          );
        }
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, []);

  return null;
}

export default useSessionTracking;
