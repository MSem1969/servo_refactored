#!/usr/bin/env python3
"""Crea utente admin per primo accesso."""
import bcrypt
from app.database_pg import get_db

password = b"admin123"
salt = bcrypt.gensalt()
h = bcrypt.hashpw(password, salt).decode('utf-8')

db = get_db()
db.execute("DELETE FROM operatori WHERE username = %s", ("admin",))
db.execute(
    "INSERT INTO operatori (username, password_hash, nome, cognome, ruolo, attivo) VALUES (%s, %s, %s, %s, %s, %s)",
    ("admin", h, "Admin", "Sistema", "admin", True)
)
db.commit()
print("Admin creato! Login: admin / admin123")
