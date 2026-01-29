// =============================================================================
// SERV.O v10.1 - COMMON COMPONENTS INDEX
// =============================================================================
// Export componenti UI riutilizzabili
// =============================================================================

// Basic Components
export { default as Button } from './Button';
export { default as StatusBadge } from './StatusBadge';
export { default as VendorBadge } from './VendorBadge';
export { default as Loading } from './Loading';
export { default as ErrorBox } from './ErrorBox';
export { default as PdfViewerButton } from './PdfViewerButton'; // v11.4

// Modal (v11.0: both named and default export)
export { default as ModalBase, ModalBase as Modal } from './ModalBase';

// Table
export { default as Table, TableCell } from './Table';

// Filters
export { default as FilterBar, QuickFilters } from './FilterBar';

// Form Components
export {
  default as FormField,
  FormRow,
  FormSection,
  Checkbox,
  RadioGroup,
  Toggle,
} from './FormField';

// Riga Edit Form (v11.0 TIER 3.1)
export {
  default as RigaEditForm,
  QuantitaSection,
  PrezziSection,
  IdentificazioneSection,
  NoteSection,
  FormInput,
  FormTextarea,
  FormDisplay,
} from './RigaEditForm';

// Anomalie Utils (condiviso)
export * from './anomalieUtils';
