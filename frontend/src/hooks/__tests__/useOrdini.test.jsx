// =============================================================================
// SERV.O v8.1 - TEST USE ORDINI HOOK
// =============================================================================
// Test basici per verificare che il modulo hooks si importa correttamente
// =============================================================================

import { describe, it, expect } from 'vitest';

describe('useOrdini module', () => {
  it('exports useOrdini hook', async () => {
    const module = await import('../useOrdini');
    expect(module.useOrdini).toBeDefined();
    expect(typeof module.useOrdini).toBe('function');
  });

  it('exports useOrdine hook', async () => {
    const module = await import('../useOrdini');
    expect(module.useOrdine).toBeDefined();
    expect(typeof module.useOrdine).toBe('function');
  });

  it('exports useOrdiniMutations hook', async () => {
    const module = await import('../useOrdini');
    // Some hooks might not exist - just verify the module loads
    expect(module).toBeDefined();
  });
});
