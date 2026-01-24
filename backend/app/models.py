# =============================================================================
# SERV.O v6.2 - AUTH MODELS
# =============================================================================
# Modelli Pydantic per autenticazione e gestione utenti.
# Definisce strutture dati per request/response delle API auth.
#
# STRUTTURA:
# - Enumerazioni (RuoloUtente, CategoriaAzione)
# - Request models (Login, CreaUtente, ModificaUtente, etc.)
# - Response models (UtenteResponse, SessioneResponse, etc.)
# - TokenPayload (interno per JWT)
# =============================================================================

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# =============================================================================
# ENUMERAZIONI RUOLI
# =============================================================================

class RuoloUtente(str, Enum):
    """
    Enum dei ruoli disponibili nel sistema.

    Gerarchia (dal più alto al più basso):
    1. admin       - Accesso totale backend+frontend, crea supervisori
    2. supervisore - Frontend completo, crea operatori
    3. operatore   - Solo Database + Upload
    4. readonly    - Solo visualizzazione (legacy, mantenuto per compatibilità)

    Note:
    - Il valore stringa corrisponde a quello salvato nel DB
    - La gerarchia è gestita in permissions.py
    """
    ADMIN = "admin"
    SUPERVISORE = "supervisore"
    OPERATORE = "operatore"
    READONLY = "readonly"


class CategoriaAzione(str, Enum):
    """
    Categorie per classificare le azioni nel log audit.

    Utile per:
    - Filtrare log per tipologia
    - Raggruppare statistiche
    - Generare report di audit
    """
    AUTH = "AUTH"              # Login, logout, token refresh
    USER_MGMT = "USER_MGMT"    # Creazione, modifica, disabilitazione utenti
    DATA = "DATA"              # Operazioni su ordini, anomalie, etc.
    SYSTEM = "SYSTEM"          # Operazioni di sistema, backup, etc.
    EXPORT = "EXPORT"          # Esportazioni tracciati


# =============================================================================
# MODELLI REQUEST - LOGIN
# =============================================================================

class LoginRequest(BaseModel):
    """
    Request body per endpoint POST /auth/login.

    Campi:
    - username: nome utente (verrà normalizzato a lowercase)
    - password: password in chiaro (confrontata con hash in DB)

    Validazioni:
    - username: min 3, max 50 caratteri
    - password: min 6 caratteri
    """
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Nome utente per l'accesso"
    )
    password: str = Field(
        ...,
        min_length=6,
        description="Password dell'utente"
    )

    @field_validator('username')
    @classmethod
    def username_lowercase(cls, v):
        """Normalizza username a lowercase e rimuove spazi."""
        return v.strip().lower()


class LoginResponse(BaseModel):
    """
    Response body per login riuscito.

    Campi:
    - access_token: JWT da usare nelle richieste successive (header Authorization)
    - token_type: sempre "bearer" (standard OAuth2)
    - expires_in: secondi alla scadenza del token
    - user: informazioni complete dell'utente loggato

    Uso frontend:
    1. Salvare access_token in localStorage
    2. Usare in header: Authorization: Bearer <access_token>
    3. Usare user per mostrare info utente e permessi
    """
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Secondi alla scadenza del token")
    user: "UtenteResponse"


# =============================================================================
# MODELLI REQUEST - GESTIONE UTENTI
# =============================================================================

class CreaUtenteRequest(BaseModel):
    """
    Request body per POST /utenti (creazione nuovo utente).

    Regole di creazione (verificate nel router):
    - admin può creare: supervisore, operatore
    - supervisore può creare: solo operatore
    - operatore non può creare nessuno

    Validazioni:
    - username: 3-50 char, solo lettere/numeri/._-, univoco
    - password: min 8 caratteri
    - nome/cognome: min 2 char
    - email: formato valido se fornita, univoca
    - ruolo: deve essere uno dei valori enum
    """
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r'^[a-zA-Z0-9._-]+$',
        description="Username univoco (lettere, numeri, . _ -)"
    )

    password: str = Field(
        ...,
        min_length=8,
        description="Password (minimo 8 caratteri)"
    )
    nome: str = Field(..., min_length=2, max_length=100)
    cognome: str = Field(..., min_length=2, max_length=100)
    email: Optional[EmailStr] = Field(None, description="Email opzionale")
    ruolo: RuoloUtente = Field(
        ...,
        description="Ruolo da assegnare all'utente"
    )

    @field_validator('username')
    @classmethod
    def username_lowercase(cls, v):
        """Normalizza username a lowercase."""
        return v.strip().lower()

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        """Validazione base forza password."""
        if len(v) < 8:
            raise ValueError('Password deve essere almeno 8 caratteri')
        # Nota: per sicurezza avanzata, aggiungere controlli su:
        # - Presenza maiuscole/minuscole
        # - Presenza numeri
        # - Presenza caratteri speciali
        return v


class ModificaUtenteRequest(BaseModel):
    """
    Request body per PATCH /utenti/{id} (modifica utente).

    Tutti i campi sono opzionali: si aggiornano solo quelli forniti.

    Campi NON modificabili (per design):
    - username: identificativo univoco, non cambia mai
    - ruolo: per cambiare ruolo, disabilitare e creare nuovo utente

    Note:
    - Email viene validata solo se fornita
    - Campi vuoti ("") sono diversi da None (non fornito)
    """
    nome: Optional[str] = Field(None, min_length=2, max_length=100)
    cognome: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None


class CambioPasswordRequest(BaseModel):
    """
    Request body per POST /utenti/{id}/cambio-password.

    Logica:
    - Se utente cambia la PROPRIA password: richiede vecchia_password
    - Se admin/supervisore cambia password ALTRUI: vecchia_password non richiesta

    Sicurezza:
    - Dopo cambio password, tutte le altre sessioni vengono revocate
    - Se cambio propria, sessione corrente mantenuta
    """
    vecchia_password: Optional[str] = Field(
        None,
        description="Richiesta se utente cambia la propria password"
    )
    nuova_password: str = Field(..., min_length=8)

    @field_validator('nuova_password')
    @classmethod
    def password_strength(cls, v):
        """Validazione forza nuova password."""
        if len(v) < 8:
            raise ValueError('Password deve essere almeno 8 caratteri')
        return v


class DisabilitaUtenteRequest(BaseModel):
    """
    Request body per POST /utenti/{id}/disabilita.

    La disabilitazione è un "soft delete":
    - Utente non può più fare login
    - Tutte le sessioni attive vengono revocate
    - Dati e log rimangono per audit
    - Può essere riabilitato in futuro
    """
    motivo: Optional[str] = Field(
        None,
        max_length=500,
        description="Motivo della disabilitazione (opzionale ma consigliato)"
    )


# =============================================================================
# MODELLI RESPONSE - UTENTI
# =============================================================================

class UtenteResponse(BaseModel):
    """
    Response standard per dati utente.

    Sicurezza:
    - NON include mai password_hash
    - NON include dati sensibili interni

    Campi audit:
    - data_creazione: quando è stato creato
    - created_by_operatore: ID di chi lo ha creato (catena responsabilità)
    - last_login_at: ultimo accesso (utile per audit)

    Campi disabilitazione (popolati solo se disabilitato):
    - disabled_at: quando è stato disabilitato
    - disabled_by_operatore: chi lo ha disabilitato
    - disable_reason: motivo fornito
    """
    id_operatore: int
    username: str
    nome: Optional[str]
    cognome: Optional[str]
    email: Optional[str]
    ruolo: RuoloUtente
    attivo: bool

    # Audit creazione
    data_creazione: Optional[datetime]
    created_by_operatore: Optional[int]
    last_login_at: Optional[datetime]

    # Campi disabilitazione
    disabled_at: Optional[datetime]
    disabled_by_operatore: Optional[int]
    disable_reason: Optional[str]

    class Config:
        """Configurazione Pydantic per compatibilità ORM."""
        from_attributes = True


class UtenteListResponse(BaseModel):
    """
    Response per lista utenti con paginazione.

    Campi paginazione:
    - total: numero totale utenti (con filtri applicati)
    - page: pagina corrente (1-indexed)
    - page_size: elementi per pagina
    - pages: numero totale pagine
    """
    items: List[UtenteResponse]
    total: int
    page: int
    page_size: int
    pages: int


# =============================================================================
# MODELLI RESPONSE - SESSIONI
# =============================================================================

class SessioneResponse(BaseModel):
    """
    Informazioni su una sessione attiva.

    Utile per:
    - Mostrare all'utente le sue sessioni attive
    - Permettere revoca selettiva di sessioni
    - Identificare accessi sospetti
    """
    id_session: int
    created_at: datetime
    expires_at: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    is_current: bool = Field(
        False,
        description="True se è la sessione corrente dell'utente"
    )


class SessioniAttiveResponse(BaseModel):
    """Lista sessioni attive per un utente."""
    sessioni: List[SessioneResponse]
    totale: int


# =============================================================================
# MODELLI LOG ATTIVITÀ
# =============================================================================

class LogAttivitaResponse(BaseModel):
    """
    Singola entry del log attività.

    Campi azione:
    - tipo_operazione: codice azione (LOGIN, USER_CREATE, etc.)
    - action_category: categoria (AUTH, USER_MGMT, DATA, etc.)
    - entita/id_entita: oggetto interessato dall'azione

    Campi esito:
    - success: True se azione completata con successo
    - error_message: messaggio errore se fallita

    Campi audit:
    - ip_address: IP da cui è stata eseguita
    - timestamp: quando è stata eseguita
    - username_snapshot: username al momento dell'azione (preservato)
    """
    id_log: int
    tipo_operazione: str
    action_category: Optional[str]
    entita: Optional[str]
    id_entita: Optional[int]
    descrizione: Optional[str]
    success: bool
    error_message: Optional[str]
    ip_address: Optional[str]
    timestamp: datetime

    # Info utente che ha eseguito l'azione
    id_operatore: int
    username_snapshot: Optional[str]


class LogAttivitaListResponse(BaseModel):
    """Response per lista log con paginazione."""
    items: List[LogAttivitaResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# MODELLO TOKEN PAYLOAD (interno)
# =============================================================================

class TokenPayload(BaseModel):
    """
    Struttura payload JWT.

    Usato internamente per encode/decode token.
    NON esposto nelle API.

    Campi standard JWT:
    - sub: subject (id_operatore)
    - exp: expiration time
    - iat: issued at
    - jti: JWT ID univoco (per revoca)

    Campi custom:
    - username: per display senza query DB
    - ruolo: per controllo permessi senza query DB
    - permissions: lista permessi pre-calcolata
    """
    sub: int = Field(..., description="Subject: id_operatore")
    username: str
    ruolo: RuoloUtente
    permissions: List[str] = Field(
        default_factory=list,
        description="Lista permessi specifici del ruolo"
    )
    exp: datetime = Field(..., description="Expiration time")
    iat: datetime = Field(..., description="Issued at")
    jti: str = Field(..., description="JWT ID univoco per revoca")


# =============================================================================
# RISOLUZIONE FORWARD REFERENCES
# =============================================================================

# In Pydantic v2, model_rebuild() sostituisce update_forward_refs()
LoginResponse.model_rebuild()
