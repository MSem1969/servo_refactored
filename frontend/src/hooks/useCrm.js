/**
 * React Query hooks per CRM/Ticketing API (v8.1)
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { crmApi } from '../api'

// =============================================================================
// QUERY KEYS
// =============================================================================
export const crmKeys = {
  all: ['crm'],
  tickets: () => [...crmKeys.all, 'tickets'],
  ticketList: (filters) => [...crmKeys.tickets(), 'list', filters],
  ticketDetail: (id) => [...crmKeys.tickets(), 'detail', id],
  messages: (ticketId) => [...crmKeys.all, 'messages', ticketId],
  stats: () => [...crmKeys.all, 'stats'],
  constants: () => [...crmKeys.all, 'constants'],
}

// =============================================================================
// HOOKS TICKETS
// =============================================================================

/**
 * Hook per lista ticket
 */
export function useTickets(filters = {}, options = {}) {
  return useQuery({
    queryKey: crmKeys.ticketList(filters),
    queryFn: () => crmApi.getTickets(filters),
    staleTime: 30 * 1000, // 30 secondi
    ...options,
  })
}

/**
 * Hook per dettaglio ticket
 */
export function useTicket(id, options = {}) {
  return useQuery({
    queryKey: crmKeys.ticketDetail(id),
    queryFn: () => crmApi.getTicket(id),
    enabled: !!id,
    staleTime: 30 * 1000,
    ...options,
  })
}

/**
 * Hook per creare ticket
 */
export function useCreateTicket() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: crmApi.createTicket,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: crmKeys.tickets() })
      queryClient.invalidateQueries({ queryKey: crmKeys.stats() })
    },
  })
}

/**
 * Hook per aggiornare stato ticket
 */
export function useUpdateTicketStatus() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, stato }) => crmApi.updateStatus(id, stato),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: crmKeys.ticketDetail(id) })
      queryClient.invalidateQueries({ queryKey: crmKeys.tickets() })
      queryClient.invalidateQueries({ queryKey: crmKeys.stats() })
    },
  })
}

/**
 * Hook per aggiornare ticket
 */
export function useUpdateTicket() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }) => crmApi.updateTicket(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: crmKeys.ticketDetail(id) })
      queryClient.invalidateQueries({ queryKey: crmKeys.tickets() })
    },
  })
}

// =============================================================================
// HOOKS MESSAGGI
// =============================================================================

/**
 * Hook per messaggi di un ticket
 */
export function useTicketMessages(ticketId, options = {}) {
  return useQuery({
    queryKey: crmKeys.messages(ticketId),
    queryFn: () => crmApi.getMessages(ticketId),
    enabled: !!ticketId,
    staleTime: 10 * 1000, // 10 secondi
    refetchInterval: 30 * 1000, // Refresh ogni 30 secondi
    ...options,
  })
}

/**
 * Hook per aggiungere messaggio
 */
export function useAddMessage() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ ticketId, contenuto }) => crmApi.addMessage(ticketId, contenuto),
    onSuccess: (_, { ticketId }) => {
      queryClient.invalidateQueries({ queryKey: crmKeys.messages(ticketId) })
      queryClient.invalidateQueries({ queryKey: crmKeys.ticketDetail(ticketId) })
      queryClient.invalidateQueries({ queryKey: crmKeys.tickets() })
    },
  })
}

// =============================================================================
// HOOKS STATISTICHE
// =============================================================================

/**
 * Hook per statistiche CRM
 */
export function useCrmStats(options = {}) {
  return useQuery({
    queryKey: crmKeys.stats(),
    queryFn: crmApi.getStats,
    staleTime: 60 * 1000, // 1 minuto
    ...options,
  })
}

/**
 * Hook per costanti CRM (stati, categorie, priorita)
 */
export function useCrmConstants(options = {}) {
  return useQuery({
    queryKey: crmKeys.constants(),
    queryFn: crmApi.getConstants,
    staleTime: Infinity, // Non cambiano mai
    cacheTime: Infinity,
    ...options,
  })
}

// =============================================================================
// HOOKS ALLEGATI
// =============================================================================

/**
 * Hook per allegati di un ticket
 */
export function useTicketAttachments(ticketId, options = {}) {
  return useQuery({
    queryKey: [...crmKeys.ticketDetail(ticketId), 'allegati'],
    queryFn: () => crmApi.getAttachments(ticketId),
    enabled: !!ticketId,
    staleTime: 30 * 1000,
    ...options,
  })
}

/**
 * Hook per upload allegato
 */
export function useUploadAttachment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ ticketId, file }) => crmApi.uploadAttachment(ticketId, file),
    onSuccess: (_, { ticketId }) => {
      queryClient.invalidateQueries({ queryKey: [...crmKeys.ticketDetail(ticketId), 'allegati'] })
    },
  })
}

/**
 * Hook per eliminare allegato
 */
export function useDeleteAttachment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: crmApi.deleteAttachment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: crmKeys.tickets() })
    },
  })
}
