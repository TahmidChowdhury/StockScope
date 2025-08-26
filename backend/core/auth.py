"""Authentication dependencies for API routes."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import secrets

security = HTTPBearer()

# Simple password-based auth for now
API_PASSWORD = os.getenv("API_PASSWORD", "defaultpassword123")

def verify_password_dependency(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify API password from Authorization header."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Simple password check (in production, use proper JWT/OAuth)
    if not secrets.compare_digest(credentials.credentials, API_PASSWORD):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return "authenticated_user"