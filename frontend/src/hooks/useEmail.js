/**
 * React Query hooks per Email Config API (v8.1)
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { emailApi } from '../api'

// =============================================================================
// QUERY KEYS
// =============================================================================
export const emailKeys = {
  all: ['email'],
  config: () => [...emailKeys.all, 'config'],
  imapConfig: () => [...emailKeys.all, 'imap'],
  smtpConfig: () => [...emailKeys.all, 'smtp'],
  log: (filters) => [...emailKeys.all, 'log', filters],
}

// =============================================================================
// HOOKS CONFIGURAZIONE
// =============================================================================

/**
 * Hook per ottenere configurazione email completa
 */
export function useEmailConfig(options = {}) {
  return useQuery({
    queryKey: emailKeys.config(),
    queryFn: async () => {
      const response = await emailApi.getConfig()
      return response.data // Estrae data dal wrapper { success, data }
    },
    staleTime: 5 * 60 * 1000, // 5 minuti
    ...options,
  })
}

/**
 * Hook per ottenere configurazione IMAP
 */
export function useImapConfig(options = {}) {
  return useQuery({
    queryKey: emailKeys.imapConfig(),
    queryFn: emailApi.getImapConfig,
    staleTime: 5 * 60 * 1000,
    ...options,
  })
}

/**
 * Hook per ottenere configurazione SMTP
 */
export function useSmtpConfig(options = {}) {
  return useQuery({
    queryKey: emailKeys.smtpConfig(),
    queryFn: emailApi.getSmtpConfig,
    staleTime: 5 * 60 * 1000,
    ...options,
  })
}

/**
 * Hook per salvare configurazione email
 */
export function useSaveEmailConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: emailApi.saveConfig,
    onSuccess: () => {
      // Invalida tutte le query email config
      queryClient.invalidateQueries({ queryKey: emailKeys.all })
    },
  })
}

// =============================================================================
// HOOKS TEST CONNESSIONE
// =============================================================================

/**
 * Hook per test connessione IMAP
 */
export function useTestImap() {
  return useMutation({
    mutationFn: emailApi.testImap,
  })
}

/**
 * Hook per test connessione SMTP
 */
export function useTestSmtp() {
  return useMutation({
    mutationFn: (destinatario) => emailApi.testSmtp(destinatario),
  })
}

// =============================================================================
// HOOKS LOG EMAIL
// =============================================================================

/**
 * Hook per ottenere log email inviate
 */
export function useEmailLog(filters = {}, options = {}) {
  return useQuery({
    queryKey: emailKeys.log(filters),
    queryFn: () => emailApi.getLog(filters),
    staleTime: 30 * 1000, // 30 secondi
    ...options,
  })
}

/**
 * Hook per ritentare invio email
 */
export function useRetryEmail() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: emailApi.retryEmail,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: emailKeys.log({}) })
    },
  })
}
