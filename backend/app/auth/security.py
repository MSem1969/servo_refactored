# =============================================================================
# SERV.O v6.2 - SECURITY
# =============================================================================
# Funzioni di sicurezza: hashing password, generazione/validazione JWT.
#
# COMPONENTI:
# - Password hashing (bcrypt)
# - JWT token creation/validation
# - Token storage hashing (SHA256)
# - Utility functions
#
# CONFIGURAZIONE:
# - JWT_SECRET_KEY: chiave segreta per firma JWT (CAMBIARE IN PRODUZIONE!)
# - JWT_ALGORITHM: algoritmo firma (HS256)
# - JWT_EXPIRATION_HOURS: durata token (8 ore)
# =============================================================================

import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
import jwt
import bcrypt

from .models import TokenPayload, RuoloUtente
from .permissions import get_permessi_ruolo


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

# Chiave segreta per firma JWT
# In produzione: usa variabile d'ambiente JWT_SECRET_KEY
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "SERV.O_SECRET_KEY_CHANGE_IN_PRODUCTION_2024")

# Algoritmo per firma JWT (HS256 = HMAC with SHA-256)
JWT_ALGORITHM = "HS256"

# Durata validità token in ore
JWT_EXPIRATION_HOURS = 8


# =============================================================================
# FUNZIONI PASSWORD
# =============================================================================

def hash_password(password: str) -> str:
    """
    Genera hash bcrypt della password.

    Args:
        password: Password in chiaro da hashare

    Returns:
        Hash bcrypt della password (stringa ~60 caratteri)

    Note:
        - bcrypt include automaticamente un salt random
        - Lo stesso input genera hash diversi (salt diverso)
        - Il salt è incorporato nell'hash per la verifica
        - Formato output: $2b$12$<salt><hash>

    Esempio:
        hash = hash_password("mypassword123")
        # "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.4zLHR3xmZKJKGe"
    """
    # Usa bcrypt direttamente (passlib ha problemi di compatibilità)
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica password in chiaro contro hash salvato.

    Args:
        plain_password: Password in chiaro da verificare
        hashed_password: Hash bcrypt memorizzato nel database

    Returns:
        True se la password corrisponde, False altrimenti

    Note:
        - Usa timing-safe comparison per prevenire timing attacks
        - Gestisce automaticamente hash malformati

    Esempio:
        is_valid = verify_password("mypassword123", stored_hash)
    """
    try:
        # Usa bcrypt direttamente (passlib ha problemi di compatibilità)
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        # In caso di hash malformato o altri errori
        # Ritorna False per sicurezza (non esporre errori)
        return False


# =============================================================================
# FUNZIONI JWT - CREAZIONE
# =============================================================================

def create_access_token(
    user_id: int,
    username: str,
    ruolo: RuoloUtente,
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, str, datetime]:
    """
    Crea un JWT access token.
    
    Args:
        user_id: id_operatore dell'utente
        username: username dell'utente
        ruolo: ruolo dell'utente (RuoloUtente enum)
        expires_delta: durata custom (default: JWT_EXPIRATION_HOURS)
        
    Returns:
        Tupla (token, jti, expires_at):
        - token: JWT encoded string
        - jti: ID univoco del token (per tracciamento/revoca)
        - expires_at: datetime di scadenza
        
    Struttura payload JWT:
        {
            "sub": 123,                    # user_id
            "username": "mario.rossi",
            "ruolo": "supervisore",
            "permissions": ["frontend:dashboard", ...],
            "exp": 1704067200,             # expiration timestamp
            "iat": 1704038400,             # issued at timestamp
            "jti": "abc123..."             # unique token ID
        }
        
    Note:
        - Il jti viene salvato nel DB (hash) per permettere revoca
        - I permessi sono pre-calcolati per evitare query DB ad ogni richiesta
        - exp e iat sono timestamp Unix (secondi dal 1970-01-01)
    """
    # Calcola scadenza
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    # Genera ID univoco per questo token (32 caratteri hex)
    # Usato per:
    # - Identificare univocamente il token
    # - Permettere revoca selettiva
    # - Tracciare sessioni
    jti = secrets.token_hex(16)
    
    # Costruisci payload usando il modello Pydantic
    payload = TokenPayload(
        sub=user_id,
        username=username,
        ruolo=ruolo,
        permissions=get_permessi_ruolo(ruolo),
        exp=expire,
        iat=datetime.utcnow(),
        jti=jti
    )
    
    # Encode JWT
    # Il token è firmato con la chiave segreta
    # Chiunque può decodificare il payload, ma solo chi ha la chiave può verificarlo
    token = jwt.encode(
        payload.dict(),
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )
    
    return token, jti, expire


# =============================================================================
# FUNZIONI JWT - VALIDAZIONE
# =============================================================================

def decode_access_token(token: str) -> Optional[TokenPayload]:
    """
    Decodifica e valida un JWT token.
    
    Args:
        token: JWT string da header Authorization
        
    Returns:
        TokenPayload se token valido, None se invalido/scaduto
        
    Verifiche effettuate:
    1. Firma valida (token non manomesso)
    2. Token non scaduto (exp > now)
    3. Formato payload corretto
    
    Note:
        - NON verifica se token è stato revocato (fatto separatamente)
        - NON verifica se utente è ancora attivo (fatto separatamente)
        
    Errori gestiti:
        - jwt.ExpiredSignatureError: token scaduto
        - jwt.InvalidTokenError: firma invalida o formato errato
    """
    try:
        # Decodifica e verifica firma
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )
        
        # Converti in TokenPayload per validazione struttura
        return TokenPayload(
            sub=payload["sub"],
            username=payload["username"],
            ruolo=RuoloUtente(payload["ruolo"]),
            permissions=payload.get("permissions", []),
            exp=datetime.fromtimestamp(payload["exp"]),
            iat=datetime.fromtimestamp(payload["iat"]),
            jti=payload["jti"]
        )
        
    except jwt.ExpiredSignatureError:
        # Token scaduto (exp < now)
        return None
    except jwt.InvalidTokenError:
        # Firma invalida, formato errato, etc.
        return None
    except (KeyError, ValueError) as e:
        # Payload mancante di campi richiesti o valori invalidi
        return None
    except Exception:
        # Qualsiasi altro errore
        return None


# =============================================================================
# FUNZIONI STORAGE TOKEN
# =============================================================================

def hash_token_for_storage(token: str) -> str:
    """
    Genera hash del token per storage sicuro nel database.
    
    Args:
        token: JWT token completo
        
    Returns:
        SHA256 hash del token (64 caratteri hex)
        
    Perché hashare:
        - Non salviamo mai token in chiaro nel DB
        - Se DB compromesso, token non utilizzabili
        - Usiamo SHA256 (veloce) perché token già random/lungo
        
    Perché non bcrypt:
        - Token già random (non come password scelte da utenti)
        - SHA256 è deterministico (necessario per lookup)
        - Prestazioni migliori per operazioni frequenti
        
    Uso:
        token_hash = hash_token_for_storage(jwt_token)
        # Salva token_hash in USER_SESSIONS
        # Per verificare: hash(token_ricevuto) == token_hash_salvato
    """
    return hashlib.sha256(token.encode()).hexdigest()


# =============================================================================
# UTILITY
# =============================================================================

def get_token_expiration_seconds() -> int:
    """
    Ritorna durata validità token in secondi.
    
    Usato per:
    - Campo expires_in in LoginResponse
    - Calcolo lato frontend per refresh/logout automatico
    
    Returns:
        Secondi di validità (es. 28800 per 8 ore)
    """
    return JWT_EXPIRATION_HOURS * 3600


def generate_temp_password(length: int = 12) -> str:
    """
    Genera password temporanea sicura.
    
    Args:
        length: lunghezza password (default 12)
        
    Returns:
        Password random URL-safe (lettere, numeri, - e _)
        
    Uso:
        - Reset password utente
        - Creazione utente con password temporanea
        
    Nota: la lunghezza effettiva potrebbe essere leggermente diversa
    a causa dell'encoding base64
    """
    return secrets.token_urlsafe(length)


def is_password_strong(password: str) -> Tuple[bool, str]:
    """
    Verifica forza password con criteri configurabili.
    
    Args:
        password: password da verificare
        
    Returns:
        Tupla (is_strong, message):
        - is_strong: True se password soddisfa i criteri
        - message: messaggio di errore se non valida, stringa vuota se OK
        
    Criteri attuali:
    - Minimo 8 caratteri
    
    Criteri futuri (da abilitare se richiesto):
    - Almeno una maiuscola
    - Almeno una minuscola
    - Almeno un numero
    - Almeno un carattere speciale
    """
    if len(password) < 8:
        return False, "Password deve essere almeno 8 caratteri"
    
    # Criteri opzionali (decommentare se richiesti)
    # if not any(c.isupper() for c in password):
    #     return False, "Password deve contenere almeno una maiuscola"
    # if not any(c.islower() for c in password):
    #     return False, "Password deve contenere almeno una minuscola"
    # if not any(c.isdigit() for c in password):
    #     return False, "Password deve contenere almeno un numero"
    # if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
    #     return False, "Password deve contenere almeno un carattere speciale"
    
    return True, ""
