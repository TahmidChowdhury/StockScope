#!/usr/bin/env python3
"""
StockScope Authentication Setup Script
Run this script to generate a secure password hash for your StockScope installation.
Never commit the generated hash to version control.
"""

import getpass
import secrets
from passlib.context import CryptContext

def main():
    print("🔐 StockScope Authentication Setup")
    print("=" * 40)
    
    # Initialize password context
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    print("\n1. Choose your master password:")
    print("   - Use a strong, unique password")
    print("   - This will be the only way to access StockScope")
    print("   - You can change it later by running this script again")
    
    while True:
        password = getpass.getpass("\nEnter your master password: ")
        confirm_password = getpass.getpass("Confirm your master password: ")
        
        if password != confirm_password:
            print("❌ Passwords don't match. Please try again.")
            continue
            
        if len(password) < 8:
            print("❌ Password must be at least 8 characters long.")
            continue
            
        break
    
    print("\n2. Generating secure hash...")
    password_hash = pwd_context.hash(password)
    
    print("\n3. Generate random secret key...")
    secret_key = secrets.token_urlsafe(32)
    
    print("\n" + "="*60)
    print("✅ SETUP COMPLETE - SAVE THESE VALUES SECURELY")
    print("="*60)
    
    print(f"\nAdd these to your .env file or environment variables:")
    print(f"STOCKSCOPE_PASSWORD_HASH={password_hash}")
    print(f"SECRET_KEY={secret_key}")
    
    print(f"\nOr export them in your terminal:")
    print(f"export STOCKSCOPE_PASSWORD_HASH='{password_hash}'")
    print(f"export SECRET_KEY='{secret_key}'")
    
    print("\n" + "="*60)
    print("🚨 SECURITY WARNINGS:")
    print("- NEVER commit these values to git")
    print("- Store them securely (password manager, etc.)")
    print("- Don't share them with anyone")
    print("- The password hash is specific to your chosen password")
    print("="*60)
    
    # Verify the hash works
    if pwd_context.verify(password, password_hash):
        print("\n✅ Password hash verification successful!")
    else:
        print("\n❌ Password hash verification failed!")
        
    print(f"\nYour login password is: {password}")
    print("Remember this password - you'll need it to access StockScope!")

if __name__ == "__main__":
    main()