"""
PDF Uploader - Caricamento PDF al backend locale
Gestisce upload via API, retry, e verifica disponibilità backend
"""

import time
import logging
from pathlib import Path
from typing import Optional, Dict
import requests

from config import Config

logger = logging.getLogger(__name__)


class PDFUploader:
    """Gestisce l'upload di PDF al backend locale"""

    def __init__(self):
        """Inizializza l'uploader"""
        self.backend_url = Config.BACKEND_URL
        self.upload_endpoint = f"{self.backend_url}{Config.UPLOAD_ENDPOINT}"
        self.timeout = Config.UPLOAD_TIMEOUT
        self.max_retries = Config.MAX_RETRIES
        self.retry_delay = Config.RETRY_DELAY_SECONDS

    def verifica_backend(self) -> bool:
        """
        Verifica che il backend sia raggiungibile

        Returns:
            True se backend disponibile, False altrimenti
        """
        try:
            # Prova a raggiungere la root API
            response = requests.get(
                f"{self.backend_url}/",
                timeout=5
            )

            if response.status_code == 200:
                logger.info(f"✅ Backend disponibile: {self.backend_url}")
                return True
            else:
                logger.warning(
                    f"Backend risponde ma con status {response.status_code}")
                return False

        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Backend non raggiungibile: {self.backend_url}")
            logger.error(
                "Assicurati che il backend sia avviato: python run.py")
            return False

        except requests.exceptions.Timeout:
            logger.error("❌ Timeout connessione backend")
            return False

        except Exception as e:
            logger.error(f"❌ Errore verifica backend: {e}")
            return False

    def upload_pdf(
        self,
        pdf_path: Path,
        vendor: str = None
    ) -> Optional[Dict]:
        """
        Carica PDF al backend con retry automatico

        Args:
            pdf_path: Path al file PDF
            vendor: Codice vendor (opzionale, auto-detect se None)

        Returns:
            Dizionario con risposta backend, o None se errore
            {
                'success': True,
                'data': {
                    'id_acquisizione': 123,
                    'filename': 'file.pdf',
                    'vendor': 'ANGELINI',
                    'stato': 'ESTRATTO'
                }
            }
        """
        if not pdf_path.exists():
            logger.error(f"File PDF non trovato: {pdf_path}")
            return None

        # Tenta upload con retry
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"Upload tentativo {attempt}/{self.max_retries}: {pdf_path.name}")

                # Prepara file per upload
                with open(pdf_path, 'rb') as f:
                    files = {
                        'file': (pdf_path.name, f, 'application/pdf')
                    }

                    # Prepara dati opzionali
                    data = {}
                    if vendor:
                        data['vendor'] = vendor

                    # Esegui POST
                    response = requests.post(
                        self.upload_endpoint,
                        files=files,
                        data=data if data else None,
                        timeout=self.timeout
                    )

                # Verifica risposta
                if response.status_code == 200:
                    result = response.json()

                    if result.get('success'):
                        logger.info(f"✅ Upload riuscito: {pdf_path.name}")
                        logger.info(
                            f"   ID acquisizione: {result['data'].get('id_acquisizione')}")
                        logger.info(
                            f"   Vendor: {result['data'].get('vendor')}")
                        logger.info(f"   Stato: {result['data'].get('stato')}")
                        return result
                    else:
                        logger.error(
                            f"❌ Backend ha rifiutato il file: {result.get('error', 'Unknown')}")
                        return None

                elif response.status_code == 413:
                    logger.error(f"❌ File troppo grande: {pdf_path.name}")
                    return None  # Non ritentare per file troppo grandi

                elif response.status_code == 422:
                    logger.error(f"❌ Errore validazione: {response.text}")
                    return None  # Non ritentare per errori di validazione

                else:
                    logger.warning(
                        f"⚠️  Status code {response.status_code}: {response.text}")

                    # Ritenta solo per errori 5xx
                    if response.status_code >= 500 and attempt < self.max_retries:
                        logger.info(
                            f"Ritento tra {self.retry_delay} secondi...")
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        return None

            except requests.exceptions.ConnectionError as e:
                logger.error(
                    f"❌ Errore connessione backend (tentativo {attempt}): {e}")

                if attempt < self.max_retries:
                    logger.info(f"Ritento tra {self.retry_delay} secondi...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(
                        "❌ Tutti i tentativi falliti (ConnectionError)")
                    return None

            except requests.exceptions.Timeout as e:
                logger.error(f"❌ Timeout upload (tentativo {attempt}): {e}")

                if attempt < self.max_retries:
                    logger.info(f"Ritento tra {self.retry_delay} secondi...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error("❌ Tutti i tentativi falliti (Timeout)")
                    return None

            except Exception as e:
                logger.error(
                    f"❌ Errore inatteso upload (tentativo {attempt}): {e}")

                if attempt < self.max_retries:
                    logger.info(f"Ritento tra {self.retry_delay} secondi...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(
                        "❌ Tutti i tentativi falliti (Errore generico)")
                    return None

        return None

    def get_statistiche_backend(self) -> Optional[Dict]:
        """
        Recupera statistiche dal backend

        Returns:
            Dizionario con statistiche o None se errore
        """
        try:
            response = requests.get(
                f"{self.backend_url}/api/v1/dashboard/stats",
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    f"Impossibile recuperare statistiche: {response.status_code}")
                return None

        except Exception as e:
            logger.debug(f"Errore recupero statistiche: {e}")
            return None

    def verifica_duplicato(self, hash_file: str) -> bool:
        """
        Verifica se un file con questo hash è già stato caricato

        Args:
            hash_file: SHA256 hash del file

        Returns:
            True se duplicato, False altrimenti
        """
        try:
            # Questa funzionalità richiede un endpoint specifico nel backend
            # Per ora facciamo solo un check locale tramite email_db
            # Il backend farà il suo check durante l'upload
            return False

        except Exception as e:
            logger.debug(f"Errore verifica duplicato: {e}")
            return False


# =============================================================
