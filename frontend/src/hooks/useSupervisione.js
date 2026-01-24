// =============================================================================
// SERV.O v11.0 - SUPERVISIONE HOOKS (TIER 2.3)
// =============================================================================
// React Query hooks per gestione supervisione con invalidation centralizzata
// =============================================================================

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supervisioneApi } from '../api';
import { anomalieKeys } from './useAnomalies';
import { ordiniKeys } from './useOrdini';

// Query keys factory
export const supervisioneKeys = {
  all: ['supervisione'],
  // Liste
  pending: () => [...supervisioneKeys.all, 'pending'],
  pendingGrouped: () => [...supervisioneKeys.all, 'pending', 'grouped'],
  pendingCount: () => [...supervisioneKeys.all, 'pending', 'count'],
  // Dettagli
  detail: (id) => [...supervisioneKeys.all, 'detail', id],
  byOrdine: (idTestata) => [...supervisioneKeys.all, 'ordine', idTestata],
  // Criteri ML
  criteri: () => [...supervisioneKeys.all, 'criteri'],
  criteriOrdinari: () => [...supervisioneKeys.criteri(), 'ordinari'],
  criteriTutti: () => [...supervisioneKeys.criteri(), 'tutti'],
  criteriStats: () => [...supervisioneKeys.criteri(), 'stats'],
  pattern: (signature) => [...supervisioneKeys.criteri(), 'pattern', signature],
  storico: () => [...supervisioneKeys.all, 'storico'],
  // AIC specifico
  aic: () => [...supervisioneKeys.all, 'aic'],
  aicPending: () => [...supervisioneKeys.aic(), 'pending'],
  aicDetail: (id) => [...supervisioneKeys.aic(), 'detail', id],
  aicStats: () => [...supervisioneKeys.aic(), 'stats'],
  // Lookup specifico
  lookup: () => [...supervisioneKeys.all, 'lookup'],
  lookupDetail: (id) => [...supervisioneKeys.lookup(), 'detail', id],
  // Listino specifico
  listino: () => [...supervisioneKeys.all, 'listino'],
  listinoDetail: (id) => [...supervisioneKeys.listino(), 'detail', id],
  listinoPattern: (codiceAic) => [...supervisioneKeys.listino(), 'pattern', codiceAic],
};

// ============================================================================
// QUERY HOOKS - Lettura dati
// ============================================================================

/** Hook per supervisioni pending (raggruppate per pattern) */
export function usePendingGrouped(options = {}) {
  return useQuery({
    queryKey: supervisioneKeys.pendingGrouped(),
    queryFn: () => supervisioneApi.getPendingGrouped(),
    ...options,
  });
}

/** Hook per supervisioni pending (lista flat) */
export function usePending(options = {}) {
  return useQuery({
    queryKey: supervisioneKeys.pending(),
    queryFn: () => supervisioneApi.getPending(),
    ...options,
  });
}

/** Hook per conteggio pending */
export function usePendingCount(options = {}) {
  return useQuery({
    queryKey: supervisioneKeys.pendingCount(),
    queryFn: () => supervisioneApi.getPendingCount(),
    staleTime: 30000, // 30 secondi
    ...options,
  });
}

/** Hook per dettaglio supervisione */
export function useSupervisioneDetail(id, options = {}) {
  return useQuery({
    queryKey: supervisioneKeys.detail(id),
    queryFn: () => supervisioneApi.getDetail(id),
    enabled: !!id,
    ...options,
  });
}

/** Hook per supervisioni di un ordine */
export function useSupervisioneByOrdine(idTestata, options = {}) {
  return useQuery({
    queryKey: supervisioneKeys.byOrdine(idTestata),
    queryFn: () => supervisioneApi.getByOrdine(idTestata),
    enabled: !!idTestata,
    ...options,
  });
}

/** Hook per criteri ordinari ML */
export function useCriteriOrdinari(options = {}) {
  return useQuery({
    queryKey: supervisioneKeys.criteriOrdinari(),
    queryFn: () => supervisioneApi.getCriteriOrdinari(),
    staleTime: 60000, // 1 minuto
    ...options,
  });
}

/** Hook per stats criteri */
export function useCriteriStats(options = {}) {
  return useQuery({
    queryKey: supervisioneKeys.criteriStats(),
    queryFn: () => supervisioneApi.getCriteriStats(),
    ...options,
  });
}

/** Hook per storico applicazioni */
export function useStorico(limit = 50, options = {}) {
  return useQuery({
    queryKey: [...supervisioneKeys.storico(), limit],
    queryFn: () => supervisioneApi.getStorico(limit),
    ...options,
  });
}

/** Hook per dettaglio AIC */
export function useAicDetail(id, options = {}) {
  return useQuery({
    queryKey: supervisioneKeys.aicDetail(id),
    queryFn: () => supervisioneApi.getAicDetail(id),
    enabled: !!id,
    ...options,
  });
}

/** Hook per pending AIC */
export function useAicPending(options = {}) {
  return useQuery({
    queryKey: supervisioneKeys.aicPending(),
    queryFn: () => supervisioneApi.getAicPending(),
    ...options,
  });
}

/** Hook per stats AIC */
export function useAicStats(options = {}) {
  return useQuery({
    queryKey: supervisioneKeys.aicStats(),
    queryFn: () => supervisioneApi.getAicStats(),
    ...options,
  });
}

/** Hook per dettaglio Lookup */
export function useLookupDetail(id, options = {}) {
  return useQuery({
    queryKey: supervisioneKeys.lookupDetail(id),
    queryFn: () => supervisioneApi.getLookupDetail(id),
    enabled: !!id,
    ...options,
  });
}

/** Hook per dettaglio Listino */
export function useListinoDetail(id, options = {}) {
  return useQuery({
    queryKey: supervisioneKeys.listinoDetail(id),
    queryFn: () => supervisioneApi.getListinoDetail(id),
    enabled: !!id,
    ...options,
  });
}

// ============================================================================
// MUTATION HOOKS - Decisioni base
// ============================================================================

/**
 * Hook per approvare una supervisione
 * Invalida: pending, pendingGrouped, pendingCount, anomalie, ordini
 */
export function useApprova(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, operatore, note }) =>
      supervisioneApi.approva(id, operatore, note),
    onSuccess: (data, { id }) => {
      // Invalidate supervisione
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pending() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pendingGrouped() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pendingCount() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.detail(id) });
      // Invalidate anomalie (risolte automaticamente)
      queryClient.invalidateQueries({ queryKey: anomalieKeys.lists() });
    },
    ...options,
  });
}

/**
 * Hook per rifiutare una supervisione
 */
export function useRifiuta(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, operatore, note }) =>
      supervisioneApi.rifiuta(id, operatore, note),
    onSuccess: (data, { id }) => {
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pending() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pendingGrouped() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pendingCount() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.detail(id) });
    },
    ...options,
  });
}

/**
 * Hook per modificare e approvare
 */
export function useModifica(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, operatore, modifiche, note }) =>
      supervisioneApi.modifica(id, operatore, modifiche, note),
    onSuccess: (data, { id }) => {
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pending() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pendingGrouped() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pendingCount() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: anomalieKeys.lists() });
    },
    ...options,
  });
}

// ============================================================================
// MUTATION HOOKS - Bulk operations
// ============================================================================

/**
 * Hook per approvazione bulk (per pattern)
 * Invalida tutte le supervisioni del pattern
 */
export function useApprovaBulk(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ patternSignature, operatore, note }) =>
      supervisioneApi.approvaBulk(patternSignature, operatore, note),
    onSuccess: () => {
      // Full invalidation per bulk
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.all });
      queryClient.invalidateQueries({ queryKey: anomalieKeys.lists() });
    },
    ...options,
  });
}

/**
 * Hook per rifiuto bulk (per pattern)
 */
export function useRifiutaBulk(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ patternSignature, operatore, note }) =>
      supervisioneApi.rifiutaBulk(patternSignature, operatore, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.all });
    },
    ...options,
  });
}

// ============================================================================
// MUTATION HOOKS - AIC specific
// ============================================================================

/**
 * Hook per risolvere supervisione AIC
 * Propaga AIC e invalida ordini
 */
export function useRisolviAic(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, operatore, codiceAic, livelloPropagazione, note }) =>
      supervisioneApi.risolviAic(id, operatore, codiceAic, livelloPropagazione, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.all });
      queryClient.invalidateQueries({ queryKey: anomalieKeys.lists() });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.lists() });
    },
    ...options,
  });
}

/**
 * Hook per rifiutare supervisione AIC
 */
export function useRifiutaAic(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, operatore, note }) =>
      supervisioneApi.rifiutaAic(id, operatore, note),
    onSuccess: (data, { id }) => {
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.aicPending() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.aicDetail(id) });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pendingGrouped() });
    },
    ...options,
  });
}

/**
 * Hook per approvazione bulk AIC (per pattern)
 */
export function useApprovaBulkAic(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ patternSignature, operatore, codiceAic, note }) =>
      supervisioneApi.approvaBulkAic(patternSignature, operatore, codiceAic, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.all });
      queryClient.invalidateQueries({ queryKey: anomalieKeys.lists() });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.lists() });
    },
    ...options,
  });
}

/**
 * Hook per correggere errore AIC (batch)
 */
export function useCorreggiErroreAic(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ aicErrato, aicCorretto, operatore, note }) =>
      supervisioneApi.correggiErroreAic(aicErrato, aicCorretto, operatore, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.all });
      queryClient.invalidateQueries({ queryKey: anomalieKeys.lists() });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.lists() });
    },
    ...options,
  });
}

// ============================================================================
// MUTATION HOOKS - Lookup specific
// ============================================================================

/**
 * Hook per risolvere supervisione Lookup
 */
export function useRisolviLookup(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) =>
      supervisioneApi.risolviLookup(id, data),
    onSuccess: (result, { id }) => {
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pending() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pendingGrouped() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.lookupDetail(id) });
      queryClient.invalidateQueries({ queryKey: anomalieKeys.lists() });
      // Invalida ordine se presente nel risultato
      if (result?.id_testata) {
        queryClient.invalidateQueries({ queryKey: ordiniKeys.detail(result.id_testata) });
      }
    },
    ...options,
  });
}

/**
 * Hook per rifiutare supervisione Lookup
 */
export function useRifiutaLookup(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, operatore, note }) =>
      supervisioneApi.rifiutaLookup(id, operatore, note),
    onSuccess: (data, { id }) => {
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pending() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pendingGrouped() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.lookupDetail(id) });
    },
    ...options,
  });
}

// ============================================================================
// MUTATION HOOKS - Listino specific
// ============================================================================

/**
 * Hook per correggere listino
 */
export function useCorreggiListino(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) =>
      supervisioneApi.correggiListino(id, data),
    onSuccess: (result, { id }) => {
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pending() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pendingGrouped() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.listinoDetail(id) });
      queryClient.invalidateQueries({ queryKey: anomalieKeys.lists() });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.lists() });
    },
    ...options,
  });
}

/**
 * Hook per archiviare riga listino
 */
export function useArchiviaListino(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) =>
      supervisioneApi.archiviaListino(id, data),
    onSuccess: (result, { id }) => {
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pending() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pendingGrouped() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.listinoDetail(id) });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.lists() });
    },
    ...options,
  });
}

/**
 * Hook per ri-applicare listino in bulk
 */
export function useRiapplicaListinoBulk(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (operatore) =>
      supervisioneApi.riapplicaListinoBulk(operatore),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.all });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.lists() });
    },
    ...options,
  });
}

// ============================================================================
// MUTATION HOOKS - Pattern ML
// ============================================================================

/**
 * Hook per promuovere pattern a ordinario
 */
export function usePromuoviPattern(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ signature, operatore }) =>
      supervisioneApi.promuoviPattern(signature, operatore),
    onSuccess: (data, { signature }) => {
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.criteriOrdinari() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.criteriStats() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pattern(signature) });
    },
    ...options,
  });
}

/**
 * Hook per resettare pattern
 */
export function useResetPattern(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ signature, operatore }) =>
      supervisioneApi.resetPattern(signature, operatore),
    onSuccess: (data, { signature }) => {
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.criteriOrdinari() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.criteriStats() });
      queryClient.invalidateQueries({ queryKey: supervisioneKeys.pattern(signature) });
    },
    ...options,
  });
}

// ============================================================================
// CONVENIENCE HOOKS
// ============================================================================

/**
 * Hook combinato per supervisione page
 * Ritorna pending + stats + count in un'unica chiamata
 */
export function useSupervisioneDashboard(options = {}) {
  const pendingQuery = usePendingGrouped(options);
  const countQuery = usePendingCount(options);
  const statsQuery = useCriteriStats(options);

  return {
    pending: pendingQuery.data,
    count: countQuery.data,
    stats: statsQuery.data,
    isLoading: pendingQuery.isLoading || countQuery.isLoading || statsQuery.isLoading,
    isError: pendingQuery.isError || countQuery.isError || statsQuery.isError,
    error: pendingQuery.error || countQuery.error || statsQuery.error,
    refetch: () => {
      pendingQuery.refetch();
      countQuery.refetch();
      statsQuery.refetch();
    },
  };
}
