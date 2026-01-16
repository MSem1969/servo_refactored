// =============================================================================
// SERV.O v7.0 - HOOKS INDEX
// =============================================================================

// Session tracking (esistente)
export { default as useSessionTracking } from './useSessionTracking';

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
