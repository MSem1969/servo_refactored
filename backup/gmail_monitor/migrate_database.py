import sqlite3

DB_PATH = '/home/jobseminara/USABILITA_FRONTEND-v6.1/backend/to_extractor.db'

print("MIGRAZIONE DATABASE")
print("=" * 60)
print(f"Database: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
db = conn.cursor()

exists = db.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name='EMAIL_ACQUISIZIONI'").fetchone()

if exists:
    print("Tabella EMAIL_ACQUISIZIONI gia esistente")
else:
    print("Creazione tabella EMAIL_ACQUISIZIONI...")

    db.execute("""CREATE TABLE EMAIL_ACQUISIZIONI (
        id_email INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT UNIQUE NOT NULL,
        gmail_id TEXT,
        subject TEXT,
        sender_email TEXT NOT NULL,
        sender_name TEXT,
        received_date TEXT NOT NULL,
        attachment_filename TEXT NOT NULL,
        attachment_size INTEGER,
        attachment_hash TEXT NOT NULL,
        id_acquisizione INTEGER,
        stato TEXT DEFAULT 'DA_PROCESSARE',
        data_elaborazione TEXT,
        errore_messaggio TEXT,
        num_retry INTEGER DEFAULT 0,
        label_applicata TEXT,
        marcata_come_letta INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""")

    db.execute(
        "CREATE INDEX idx_email_message_id ON EMAIL_ACQUISIZIONI(message_id)")
    db.execute(
        "CREATE INDEX idx_email_hash ON EMAIL_ACQUISIZIONI(attachment_hash)")
    db.execute("CREATE INDEX idx_email_stato ON EMAIL_ACQUISIZIONI(stato)")

    conn.commit()
    print("OK tabella creata!")

conn.close()
print("=" * 60)
print("COMPLETATO")
