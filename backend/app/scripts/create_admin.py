#!/usr/bin/env python3
# =============================================================================
# SERV.O v6.2 - CREATE ADMIN SCRIPT
# =============================================================================
# Script per creare l'utente admin iniziale.
# Eseguire una sola volta dopo la migrazione del database.
#
# USO:
#   python -m app.scripts.create_admin
#   python -m app.scripts.create_admin --username admin --password MySecurePass123
# =============================================================================

import sys
import os
import argparse

# Aggiungi path per import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def create_initial_admin(
    username: str = "admin",
    password: str = "admin123",
    nome: str = "Amministratore",
    cognome: str = "Sistema",
    email: str = None
) -> bool:
    """
    Crea l'utente admin iniziale.
    
    Args:
        username: Username admin (default: "admin")
        password: Password admin (default: "admin123")
        nome: Nome admin
        cognome: Cognome admin
        email: Email admin (opzionale)
        
    Returns:
        True se creato con successo, False se già esiste
    """
    # Import lazy per evitare problemi di path
    from app.database_pg import get_db
    from app.auth.security import hash_password
    
    db = get_db()
    
    # Verifica se esiste già un admin (escludendo SYSTEM)
    existing = db.execute(
        "SELECT id_operatore, username FROM OPERATORI WHERE ruolo = 'admin' AND username != 'SYSTEM'"
    ).fetchone()
    
    if existing:
        print(f"⚠️  Esiste già un admin: {existing['username']} (id={existing['id_operatore']})")
        return False
    
    # Verifica se username esiste già
    existing_username = db.execute(
        "SELECT id_operatore FROM OPERATORI WHERE LOWER(username) = LOWER(?)",
        (username,)
    ).fetchone()
    
    if existing_username:
        print(f"⚠️  Username '{username}' già esistente (id={existing_username['id_operatore']})")
        return False
    
    # Hash password
    password_hash = hash_password(password)
    
    # Inserisci admin
    cursor = db.execute(
        """
        INSERT INTO OPERATORI (
            username, password_hash, nome, cognome, email,
            ruolo, attivo, created_by_operatore, data_creazione, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'admin', 1, NULL, datetime('now'), datetime('now'))
        """,
        (username.lower(), password_hash, nome, cognome, email)
    )
    db.commit()
    
    admin_id = cursor.lastrowid
    
    print("=" * 60)
    print("✅ ADMIN CREATO CON SUCCESSO!")
    print("=" * 60)
    print(f"   ID:       {admin_id}")
    print(f"   Username: {username}")
    print(f"   Password: {password}")
    print(f"   Nome:     {nome} {cognome}")
    if email:
        print(f"   Email:    {email}")
    print("=" * 60)
    print("")
    print("⚠️  IMPORTANTE: Cambiare la password dopo il primo accesso!")
    print("")
    
    return True


def main():
    """Entry point per esecuzione da linea di comando."""
    parser = argparse.ArgumentParser(
        description="Crea utente admin iniziale per SERV.O",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python -m app.scripts.create_admin
  python -m app.scripts.create_admin --username myadmin --password SecurePass123
  python -m app.scripts.create_admin --nome Mario --cognome Rossi --email admin@example.com
        """
    )
    
    parser.add_argument(
        "--username", 
        default="admin", 
        help="Username admin (default: admin)"
    )
    parser.add_argument(
        "--password", 
        default="admin123", 
        help="Password admin (default: admin123)"
    )
    parser.add_argument(
        "--nome", 
        default="Amministratore", 
        help="Nome admin (default: Amministratore)"
    )
    parser.add_argument(
        "--cognome", 
        default="Sistema", 
        help="Cognome admin (default: Sistema)"
    )
    parser.add_argument(
        "--email", 
        default=None, 
        help="Email admin (opzionale)"
    )
    
    args = parser.parse_args()
    
    # Validazione base
    if len(args.password) < 8:
        print("❌ Errore: la password deve essere almeno 8 caratteri")
        sys.exit(1)
    
    if len(args.username) < 3:
        print("❌ Errore: username deve essere almeno 3 caratteri")
        sys.exit(1)
    
    try:
        success = create_initial_admin(
            username=args.username,
            password=args.password,
            nome=args.nome,
            cognome=args.cognome,
            email=args.email
        )
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Errore durante la creazione admin: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
