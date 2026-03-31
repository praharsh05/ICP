#!/usr/bin/env python3
"""
Generate a secure JWT secret key
"""
import secrets

def generate_jwt_secret():
    """Generate a secure random secret key for JWT"""
    secret = secrets.token_urlsafe(32)
    print("Generated JWT Secret Key:")
    print(secret)
    print("\nAdd this to your .env file:")
    print(f"JWT_SECRET_KEY={secret}")
    return secret

if __name__ == "__main__":
    generate_jwt_secret()





