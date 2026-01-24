// =============================================================================
// SERV.O v7.0 - ORDINI HOOKS
// =============================================================================
// React Query hooks per gestione ordini
// =============================================================================

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ordiniApi } from '../api';

// Query keys factory
export const ordiniKeys = {
  all: ['ordini'],
  lists: () => [...ordiniKeys.all, 'list'],
  list: (filters) => [...ordiniKeys.lists(), filters],
  details: () => [...ordiniKeys.all, 'detail'],
  detail: (id) => [...ordiniKeys.details(), id],
  righe: (id) => [...ordiniKeys.all, 'righe', id],
  statoRighe: (id) => [...ordiniKeys.all, 'stato-righe', id],
  rigaDettaglio: (idTestata, idDettaglio) => [...ordiniKeys.all, 'riga', idTestata, idDettaglio],
};

// Hook per lista ordini
export function useOrdini(filters = {}, options = {}) {
  return useQuery({
    queryKey: ordiniKeys.list(filters),
    queryFn: () => ordiniApi.getList(filters),
    ...options,
  });
}

// Hook per dettaglio ordine
export function useOrdine(id, options = {}) {
  return useQuery({
    queryKey: ordiniKeys.detail(id),
    queryFn: () => ordiniApi.getDetail(id),
    enabled: !!id,
    ...options,
  });
}

// Hook per righe ordine
export function useOrdineRighe(id, options = {}) {
  return useQuery({
    queryKey: ordiniKeys.righe(id),
    queryFn: () => ordiniApi.getRighe(id),
    enabled: !!id,
    ...options,
  });
}

// Hook per stato righe ordine
export function useStatoRighe(id, options = {}) {
  return useQuery({
    queryKey: ordiniKeys.statoRighe(id),
    queryFn: () => ordiniApi.getStatoRighe(id),
    enabled: !!id,
    ...options,
  });
}

// Hook per dettaglio singola riga
export function useRigaDettaglio(idTestata, idDettaglio, options = {}) {
  return useQuery({
    queryKey: ordiniKeys.rigaDettaglio(idTestata, idDettaglio),
    queryFn: () => ordiniApi.getRigaDettaglio(idTestata, idDettaglio),
    enabled: !!idTestata && !!idDettaglio,
    ...options,
  });
}

// Mutation: aggiorna stato ordine
export function useUpdateStatoOrdine() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, stato }) => ordiniApi.updateStato(id, stato),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ordiniKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.lists() });
    },
  });
}

// Mutation: elimina ordine
export function useDeleteOrdine() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id) => ordiniApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ordiniKeys.lists() });
    },
  });
}

// Mutation: conferma riga
export function useConfermaRiga() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ idTestata, idDettaglio, operatore, note }) =>
      ordiniApi.confermaRiga(idTestata, idDettaglio, operatore, note),
    onSuccess: (_, { idTestata }) => {
      queryClient.invalidateQueries({ queryKey: ordiniKeys.detail(idTestata) });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.righe(idTestata) });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.statoRighe(idTestata) });
    },
  });
}

// Mutation: conferma ordine completo
export function useConfermaOrdineCompleto() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ idTestata, operatore, forzaConferma, note }) =>
      ordiniApi.confermaOrdineCompleto(idTestata, operatore, forzaConferma, note),
    onSuccess: (_, { idTestata }) => {
      queryClient.invalidateQueries({ queryKey: ordiniKeys.detail(idTestata) });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.righe(idTestata) });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.statoRighe(idTestata) });
    },
  });
}

// Mutation: modifica riga
export function useModificaRiga() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ idTestata, idDettaglio, operatore, modifiche, note }) =>
      ordiniApi.modificaRiga(idTestata, idDettaglio, operatore, modifiche, note),
    onSuccess: (_, { idTestata, idDettaglio }) => {
      queryClient.invalidateQueries({ queryKey: ordiniKeys.detail(idTestata) });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.righe(idTestata) });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.rigaDettaglio(idTestata, idDettaglio) });
    },
  });
}

// Mutation: valida e genera tracciato
export function useValidaEGeneraTracciato() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ idTestata, operatore, validazioneMassiva }) =>
      ordiniApi.validaEGeneraTracciato(idTestata, operatore, validazioneMassiva),
    onSuccess: (_, { idTestata }) => {
      queryClient.invalidateQueries({ queryKey: ordiniKeys.detail(idTestata) });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.lists() });
    },
  });
}

// Mutation: registra evasione
export function useRegistraEvasione() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ idTestata, idDettaglio, qDaEvadere, operatore }) =>
      ordiniApi.registraEvasione(idTestata, idDettaglio, qDaEvadere, operatore),
    onSuccess: (_, { idTestata }) => {
      queryClient.invalidateQueries({ queryKey: ordiniKeys.detail(idTestata) });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.righe(idTestata) });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.statoRighe(idTestata) });
    },
  });
}

// Mutation: ripristina riga
export function useRipristinaRiga() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ idTestata, idDettaglio, operatore }) =>
      ordiniApi.ripristinaRiga(idTestata, idDettaglio, operatore),
    onSuccess: (_, { idTestata }) => {
      queryClient.invalidateQueries({ queryKey: ordiniKeys.detail(idTestata) });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.righe(idTestata) });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.statoRighe(idTestata) });
    },
  });
}

// Mutation: ripristina tutto
export function useRipristinaTutto() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ idTestata, operatore }) =>
      ordiniApi.ripristinaTutto(idTestata, operatore),
    onSuccess: (_, { idTestata }) => {
      queryClient.invalidateQueries({ queryKey: ordiniKeys.detail(idTestata) });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.righe(idTestata) });
      queryClient.invalidateQueries({ queryKey: ordiniKeys.statoRighe(idTestata) });
    },
  });
}

// Mutation: batch update stato
export function useBatchUpdateStato() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ids, stato }) => ordiniApi.batchUpdateStato(ids, stato),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ordiniKeys.lists() });
    },
  });
}

// Mutation: batch delete
export function useBatchDelete() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ids) => ordiniApi.batchDelete(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ordiniKeys.lists() });
    },
  });
}
