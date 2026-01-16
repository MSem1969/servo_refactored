# =============================================================================
# SERV.O v7.0 - SUPERVISION CONSTANTS
# =============================================================================
# Costanti per il sistema di supervisione
# =============================================================================

# Soglia per promozione pattern a "ordinario"
# Dopo N approvazioni con stesso pattern, diventa automatico
# v8.1: Differenziato per tipo anomalia
SOGLIA_PROMOZIONE = 5  # Per anomalie GRAVI (LST, LKP score < 80%, ESP)
SOGLIA_PROMOZIONE_ORDINARIA = 1  # Per anomalie ORDINARIE (LKP score >= 80%)

# Fasce scostamento per normalizzazione pattern
# Usate per raggruppare scostamenti simili
FASCE_NORMALIZZATE = {
    (-10, 0): '-10/0%',
    (-20, -10): '-20/-10%',
    (-50, -20): '-50/-20%',
    (0, 10): '0/+10%',
    (10, 20): '+10/+20%',
    (20, 50): '+20/+50%',
}
