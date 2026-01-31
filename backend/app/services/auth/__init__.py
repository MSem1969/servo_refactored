# =============================================================================
# SERV.O v11.6 - AUTH SERVICES
# =============================================================================
# Servizi autenticazione avanzata: 2FA, OTP, etc.
# =============================================================================

from .otp import (
    OTPService,
    generate_otp,
    request_otp,
    verify_otp,
    OTPVerificationRequired
)

__all__ = [
    'OTPService',
    'generate_otp',
    'request_otp',
    'verify_otp',
    'OTPVerificationRequired'
]
