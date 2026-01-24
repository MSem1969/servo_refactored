#!/usr/bin/env python3
"""
Wizard di configurazione Gmail Monitor
Crea/aggiorna il file .env in modo guidato
"""

from pathlib import Path


def setup_wizard():
    """Wizard interattivo per configurazione"""

    print("=" * 60)
    print("🧙 WIZARD CONFIGURAZIONE GMAIL MONITOR")
    print("=" * 60)
    print()

    env_path = Path(__file__).parent / '.env'

    # 1. EMAIL
    print("📧 STEP 1: Credenziali Gmail")
    print("-" * 60)
    email = input("Inserisci email Gmail: ").strip()

    print()
    print("ℹ️  Per ottenere la password app:")
    print("   1. Vai su https://myaccount.google.com/security")
    print("   2. Abilita 'Verifica in due passaggi'")
    print("   3. Cerca 'Password per le app'")
    print("   4. Genera password per 'Mail'")
    print()

    app_password = input("Inserisci password app (16 caratteri): ").strip()
    app_password = app_password.replace(' ', '')  # Rimuovi spazi

    # 2. FILTRI
    print()
    print("🔍 STEP 2: Filtri Email")
    print("-" * 60)

    print("Quale etichetta Gmail monitorare?")
    print("  1. INBOX (tutte le email in arrivo)")
    print("  2. Etichetta personalizzata (es: TO_Orders)")
    scelta = input("Scelta [1/2]: ").strip()

    if scelta == '2':
        label = input("Nome etichetta: ").strip()
    else:
        label = "INBOX"

    print()
    keywords = input(
        "Parole chiave oggetto (separate da virgola) [Transfer Order,TO ,Ordine]: ").strip()
    if not keywords:
        keywords = "Transfer Order,TO ,Ordine"

    print()
    whitelist = input(
        "Mittenti autorizzati (vuoto=tutti, separate da virgola): ").strip()

    # 3. COMPORTAMENTO
    print()
    print("⚙️  STEP 3: Comportamento")
    print("-" * 60)

    mark_read = input(
        "Marcare email come lette dopo elaborazione? [S/n]: ").strip().lower()
    mark_read = 'true' if mark_read != 'n' else 'false'

    apply_label = input(
        "Applicare etichetta 'Processed' dopo elaborazione? [S/n]: ").strip().lower()
    apply_label_name = 'Processed' if apply_label != 'n' else ''

    # 4. SCRIVI FILE .env
    print()
    print("💾 Salvataggio configurazione...")

    config_content = f"""# ===================================================
# GMAIL MONITOR - CONFIGURAZIONE
# Generato da setup_wizard.py
# ===================================================

# ========== CREDENZIALI GMAIL ==========
GMAIL_EMAIL={email}
GMAIL_APP_PASSWORD={app_password}

# ========== FILTRI EMAIL ==========
GMAIL_LABEL={label}
UNREAD_ONLY=true
SUBJECT_KEYWORDS={keywords}
SENDER_WHITELIST={whitelist}

# ========== BACKEND LOCALE ==========
BACKEND_URL=http://localhost:8000
UPLOAD_TIMEOUT=120

# ========== COMPORTAMENTO ==========
MARK_AS_READ={mark_read}
APPLY_LABEL={apply_label_name}
DELETE_TEMP_FILES=true

# ========== LIMITI ==========
MAX_EMAILS_PER_RUN=50
MAX_ATTACHMENT_SIZE_MB=50
MIN_ATTACHMENT_SIZE_KB=10

# ========== RETRY ==========
MAX_RETRIES=3
RETRY_DELAY_SECONDS=60

# ========== LOGGING ==========
LOG_LEVEL=INFO
LOG_FILE=logs/gmail_monitor.log
"""

    with open(env_path, 'w') as f:
        f.write(config_content)

    print()
    print("✅ Configurazione salvata in .env")
    print()

    # 5. TEST CONFIGURAZIONE
    print("🧪 Test configurazione...")
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from config import Config

        errors = Config.validate()
        if errors:
            print("❌ Errori trovati:")
            for error in errors:
                print(f"   - {error}")
        else:
            print("✅ Configurazione valida!")
            print()
            Config.print_config()
    except Exception as e:
        print(f"⚠️  Impossibile validare: {e}")

    print()
    print("=" * 60)
    print("🎉 Setup completato!")
    print("=" * 60)
    print()
    print("Prossimi passi:")
    print("  1. Verifica che il backend sia attivo: python run.py")
    print("  2. Testa il monitor: python gmail_monitor.py --test")
    print("  3. Esegui manualmente: python gmail_monitor.py --run-once")
    print()


if __name__ == "__main__":
    setup_wizard()
