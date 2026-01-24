/**
 * Components Index - v6.2 Refactoring
 * Export centralizzato dei componenti condivisi
 */

export { Modal } from './Modal';
export { StatCard, StatCardGrid } from './StatCard';
// Badge consolidati in common/StatusBadge.jsx
export {
  Badge,
  StatoOrdineBadge,
  StatoAnomaliaBadge,
  TipoAnomaliaBadge,
  SeveritaBadge,
  BooleanBadge,
  colorMappings
} from '../common/StatusBadge';
export { AnomaliaDetailModal } from './AnomaliaDetailModal';
export { default as Avatar, AvatarWithName } from './Avatar';
export { default as ProfiloModal } from './ProfiloModal';
// v11.0: Unified AIC Assignment Modal (TIER 2.1)
export {
  AicAssignmentModal,
  AIC_MODAL_MODES,
  PROPAGATION_LEVELS
} from './AicAssignmentModal';
