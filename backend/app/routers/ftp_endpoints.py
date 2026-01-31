# =============================================================================
# SERV.O v11.6 - FTP ENDPOINTS MANAGEMENT ROUTER
# =============================================================================
# API per gestione configurazione endpoint FTP con 2FA
# Requisito NIS-2 compliance
# =============================================================================

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..database_pg import get_db, log_operation
from ..auth import get_current_user
from ..services.crypto import encrypt_password, decrypt_password, CryptoError
from ..services.auth import OTPService, request_otp, verify_otp

router = APIRouter(prefix="/ftp-endpoints", tags=["FTP Endpoints"])


# =============================================================================
# MODELLI PYDANTIC
# =============================================================================

class FTPEndpointCreate(BaseModel):
    """Modello per creazione endpoint FTP."""
    nome: str = Field(..., min_length=1, max_length=100)
    descrizione: Optional[str] = None
    vendor_code: str = Field(..., min_length=1, max_length=50)
    deposito: Optional[str] = Field(None, max_length=10)
    ftp_host: str = Field(..., min_length=1, max_length=100)
    ftp_port: int = Field(21, ge=1, le=65535)
    ftp_path: str = Field(..., min_length=1, max_length=255)
    ftp_username: str = Field(..., min_length=1, max_length=100)
    ftp_password: str = Field(..., min_length=1)
    ftp_passive_mode: bool = False
    ftp_timeout: int = Field(30, ge=5, le=300)
    max_tentativi: int = Field(3, ge=1, le=10)
    intervallo_retry_sec: int = Field(60, ge=10, le=600)
    attivo: bool = True
    ordine: int = 0


class FTPEndpointUpdate(BaseModel):
    """Modello per aggiornamento endpoint FTP."""
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descrizione: Optional[str] = None
    ftp_host: Optional[str] = Field(None, min_length=1, max_length=100)
    ftp_port: Optional[int] = Field(None, ge=1, le=65535)
    ftp_path: Optional[str] = Field(None, min_length=1, max_length=255)
    ftp_username: Optional[str] = Field(None, min_length=1, max_length=100)
    ftp_password: Optional[str] = None  # Se vuoto, mantiene la password esistente
    ftp_passive_mode: Optional[bool] = None
    ftp_timeout: Optional[int] = Field(None, ge=5, le=300)
    max_tentativi: Optional[int] = Field(None, ge=1, le=10)
    intervallo_retry_sec: Optional[int] = Field(None, ge=10, le=600)
    attivo: Optional[bool] = None
    ordine: Optional[int] = None


class OTPVerifyRequest(BaseModel):
    """Modello per verifica OTP."""
    codice: str = Field(..., min_length=6, max_length=6)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_client_info(request: Request) -> tuple:
    """Estrae IP e User-Agent dalla request."""
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", None)
    return ip, user_agent


def _check_admin_role(current_user) -> None:
    """Verifica che l'utente sia admin."""
    if current_user.ruolo != 'admin':
        raise HTTPException(403, "Solo gli admin possono gestire gli endpoint FTP")


# =============================================================================
# ENDPOINT LETTURA (NO 2FA REQUIRED)
# =============================================================================

@router.get("/")
async def list_ftp_endpoints(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Lista tutti gli endpoint FTP configurati.
    Le password sono MASCHERATE.
    """
    _check_admin_role(current_user)

    db = get_db()
    try:
        cursor = db.execute("""
            SELECT
                id, nome, descrizione, vendor_code, deposito,
                ftp_host, ftp_port, ftp_path, ftp_username,
                ftp_passive_mode, ftp_timeout, attivo, ordine,
                max_tentativi, intervallo_retry_sec,
                created_at, updated_at
            FROM ftp_endpoints
            ORDER BY ordine, vendor_code, deposito
        """)
        rows = cursor.fetchall()

        endpoints = []
        for row in rows:
            endpoints.append({
                'id': row['id'],
                'nome': row['nome'],
                'descrizione': row['descrizione'],
                'vendor_code': row['vendor_code'],
                'deposito': row['deposito'],
                'ftp_host': row['ftp_host'],
                'ftp_port': row['ftp_port'],
                'ftp_path': row['ftp_path'],
                'ftp_username': row['ftp_username'],
                'ftp_password_masked': '••••••••',  # Password sempre mascherata
                'ftp_passive_mode': row['ftp_passive_mode'],
                'ftp_timeout': row['ftp_timeout'],
                'attivo': row['attivo'],
                'ordine': row['ordine'],
                'max_tentativi': row['max_tentativi'],
                'intervallo_retry_sec': row['intervallo_retry_sec'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
            })

        return {'success': True, 'data': endpoints, 'count': len(endpoints)}

    except Exception as e:
        raise HTTPException(500, f"Errore recupero endpoint: {str(e)}")


@router.get("/vendors")
async def list_available_vendors(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Lista vendor disponibili per configurazione endpoint.
    Include quelli esistenti in ordini + predefiniti.
    """
    _check_admin_role(current_user)

    db = get_db()
    try:
        # Vendor predefiniti
        predefined = ['ANGELINI', 'BAYER', 'CODIFI', 'MENARINI', 'DOC_GENERICI', 'OPELLA', 'VIATRIS', 'CHIESI']

        # Vendor dagli ordini (converti a stringa per sicurezza)
        cursor = db.execute("""
            SELECT DISTINCT id_vendor FROM ordini_testata WHERE id_vendor IS NOT NULL
        """)
        from_orders = [str(row['id_vendor']) for row in cursor.fetchall() if row['id_vendor']]

        # Unisci e ordina (solo stringhe)
        all_vendors = sorted(set(predefined + [v for v in from_orders if isinstance(v, str)]))

        # Depositi disponibili (da ftp_endpoints o default)
        try:
            cursor = db.execute("""
                SELECT DISTINCT deposito FROM ftp_endpoints WHERE deposito IS NOT NULL
            """)
            depositi = [row['deposito'] for row in cursor.fetchall()]
        except Exception:
            depositi = []
        if not depositi:
            depositi = ['CT', 'CL']  # Default

        return {
            'success': True,
            'data': {
                'vendors': all_vendors,
                'depositi': depositi
            }
        }

    except Exception as e:
        raise HTTPException(500, f"Errore recupero vendor: {str(e)}")


@router.get("/log")
async def get_ftp_log(
    limit: int = Query(100, ge=1, le=1000),
    endpoint_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Recupera log operazioni FTP.
    """
    _check_admin_role(current_user)

    db = get_db()
    try:
        where_clause = "WHERE 1=1"
        params = []

        if endpoint_id:
            where_clause += " AND id_endpoint = %s"
            params.append(endpoint_id)

        query = f"""
            SELECT
                l.id, l.id_esportazione, l.azione, l.esito,
                l.file_name, l.ftp_path, l.messaggio,
                l.created_at, l.id_endpoint,
                e.nome as endpoint_nome
            FROM ftp_log l
            LEFT JOIN ftp_endpoints e ON l.id_endpoint = e.id
            {where_clause}
            ORDER BY l.created_at DESC
            LIMIT %s
        """
        params.append(limit)

        cursor = db.execute(query, tuple(params))
        rows = cursor.fetchall()

        logs = []
        for row in rows:
            logs.append({
                'id': row['id'],
                'id_esportazione': row['id_esportazione'],
                'operazione': row['azione'],
                'esito': row['esito'],
                'host': row['ftp_path'],
                'file_remoto': row['file_name'],
                'messaggio': row['messaggio'],
                'dettagli': None,
                'timestamp': row['created_at'].isoformat() if row['created_at'] else None,
                'id_endpoint': row['id_endpoint'],
                'endpoint_nome': row['endpoint_nome'],
            })

        return {'success': True, 'data': logs, 'count': len(logs)}

    except Exception as e:
        raise HTTPException(500, f"Errore recupero log: {str(e)}")


# =============================================================================
# CREAZIONE ENDPOINT (NO 2FA - solo admin)
# =============================================================================

@router.post("/")
async def create_ftp_endpoint(
    data: FTPEndpointCreate,
    request: Request,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Crea nuovo endpoint FTP.
    NON richiede 2FA (solo per modifica/visualizzazione password).
    """
    _check_admin_role(current_user)

    db = get_db()
    ip, user_agent = _get_client_info(request)

    try:
        # Verifica univocita vendor+deposito
        cursor = db.execute("""
            SELECT id FROM ftp_endpoints
            WHERE vendor_code = %s AND (deposito = %s OR (deposito IS NULL AND %s IS NULL))
        """, (data.vendor_code, data.deposito, data.deposito))

        if cursor.fetchone():
            raise HTTPException(
                409,
                f"Esiste gia un endpoint per {data.vendor_code}/{data.deposito or 'TUTTI'}"
            )

        # Cripta password
        encrypted_password = encrypt_password(data.ftp_password)

        # Inserisci
        cursor = db.execute("""
            INSERT INTO ftp_endpoints (
                nome, descrizione, vendor_code, deposito,
                ftp_host, ftp_port, ftp_path, ftp_username, ftp_password_encrypted,
                ftp_passive_mode, ftp_timeout, attivo, ordine,
                max_tentativi, intervallo_retry_sec,
                created_by, updated_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data.nome, data.descrizione, data.vendor_code, data.deposito,
            data.ftp_host, data.ftp_port, data.ftp_path, data.ftp_username, encrypted_password,
            data.ftp_passive_mode, data.ftp_timeout, data.attivo, data.ordine,
            data.max_tentativi, data.intervallo_retry_sec,
            current_user.id_operatore, current_user.id_operatore
        ))

        new_id = cursor.fetchone()['id']
        db.commit()

        log_operation(
            'FTP_ENDPOINT_CREATE', 'ftp_endpoints', new_id,
            f'Creato endpoint FTP: {data.nome} ({data.vendor_code}/{data.deposito or "TUTTI"})',
            operatore=current_user.username
        )

        return {
            'success': True,
            'message': f'Endpoint FTP creato: {data.nome}',
            'id': new_id
        }

    except HTTPException:
        raise
    except CryptoError as e:
        raise HTTPException(500, f"Errore crittografia: {str(e)}")
    except Exception as e:
        db._conn.rollback()
        raise HTTPException(500, f"Errore creazione endpoint: {str(e)}")


# =============================================================================
# 2FA - RICHIESTA OTP
# =============================================================================

@router.post("/{endpoint_id}/request-otp")
async def request_endpoint_otp(
    endpoint_id: int,
    operation: str = Query(..., regex="^(FTP_VIEW_PASSWORD|FTP_EDIT)$"),
    request: Request = None,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Richiede OTP per operazione sensibile su endpoint FTP.

    Operations:
    - FTP_VIEW_PASSWORD: Visualizzare password in chiaro
    - FTP_EDIT: Modificare configurazione endpoint
    """
    _check_admin_role(current_user)

    db = get_db()
    ip, user_agent = _get_client_info(request)

    # Verifica esistenza endpoint
    cursor = db.execute("SELECT id, nome FROM ftp_endpoints WHERE id = %s", (endpoint_id,))
    endpoint = cursor.fetchone()
    if not endpoint:
        raise HTTPException(404, "Endpoint non trovato")

    # Richiedi OTP
    result = request_otp(
        id_operatore=current_user.id_operatore,
        tipo_operazione=operation,
        riferimento_id=endpoint_id,
        ip_address=ip,
        user_agent=user_agent
    )

    if not result['success']:
        raise HTTPException(400, result.get('error', 'Errore richiesta OTP'))

    return result


# =============================================================================
# OPERAZIONI CON 2FA
# =============================================================================

@router.post("/{endpoint_id}/view-password")
async def view_endpoint_password(
    endpoint_id: int,
    otp_data: OTPVerifyRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Visualizza password FTP in chiaro.
    RICHIEDE verifica 2FA.
    """
    _check_admin_role(current_user)

    db = get_db()
    ip, user_agent = _get_client_info(request)

    # Verifica OTP
    otp_result = verify_otp(
        id_operatore=current_user.id_operatore,
        codice=otp_data.codice,
        tipo_operazione='FTP_VIEW_PASSWORD',
        riferimento_id=endpoint_id,
        ip_address=ip,
        user_agent=user_agent
    )

    if not otp_result['success']:
        raise HTTPException(401, otp_result.get('error', 'Verifica OTP fallita'))

    # Recupera e decripta password
    try:
        cursor = db.execute("""
            SELECT nome, ftp_password_encrypted FROM ftp_endpoints WHERE id = %s
        """, (endpoint_id,))
        endpoint = cursor.fetchone()

        if not endpoint:
            raise HTTPException(404, "Endpoint non trovato")

        password = decrypt_password(endpoint['ftp_password_encrypted'])

        log_operation(
            'FTP_PASSWORD_VIEW', 'ftp_endpoints', endpoint_id,
            f'Password visualizzata per: {endpoint["nome"]}',
            operatore=current_user.username
        )

        return {
            'success': True,
            'password': password,
            'message': 'Password visualizzata con successo (valida per questa sessione)'
        }

    except CryptoError as e:
        raise HTTPException(500, f"Errore decriptazione: {str(e)}")


@router.put("/{endpoint_id}")
async def update_ftp_endpoint(
    endpoint_id: int,
    data: FTPEndpointUpdate,
    otp_code: str = Query(..., min_length=6, max_length=6),
    request: Request = None,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Aggiorna endpoint FTP esistente.
    RICHIEDE verifica 2FA.
    """
    _check_admin_role(current_user)

    db = get_db()
    ip, user_agent = _get_client_info(request)

    # Verifica OTP
    otp_result = verify_otp(
        id_operatore=current_user.id_operatore,
        codice=otp_code,
        tipo_operazione='FTP_EDIT',
        riferimento_id=endpoint_id,
        ip_address=ip,
        user_agent=user_agent
    )

    if not otp_result['success']:
        raise HTTPException(401, otp_result.get('error', 'Verifica OTP fallita'))

    try:
        # Verifica esistenza
        cursor = db.execute("SELECT id, nome FROM ftp_endpoints WHERE id = %s", (endpoint_id,))
        endpoint = cursor.fetchone()
        if not endpoint:
            raise HTTPException(404, "Endpoint non trovato")

        # Costruisci query dinamica
        updates = []
        params = []

        if data.nome is not None:
            updates.append("nome = %s")
            params.append(data.nome)

        if data.descrizione is not None:
            updates.append("descrizione = %s")
            params.append(data.descrizione)

        if data.ftp_host is not None:
            updates.append("ftp_host = %s")
            params.append(data.ftp_host)

        if data.ftp_port is not None:
            updates.append("ftp_port = %s")
            params.append(data.ftp_port)

        if data.ftp_path is not None:
            updates.append("ftp_path = %s")
            params.append(data.ftp_path)

        if data.ftp_username is not None:
            updates.append("ftp_username = %s")
            params.append(data.ftp_username)

        if data.ftp_password:  # Solo se fornita nuova password
            encrypted = encrypt_password(data.ftp_password)
            updates.append("ftp_password_encrypted = %s")
            params.append(encrypted)

        if data.ftp_passive_mode is not None:
            updates.append("ftp_passive_mode = %s")
            params.append(data.ftp_passive_mode)

        if data.ftp_timeout is not None:
            updates.append("ftp_timeout = %s")
            params.append(data.ftp_timeout)

        if data.max_tentativi is not None:
            updates.append("max_tentativi = %s")
            params.append(data.max_tentativi)

        if data.intervallo_retry_sec is not None:
            updates.append("intervallo_retry_sec = %s")
            params.append(data.intervallo_retry_sec)

        if data.attivo is not None:
            updates.append("attivo = %s")
            params.append(data.attivo)

        if data.ordine is not None:
            updates.append("ordine = %s")
            params.append(data.ordine)

        if not updates:
            return {'success': True, 'message': 'Nessuna modifica'}

        updates.append("updated_at = NOW()")
        updates.append("updated_by = %s")
        params.append(current_user.id_operatore)

        params.append(endpoint_id)

        db.execute(f"""
            UPDATE ftp_endpoints
            SET {', '.join(updates)}
            WHERE id = %s
        """, tuple(params))

        db.commit()

        log_operation(
            'FTP_ENDPOINT_UPDATE', 'ftp_endpoints', endpoint_id,
            f'Aggiornato endpoint FTP: {endpoint["nome"]}',
            operatore=current_user.username
        )

        return {
            'success': True,
            'message': f'Endpoint aggiornato: {data.nome or endpoint["nome"]}'
        }

    except HTTPException:
        raise
    except CryptoError as e:
        raise HTTPException(500, f"Errore crittografia: {str(e)}")
    except Exception as e:
        db._conn.rollback()
        raise HTTPException(500, f"Errore aggiornamento: {str(e)}")


@router.delete("/{endpoint_id}")
async def delete_ftp_endpoint(
    endpoint_id: int,
    otp_code: str = Query(..., min_length=6, max_length=6),
    request: Request = None,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Elimina endpoint FTP.
    RICHIEDE verifica 2FA.
    """
    _check_admin_role(current_user)

    db = get_db()
    ip, user_agent = _get_client_info(request)

    # Verifica OTP
    otp_result = verify_otp(
        id_operatore=current_user.id_operatore,
        codice=otp_code,
        tipo_operazione='FTP_EDIT',
        riferimento_id=endpoint_id,
        ip_address=ip,
        user_agent=user_agent
    )

    if not otp_result['success']:
        raise HTTPException(401, otp_result.get('error', 'Verifica OTP fallita'))

    try:
        # Verifica esistenza
        cursor = db.execute("SELECT id, nome, vendor_code FROM ftp_endpoints WHERE id = %s", (endpoint_id,))
        endpoint = cursor.fetchone()
        if not endpoint:
            raise HTTPException(404, "Endpoint non trovato")

        # Elimina
        db.execute("DELETE FROM ftp_endpoints WHERE id = %s", (endpoint_id,))
        db.commit()

        log_operation(
            'FTP_ENDPOINT_DELETE', 'ftp_endpoints', endpoint_id,
            f'Eliminato endpoint FTP: {endpoint["nome"]} ({endpoint["vendor_code"]})',
            operatore=current_user.username
        )

        return {
            'success': True,
            'message': f'Endpoint eliminato: {endpoint["nome"]}'
        }

    except HTTPException:
        raise
    except Exception as e:
        db._conn.rollback()
        raise HTTPException(500, f"Errore eliminazione: {str(e)}")


# =============================================================================
# TOGGLE ATTIVO (NO 2FA - operazione rapida)
# =============================================================================

@router.patch("/{endpoint_id}/toggle")
async def toggle_endpoint_active(
    endpoint_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Attiva/disattiva endpoint FTP.
    NON richiede 2FA (operazione rapida e reversibile).
    """
    _check_admin_role(current_user)

    db = get_db()

    try:
        cursor = db.execute("""
            SELECT id, nome, attivo FROM ftp_endpoints WHERE id = %s
        """, (endpoint_id,))
        endpoint = cursor.fetchone()

        if not endpoint:
            raise HTTPException(404, "Endpoint non trovato")

        new_status = not endpoint['attivo']

        db.execute("""
            UPDATE ftp_endpoints
            SET attivo = %s, updated_at = NOW(), updated_by = %s
            WHERE id = %s
        """, (new_status, current_user.id_operatore, endpoint_id))

        db.commit()

        action = 'attivato' if new_status else 'disattivato'
        log_operation(
            'FTP_ENDPOINT_TOGGLE', 'ftp_endpoints', endpoint_id,
            f'Endpoint {action}: {endpoint["nome"]}',
            operatore=current_user.username
        )

        return {
            'success': True,
            'message': f'Endpoint {action}: {endpoint["nome"]}',
            'attivo': new_status
        }

    except HTTPException:
        raise
    except Exception as e:
        db._conn.rollback()
        raise HTTPException(500, f"Errore toggle: {str(e)}")


# =============================================================================
# TEST CONNESSIONE
# =============================================================================

@router.post("/{endpoint_id}/test")
async def test_ftp_connection(
    endpoint_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Testa la connessione FTP di un endpoint.
    Prova a connettersi, listare la directory e disconnettersi.
    """
    _check_admin_role(current_user)

    db = get_db()

    try:
        cursor = db.execute("""
            SELECT nome, ftp_host, ftp_port, ftp_path, ftp_username,
                   ftp_password_encrypted, ftp_passive_mode, ftp_timeout
            FROM ftp_endpoints WHERE id = %s
        """, (endpoint_id,))
        endpoint = cursor.fetchone()

        if not endpoint:
            raise HTTPException(404, "Endpoint non trovato")

        # Decripta password
        password = decrypt_password(endpoint['ftp_password_encrypted'])

        # Test connessione
        import ftplib
        from datetime import datetime

        start_time = datetime.now()
        ftp = None
        steps = []

        try:
            # 1. Connessione
            ftp = ftplib.FTP(timeout=endpoint['ftp_timeout'])
            ftp.connect(endpoint['ftp_host'], endpoint['ftp_port'])
            steps.append({'step': 'connect', 'success': True, 'message': f'Connesso a {endpoint["ftp_host"]}:{endpoint["ftp_port"]}'})

            # 2. Login
            ftp.login(endpoint['ftp_username'], password)
            steps.append({'step': 'login', 'success': True, 'message': f'Login con utente {endpoint["ftp_username"]}'})

            # 3. Passive mode
            if endpoint['ftp_passive_mode']:
                ftp.set_pasv(True)
                steps.append({'step': 'passive', 'success': True, 'message': 'Modalita passiva attivata'})

            # 4. Change directory
            ftp.cwd(endpoint['ftp_path'])
            steps.append({'step': 'cwd', 'success': True, 'message': f'Directory: {endpoint["ftp_path"]}'})

            # 5. List directory
            files = ftp.nlst()
            steps.append({'step': 'list', 'success': True, 'message': f'{len(files)} file/cartelle trovate'})

            # 6. Disconnect
            ftp.quit()
            steps.append({'step': 'disconnect', 'success': True, 'message': 'Disconnesso correttamente'})

            elapsed = (datetime.now() - start_time).total_seconds()

            log_operation(
                'FTP_TEST_SUCCESS', 'ftp_endpoints', endpoint_id,
                f'Test connessione OK: {endpoint["nome"]} ({elapsed:.2f}s)',
                operatore=current_user.username
            )

            return {
                'success': True,
                'message': f'Connessione riuscita in {elapsed:.2f}s',
                'steps': steps,
                'elapsed_seconds': elapsed
            }

        except ftplib.error_perm as e:
            error_msg = str(e)
            steps.append({'step': 'error', 'success': False, 'message': f'Errore permessi: {error_msg}'})
            raise HTTPException(400, f'Errore FTP: {error_msg}')

        except ftplib.error_temp as e:
            error_msg = str(e)
            steps.append({'step': 'error', 'success': False, 'message': f'Errore temporaneo: {error_msg}'})
            raise HTTPException(503, f'Errore FTP temporaneo: {error_msg}')

        except Exception as e:
            error_msg = str(e)
            steps.append({'step': 'error', 'success': False, 'message': error_msg})
            raise HTTPException(500, f'Errore connessione: {error_msg}')

        finally:
            if ftp:
                try:
                    ftp.close()
                except:
                    pass

    except HTTPException:
        raise
    except CryptoError as e:
        raise HTTPException(500, f"Errore decriptazione password: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Errore test connessione: {str(e)}")


# =============================================================================
# STATISTICHE
# =============================================================================

@router.get("/stats")
async def get_ftp_stats(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Statistiche FTP per dashboard.
    """
    _check_admin_role(current_user)

    db = get_db()

    try:
        # Conteggi endpoint
        cursor = db.execute("""
            SELECT
                COUNT(*) as totale,
                COUNT(*) FILTER (WHERE attivo = TRUE) as attivi,
                COUNT(*) FILTER (WHERE attivo = FALSE) as disattivi
            FROM ftp_endpoints
        """)
        row = cursor.fetchone()
        endpoints = {'totale': row['totale'], 'attivi': row['attivi'], 'disattivi': row['disattivi']}

        # Log ultimi 24h
        cursor = db.execute("""
            SELECT
                COUNT(*) as totale,
                COUNT(*) FILTER (WHERE esito = 'SUCCESS') as successo,
                COUNT(*) FILTER (WHERE esito = 'FAILED') as falliti
            FROM ftp_log
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """)
        row = cursor.fetchone()
        log_24h = {'totale': row['totale'], 'successo': row['successo'], 'falliti': row['falliti']}

        # Ultimo invio per endpoint
        cursor = db.execute("""
            SELECT
                e.id, e.nome, e.vendor_code,
                MAX(l.created_at) as ultimo_invio,
                (SELECT esito FROM ftp_log WHERE id_endpoint = e.id ORDER BY created_at DESC LIMIT 1) as ultimo_esito
            FROM ftp_endpoints e
            LEFT JOIN ftp_log l ON l.id_endpoint = e.id
            GROUP BY e.id, e.nome, e.vendor_code
            ORDER BY e.ordine, e.vendor_code
        """)
        per_endpoint = []
        for row in cursor.fetchall():
            per_endpoint.append({
                'id': row['id'],
                'nome': row['nome'],
                'vendor_code': row['vendor_code'],
                'ultimo_invio': row['ultimo_invio'].isoformat() if row['ultimo_invio'] else None,
                'ultimo_esito': row['ultimo_esito']
            })

        return {
            'success': True,
            'data': {
                'endpoints': endpoints,
                'log_24h': log_24h,
                'per_endpoint': per_endpoint
            }
        }

    except Exception as e:
        raise HTTPException(500, f"Errore statistiche: {str(e)}")
