// =============================================================================
// SERV.O v8.1 - TEST CONFERMA UTILITIES
// =============================================================================

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  PAROLA_CONFERMA,
  MESSAGGIO_CONFERMA,
  richiestaConferma,
  richiestaConfermaSemplice,
  richiestaInput,
} from '../confirmazione';

describe('Conferma Utilities', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('constants', () => {
    it('has correct PAROLA_CONFERMA', () => {
      expect(PAROLA_CONFERMA).toBe('CONFERMA');
    });

    it('has correct MESSAGGIO_CONFERMA', () => {
      expect(MESSAGGIO_CONFERMA).toContain('CONFERMA');
    });
  });

  describe('richiestaConferma', () => {
    it('returns true when user types CONFERMA', () => {
      window.prompt = vi.fn(() => 'CONFERMA');
      const result = richiestaConferma('Test operazione');
      expect(result).toBe(true);
    });

    it('returns true when user types conferma (lowercase)', () => {
      window.prompt = vi.fn(() => 'conferma');
      const result = richiestaConferma('Test operazione');
      expect(result).toBe(true);
    });

    it('returns true when user types CoNfErMa (mixed case)', () => {
      window.prompt = vi.fn(() => 'CoNfErMa');
      const result = richiestaConferma('Test operazione');
      expect(result).toBe(true);
    });

    it('returns false when user types wrong word', () => {
      window.prompt = vi.fn(() => 'SBAGLIATO');
      const result = richiestaConferma('Test operazione');
      expect(result).toBe(false);
    });

    it('returns false when user cancels', () => {
      window.prompt = vi.fn(() => null);
      const result = richiestaConferma('Test operazione');
      expect(result).toBe(false);
    });

    it('returns false when user types empty string', () => {
      window.prompt = vi.fn(() => '');
      const result = richiestaConferma('Test operazione');
      expect(result).toBe(false);
    });

    it('includes operation description in prompt', () => {
      window.prompt = vi.fn(() => 'CONFERMA');
      richiestaConferma('Elimina tutti i dati');
      expect(window.prompt).toHaveBeenCalledWith(
        expect.stringContaining('Elimina tutti i dati')
      );
    });

    it('includes details when provided', () => {
      window.prompt = vi.fn(() => 'CONFERMA');
      richiestaConferma('Operazione', 'Dettagli aggiuntivi');
      expect(window.prompt).toHaveBeenCalledWith(
        expect.stringContaining('Dettagli aggiuntivi')
      );
    });
  });

  describe('richiestaConfermaSemplice', () => {
    it('returns true when user confirms', () => {
      window.confirm = vi.fn(() => true);
      const result = richiestaConfermaSemplice('Sei sicuro?');
      expect(result).toBe(true);
    });

    it('returns false when user cancels', () => {
      window.confirm = vi.fn(() => false);
      const result = richiestaConfermaSemplice('Sei sicuro?');
      expect(result).toBe(false);
    });

    it('passes message to confirm', () => {
      window.confirm = vi.fn(() => true);
      richiestaConfermaSemplice('Messaggio personalizzato');
      expect(window.confirm).toHaveBeenCalledWith('Messaggio personalizzato');
    });
  });

  describe('richiestaInput', () => {
    it('returns user input', () => {
      window.prompt = vi.fn(() => 'User input');
      const result = richiestaInput('Inserisci valore');
      expect(result).toBe('User input');
    });

    it('returns null when cancelled', () => {
      window.prompt = vi.fn(() => null);
      const result = richiestaInput('Inserisci valore');
      expect(result).toBeNull();
    });

    it('returns null when empty and required', () => {
      window.prompt = vi.fn(() => '');
      const result = richiestaInput('Inserisci valore', { required: true });
      expect(result).toBeNull();
    });

    it('returns null when too short and minLength set', () => {
      window.prompt = vi.fn(() => 'ab');
      const result = richiestaInput('Inserisci valore', { minLength: 5 });
      expect(result).toBeNull();
    });

    it('returns input when meets minLength', () => {
      window.prompt = vi.fn(() => 'abcdef');
      const result = richiestaInput('Inserisci valore', { minLength: 5 });
      expect(result).toBe('abcdef');
    });

    it('trims whitespace', () => {
      window.prompt = vi.fn(() => '  value  ');
      const result = richiestaInput('Inserisci valore');
      expect(result).toBe('value');
    });
  });
});
