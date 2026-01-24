// =============================================================================
// SERV.O v10.1 - HOOKS INDEX
// =============================================================================

// Session tracking
export { default as useSessionTracking } from './useSessionTracking';

// Base Hooks (v10.1)
export { useTableSelection } from './useTableSelection';
export { useMultiModal, useModal } from './useMultiModal';
export { useFilterState, createFilterHandler } from './useFilterState';

// Utilities (v10.1)
export {
  buildQueryParams,
  filtersToQueryString,
  parseQueryParams,
  mergeFilters,
  createMutation,
  createSimpleMutation,
  createIdMutation,
} from './utils';

// Ordini hooks
export {
  ordiniKeys,
  useOrdini,
  useOrdine,
  useOrdineRighe,
  useStatoRighe,
  useRigaDettaglio,
  useUpdateStatoOrdine,
  useDeleteOrdine,
  useConfermaRiga,
  useConfermaOrdineCompleto,
  useModificaRiga,
  useValidaEGeneraTracciato,
  useRegistraEvasione,
  useRipristinaRiga,
  useRipristinaTutto,
  useBatchUpdateStato,
  useBatchDelete,
} from './useOrdini';

// Anomalie hooks
export {
  anomalieKeys,
  useAnomalies,
  useAnomalieByOrdine,
  useAnomaliaDettaglio,
  useTipiAnomalie,
  useLivelliAnomalie,
  useStatiAnomalie,
  useUpdateAnomalia,
  useRisolviAnomalia,
  useBatchRisolviAnomalie,
  useBatchIgnoraAnomalie,
  useModificaRigaAnomalia,
} from './useAnomalies';

// Dashboard hooks
export {
  dashboardKeys,
  useDashboardStats,
  useDashboardSummary,
  useOrdiniRecenti,
  useAnomalieCritiche,
  useVendorStats,
  useAnagraficaStats,
} from './useDashboard';

// Tracciati hooks
export {
  tracciatiKeys,
  useOrdiniProntiExport,
  useTracciatiStorico,
  useTracciatiPreview,
  useTracciatiFiles,
  useGeneraTracciati,
  useGeneraTracciatoSingolo,
  useDeleteTracciatiFiles,
} from './useTracciati';

// Supervisione hooks (v11.0 - TIER 2.3)
export {
  supervisioneKeys,
  // Query hooks
  usePendingGrouped,
  usePending,
  usePendingCount,
  useSupervisioneDetail,
  useSupervisioneByOrdine,
  useCriteriOrdinari,
  useCriteriStats,
  useStorico,
  useAicDetail,
  useAicPending,
  useAicStats,
  useLookupDetail,
  useListinoDetail,
  // Mutation hooks - base
  useApprova,
  useRifiuta,
  useModifica,
  // Mutation hooks - bulk
  useApprovaBulk,
  useRifiutaBulk,
  // Mutation hooks - AIC
  useRisolviAic,
  useRifiutaAic,
  useApprovaBulkAic,
  useCorreggiErroreAic,
  // Mutation hooks - Lookup
  useRisolviLookup,
  useRifiutaLookup,
  // Mutation hooks - Listino
  useCorreggiListino,
  useArchiviaListino,
  useRiapplicaListinoBulk,
  // Mutation hooks - Pattern
  usePromuoviPattern,
  useResetPattern,
  // Convenience hooks
  useSupervisioneDashboard,
} from './useSupervisione';
