// =============================================================================
// SERV.O v7.0 - ANOMALIE HOOKS
// =============================================================================
// React Query hooks per gestione anomalie
// =============================================================================

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { anomalieApi } from '../api';

// Query keys factory
export const anomalieKeys = {
  all: ['anomalie'],
  lists: () => [...anomalieKeys.all, 'list'],
  list: (filters) => [...anomalieKeys.lists(), filters],
  byOrdine: (id) => [...anomalieKeys.all, 'ordine', id],
  dettaglio: (id) => [...anomalieKeys.all, 'dettaglio', id],
  tipi: () => [...anomalieKeys.all, 'tipi'],
  livelli: () => [...anomalieKeys.all, 'livelli'],
  stati: () => [...anomalieKeys.all, 'stati'],
};

// Hook per lista anomalie
export function useAnomalies(filters = {}, options = {}) {
  return useQuery({
    queryKey: anomalieKeys.list(filters),
    queryFn: () => anomalieApi.getList(filters),
    ...options,
  });
}

// Hook per anomalie di un ordine
export function useAnomalieByOrdine(idOrdine, options = {}) {
  return useQuery({
    queryKey: anomalieKeys.byOrdine(idOrdine),
    queryFn: () => anomalieApi.getByOrdine(idOrdine),
    enabled: !!idOrdine,
    ...options,
  });
}

// Hook per dettaglio anomalia
export function useAnomaliaDettaglio(id, options = {}) {
  return useQuery({
    queryKey: anomalieKeys.dettaglio(id),
    queryFn: () => anomalieApi.getDettaglio(id),
    enabled: !!id,
    ...options,
  });
}

// Hook per tipi anomalie
export function useTipiAnomalie(options = {}) {
  return useQuery({
    queryKey: anomalieKeys.tipi(),
    queryFn: anomalieApi.getTipi,
    staleTime: 1000 * 60 * 60, // 1 ora - dati statici
    ...options,
  });
}

// Hook per livelli anomalie
export function useLivelliAnomalie(options = {}) {
  return useQuery({
    queryKey: anomalieKeys.livelli(),
    queryFn: anomalieApi.getLivelli,
    staleTime: 1000 * 60 * 60,
    ...options,
  });
}

// Hook per stati anomalie
export function useStatiAnomalie(options = {}) {
  return useQuery({
    queryKey: anomalieKeys.stati(),
    queryFn: anomalieApi.getStati,
    staleTime: 1000 * 60 * 60,
    ...options,
  });
}

// Mutation: aggiorna anomalia
export function useUpdateAnomalia() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => anomalieApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: anomalieKeys.dettaglio(id) });
      queryClient.invalidateQueries({ queryKey: anomalieKeys.lists() });
    },
  });
}

// Mutation: risolvi anomalia
export function useRisolviAnomalia() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, note }) => anomalieApi.risolviDettaglio(id, note),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: anomalieKeys.dettaglio(id) });
      queryClient.invalidateQueries({ queryKey: anomalieKeys.lists() });
    },
  });
}

// Mutation: batch risolvi
export function useBatchRisolviAnomalie() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ids, note }) => anomalieApi.batchRisolvi(ids, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: anomalieKeys.lists() });
    },
  });
}

// Mutation: batch ignora
export function useBatchIgnoraAnomalie() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ids, note }) => anomalieApi.batchIgnora(ids, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: anomalieKeys.lists() });
    },
  });
}

// Mutation: modifica riga anomalia
export function useModificaRigaAnomalia() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => anomalieApi.modificaRiga(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: anomalieKeys.dettaglio(id) });
      queryClient.invalidateQueries({ queryKey: anomalieKeys.lists() });
    },
  });
}
