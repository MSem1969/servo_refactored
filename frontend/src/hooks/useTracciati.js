// =============================================================================
// SERV.O v7.0 - TRACCIATI HOOKS
// =============================================================================
// React Query hooks per gestione tracciati EDI
// =============================================================================

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tracciatiApi } from '../api';
import { ordiniKeys } from './useOrdini';

// Query keys factory
export const tracciatiKeys = {
  all: ['tracciati'],
  pronti: () => [...tracciatiKeys.all, 'pronti'],
  storico: (limit) => [...tracciatiKeys.all, 'storico', limit],
  preview: (id) => [...tracciatiKeys.all, 'preview', id],
  files: () => [...tracciatiKeys.all, 'files'],
};

// Hook per ordini pronti per export
export function useOrdiniProntiExport(options = {}) {
  return useQuery({
    queryKey: tracciatiKeys.pronti(),
    queryFn: tracciatiApi.getPronti,
    ...options,
  });
}

// Hook per storico esportazioni
export function useTracciatiStorico(limit = 20, options = {}) {
  return useQuery({
    queryKey: tracciatiKeys.storico(limit),
    queryFn: () => tracciatiApi.getStorico(limit),
    ...options,
  });
}

// Hook per preview tracciato
export function useTracciatiPreview(id, options = {}) {
  return useQuery({
    queryKey: tracciatiKeys.preview(id),
    queryFn: () => tracciatiApi.getPreview(id),
    enabled: !!id,
    ...options,
  });
}

// Hook per lista file tracciati
export function useTracciatiFiles(options = {}) {
  return useQuery({
    queryKey: tracciatiKeys.files(),
    queryFn: tracciatiApi.getFiles,
    ...options,
  });
}

// Mutation: genera tracciati multipli
export function useGeneraTracciati() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ordiniIds) => tracciatiApi.genera(ordiniIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tracciatiKeys.pronti() });
      queryClient.invalidateQueries({ queryKey: tracciatiKeys.storico() });
      queryClient.invalidateQueries({ queryKey: tracciatiKeys.files() });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.lists() });
    },
  });
}

// Mutation: genera tracciato singolo
export function useGeneraTracciatoSingolo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id) => tracciatiApi.generaSingolo(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: tracciatiKeys.pronti() });
      queryClient.invalidateQueries({ queryKey: tracciatiKeys.storico() });
      queryClient.invalidateQueries({ queryKey: tracciatiKeys.files() });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.lists() });
    },
  });
}

// Mutation: elimina file tracciati
export function useDeleteTracciatiFiles() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => tracciatiApi.deleteFiles(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tracciatiKeys.files() });
    },
  });
}
