// =============================================================================
// SERV.O v7.0 - DASHBOARD HOOKS
// =============================================================================
// React Query hooks per dashboard e statistiche
// =============================================================================

import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '../api';

// Query keys factory
export const dashboardKeys = {
  all: ['dashboard'],
  stats: () => [...dashboardKeys.all, 'stats'],
  summary: () => [...dashboardKeys.all, 'summary'],
  ordiniRecenti: (limit) => [...dashboardKeys.all, 'ordini-recenti', limit],
  anomalieCritiche: (limit) => [...dashboardKeys.all, 'anomalie-critiche', limit],
  vendorStats: () => [...dashboardKeys.all, 'vendor-stats'],
  anagraficaStats: () => [...dashboardKeys.all, 'anagrafica-stats'],
};

// Hook per statistiche dashboard
export function useDashboardStats(options = {}) {
  return useQuery({
    queryKey: dashboardKeys.stats(),
    queryFn: dashboardApi.getStats,
    staleTime: 1000 * 30, // 30 secondi - dati frequentemente aggiornati
    ...options,
  });
}

// Hook per summary
export function useDashboardSummary(options = {}) {
  return useQuery({
    queryKey: dashboardKeys.summary(),
    queryFn: dashboardApi.getSummary,
    staleTime: 1000 * 30,
    ...options,
  });
}

// Hook per ordini recenti
export function useOrdiniRecenti(limit = 10, options = {}) {
  return useQuery({
    queryKey: dashboardKeys.ordiniRecenti(limit),
    queryFn: () => dashboardApi.getOrdiniRecenti(limit),
    staleTime: 1000 * 30,
    ...options,
  });
}

// Hook per anomalie critiche
export function useAnomalieCritiche(limit = 10, options = {}) {
  return useQuery({
    queryKey: dashboardKeys.anomalieCritiche(limit),
    queryFn: () => dashboardApi.getAnomalieCritiche(limit),
    staleTime: 1000 * 30,
    ...options,
  });
}

// Hook per statistiche vendor
export function useVendorStats(options = {}) {
  return useQuery({
    queryKey: dashboardKeys.vendorStats(),
    queryFn: dashboardApi.getVendorStats,
    staleTime: 1000 * 60 * 5, // 5 minuti
    ...options,
  });
}

// Hook per statistiche anagrafica
export function useAnagraficaStats(options = {}) {
  return useQuery({
    queryKey: dashboardKeys.anagraficaStats(),
    queryFn: dashboardApi.getAnagraficaStats,
    staleTime: 1000 * 60 * 5,
    ...options,
  });
}
