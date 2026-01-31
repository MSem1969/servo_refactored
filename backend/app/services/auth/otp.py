# =============================================================================
# SERV.O v11.6 - OTP SERVICE (2FA)
# =============================================================================
# Sistema autenticazione a due fattori via Email OTP
# Requisito NIS-2 compliance
# =============================================================================

import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from ...database_pg import get_db, log_operation


# Costanti
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 3


class OTPVerificationRequired(Exception):
    """Eccezione per operazioni che richiedono verifica 2FA."""

    def __init__(self, operation: str, message: str = None):
        self.operation = operation
        self.message = message or f"Operazione '{operation}' richiede verifica 2FA"
        super().__init__(self.message)


class OTPService:
    """
    Servizio gestione OTP per autenticazione a due fattori.

    Flusso:
    1. request_otp() - Genera OTP e invia email
    2. verify_otp() - Verifica codice inserito
    3. Operazione autorizzata se verifica OK
    """

    def __init__(self):
        self.db = get_db()

    def generate_code(self) -> str:
        """Genera codice OTP a 6 cifre."""
        return ''.join(secrets.choice(string.digits) for _ in range(OTP_LENGTH))

    def request_otp(
        self,
        id_operatore: int,
        tipo_operazione: str,
        riferimento_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Genera OTP e invia via email.

        Args:
            id_operatore: ID operatore richiedente
            tipo_operazione: Tipo operazione (FTP_VIEW_PASSWORD, FTP_EDIT, etc.)
            riferimento_id: ID risorsa correlata (opzionale)
            ip_address: IP richiedente per audit
            user_agent: User agent per audit

        Returns:
            {success, message, email_masked, scadenza}
        """
        # Recupera operatore e email
        operatore = self.db.execute("""
            SELECT id_operatore, username, email, email_2fa, ruolo
            FROM operatori WHERE id_operatore = %s AND attivo = TRUE
        """, (id_operatore,)).fetchone()

        if not operatore:
            return {'success': False, 'error': 'Operatore non trovato o non attivo'}

        # Usa email_2fa se configurata, altrimenti email principale
        email = operatore['email_2fa'] or operatore['email']
        if not email:
            return {'success': False, 'error': 'Nessuna email configurata per 2FA'}

        # Invalida OTP precedenti non utilizzati per stessa operazione
        self.db.execute("""
            UPDATE otp_tokens
            SET utilizzato = TRUE
            WHERE id_operatore = %s
              AND tipo_operazione = %s
              AND utilizzato = FALSE
        """, (id_operatore, tipo_operazione))

        # Genera nuovo OTP
        codice = self.generate_code()
        scadenza = datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)

        # Salva token
        self.db.execute("""
            INSERT INTO otp_tokens
            (id_operatore, codice, tipo_operazione, riferimento_id, scadenza, ip_richiesta, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (id_operatore, codice, tipo_operazione, riferimento_id, scadenza, ip_address, user_agent))

        self.db.commit()

        # Invia email
        email_sent = self._send_otp_email(email, codice, tipo_operazione, operatore['username'])

        if not email_sent:
            return {'success': False, 'error': 'Errore invio email OTP'}

        # Maschera email per risposta
        email_masked = self._mask_email(email)

        # Log audit
        self._log_audit(id_operatore, tipo_operazione, 'REQUESTED', ip_address, user_agent,
                       f'OTP inviato a {email_masked}')

        return {
            'success': True,
            'message': f'Codice OTP inviato a {email_masked}',
            'email_masked': email_masked,
            'scadenza': scadenza.isoformat(),
            'scadenza_secondi': OTP_EXPIRY_MINUTES * 60
        }

    def verify_otp(
        self,
        id_operatore: int,
        codice: str,
        tipo_operazione: str,
        riferimento_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verifica codice OTP.

        Args:
            id_operatore: ID operatore
            codice: Codice OTP inserito
            tipo_operazione: Tipo operazione da autorizzare
            riferimento_id: ID risorsa correlata (opzionale)
            ip_address: IP per audit
            user_agent: User agent per audit

        Returns:
            {success, message, token_id}
        """
        # Cerca token valido
        token = self.db.execute("""
            SELECT id, codice, scadenza, riferimento_id
            FROM otp_tokens
            WHERE id_operatore = %s
              AND tipo_operazione = %s
              AND utilizzato = FALSE
              AND scadenza > NOW()
            ORDER BY created_at DESC
            LIMIT 1
        """, (id_operatore, tipo_operazione)).fetchone()

        if not token:
            self._log_audit(id_operatore, tipo_operazione, 'EXPIRED', ip_address, user_agent,
                           'Nessun token valido trovato')
            return {'success': False, 'error': 'Codice OTP scaduto o non valido. Richiedine uno nuovo.'}

        # Verifica riferimento se specificato
        if riferimento_id and token['riferimento_id'] and token['riferimento_id'] != riferimento_id:
            self._log_audit(id_operatore, tipo_operazione, 'INVALID', ip_address, user_agent,
                           f'Riferimento non corrispondente: atteso {token["riferimento_id"]}, ricevuto {riferimento_id}')
            return {'success': False, 'error': 'Codice OTP non valido per questa risorsa'}

        # Verifica codice
        if token['codice'] != codice:
            self._log_audit(id_operatore, tipo_operazione, 'FAILED', ip_address, user_agent,
                           'Codice errato')
            return {'success': False, 'error': 'Codice OTP errato'}

        # Marca come utilizzato
        self.db.execute("""
            UPDATE otp_tokens
            SET utilizzato = TRUE, verified_at = NOW()
            WHERE id = %s
        """, (token['id'],))

        self.db.commit()

        # Log audit successo
        self._log_audit(id_operatore, tipo_operazione, 'SUCCESS', ip_address, user_agent,
                       'Verifica OTP completata')

        log_operation('OTP_VERIFIED', 'otp_tokens', token['id'],
                     f'2FA verificato per {tipo_operazione}',
                     operatore=str(id_operatore))

        return {
            'success': True,
            'message': 'Verifica 2FA completata',
            'token_id': token['id']
        }

    def _send_otp_email(
        self,
        email: str,
        codice: str,
        tipo_operazione: str,
        username: str
    ) -> bool:
        """Invia email con codice OTP."""
        try:
            from ..email.sender import EmailSender

            # Mappa tipo operazione a descrizione user-friendly
            operazione_desc = {
                'FTP_VIEW_PASSWORD': 'visualizzare la password FTP',
                'FTP_EDIT': 'modificare la configurazione FTP',
                'ADMIN_ACTION': 'eseguire un\'azione amministrativa'
            }.get(tipo_operazione, tipo_operazione)

            subject = f"[SERV.O] Codice di verifica: {codice}"

            body_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #3B82F6, #1E40AF); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">SERV.O</h1>
                    <p style="color: #BFDBFE; margin: 5px 0 0 0;">Verifica Identita</p>
                </div>

                <div style="padding: 30px; background: #F8FAFC;">
                    <p style="color: #334155;">Ciao <strong>{username}</strong>,</p>

                    <p style="color: #334155;">
                        Hai richiesto di <strong>{operazione_desc}</strong>.
                        Usa il codice seguente per completare la verifica:
                    </p>

                    <div style="background: #1E293B; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                        <span style="font-family: monospace; font-size: 32px; letter-spacing: 8px; color: #10B981; font-weight: bold;">
                            {codice}
                        </span>
                    </div>

                    <p style="color: #64748B; font-size: 14px;">
                        Il codice scade tra <strong>{OTP_EXPIRY_MINUTES} minuti</strong>.
                    </p>

                    <p style="color: #64748B; font-size: 14px;">
                        Se non hai richiesto tu questo codice, ignora questa email.
                        Nessuna azione verra eseguita senza la verifica.
                    </p>
                </div>

                <div style="background: #E2E8F0; padding: 15px; text-align: center;">
                    <p style="color: #64748B; font-size: 12px; margin: 0;">
                        Questo e un messaggio automatico di sicurezza.
                        Non rispondere a questa email.
                    </p>
                </div>
            </div>
            """

            sender = EmailSender(self.db)
            result = sender.send(
                to=email,
                subject=subject,
                body_html=body_html,
                email_type='otp_verification'
            )

            return result.get('success', False)

        except Exception as e:
            print(f"Errore invio email OTP: {e}")
            return False

    def _mask_email(self, email: str) -> str:
        """Maschera email per privacy (es: m***@email.it)."""
        if '@' not in email:
            return '***'

        local, domain = email.split('@', 1)
        if len(local) <= 2:
            masked_local = local[0] + '*'
        else:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]

        return f"{masked_local}@{domain}"

    def _log_audit(
        self,
        id_operatore: int,
        tipo_operazione: str,
        esito: str,
        ip_address: Optional[str],
        user_agent: Optional[str],
        dettagli: str
    ):
        """Registra evento nel log audit 2FA."""
        try:
            self.db.execute("""
                INSERT INTO otp_audit_log
                (id_operatore, tipo_operazione, esito, ip_address, user_agent, dettagli)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (id_operatore, tipo_operazione, esito, ip_address, user_agent, dettagli))
            self.db.commit()
        except Exception as e:
            print(f"Errore log audit OTP: {e}")

    def cleanup_expired(self) -> int:
        """Pulisce token OTP scaduti. Ritorna numero eliminati."""
        result = self.db.execute("""
            DELETE FROM otp_tokens
            WHERE scadenza < NOW() - INTERVAL '1 hour'
               OR (utilizzato = TRUE AND created_at < NOW() - INTERVAL '1 day')
        """)
        self.db.commit()
        return result.rowcount


# =============================================================================
# FUNZIONI HELPER
# =============================================================================

def generate_otp() -> str:
    """Genera codice OTP a 6 cifre."""
    return OTPService().generate_code()


def request_otp(
    id_operatore: int,
    tipo_operazione: str,
    riferimento_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Dict[str, Any]:
    """Richiede nuovo OTP via email."""
    return OTPService().request_otp(
        id_operatore, tipo_operazione, riferimento_id, ip_address, user_agent
    )


def verify_otp(
    id_operatore: int,
    codice: str,
    tipo_operazione: str,
    riferimento_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Dict[str, Any]:
    """Verifica codice OTP."""
    return OTPService().verify_otp(
        id_operatore, codice, tipo_operazione, riferimento_id, ip_address, user_agent
    )
