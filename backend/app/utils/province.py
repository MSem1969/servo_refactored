# =============================================================================
# SERV.O v7.0 - UTILS/PROVINCE
# =============================================================================
# Funzioni per normalizzazione province italiane
# =============================================================================

from ..config import PROVINCE_MAP


def provincia_nome_to_sigla(nome: str) -> str:
    """
    Converte nome provincia in sigla (2 lettere).

    Args:
        nome: Nome provincia (es: "Milano", "ROMA", "Pordenone")

    Returns:
        Sigla provincia (es: "MI", "RM", "PN")
    """
    if not nome:
        return ''

    nome = nome.strip().upper()

    # Se già sigla (2 lettere)
    if len(nome) == 2 and nome.isalpha():
        return nome

    # Cerca nel mapping
    sigla = PROVINCE_MAP.get(nome)
    if sigla:
        return sigla

    # Prova match parziale
    for prov_nome, prov_sigla in PROVINCE_MAP.items():
        if prov_nome.startswith(nome) or nome.startswith(prov_nome):
            return prov_sigla

    # Fallback: prime 2 lettere
    return nome[:2] if len(nome) >= 2 else ''


def sigla_to_provincia_nome(sigla: str) -> str:
    """Converte sigla provincia in nome completo."""
    if not sigla:
        return ''

    sigla = sigla.strip().upper()

    # Cerca nel mapping inverso
    for nome, sig in PROVINCE_MAP.items():
        if sig == sigla:
            return nome.title()

    return sigla
