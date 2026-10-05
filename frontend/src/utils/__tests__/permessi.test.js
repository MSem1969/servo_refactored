import { describe, it, expect, beforeEach } from 'vitest';
import {
  setPermessiUtente, resetPermessiUtente, puoVedere, puoModificare,
  puoPropagareGlobale, gestisceRuoliInferiori,
} from '../permessi';

describe('permessi di sezione (matrice)', () => {
  beforeEach(() => resetPermessiUtente());

  it('segue la matrice per i ruoli non admin', () => {
    setPermessiUtente({ ruolo: 'supervisore' }, {
      tracciati: { can_view: true, can_edit: true },
      backup: { can_view: true, can_edit: false },
    });
    expect(puoModificare('tracciati')).toBe(true);
    expect(puoVedere('backup')).toBe(true);
    expect(puoModificare('backup')).toBe(false);
    expect(puoVedere('sistema')).toBe(false);
  });

  it('admin ha sempre accesso pieno', () => {
    setPermessiUtente({ ruolo: 'ADMIN' }, {});
    expect(puoModificare('sistema')).toBe(true);
    expect(puoPropagareGlobale()).toBe(true);
  });

  it('propagazione GLOBALE = can_edit su supervisione, non il ruolo', () => {
    setPermessiUtente({ ruolo: 'supervisore' }, { supervisione: { can_view: true, can_edit: false } });
    expect(puoPropagareGlobale()).toBe(false);
    setPermessiUtente({ ruolo: 'operatore' }, { supervisione: { can_view: true, can_edit: true } });
    expect(puoPropagareGlobale()).toBe(true);
  });

  it('dopo il logout non resta nulla', () => {
    setPermessiUtente({ ruolo: 'admin' }, {});
    resetPermessiUtente();
    expect(puoVedere('dashboard')).toBe(false);
  });

  it('gestione ruoli inferiori segue la gerarchia', () => {
    for (const r of ['admin', 'superuser', 'supervisore']) {
      setPermessiUtente({ ruolo: r }, {});
      expect(gestisceRuoliInferiori()).toBe(true);
    }
    for (const r of ['operatore', 'readonly']) {
      setPermessiUtente({ ruolo: r }, {});
      expect(gestisceRuoliInferiori()).toBe(false);
    }
  });
});
