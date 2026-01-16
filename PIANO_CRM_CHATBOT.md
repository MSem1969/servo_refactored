# Piano: Sistema CRM Interno con Chatbot + Email

## Obiettivo
Creare un sistema di ticketing interno dove gli utenti possono inviare suggerimenti, critiche o segnalazioni bug tramite un chatbot visibile su ogni pagina. L'admin può rispondere, gestire i ticket e **inviare notifiche email** sullo stato.

## Requisiti Confermati
- **Stati ticket**: aperto → in_lavorazione → chiuso (con workflow)
- **Categorie**: Suggerimento, Bug Report
- **Storico utente**: L'utente vede i propri ticket con risposte admin
- **Contesto pagina**: Ogni ticket registra la pagina/funzione da cui è stato aperto
- **Notifiche Email**: Invio email su cambio stato e risposte (verso esterno)
- **Configurazione Email Unificata**: Una sola tabella per gestire IMAP (ricezione) e SMTP (invio)

---

## Architettura

### Database (5 tabelle)

```sql
-- ============================================================
-- CONFIGURAZIONE EMAIL UNIFICATA (IMAP + SMTP)
-- ============================================================
-- Sostituisce la configurazione .env di gmail_monitor
-- Gestisce sia ricezione email (IMAP) che invio (SMTP)
-- ============================================================

CREATE TABLE email_config (
    id_config SERIAL PRIMARY KEY,

    -- ========== SEZIONE IMAP (Ricezione - Gmail Monitor) ==========
    imap_enabled BOOLEAN DEFAULT FALSE,
    imap_host VARCHAR(100) DEFAULT 'imap.gmail.com',
    imap_port INTEGER DEFAULT 993,
    imap_user VARCHAR(100),              -- Email account (es: ordini@azienda.com)
    imap_password VARCHAR(200),          -- App Password (encrypted)
    imap_use_ssl BOOLEAN DEFAULT TRUE,
    imap_folder VARCHAR(50) DEFAULT 'INBOX',
    imap_unread_only BOOLEAN DEFAULT TRUE,
    imap_mark_as_read BOOLEAN DEFAULT TRUE,
    imap_apply_label VARCHAR(50) DEFAULT 'Processed',
    imap_subject_keywords TEXT,          -- JSON array: ["Transfer Order", "TO ", "Ordine"]
    imap_sender_whitelist TEXT,          -- JSON array: ["vendor1@mail.com", "vendor2@mail.com"]
    imap_max_emails_per_run INTEGER DEFAULT 50,
    imap_max_attachment_mb INTEGER DEFAULT 50,
    imap_min_attachment_kb INTEGER DEFAULT 10,

    -- ========== SEZIONE SMTP (Invio - CRM Notifiche) ==========
    smtp_enabled BOOLEAN DEFAULT FALSE,
    smtp_host VARCHAR(100) DEFAULT 'smtp.gmail.com',
    smtp_port INTEGER DEFAULT 587,
    smtp_user VARCHAR(100),              -- Può essere uguale a imap_user
    smtp_password VARCHAR(200),          -- Può essere uguale a imap_password
    smtp_use_tls BOOLEAN DEFAULT TRUE,
    smtp_sender_email VARCHAR(100),      -- Email mittente (es: noreply@azienda.com)
    smtp_sender_name VARCHAR(100) DEFAULT 'TO_EXTRACTOR',
    smtp_rate_limit INTEGER DEFAULT 10,  -- Max email/minuto

    -- ========== METADATI ==========
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES operatori(id_operatore)
);

-- Inserisce configurazione default (singleton)
INSERT INTO email_config (id_config) VALUES (1) ON CONFLICT DO NOTHING;

-- ============================================================
-- TABELLE CRM
-- ============================================================

-- Tabella ticket
CREATE TABLE crm_tickets (
    id_ticket SERIAL PRIMARY KEY,
    id_operatore INTEGER REFERENCES operatori(id_operatore),
    categoria VARCHAR(20) NOT NULL,  -- 'suggerimento', 'bug_report'
    oggetto VARCHAR(200) NOT NULL,
    pagina_origine VARCHAR(50),       -- es: 'dashboard', 'ordine-detail'
    pagina_dettaglio VARCHAR(200),    -- es: 'Ordine #12345'
    stato VARCHAR(20) DEFAULT 'aperto', -- 'aperto', 'in_lavorazione', 'chiuso'
    priorita VARCHAR(10) DEFAULT 'normale', -- 'bassa', 'normale', 'alta'
    email_notifica VARCHAR(100),      -- Email esterna per notifiche (opzionale)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    closed_by INTEGER REFERENCES operatori(id_operatore)
);

-- Tabella messaggi (thread conversazione)
CREATE TABLE crm_messaggi (
    id_messaggio SERIAL PRIMARY KEY,
    id_ticket INTEGER REFERENCES crm_tickets(id_ticket) ON DELETE CASCADE,
    id_operatore INTEGER REFERENCES operatori(id_operatore),
    contenuto TEXT NOT NULL,
    is_admin_reply BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Log email inviate (CRM)
CREATE TABLE email_log (
    id_log SERIAL PRIMARY KEY,
    id_ticket INTEGER REFERENCES crm_tickets(id_ticket),
    destinatario VARCHAR(100) NOT NULL,
    oggetto VARCHAR(200) NOT NULL,
    tipo VARCHAR(20) NOT NULL,        -- 'stato_cambiato', 'nuova_risposta', 'ticket_creato'
    stato_invio VARCHAR(20) DEFAULT 'pending', -- 'pending', 'sent', 'failed'
    errore TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP
);
```

### Vantaggi Configurazione Unificata

1. **Singolo punto di gestione**: Una sola tabella per IMAP e SMTP
2. **UI unificata**: Un solo pannello in Settings per configurare tutto
3. **Credenziali condivise**: Se usi Gmail, stesse credenziali per ricezione/invio
4. **Migrazione graduale**: Il gmail_monitor leggerà prima da DB, poi fallback su .env
5. **Audit completo**: Traccia chi modifica la configurazione

---

## Backend

### Router CRM (`/crm`)

| Endpoint | Metodo | Descrizione | Auth |
|----------|--------|-------------|------|
| `/crm/tickets` | POST | Crea nuovo ticket | User |
| `/crm/tickets` | GET | Lista ticket (admin: tutti, user: propri) | User |
| `/crm/tickets/{id}` | GET | Dettaglio ticket con messaggi | User/Admin |
| `/crm/tickets/{id}/messaggi` | POST | Aggiungi messaggio/risposta | User/Admin |
| `/crm/tickets/{id}/stato` | PATCH | Cambia stato (+ invio email) | Admin |
| `/crm/stats` | GET | Statistiche ticket | Admin |

### Router Email Unificato (`/email`)

| Endpoint | Metodo | Descrizione | Auth |
|----------|--------|-------------|------|
| `/email/config` | GET | Ottieni configurazione completa (IMAP+SMTP) | Admin |
| `/email/config` | PUT | Salva configurazione completa | Admin |
| `/email/config/imap` | GET | Solo configurazione IMAP | Admin |
| `/email/config/imap` | PUT | Salva solo IMAP | Admin |
| `/email/config/smtp` | GET | Solo configurazione SMTP | Admin |
| `/email/config/smtp` | PUT | Salva solo SMTP | Admin |
| `/email/test/imap` | POST | Test connessione IMAP | Admin |
| `/email/test/smtp` | POST | Test invio email SMTP | Admin |
| `/email/send` | POST | Invia email manuale per ticket | Admin |
| `/email/log` | GET | Log email inviate | Admin |
| `/email/log/{id}/retry` | POST | Ritenta invio email fallita | Admin |

---

## File da Creare/Modificare

### Backend
| File | Azione | Descrizione |
|------|--------|-------------|
| `backend/app/routers/crm.py` | NUOVO | Router CRM completo |
| `backend/app/routers/email.py` | NUOVO | Router gestione email unificata (IMAP+SMTP) |
| `backend/app/services/email_service.py` | NUOVO | Servizio email (invio SMTP + config DB) |
| `backend/app/main.py` | MODIFICA | Registrare router CRM e Email |
| `backend/app/database_pg.py` | MODIFICA | Init tabelle CRM + Email |
| `gmail_monitor/config.py` | MODIFICA | Leggere config da DB con fallback .env |
| `backend/app/routers/gmail.py` | MODIFICA | Usare config unificata da DB |

### Frontend
| File | Azione | Descrizione |
|------|--------|-------------|
| `frontend/src/components/CrmChatbot.jsx` | NUOVO | Componente chatbot |
| `frontend/src/layout/Layout.jsx` | MODIFICA | Aggiungere CrmChatbot |
| `frontend/src/api.js` | MODIFICA | Aggiungere crmApi + emailApi |
| `frontend/src/pages/SettingsPage.jsx` | MODIFICA | Tab configurazione email unificata (IMAP+SMTP) |

---

## Dettaglio Implementazione

### 1. Servizio Email Unificato (`email_service.py`)

```python
import smtplib
import imaplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List
from ..database_pg import get_db

class EmailConfigService:
    """
    Gestisce la configurazione email unificata (IMAP + SMTP).
    Legge da database con fallback su .env per retrocompatibilità.
    """

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Recupera configurazione email da database"""
        db = get_db()
        row = db.execute("SELECT * FROM email_config WHERE id_config = 1").fetchone()
        if row:
            config = dict(row)
            # Deserializza campi JSON
            if config.get('imap_subject_keywords'):
                config['imap_subject_keywords'] = json.loads(config['imap_subject_keywords'])
            if config.get('imap_sender_whitelist'):
                config['imap_sender_whitelist'] = json.loads(config['imap_sender_whitelist'])
            return config
        return None

    @staticmethod
    def get_imap_config() -> Dict[str, Any]:
        """Recupera solo configurazione IMAP"""
        config = EmailConfigService.get_config()
        if not config:
            return None
        return {k: v for k, v in config.items() if k.startswith('imap_')}

    @staticmethod
    def get_smtp_config() -> Dict[str, Any]:
        """Recupera solo configurazione SMTP"""
        config = EmailConfigService.get_config()
        if not config:
            return None
        return {k: v for k, v in config.items() if k.startswith('smtp_')}

    @staticmethod
    def update_config(section: str, data: Dict[str, Any], updated_by: int) -> bool:
        """Aggiorna configurazione (section: 'imap', 'smtp', 'all')"""
        db = get_db()

        # Serializza campi JSON
        if 'imap_subject_keywords' in data and isinstance(data['imap_subject_keywords'], list):
            data['imap_subject_keywords'] = json.dumps(data['imap_subject_keywords'])
        if 'imap_sender_whitelist' in data and isinstance(data['imap_sender_whitelist'], list):
            data['imap_sender_whitelist'] = json.dumps(data['imap_sender_whitelist'])

        # Costruisci query UPDATE
        fields = []
        values = []
        for key, value in data.items():
            if section == 'all' or key.startswith(f'{section}_'):
                fields.append(f"{key} = %s")
                values.append(value)

        fields.append("updated_at = CURRENT_TIMESTAMP")
        fields.append("updated_by = %s")
        values.append(updated_by)

        query = f"UPDATE email_config SET {', '.join(fields)} WHERE id_config = 1"
        db.execute(query, values)
        db.commit()
        return True


class EmailSender:
    """Servizio invio email via SMTP"""

    def __init__(self):
        config = EmailConfigService.get_smtp_config()
        if not config or not config.get('smtp_enabled'):
            raise ValueError("SMTP non configurato o disabilitato")

        self.host = config['smtp_host']
        self.port = config['smtp_port']
        self.user = config['smtp_user']
        self.password = config['smtp_password']
        self.use_tls = config['smtp_use_tls']
        self.sender_email = config['smtp_sender_email']
        self.sender_name = config['smtp_sender_name']

    def send_email(self, to: str, subject: str, body_html: str) -> bool:
        """Invia email via SMTP"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.sender_name} <{self.sender_email}>"
        msg['To'] = to

        msg.attach(MIMEText(body_html, 'html'))

        with smtplib.SMTP(self.host, self.port) as server:
            if self.use_tls:
                server.starttls()
            server.login(self.user, self.password)
            server.send_message(msg)
        return True

    def send_ticket_status_update(self, ticket: dict, new_status: str):
        """Invia notifica cambio stato ticket"""
        subject = f"[Ticket #{ticket['id_ticket']}] Stato aggiornato: {new_status}"
        body = f"""
        <h2>Aggiornamento Ticket</h2>
        <p><strong>Oggetto:</strong> {ticket['oggetto']}</p>
        <p><strong>Nuovo stato:</strong> {new_status}</p>
        <p><strong>Categoria:</strong> {ticket['categoria']}</p>
        <hr>
        <p>Questo messaggio è stato inviato automaticamente da TO_EXTRACTOR.</p>
        """
        return self.send_email(ticket['email_notifica'], subject, body)

    @staticmethod
    def test_connection() -> Dict[str, Any]:
        """Test connessione SMTP"""
        try:
            sender = EmailSender()
            with smtplib.SMTP(sender.host, sender.port, timeout=10) as server:
                if sender.use_tls:
                    server.starttls()
                server.login(sender.user, sender.password)
            return {"success": True, "message": "Connessione SMTP OK"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class ImapTester:
    """Test connessione IMAP"""

    @staticmethod
    def test_connection() -> Dict[str, Any]:
        """Test connessione IMAP"""
        config = EmailConfigService.get_imap_config()
        if not config or not config.get('imap_enabled'):
            return {"success": False, "error": "IMAP non configurato o disabilitato"}

        try:
            if config['imap_use_ssl']:
                mail = imaplib.IMAP4_SSL(config['imap_host'], config['imap_port'])
            else:
                mail = imaplib.IMAP4(config['imap_host'], config['imap_port'])

            mail.login(config['imap_user'], config['imap_password'])
            mail.select(config['imap_folder'])

            # Conta email non lette
            status, messages = mail.search(None, 'UNSEEN')
            unread_count = len(messages[0].split()) if messages[0] else 0

            mail.logout()
            return {
                "success": True,
                "message": f"Connessione IMAP OK - {unread_count} email non lette"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
```

### 1b. Migrazione Gmail Monitor (`gmail_monitor/config.py`)

```python
# Modifica per leggere da DB con fallback .env

class Config:
    """Configurazione Gmail Monitor - Legge da DB, fallback su .env"""

    _db_config = None

    @classmethod
    def _load_from_db(cls):
        """Carica configurazione da database"""
        if cls._db_config is not None:
            return cls._db_config

        try:
            # Importa dal backend (path relativo)
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent / 'backend' / 'app'))
            from database_pg import get_db

            db = get_db()
            row = db.execute("SELECT * FROM email_config WHERE id_config = 1").fetchone()
            if row and row['imap_enabled']:
                cls._db_config = dict(row)
                return cls._db_config
        except Exception as e:
            print(f"⚠️ Fallback su .env: {e}")

        return None

    @classmethod
    def _get(cls, db_key: str, env_key: str, default):
        """Recupera valore da DB o .env"""
        db_config = cls._load_from_db()
        if db_config and db_key in db_config:
            return db_config[db_key]
        return os.getenv(env_key, default)

    # ========== GMAIL CREDENTIALS (ora da DB) ==========
    @property
    def GMAIL_EMAIL(self):
        return self._get('imap_user', 'GMAIL_EMAIL', '')

    @property
    def GMAIL_APP_PASSWORD(self):
        return self._get('imap_password', 'GMAIL_APP_PASSWORD', '')

    # ... altri campi con stesso pattern ...
```

### 2. Template Email

```python
EMAIL_TEMPLATES = {
    'ticket_creato': {
        'subject': '[Ticket #{id}] Nuovo ticket creato',
        'body': '''
            <h2>Nuovo Ticket Creato</h2>
            <p><strong>ID:</strong> #{id}</p>
            <p><strong>Categoria:</strong> {categoria}</p>
            <p><strong>Oggetto:</strong> {oggetto}</p>
            <p><strong>Pagina:</strong> {pagina_origine}</p>
        '''
    },
    'stato_cambiato': {
        'subject': '[Ticket #{id}] Stato aggiornato: {stato}',
        'body': '''
            <h2>Aggiornamento Stato Ticket</h2>
            <p><strong>ID:</strong> #{id}</p>
            <p><strong>Nuovo Stato:</strong> {stato}</p>
            <p><strong>Oggetto:</strong> {oggetto}</p>
        '''
    },
    'nuova_risposta': {
        'subject': '[Ticket #{id}] Nuova risposta',
        'body': '''
            <h2>Nuova Risposta al Ticket</h2>
            <p><strong>ID:</strong> #{id}</p>
            <p><strong>Messaggio:</strong></p>
            <blockquote>{messaggio}</blockquote>
        '''
    }
}
```

### 3. Request Models

```python
class CreaTicketRequest(BaseModel):
    categoria: Literal['suggerimento', 'bug_report']
    oggetto: str = Field(..., min_length=5, max_length=200)
    contenuto: str = Field(..., min_length=10)
    pagina_origine: str
    pagina_dettaglio: Optional[str] = None
    email_notifica: Optional[EmailStr] = None  # Email esterna opzionale

class EmailConfigRequest(BaseModel):
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    smtp_use_tls: bool = True
    sender_email: EmailStr
    sender_name: str = 'TO_EXTRACTOR CRM'
    is_active: bool = False

class InviaEmailRequest(BaseModel):
    id_ticket: int
    destinatario: EmailStr
    oggetto: str
    contenuto: str
```

### 4. Frontend - Form Ticket con Email

```jsx
// Nel form creazione ticket
<div className="space-y-4">
  <select name="categoria" required>
    <option value="suggerimento">Suggerimento</option>
    <option value="bug_report">Bug Report</option>
  </select>

  <input
    type="text"
    name="oggetto"
    placeholder="Oggetto"
    required
  />

  <textarea
    name="contenuto"
    placeholder="Descrizione..."
    required
  />

  {/* Campo opzionale per notifiche esterne */}
  <input
    type="email"
    name="email_notifica"
    placeholder="Email per notifiche (opzionale)"
  />

  {/* Info pagina (readonly, auto-compilato) */}
  <div className="text-xs text-slate-500">
    📍 Segnalazione da: {paginaOrigine}
  </div>
</div>
```

### 5. Frontend - Configurazione Email Unificata (Settings)

```jsx
// Nuovo tab in SettingsPage.jsx - Configurazione Email Unificata
<Tab label="Email">
  <div className="space-y-6">

    {/* ========== SEZIONE IMAP (Ricezione) ========== */}
    <div className="bg-slate-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium flex items-center gap-2">
          📥 Ricezione Email (IMAP)
        </h3>
        <label className="flex items-center gap-2">
          <input type="checkbox" name="imap_enabled" />
          <span className="text-sm">Attivo</span>
        </label>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <input name="imap_host" placeholder="imap.gmail.com" />
        <input name="imap_port" type="number" defaultValue={993} />
        <input name="imap_user" placeholder="ordini@azienda.com" />
        <input name="imap_password" type="password" placeholder="App Password" />
        <input name="imap_folder" placeholder="INBOX" />
        <input name="imap_apply_label" placeholder="Processed" />
      </div>

      <div className="flex gap-4 mt-3">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" name="imap_use_ssl" defaultChecked />
          Usa SSL
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" name="imap_unread_only" defaultChecked />
          Solo non lette
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" name="imap_mark_as_read" defaultChecked />
          Marca come lette
        </label>
      </div>

      {/* Keywords e Whitelist */}
      <div className="mt-4 space-y-2">
        <input
          name="imap_subject_keywords"
          placeholder="Keywords oggetto (es: Transfer Order, Ordine)"
        />
        <input
          name="imap_sender_whitelist"
          placeholder="Whitelist mittenti (opzionale, separati da virgola)"
        />
      </div>

      <button
        type="button"
        onClick={handleTestImap}
        className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
      >
        🔌 Test Connessione IMAP
      </button>
    </div>

    {/* ========== SEZIONE SMTP (Invio) ========== */}
    <div className="bg-slate-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium flex items-center gap-2">
          📤 Invio Email (SMTP)
        </h3>
        <label className="flex items-center gap-2">
          <input type="checkbox" name="smtp_enabled" />
          <span className="text-sm">Attivo</span>
        </label>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <input name="smtp_host" placeholder="smtp.gmail.com" />
        <input name="smtp_port" type="number" defaultValue={587} />
        <input name="smtp_user" placeholder="noreply@azienda.com" />
        <input name="smtp_password" type="password" placeholder="App Password" />
        <input name="smtp_sender_email" placeholder="noreply@azienda.com" />
        <input name="smtp_sender_name" placeholder="TO_EXTRACTOR" />
      </div>

      <label className="flex items-center gap-2 text-sm mt-3">
        <input type="checkbox" name="smtp_use_tls" defaultChecked />
        Usa TLS
      </label>

      <button
        type="button"
        onClick={handleTestSmtp}
        className="mt-4 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg"
      >
        📧 Invia Email di Test
      </button>
    </div>

    {/* ========== CHECKBOX CREDENZIALI CONDIVISE ========== */}
    <div className="flex items-center gap-2 text-sm text-slate-400">
      <input
        type="checkbox"
        name="use_same_credentials"
        onChange={(e) => {
          if (e.target.checked) {
            // Copia credenziali IMAP su SMTP
            form.smtp_user = form.imap_user;
            form.smtp_password = form.imap_password;
          }
        }}
      />
      <span>Usa stesse credenziali per IMAP e SMTP (consigliato per Gmail)</span>
    </div>

    {/* ========== BOTTONI SALVA ========== */}
    <div className="flex gap-4">
      <button
        type="submit"
        className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
      >
        💾 Salva Configurazione
      </button>
    </div>

  </div>
</Tab>
```

---

## Flusso Email

### Automatico (se email_notifica presente)
1. **Ticket creato** → Email "Ticket ricevuto" all'utente
2. **Admin risponde** → Email "Nuova risposta" all'utente
3. **Stato cambiato** → Email "Stato aggiornato" all'utente
4. **Ticket chiuso** → Email "Ticket risolto" all'utente

### Manuale (Admin)
1. Admin apre ticket
2. Clicca "Invia Email"
3. Compila destinatario, oggetto, corpo
4. Conferma invio
5. Log salvato in `email_log`

---

## Configurazioni Provider Email Comuni

| Provider | Host | Porta | Note |
|----------|------|-------|------|
| Gmail | smtp.gmail.com | 587 | Richiede App Password |
| Outlook | smtp.office365.com | 587 | TLS obbligatorio |
| SendGrid | smtp.sendgrid.net | 587 | API Key come password |
| Mailgun | smtp.mailgun.org | 587 | - |
| Custom SMTP | custom | 25/465/587 | - |

---

## Verifica

### Test CRM Base
1. Creare ticket da pagina Database
2. Verificare `pagina_origine = 'database'`
3. Admin risponde, utente vede thread

### Test Email
1. Configurare SMTP in Settings
2. Inviare email di test
3. Creare ticket con `email_notifica`
4. Verificare ricezione email su cambio stato
5. Verificare log in `email_log`

### Test Email Manuale
1. Admin apre ticket
2. Clicca "Invia Email Manuale"
3. Compila form e invia
4. Verifica ricezione e log

---

## Sicurezza Email

- **Password SMTP criptata** in database
- **Rate limiting**: max 10 email/minuto per evitare spam
- **Validazione destinatari**: solo email valide
- **Log completo**: traccia ogni invio per audit
- **Retry automatico**: tentativi falliti riprovati dopo 5 minuti

---

## Sistema Email: Architettura Completa

### Flusso Dati Email

```
┌─────────────────────────────────────────────────────────────────┐
│                        SISTEMA EMAIL                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │   RICEZIONE  │     │  ELABORAZIONE │     │    INVIO     │     │
│  │    (IMAP)    │────▶│   (Backend)   │────▶│   (SMTP)     │     │
│  └──────────────┘     └──────────────┘     └──────────────┘     │
│         │                     │                     │            │
│         ▼                     ▼                     ▼            │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │ Gmail/IMAP   │     │  Database    │     │ Gmail/SMTP   │     │
│  │   Server     │     │  PostgreSQL  │     │   Server     │     │
│  └──────────────┘     └──────────────┘     └──────────────┘     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Componenti Email

| Componente | Protocollo | Funzione | Stato |
|------------|------------|----------|-------|
| **Gmail Monitor** | IMAP | Scarica PDF allegati da email ordini | Attivo |
| **CRM Notifier** | SMTP | Invia notifiche ticket utenti | Da implementare |
| **Email Log** | DB | Traccia tutti gli invii | Da implementare |

---

## Gestione Credenziali con .env

### Principio di Sicurezza

**Le credenziali sensibili NON devono MAI essere committate su GitHub.**

La strategia è:
1. **Credenziali** (password, API key) → File `.env` (fuori da Git)
2. **Configurazioni** (host, porta, opzioni) → Database (modificabili da UI)
3. **Fallback** → Il sistema legge prima da `.env`, poi le configurazioni da DB

### File .env.example

Creare un file `.env.example` come template (questo SÌ va su Git):

```bash
# ============================================================
# CONFIGURAZIONE EMAIL - TO_EXTRACTOR
# ============================================================
# Copia questo file in .env e compila con i valori reali
# Il file .env NON deve MAI essere committato su GitHub
# ============================================================

# ========== DATABASE ==========
DATABASE_URL=postgresql://user:password@localhost:5432/to_extractor

# ========== CREDENZIALI IMAP (Ricezione Email) ==========
# Usato da gmail_monitor per scaricare PDF dagli ordini
IMAP_USER=ordini@tuaazienda.com
IMAP_PASSWORD=app_password_qui
# Per Gmail: generare App Password da https://myaccount.google.com/apppasswords

# ========== CREDENZIALI SMTP (Invio Email) ==========
# Usato dal CRM per inviare notifiche ai clienti
SMTP_USER=noreply@tuaazienda.com
SMTP_PASSWORD=app_password_qui
# Se usi Gmail, puoi usare le stesse credenziali IMAP

# ========== OPZIONALE: Chiave di crittografia ==========
# Per criptare password salvate nel database
ENCRYPTION_KEY=genera_una_chiave_sicura_32_caratteri
```

### File .env (NON committare!)

```bash
# File reale con credenziali - AGGIUNGERE A .gitignore
IMAP_USER=ordini@mia-farmacia.it
IMAP_PASSWORD=abcd efgh ijkl mnop
SMTP_USER=noreply@mia-farmacia.it
SMTP_PASSWORD=abcd efgh ijkl mnop
```

### Aggiornare .gitignore

```gitignore
# Credenziali - MAI committare
.env
.env.local
.env.production
*.env

# Mantenere il template
!.env.example
```

---

## Backend: Lettura Configurazione Email

### Gerarchia di Configurazione

```
┌─────────────────────────────────────────────────────────────┐
│                    ORDINE DI LETTURA                         │
├─────────────────────────────────────────────────────────────┤
│  1. File .env (credenziali sensibili - password)            │
│     ↓ fallback se non presente                              │
│  2. Variabili ambiente sistema (per Docker/Kubernetes)      │
│     ↓ fallback se non presente                              │
│  3. Database email_config (configurazioni non sensibili)    │
│     ↓ fallback se non presente                              │
│  4. Valori default hardcoded (solo per sviluppo)            │
└─────────────────────────────────────────────────────────────┘
```

### Implementazione Config Service

```python
# backend/app/services/email_config.py

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Carica .env dalla root del progetto
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(env_path)

class EmailConfigService:
    """
    Gestisce configurazione email con priorità:
    1. Variabili .env (credenziali sensibili)
    2. Database (configurazioni non sensibili)
    3. Default (solo per sviluppo)
    """

    # ========== CREDENZIALI DA .ENV ==========

    @staticmethod
    def get_imap_credentials() -> Dict[str, str]:
        """
        Recupera credenziali IMAP da .env
        QUESTE NON VANNO MAI NEL DATABASE
        """
        return {
            'user': os.getenv('IMAP_USER', ''),
            'password': os.getenv('IMAP_PASSWORD', '')
        }

    @staticmethod
    def get_smtp_credentials() -> Dict[str, str]:
        """
        Recupera credenziali SMTP da .env
        QUESTE NON VANNO MAI NEL DATABASE
        """
        return {
            'user': os.getenv('SMTP_USER', ''),
            'password': os.getenv('SMTP_PASSWORD', '')
        }

    # ========== CONFIGURAZIONI DA DATABASE ==========

    @staticmethod
    def get_imap_settings(db) -> Dict[str, Any]:
        """
        Recupera impostazioni IMAP da database
        (host, porta, cartella, opzioni - NON password)
        """
        row = db.execute("""
            SELECT imap_enabled, imap_host, imap_port, imap_use_ssl,
                   imap_folder, imap_unread_only, imap_mark_as_read,
                   imap_apply_label, imap_subject_keywords,
                   imap_sender_whitelist, imap_max_emails_per_run
            FROM email_config WHERE id_config = 1
        """).fetchone()

        if row:
            return dict(row)

        # Default per sviluppo
        return {
            'imap_enabled': False,
            'imap_host': 'imap.gmail.com',
            'imap_port': 993,
            'imap_use_ssl': True,
            'imap_folder': 'INBOX'
        }

    @staticmethod
    def get_smtp_settings(db) -> Dict[str, Any]:
        """
        Recupera impostazioni SMTP da database
        (host, porta, TLS, mittente - NON password)
        """
        row = db.execute("""
            SELECT smtp_enabled, smtp_host, smtp_port, smtp_use_tls,
                   smtp_sender_email, smtp_sender_name, smtp_rate_limit
            FROM email_config WHERE id_config = 1
        """).fetchone()

        if row:
            return dict(row)

        # Default per sviluppo
        return {
            'smtp_enabled': False,
            'smtp_host': 'smtp.gmail.com',
            'smtp_port': 587,
            'smtp_use_tls': True,
            'smtp_sender_name': 'TO_EXTRACTOR'
        }

    # ========== CONFIG COMPLETA (merge .env + DB) ==========

    @classmethod
    def get_full_imap_config(cls, db) -> Dict[str, Any]:
        """Configurazione IMAP completa: credenziali + settings"""
        credentials = cls.get_imap_credentials()
        settings = cls.get_imap_settings(db)

        return {
            **settings,
            'imap_user': credentials['user'],
            'imap_password': credentials['password']
        }

    @classmethod
    def get_full_smtp_config(cls, db) -> Dict[str, Any]:
        """Configurazione SMTP completa: credenziali + settings"""
        credentials = cls.get_smtp_credentials()
        settings = cls.get_smtp_settings(db)

        return {
            **settings,
            'smtp_user': credentials['user'],
            'smtp_password': credentials['password']
        }
```

---

## Frontend: Tab Configurazione Email in Settings

### Struttura della Tab Email

La tab Email nelle Impostazioni deve:
1. **NON mostrare** le password salvate (solo indicare se sono configurate)
2. **Permettere test** connessione senza esporre credenziali
3. **Salvare configurazioni** non sensibili nel database
4. **Indicare** che le credenziali vanno configurate nel file .env

### Componente EmailSettingsTab

```jsx
// frontend/src/pages/Settings/EmailSettingsTab.jsx

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { emailApi } from '../../api';

export default function EmailSettingsTab() {
  const queryClient = useQueryClient();

  // Carica configurazione (senza password!)
  const { data: config, isLoading } = useQuery({
    queryKey: ['email-config'],
    queryFn: emailApi.getConfig
  });

  // Stato form
  const [imapSettings, setImapSettings] = useState({
    imap_enabled: false,
    imap_host: 'imap.gmail.com',
    imap_port: 993,
    imap_use_ssl: true,
    imap_folder: 'INBOX',
    imap_unread_only: true,
    imap_mark_as_read: true,
    imap_apply_label: 'Processed',
    imap_subject_keywords: '',
    imap_sender_whitelist: ''
  });

  const [smtpSettings, setSmtpSettings] = useState({
    smtp_enabled: false,
    smtp_host: 'smtp.gmail.com',
    smtp_port: 587,
    smtp_use_tls: true,
    smtp_sender_email: '',
    smtp_sender_name: 'TO_EXTRACTOR'
  });

  // Mutation salvataggio
  const saveMutation = useMutation({
    mutationFn: (data) => emailApi.saveConfig(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['email-config']);
      toast.success('Configurazione salvata');
    }
  });

  // Test connessioni
  const [testResults, setTestResults] = useState({ imap: null, smtp: null });

  const handleTestImap = async () => {
    setTestResults(prev => ({ ...prev, imap: 'testing' }));
    const result = await emailApi.testImap();
    setTestResults(prev => ({ ...prev, imap: result }));
  };

  const handleTestSmtp = async () => {
    setTestResults(prev => ({ ...prev, smtp: 'testing' }));
    const result = await emailApi.testSmtp();
    setTestResults(prev => ({ ...prev, smtp: result }));
  };

  return (
    <div className="space-y-6">

      {/* ========== AVVISO CREDENZIALI ========== */}
      <div className="bg-amber-900/30 border border-amber-600 rounded-lg p-4">
        <h4 className="font-medium text-amber-400 flex items-center gap-2">
          🔐 Configurazione Credenziali
        </h4>
        <p className="text-sm text-amber-200 mt-2">
          Le credenziali email (username e password) sono gestite tramite variabili d'ambiente
          per motivi di sicurezza. Configura il file <code className="bg-slate-800 px-1 rounded">.env</code>
          nella root del progetto:
        </p>
        <pre className="bg-slate-900 p-3 rounded mt-2 text-xs text-slate-300 overflow-x-auto">
{`# .env
IMAP_USER=ordini@tuaazienda.com
IMAP_PASSWORD=tua_app_password
SMTP_USER=noreply@tuaazienda.com
SMTP_PASSWORD=tua_app_password`}
        </pre>
        <p className="text-xs text-amber-300 mt-2">
          Per Gmail: genera una <a href="https://myaccount.google.com/apppasswords"
            target="_blank" className="underline">App Password</a> nelle impostazioni account.
        </p>
      </div>

      {/* ========== STATO CREDENZIALI ========== */}
      <div className="bg-slate-800 rounded-lg p-4">
        <h4 className="font-medium mb-3">Stato Credenziali (.env)</h4>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="flex items-center gap-2">
            {config?.imap_credentials_configured ? (
              <span className="text-green-400">✓ IMAP configurato</span>
            ) : (
              <span className="text-red-400">✗ IMAP non configurato</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {config?.smtp_credentials_configured ? (
              <span className="text-green-400">✓ SMTP configurato</span>
            ) : (
              <span className="text-red-400">✗ SMTP non configurato</span>
            )}
          </div>
        </div>
      </div>

      {/* ========== SEZIONE IMAP (Ricezione) ========== */}
      <div className="bg-slate-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium flex items-center gap-2">
            📥 Ricezione Email (IMAP)
          </h3>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={imapSettings.imap_enabled}
              onChange={(e) => setImapSettings(prev => ({
                ...prev,
                imap_enabled: e.target.checked
              }))}
              className="rounded"
            />
            <span className="text-sm">Attivo</span>
          </label>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-slate-400">Server IMAP</label>
            <input
              value={imapSettings.imap_host}
              onChange={(e) => setImapSettings(prev => ({...prev, imap_host: e.target.value}))}
              className="w-full bg-slate-700 rounded px-3 py-2"
              placeholder="imap.gmail.com"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400">Porta</label>
            <input
              type="number"
              value={imapSettings.imap_port}
              onChange={(e) => setImapSettings(prev => ({...prev, imap_port: parseInt(e.target.value)}))}
              className="w-full bg-slate-700 rounded px-3 py-2"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400">Cartella</label>
            <input
              value={imapSettings.imap_folder}
              onChange={(e) => setImapSettings(prev => ({...prev, imap_folder: e.target.value}))}
              className="w-full bg-slate-700 rounded px-3 py-2"
              placeholder="INBOX"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400">Label dopo elaborazione</label>
            <input
              value={imapSettings.imap_apply_label}
              onChange={(e) => setImapSettings(prev => ({...prev, imap_apply_label: e.target.value}))}
              className="w-full bg-slate-700 rounded px-3 py-2"
              placeholder="Processed"
            />
          </div>
        </div>

        <div className="flex gap-6 mt-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={imapSettings.imap_use_ssl}
              onChange={(e) => setImapSettings(prev => ({...prev, imap_use_ssl: e.target.checked}))}
            />
            Usa SSL
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={imapSettings.imap_unread_only}
              onChange={(e) => setImapSettings(prev => ({...prev, imap_unread_only: e.target.checked}))}
            />
            Solo non lette
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={imapSettings.imap_mark_as_read}
              onChange={(e) => setImapSettings(prev => ({...prev, imap_mark_as_read: e.target.checked}))}
            />
            Marca come lette
          </label>
        </div>

        <div className="mt-4 space-y-3">
          <div>
            <label className="text-xs text-slate-400">Keywords oggetto (separate da virgola)</label>
            <input
              value={imapSettings.imap_subject_keywords}
              onChange={(e) => setImapSettings(prev => ({...prev, imap_subject_keywords: e.target.value}))}
              className="w-full bg-slate-700 rounded px-3 py-2"
              placeholder="Transfer Order, Ordine, TO "
            />
          </div>
          <div>
            <label className="text-xs text-slate-400">Whitelist mittenti (opzionale, separate da virgola)</label>
            <input
              value={imapSettings.imap_sender_whitelist}
              onChange={(e) => setImapSettings(prev => ({...prev, imap_sender_whitelist: e.target.value}))}
              className="w-full bg-slate-700 rounded px-3 py-2"
              placeholder="ordini@fornitore1.com, noreply@fornitore2.com"
            />
          </div>
        </div>

        <button
          type="button"
          onClick={handleTestImap}
          disabled={testResults.imap === 'testing'}
          className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg flex items-center gap-2"
        >
          {testResults.imap === 'testing' ? (
            <>⏳ Test in corso...</>
          ) : (
            <>🔌 Test Connessione IMAP</>
          )}
        </button>

        {testResults.imap && testResults.imap !== 'testing' && (
          <div className={`mt-2 p-2 rounded text-sm ${
            testResults.imap.success ? 'bg-green-900/50 text-green-300' : 'bg-red-900/50 text-red-300'
          }`}>
            {testResults.imap.success ? '✓ ' : '✗ '}
            {testResults.imap.message || testResults.imap.error}
          </div>
        )}
      </div>

      {/* ========== SEZIONE SMTP (Invio) ========== */}
      <div className="bg-slate-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium flex items-center gap-2">
            📤 Invio Email (SMTP)
          </h3>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={smtpSettings.smtp_enabled}
              onChange={(e) => setSmtpSettings(prev => ({
                ...prev,
                smtp_enabled: e.target.checked
              }))}
              className="rounded"
            />
            <span className="text-sm">Attivo</span>
          </label>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-slate-400">Server SMTP</label>
            <input
              value={smtpSettings.smtp_host}
              onChange={(e) => setSmtpSettings(prev => ({...prev, smtp_host: e.target.value}))}
              className="w-full bg-slate-700 rounded px-3 py-2"
              placeholder="smtp.gmail.com"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400">Porta</label>
            <input
              type="number"
              value={smtpSettings.smtp_port}
              onChange={(e) => setSmtpSettings(prev => ({...prev, smtp_port: parseInt(e.target.value)}))}
              className="w-full bg-slate-700 rounded px-3 py-2"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400">Email mittente</label>
            <input
              value={smtpSettings.smtp_sender_email}
              onChange={(e) => setSmtpSettings(prev => ({...prev, smtp_sender_email: e.target.value}))}
              className="w-full bg-slate-700 rounded px-3 py-2"
              placeholder="noreply@tuaazienda.com"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400">Nome mittente</label>
            <input
              value={smtpSettings.smtp_sender_name}
              onChange={(e) => setSmtpSettings(prev => ({...prev, smtp_sender_name: e.target.value}))}
              className="w-full bg-slate-700 rounded px-3 py-2"
              placeholder="TO_EXTRACTOR"
            />
          </div>
        </div>

        <label className="flex items-center gap-2 text-sm mt-4">
          <input
            type="checkbox"
            checked={smtpSettings.smtp_use_tls}
            onChange={(e) => setSmtpSettings(prev => ({...prev, smtp_use_tls: e.target.checked}))}
          />
          Usa TLS (consigliato)
        </label>

        <button
          type="button"
          onClick={handleTestSmtp}
          disabled={testResults.smtp === 'testing'}
          className="mt-4 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded-lg flex items-center gap-2"
        >
          {testResults.smtp === 'testing' ? (
            <>⏳ Invio in corso...</>
          ) : (
            <>📧 Invia Email di Test</>
          )}
        </button>

        {testResults.smtp && testResults.smtp !== 'testing' && (
          <div className={`mt-2 p-2 rounded text-sm ${
            testResults.smtp.success ? 'bg-green-900/50 text-green-300' : 'bg-red-900/50 text-red-300'
          }`}>
            {testResults.smtp.success ? '✓ ' : '✗ '}
            {testResults.smtp.message || testResults.smtp.error}
          </div>
        )}
      </div>

      {/* ========== BOTTONE SALVA ========== */}
      <div className="flex justify-end">
        <button
          onClick={() => saveMutation.mutate({ ...imapSettings, ...smtpSettings })}
          disabled={saveMutation.isLoading}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg"
        >
          {saveMutation.isLoading ? '⏳ Salvataggio...' : '💾 Salva Configurazione'}
        </button>
      </div>

    </div>
  );
}
```

---

## API Frontend per Email

```javascript
// frontend/src/api.js - Aggiungere sezione emailApi

export const emailApi = {
  // Configurazione
  getConfig: async () => {
    const response = await fetch(`${API_BASE}/email/config`, {
      headers: authHeaders()
    });
    return response.json();
  },

  saveConfig: async (data) => {
    const response = await fetch(`${API_BASE}/email/config`, {
      method: 'PUT',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return response.json();
  },

  // Test connessioni
  testImap: async () => {
    const response = await fetch(`${API_BASE}/email/test/imap`, {
      method: 'POST',
      headers: authHeaders()
    });
    return response.json();
  },

  testSmtp: async () => {
    const response = await fetch(`${API_BASE}/email/test/smtp`, {
      method: 'POST',
      headers: authHeaders()
    });
    return response.json();
  },

  // Log email
  getLog: async (params) => {
    const query = new URLSearchParams(params).toString();
    const response = await fetch(`${API_BASE}/email/log?${query}`, {
      headers: authHeaders()
    });
    return response.json();
  },

  retryEmail: async (logId) => {
    const response = await fetch(`${API_BASE}/email/log/${logId}/retry`, {
      method: 'POST',
      headers: authHeaders()
    });
    return response.json();
  }
};
```

---

## Provider Email Supportati

### Gmail (Default)

```
IMAP: imap.gmail.com:993 (SSL)
SMTP: smtp.gmail.com:587 (TLS)

Requisiti:
1. Attivare "Accesso app meno sicure" OPPURE
2. Generare App Password (consigliato)
   - Vai su https://myaccount.google.com/apppasswords
   - Seleziona "Posta" e "Computer Windows"
   - Copia la password di 16 caratteri
```

### Outlook/Office 365

```
IMAP: outlook.office365.com:993 (SSL)
SMTP: smtp.office365.com:587 (TLS)

Requisiti:
- Autenticazione OAuth2 o App Password
```

### Provider Italiano (Aruba, Register, etc.)

```
IMAP: imaps.aruba.it:993 (SSL)
SMTP: smtps.aruba.it:465 (SSL) o smtp.aruba.it:587 (TLS)
```

### Server Custom (On-Premise)

```
Configurazione manuale host/porta
Supporto SSL, TLS o connessione non cifrata
```

---

---

## Architettura Modulare (v8.1)

### Principi di Design

La struttura segue i pattern già consolidati nel progetto:

1. **Single Responsibility** - Ogni modulo ha una sola responsabilità
2. **Separation of Concerns** - Router → Service → Database
3. **Extensibility** - Base classes per future estensioni (altri provider email)
4. **Retrocompatibilità** - Wrapper deprecation per migrazioni graduali
5. **DRY** - Codice condiviso tra CRM e Gmail Monitor

---

### Struttura Backend - Email & CRM

```
backend/app/
├── services/
│   ├── email/                      # 📧 NUOVO - Sistema Email Unificato
│   │   ├── __init__.py            # Re-exports pubblici
│   │   ├── constants.py           # Provider configs, rate limits
│   │   ├── config.py              # EmailConfigService (.env + DB)
│   │   ├── providers/             # Provider-specific implementations
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # BaseEmailProvider (abstract)
│   │   │   ├── gmail.py           # GmailProvider (IMAP+SMTP)
│   │   │   ├── outlook.py         # OutlookProvider (futuro)
│   │   │   └── generic.py         # GenericSMTP/IMAP
│   │   ├── sender.py              # EmailSender (SMTP operations)
│   │   ├── receiver.py            # EmailReceiver (IMAP operations)
│   │   ├── templates.py           # Email templates (HTML)
│   │   └── log.py                 # Email logging utilities
│   │
│   └── crm/                       # 🎫 NUOVO - Sistema CRM/Ticketing
│       ├── __init__.py            # Re-exports pubblici
│       ├── constants.py           # Stati, categorie, priorità
│       ├── tickets/               # Gestione ticket
│       │   ├── __init__.py
│       │   ├── queries.py         # GET operations (list, detail)
│       │   ├── commands.py        # CREATE/UPDATE operations
│       │   └── workflow.py        # State transitions
│       ├── messages/              # Thread messaggi
│       │   ├── __init__.py
│       │   ├── queries.py
│       │   └── commands.py
│       └── notifications.py       # Invio notifiche email
│
├── routers/
│   ├── email.py                   # 📧 NUOVO - Endpoints config email
│   └── crm.py                     # 🎫 NUOVO - Endpoints CRM
```

---

### Dettaglio Moduli Backend

#### 1. `services/email/constants.py` (~30 righe)

```python
"""Costanti sistema email - Centralizzate per manutenibilità"""

# Provider supportati
PROVIDERS = {
    'gmail': {
        'imap_host': 'imap.gmail.com',
        'imap_port': 993,
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'use_ssl': True,
        'use_tls': True,
    },
    'outlook': {
        'imap_host': 'outlook.office365.com',
        'imap_port': 993,
        'smtp_host': 'smtp.office365.com',
        'smtp_port': 587,
        'use_ssl': True,
        'use_tls': True,
    },
}

# Rate limiting
SMTP_RATE_LIMIT = 10  # email/minuto
SMTP_RETRY_DELAY = 300  # secondi

# Stati invio
class EmailStatus:
    PENDING = 'pending'
    SENT = 'sent'
    FAILED = 'failed'
    RETRY = 'retry'
```

#### 2. `services/email/config.py` (~80 righe)

```python
"""
Gestione configurazione email con priorità:
1. Variabili .env (credenziali sensibili)
2. Database email_config (impostazioni modificabili)
3. Default da constants.py
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pathlib import Path

# Carica .env dalla root
_env_loaded = False

def _ensure_env_loaded():
    global _env_loaded
    if not _env_loaded:
        env_path = Path(__file__).parent.parent.parent.parent.parent / '.env'
        load_dotenv(env_path)
        _env_loaded = True


class EmailConfigService:
    """Singleton per gestione configurazione email"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ========== CREDENZIALI (.env) ==========

    @staticmethod
    def get_credentials(protocol: str) -> Dict[str, str]:
        """
        Recupera credenziali da .env
        protocol: 'imap' o 'smtp'
        """
        _ensure_env_loaded()
        prefix = protocol.upper()
        return {
            'user': os.getenv(f'{prefix}_USER', ''),
            'password': os.getenv(f'{prefix}_PASSWORD', '')
        }

    @staticmethod
    def credentials_configured(protocol: str) -> bool:
        """Verifica se le credenziali sono configurate"""
        creds = EmailConfigService.get_credentials(protocol)
        return bool(creds['user'] and creds['password'])

    # ========== SETTINGS (Database) ==========

    @staticmethod
    def get_settings(db, section: str = 'all') -> Dict[str, Any]:
        """
        Recupera impostazioni da database
        section: 'imap', 'smtp', 'all'
        """
        query = "SELECT * FROM email_config WHERE id_config = 1"
        row = db.execute(query).fetchone()

        if not row:
            from .constants import PROVIDERS
            return PROVIDERS.get('gmail', {})

        config = dict(row)

        if section == 'all':
            return config

        # Filtra per sezione
        prefix = f'{section}_'
        return {k: v for k, v in config.items() if k.startswith(prefix)}

    @staticmethod
    def update_settings(db, data: Dict[str, Any], updated_by: int) -> bool:
        """Aggiorna impostazioni nel database (NO password!)"""
        # Rimuovi eventuali campi password (sicurezza)
        safe_data = {k: v for k, v in data.items()
                     if 'password' not in k.lower()}

        fields = [f"{k} = %s" for k in safe_data.keys()]
        fields.append("updated_at = CURRENT_TIMESTAMP")
        fields.append("updated_by = %s")

        values = list(safe_data.values()) + [updated_by]

        query = f"UPDATE email_config SET {', '.join(fields)} WHERE id_config = 1"
        db.execute(query, values)
        db.commit()
        return True

    # ========== CONFIG COMPLETA ==========

    @classmethod
    def get_full_config(cls, db, protocol: str) -> Dict[str, Any]:
        """Merge credenziali .env + settings DB"""
        credentials = cls.get_credentials(protocol)
        settings = cls.get_settings(db, protocol)

        return {
            **settings,
            f'{protocol}_user': credentials['user'],
            f'{protocol}_password': credentials['password']
        }


# Singleton export
email_config = EmailConfigService()
```

#### 3. `services/email/providers/base.py` (~50 righe)

```python
"""Base class per provider email - Estensibile per nuovi provider"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class BaseEmailProvider(ABC):
    """
    Abstract base class per provider email.
    Implementare per aggiungere nuovi provider (Outlook, SendGrid, etc.)
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """Valida configurazione provider-specific"""
        pass

    # ========== IMAP (Ricezione) ==========

    @abstractmethod
    def connect_imap(self) -> Any:
        """Stabilisce connessione IMAP"""
        pass

    @abstractmethod
    def fetch_emails(self, folder: str = 'INBOX',
                     unread_only: bool = True,
                     max_emails: int = 50) -> List[Dict]:
        """Recupera email dalla casella"""
        pass

    @abstractmethod
    def mark_as_read(self, email_uid: str) -> bool:
        """Marca email come letta"""
        pass

    # ========== SMTP (Invio) ==========

    @abstractmethod
    def connect_smtp(self) -> Any:
        """Stabilisce connessione SMTP"""
        pass

    @abstractmethod
    def send_email(self, to: str, subject: str,
                   body_html: str, body_text: Optional[str] = None) -> bool:
        """Invia email"""
        pass

    # ========== TEST ==========

    @abstractmethod
    def test_imap_connection(self) -> Dict[str, Any]:
        """Test connessione IMAP"""
        pass

    @abstractmethod
    def test_smtp_connection(self) -> Dict[str, Any]:
        """Test connessione SMTP"""
        pass
```

#### 4. `services/email/providers/gmail.py` (~120 righe)

```python
"""Gmail provider - Implementazione IMAP/SMTP per Gmail"""

import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional

from .base import BaseEmailProvider


class GmailProvider(BaseEmailProvider):
    """Provider per Gmail (IMAP + SMTP)"""

    def _validate_config(self) -> None:
        required = ['imap_user', 'imap_password']
        for field in required:
            if not self.config.get(field):
                raise ValueError(f"Campo richiesto mancante: {field}")

    # ========== IMAP ==========

    def connect_imap(self) -> imaplib.IMAP4_SSL:
        host = self.config.get('imap_host', 'imap.gmail.com')
        port = self.config.get('imap_port', 993)

        mail = imaplib.IMAP4_SSL(host, port)
        mail.login(
            self.config['imap_user'],
            self.config['imap_password']
        )
        return mail

    def fetch_emails(self, folder: str = 'INBOX',
                     unread_only: bool = True,
                     max_emails: int = 50) -> List[Dict]:
        mail = self.connect_imap()
        try:
            mail.select(folder)

            criteria = 'UNSEEN' if unread_only else 'ALL'
            status, messages = mail.search(None, criteria)

            if not messages[0]:
                return []

            email_ids = messages[0].split()[-max_emails:]
            emails = []

            for eid in email_ids:
                status, msg_data = mail.fetch(eid, '(RFC822)')
                if status == 'OK':
                    emails.append({
                        'uid': eid.decode(),
                        'raw': msg_data[0][1]
                    })

            return emails
        finally:
            mail.logout()

    def mark_as_read(self, email_uid: str) -> bool:
        mail = self.connect_imap()
        try:
            mail.select('INBOX')
            mail.store(email_uid.encode(), '+FLAGS', '\\Seen')
            return True
        finally:
            mail.logout()

    # ========== SMTP ==========

    def connect_smtp(self) -> smtplib.SMTP:
        host = self.config.get('smtp_host', 'smtp.gmail.com')
        port = self.config.get('smtp_port', 587)

        server = smtplib.SMTP(host, port)
        if self.config.get('smtp_use_tls', True):
            server.starttls()

        server.login(
            self.config.get('smtp_user', self.config['imap_user']),
            self.config.get('smtp_password', self.config['imap_password'])
        )
        return server

    def send_email(self, to: str, subject: str,
                   body_html: str, body_text: Optional[str] = None) -> bool:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.config.get('smtp_sender_name', 'TO_EXTRACTOR')} <{self.config.get('smtp_sender_email', self.config['imap_user'])}>"
        msg['To'] = to

        if body_text:
            msg.attach(MIMEText(body_text, 'plain'))
        msg.attach(MIMEText(body_html, 'html'))

        server = self.connect_smtp()
        try:
            server.send_message(msg)
            return True
        finally:
            server.quit()

    # ========== TEST ==========

    def test_imap_connection(self) -> Dict[str, Any]:
        try:
            mail = self.connect_imap()
            mail.select('INBOX')
            status, messages = mail.search(None, 'UNSEEN')
            unread = len(messages[0].split()) if messages[0] else 0
            mail.logout()
            return {
                'success': True,
                'message': f'Connessione OK - {unread} email non lette'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def test_smtp_connection(self) -> Dict[str, Any]:
        try:
            server = self.connect_smtp()
            server.quit()
            return {'success': True, 'message': 'Connessione SMTP OK'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
```

#### 5. `services/email/sender.py` (~60 righe)

```python
"""Email sender - Servizio invio email con logging"""

from typing import Dict, Any, Optional
from datetime import datetime

from .config import email_config
from .providers.gmail import GmailProvider
from .templates import render_template
from .log import log_email_sent, log_email_failed


class EmailSender:
    """Servizio invio email con rate limiting e logging"""

    def __init__(self, db):
        self.db = db
        self._provider = None

    @property
    def provider(self):
        if self._provider is None:
            config = email_config.get_full_config(self.db, 'smtp')
            # Per ora solo Gmail, estendibile
            self._provider = GmailProvider(config)
        return self._provider

    def send(self, to: str, subject: str,
             body_html: str, ticket_id: Optional[int] = None,
             email_type: str = 'generic') -> Dict[str, Any]:
        """
        Invia email con logging.
        Ritorna: {'success': bool, 'log_id': int, 'error': str?}
        """
        try:
            success = self.provider.send_email(to, subject, body_html)

            log_id = log_email_sent(
                self.db,
                destinatario=to,
                oggetto=subject,
                tipo=email_type,
                ticket_id=ticket_id
            )

            return {'success': True, 'log_id': log_id}

        except Exception as e:
            log_id = log_email_failed(
                self.db,
                destinatario=to,
                oggetto=subject,
                tipo=email_type,
                ticket_id=ticket_id,
                errore=str(e)
            )
            return {'success': False, 'log_id': log_id, 'error': str(e)}

    def send_from_template(self, to: str, template_name: str,
                          context: Dict[str, Any],
                          ticket_id: Optional[int] = None) -> Dict[str, Any]:
        """Invia email usando un template predefinito"""
        subject, body = render_template(template_name, context)
        return self.send(to, subject, body, ticket_id, template_name)
```

#### 6. `services/email/templates.py` (~50 righe)

```python
"""Template email HTML - Centralizzati e manutenibili"""

from typing import Tuple, Dict, Any

TEMPLATES = {
    'ticket_creato': {
        'subject': '[Ticket #{id}] Ticket creato',
        'body': '''
        <div style="font-family: Arial, sans-serif; max-width: 600px;">
            <h2 style="color: #2563eb;">Nuovo Ticket Creato</h2>
            <p><strong>ID:</strong> #{id}</p>
            <p><strong>Categoria:</strong> {categoria}</p>
            <p><strong>Oggetto:</strong> {oggetto}</p>
            <p><strong>Pagina:</strong> {pagina_origine}</p>
            <hr style="border: 1px solid #e5e7eb;">
            <p style="color: #6b7280; font-size: 12px;">
                Email automatica da TO_EXTRACTOR
            </p>
        </div>
        '''
    },
    'stato_cambiato': {
        'subject': '[Ticket #{id}] Stato: {stato}',
        'body': '''
        <div style="font-family: Arial, sans-serif; max-width: 600px;">
            <h2 style="color: #2563eb;">Aggiornamento Stato</h2>
            <p><strong>ID:</strong> #{id}</p>
            <p><strong>Nuovo Stato:</strong> <span style="color: #059669;">{stato}</span></p>
            <p><strong>Oggetto:</strong> {oggetto}</p>
            <hr style="border: 1px solid #e5e7eb;">
            <p style="color: #6b7280; font-size: 12px;">
                Email automatica da TO_EXTRACTOR
            </p>
        </div>
        '''
    },
    'nuova_risposta': {
        'subject': '[Ticket #{id}] Nuova risposta',
        'body': '''
        <div style="font-family: Arial, sans-serif; max-width: 600px;">
            <h2 style="color: #2563eb;">Nuova Risposta</h2>
            <p><strong>ID:</strong> #{id}</p>
            <p><strong>Oggetto:</strong> {oggetto}</p>
            <div style="background: #f3f4f6; padding: 16px; border-radius: 8px; margin: 16px 0;">
                {messaggio}
            </div>
            <hr style="border: 1px solid #e5e7eb;">
            <p style="color: #6b7280; font-size: 12px;">
                Email automatica da TO_EXTRACTOR
            </p>
        </div>
        '''
    }
}


def render_template(name: str, context: Dict[str, Any]) -> Tuple[str, str]:
    """
    Renderizza template con contesto.
    Ritorna: (subject, body_html)
    """
    template = TEMPLATES.get(name)
    if not template:
        raise ValueError(f"Template non trovato: {name}")

    subject = template['subject'].format(**context)
    body = template['body'].format(**context)

    return subject, body
```

#### 7. `services/crm/constants.py` (~25 righe)

```python
"""Costanti CRM - Stati, categorie, priorità"""

class TicketStatus:
    APERTO = 'aperto'
    IN_LAVORAZIONE = 'in_lavorazione'
    CHIUSO = 'chiuso'

    ALL = [APERTO, IN_LAVORAZIONE, CHIUSO]

    # Transizioni valide
    TRANSITIONS = {
        APERTO: [IN_LAVORAZIONE, CHIUSO],
        IN_LAVORAZIONE: [APERTO, CHIUSO],
        CHIUSO: [APERTO]  # Riapertura
    }


class TicketCategory:
    SUGGERIMENTO = 'suggerimento'
    BUG_REPORT = 'bug_report'

    ALL = [SUGGERIMENTO, BUG_REPORT]


class TicketPriority:
    BASSA = 'bassa'
    NORMALE = 'normale'
    ALTA = 'alta'

    ALL = [BASSA, NORMALE, ALTA]
```

#### 8. `services/crm/tickets/queries.py` (~60 righe)

```python
"""Query tickets - Operazioni di lettura"""

from typing import List, Dict, Any, Optional


def get_tickets(db, filters: Dict[str, Any] = None,
                user_id: Optional[int] = None,
                is_admin: bool = False) -> List[Dict]:
    """
    Lista ticket con filtri.
    Se non admin, mostra solo ticket dell'utente.
    """
    query = """
        SELECT t.*, o.username as operatore_nome,
               COUNT(m.id_messaggio) as num_messaggi
        FROM crm_tickets t
        LEFT JOIN operatori o ON t.id_operatore = o.id_operatore
        LEFT JOIN crm_messaggi m ON t.id_ticket = m.id_ticket
        WHERE 1=1
    """
    params = []

    if not is_admin and user_id:
        query += " AND t.id_operatore = %s"
        params.append(user_id)

    if filters:
        if filters.get('stato'):
            query += " AND t.stato = %s"
            params.append(filters['stato'])
        if filters.get('categoria'):
            query += " AND t.categoria = %s"
            params.append(filters['categoria'])
        if filters.get('search'):
            query += " AND (t.oggetto ILIKE %s OR t.id_ticket::text = %s)"
            params.extend([f"%{filters['search']}%", filters['search']])

    query += " GROUP BY t.id_ticket, o.username ORDER BY t.created_at DESC"

    rows = db.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_ticket_detail(db, ticket_id: int,
                      user_id: Optional[int] = None,
                      is_admin: bool = False) -> Optional[Dict]:
    """Dettaglio ticket con messaggi"""
    query = """
        SELECT t.*, o.username as operatore_nome
        FROM crm_tickets t
        LEFT JOIN operatori o ON t.id_operatore = o.id_operatore
        WHERE t.id_ticket = %s
    """
    params = [ticket_id]

    if not is_admin and user_id:
        query += " AND t.id_operatore = %s"
        params.append(user_id)

    row = db.execute(query, params).fetchone()
    if not row:
        return None

    ticket = dict(row)

    # Carica messaggi
    msg_query = """
        SELECT m.*, o.username as autore_nome
        FROM crm_messaggi m
        LEFT JOIN operatori o ON m.id_operatore = o.id_operatore
        WHERE m.id_ticket = %s
        ORDER BY m.created_at ASC
    """
    messages = db.execute(msg_query, [ticket_id]).fetchall()
    ticket['messaggi'] = [dict(m) for m in messages]

    return ticket
```

#### 9. `services/crm/tickets/commands.py` (~80 righe)

```python
"""Commands tickets - Operazioni di scrittura"""

from typing import Dict, Any, Optional
from datetime import datetime

from ..constants import TicketStatus


def create_ticket(db, data: Dict[str, Any],
                  user_id: int) -> Dict[str, Any]:
    """Crea nuovo ticket con messaggio iniziale"""
    query = """
        INSERT INTO crm_tickets
        (id_operatore, categoria, oggetto, pagina_origine,
         pagina_dettaglio, email_notifica, priorita)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id_ticket
    """
    params = [
        user_id,
        data['categoria'],
        data['oggetto'],
        data.get('pagina_origine'),
        data.get('pagina_dettaglio'),
        data.get('email_notifica'),
        data.get('priorita', 'normale')
    ]

    result = db.execute(query, params).fetchone()
    ticket_id = result['id_ticket']

    # Inserisci messaggio iniziale
    if data.get('contenuto'):
        msg_query = """
            INSERT INTO crm_messaggi
            (id_ticket, id_operatore, contenuto, is_admin_reply)
            VALUES (%s, %s, %s, FALSE)
        """
        db.execute(msg_query, [ticket_id, user_id, data['contenuto']])

    db.commit()
    return {'id_ticket': ticket_id, 'success': True}


def update_ticket_status(db, ticket_id: int,
                         new_status: str,
                         admin_id: int) -> Dict[str, Any]:
    """Aggiorna stato ticket con validazione transizioni"""
    # Verifica stato corrente
    current = db.execute(
        "SELECT stato FROM crm_tickets WHERE id_ticket = %s",
        [ticket_id]
    ).fetchone()

    if not current:
        return {'success': False, 'error': 'Ticket non trovato'}

    current_status = current['stato']

    # Valida transizione
    valid_transitions = TicketStatus.TRANSITIONS.get(current_status, [])
    if new_status not in valid_transitions:
        return {
            'success': False,
            'error': f'Transizione non valida: {current_status} → {new_status}'
        }

    # Aggiorna
    query = """
        UPDATE crm_tickets
        SET stato = %s, updated_at = CURRENT_TIMESTAMP
    """
    params = [new_status]

    if new_status == TicketStatus.CHIUSO:
        query += ", closed_at = CURRENT_TIMESTAMP, closed_by = %s"
        params.append(admin_id)

    query += " WHERE id_ticket = %s"
    params.append(ticket_id)

    db.execute(query, params)
    db.commit()

    return {'success': True, 'old_status': current_status, 'new_status': new_status}


def add_message(db, ticket_id: int,
                user_id: int, contenuto: str,
                is_admin: bool = False) -> Dict[str, Any]:
    """Aggiunge messaggio a ticket"""
    query = """
        INSERT INTO crm_messaggi
        (id_ticket, id_operatore, contenuto, is_admin_reply)
        VALUES (%s, %s, %s, %s)
        RETURNING id_messaggio
    """
    result = db.execute(query, [ticket_id, user_id, contenuto, is_admin]).fetchone()

    # Aggiorna timestamp ticket
    db.execute(
        "UPDATE crm_tickets SET updated_at = CURRENT_TIMESTAMP WHERE id_ticket = %s",
        [ticket_id]
    )

    db.commit()
    return {'id_messaggio': result['id_messaggio'], 'success': True}
```

---

### Struttura Frontend - Email & CRM

```
frontend/src/
├── api/
│   └── index.js              # Export centralizzato (esistente)
│       ├── emailApi          # 📧 NUOVO - API email
│       └── crmApi            # 🎫 NUOVO - API CRM
│
├── hooks/
│   ├── useEmail.js           # 📧 NUOVO - React Query hooks email
│   └── useCrm.js             # 🎫 NUOVO - React Query hooks CRM
│
├── pages/
│   └── Settings/             # Decomposizione SettingsPage
│       ├── index.jsx         # Container con tabs
│       ├── GeneralTab.jsx    # Impostazioni generali (esistenti)
│       ├── EmailTab/         # 📧 NUOVO - Tab email
│       │   ├── index.jsx     # Container tab
│       │   ├── ImapSection.jsx
│       │   ├── SmtpSection.jsx
│       │   ├── CredentialsAlert.jsx
│       │   └── hooks/useEmailSettings.js
│       └── hooks/useSettingsPage.js
│
├── components/
│   └── CrmChatbot/           # 🎫 NUOVO - Chatbot CRM
│       ├── index.jsx         # Container principale
│       ├── ChatButton.jsx    # FAB apertura chat
│       ├── ChatWindow.jsx    # Finestra chat
│       ├── TicketForm.jsx    # Form nuovo ticket
│       ├── TicketList.jsx    # Lista ticket utente
│       ├── TicketThread.jsx  # Thread messaggi
│       └── hooks/useChatbot.js
```

---

### Integrazione Gmail Monitor (Refactoring Minimo)

Il `gmail_monitor` esistente continuerà a funzionare, ma userà la configurazione unificata.

**Strategia: Adapter Pattern**

```python
# gmail_monitor/config.py - MODIFICA MINIMA

"""
Config Gmail Monitor - Ora legge da EmailConfigService con fallback .env
"""

import os
from pathlib import Path

# Prova import da backend (se disponibile)
_backend_config = None

def _load_backend_config():
    """Lazy load config da backend"""
    global _backend_config
    if _backend_config is not None:
        return _backend_config

    try:
        import sys
        backend_path = Path(__file__).parent.parent / 'backend' / 'app'
        sys.path.insert(0, str(backend_path))

        from services.email.config import email_config
        from database_pg import get_db

        db = get_db()
        _backend_config = email_config.get_full_config(db, 'imap')
        return _backend_config
    except Exception as e:
        print(f"⚠️ Backend config non disponibile, uso .env: {e}")
        return None


class Config:
    """
    Configurazione Gmail Monitor.
    Priorità: Backend DB → .env → Default
    """

    @staticmethod
    def _get(key: str, env_key: str, default=None):
        """Helper: prova backend, poi .env, poi default"""
        backend = _load_backend_config()
        if backend and key in backend:
            return backend[key]
        return os.getenv(env_key, default)

    # ========== CREDENZIALI ==========

    @property
    def GMAIL_EMAIL(self):
        return self._get('imap_user', 'IMAP_USER', '')

    @property
    def GMAIL_APP_PASSWORD(self):
        return self._get('imap_password', 'IMAP_PASSWORD', '')

    # ========== IMPOSTAZIONI IMAP ==========

    @property
    def IMAP_HOST(self):
        return self._get('imap_host', 'IMAP_HOST', 'imap.gmail.com')

    @property
    def IMAP_PORT(self):
        return int(self._get('imap_port', 'IMAP_PORT', 993))

    @property
    def IMAP_FOLDER(self):
        return self._get('imap_folder', 'IMAP_FOLDER', 'INBOX')

    @property
    def CHECK_UNREAD_ONLY(self):
        val = self._get('imap_unread_only', 'CHECK_UNREAD_ONLY', 'true')
        return str(val).lower() == 'true'

    @property
    def MARK_AS_READ(self):
        val = self._get('imap_mark_as_read', 'MARK_AS_READ', 'true')
        return str(val).lower() == 'true'

    @property
    def APPLY_LABEL(self):
        return self._get('imap_apply_label', 'APPLY_LABEL', 'Processed')

    @property
    def SUBJECT_KEYWORDS(self):
        val = self._get('imap_subject_keywords', 'SUBJECT_KEYWORDS', '')
        if isinstance(val, list):
            return val
        return [k.strip() for k in val.split(',') if k.strip()]

    # ... altri campi esistenti rimangono invariati ...


# Singleton
config = Config()
```

**Vantaggi:**
- ✅ Nessun breaking change per gmail_monitor esistente
- ✅ Se backend disponibile, usa config DB
- ✅ Fallback automatico su .env
- ✅ Configurabile da UI Settings senza modificare codice

---

### Riepilogo File Modulari

#### Backend - Nuovi File (~15 file, tutti < 100 righe)

| File | Righe | Responsabilità |
|------|-------|----------------|
| `services/email/__init__.py` | ~10 | Re-exports |
| `services/email/constants.py` | ~30 | Costanti provider |
| `services/email/config.py` | ~80 | Config .env + DB |
| `services/email/providers/base.py` | ~50 | Abstract base class |
| `services/email/providers/gmail.py` | ~120 | Gmail IMAP/SMTP |
| `services/email/sender.py` | ~60 | Servizio invio |
| `services/email/templates.py` | ~50 | Template HTML |
| `services/email/log.py` | ~40 | Logging email |
| `services/crm/__init__.py` | ~10 | Re-exports |
| `services/crm/constants.py` | ~25 | Stati, categorie |
| `services/crm/tickets/queries.py` | ~60 | GET operations |
| `services/crm/tickets/commands.py` | ~80 | CREATE/UPDATE |
| `services/crm/tickets/workflow.py` | ~40 | State machine |
| `services/crm/messages/queries.py` | ~30 | GET messaggi |
| `services/crm/messages/commands.py` | ~30 | INSERT messaggi |
| `services/crm/notifications.py` | ~50 | Invio notifiche |
| `routers/email.py` | ~80 | API endpoints |
| `routers/crm.py` | ~100 | API endpoints |

**Totale Backend: ~18 file, ~950 righe** (media 53 righe/file)

#### Frontend - Nuovi File (~12 file, tutti < 150 righe)

| File | Righe | Responsabilità |
|------|-------|----------------|
| `api/emailApi.js` | ~40 | API client email |
| `api/crmApi.js` | ~50 | API client CRM |
| `hooks/useEmail.js` | ~30 | React Query hooks |
| `hooks/useCrm.js` | ~40 | React Query hooks |
| `pages/Settings/EmailTab/index.jsx` | ~80 | Container tab |
| `pages/Settings/EmailTab/ImapSection.jsx` | ~100 | Form IMAP |
| `pages/Settings/EmailTab/SmtpSection.jsx` | ~100 | Form SMTP |
| `pages/Settings/EmailTab/CredentialsAlert.jsx` | ~40 | Alert .env |
| `components/CrmChatbot/index.jsx` | ~60 | Container chatbot |
| `components/CrmChatbot/ChatWindow.jsx` | ~150 | Finestra chat |
| `components/CrmChatbot/TicketForm.jsx` | ~80 | Form ticket |
| `components/CrmChatbot/TicketThread.jsx` | ~100 | Thread messaggi |

**Totale Frontend: ~12 file, ~870 righe** (media 72 righe/file)

---

### Vantaggi Architettura Modulare

1. **Manutenibilità** - File piccoli (<100 righe), singola responsabilità
2. **Testabilità** - Ogni modulo testabile isolatamente
3. **Estensibilità** - Aggiungere Outlook = nuovo file in `providers/`
4. **Retrocompatibilità** - Gmail Monitor continua a funzionare
5. **Debugging** - Stack trace chiaro, errori localizzati
6. **Onboarding** - Nuovi sviluppatori capiscono rapidamente

---

## Stato: DA IMPLEMENTARE

Data creazione piano: 2026-01-13
Ultima modifica: 2026-01-14 (architettura modulare completa)
