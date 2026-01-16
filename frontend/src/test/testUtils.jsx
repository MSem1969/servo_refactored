// =============================================================================
// SERV.O v8.1 - TEST UTILITIES
// =============================================================================
// Helper functions per test React
// =============================================================================

import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '../context/AuthContext';
import { UIProvider } from '../context/UIContext';

/**
 * Crea QueryClient per test (no retry, no refetch)
 */
export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
        staleTime: Infinity,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

/**
 * Wrapper con tutti i providers
 */
export function AllProviders({ children }) {
  const queryClient = createTestQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <UIProvider>{children}</UIProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

/**
 * Custom render con providers
 */
export function renderWithProviders(ui, options = {}) {
  const queryClient = options.queryClient || createTestQueryClient();

  function Wrapper({ children }) {
    return (
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <UIProvider>{children}</UIProvider>
        </AuthProvider>
      </QueryClientProvider>
    );
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...options }),
    queryClient,
  };
}

/**
 * Mock user autenticato
 */
export const mockAuthUser = {
  id: 1,
  username: 'test_user',
  email: 'test@test.local',
  ruolo: 'ADMIN',
  attivo: true,
};

/**
 * Mock ordine
 */
export const mockOrdine = {
  id: 1,
  numero_ordine: 'TEST_001',
  vendor: 'ANGELINI',
  stato: 'ESTRATTO',
  data_ordine: '2026-01-15',
  data_consegna: '2026-01-20',
  farmacia_nome: 'FARMACIA TEST',
  farmacia_piva: '12345678901',
  farmacia_citta: 'Roma',
  farmacia_provincia: 'RM',
  min_id: 'TST001',
  totale_righe: 5,
  has_anomalie: false,
};

/**
 * Mock riga ordine
 */
export const mockRiga = {
  id: 1,
  ordine_id: 1,
  n_riga: 1,
  codice_aic: '012345678',
  descrizione: 'PRODOTTO TEST',
  q_venduta: 10,
  q_omaggio: 0,
  prezzo_pubblico: 15.5,
  prezzo_netto: 10.0,
};

/**
 * Mock API response per lista ordini
 */
export const mockOrdiniResponse = {
  ordini: [mockOrdine],
  total: 1,
  page: 1,
  per_page: 20,
};

/**
 * Helper per aspettare un certo tempo
 */
export const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Helper per aspettare condizione
 */
export async function waitForCondition(condition, timeout = 5000) {
  const start = Date.now();
  while (!condition()) {
    if (Date.now() - start > timeout) {
      throw new Error('Timeout waiting for condition');
    }
    await wait(50);
  }
}
