// =============================================================================
// SERV.O v8.1 - TEST STATUS BADGE
// =============================================================================

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatusBadge from '../StatusBadge';

describe('StatusBadge', () => {
  describe('rendering', () => {
    it('renders with status prop', () => {
      render(<StatusBadge status="ESTRATTO" />);
      // Component shows label 'Estratto' for status 'ESTRATTO'
      expect(screen.getByText(/Estratto/i)).toBeInTheDocument();
    });

    it('renders with custom label', () => {
      render(<StatusBadge status="ESTRATTO" label="Custom Label" />);
      expect(screen.getByText('Custom Label')).toBeInTheDocument();
    });
  });

  describe('status variations', () => {
    it('renders ESTRATTO badge', () => {
      render(<StatusBadge status="ESTRATTO" />);
      expect(screen.getByText(/Estratto/i)).toBeInTheDocument();
    });

    it('renders CONFERMATO badge', () => {
      render(<StatusBadge status="CONFERMATO" />);
      // CONFERMATO shows as "Pronto Export" in the component
      expect(screen.getByText(/Pronto Export/i)).toBeInTheDocument();
    });

    it('renders unknown status with fallback', () => {
      // Unknown status should show as-is or use default
      const { container } = render(<StatusBadge status="UNKNOWN_STATUS" />);
      expect(container.querySelector('span')).toBeInTheDocument();
    });
  });

  describe('styling', () => {
    it('applies correct class for ESTRATTO (blue)', () => {
      const { container } = render(<StatusBadge status="ESTRATTO" />);
      const badge = container.querySelector('span');
      expect(badge).toHaveClass('bg-blue-100');
    });

    it('applies correct class for CONFERMATO (emerald)', () => {
      const { container } = render(<StatusBadge status="CONFERMATO" />);
      const badge = container.querySelector('span');
      expect(badge).toHaveClass('bg-emerald-100');
    });

    it('applies correct class for ANOMALIA (red)', () => {
      const { container } = render(<StatusBadge status="ANOMALIA" />);
      const badge = container.querySelector('span');
      expect(badge).toHaveClass('bg-red-100');
    });
  });

  describe('size variants', () => {
    it('renders small size (default)', () => {
      const { container } = render(<StatusBadge status="ESTRATTO" size="sm" />);
      const badge = container.querySelector('span');
      expect(badge).toHaveClass('text-xs');
    });

    it('renders medium size', () => {
      const { container } = render(<StatusBadge status="ESTRATTO" size="md" />);
      const badge = container.querySelector('span');
      expect(badge).toHaveClass('text-sm');
    });
  });

  describe('icon display', () => {
    it('shows icon by default', () => {
      const { container } = render(<StatusBadge status="ESTRATTO" />);
      // Icon should be present (📄 for ESTRATTO)
      expect(container.textContent).toContain('📄');
    });

    it('hides icon when showIcon is false', () => {
      const { container } = render(<StatusBadge status="ESTRATTO" showIcon={false} />);
      // Icon should not be present
      expect(container.textContent).not.toContain('📄');
    });
  });
});
