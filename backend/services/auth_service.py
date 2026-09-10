import hmac
import hashlib
import time
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.config import settings

security = HTTPBearer(auto_error=False)

TOKEN_EXPIRY_SECONDS = 86400 * 30  # 30 days validity

def create_developer_token(developer_name: str = None) -> str:
    """Generate a secure cryptographic HMAC token for the developer."""
    name = developer_name or settings.DEVELOPER_NAME
    ts = str(int(time.time()))
    payload = f"{ts}:{name}:{settings.DEVELOPER_PASSWORD}"
    sig = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"{ts}.{name}.{sig}"

def verify_developer_token(token: Optional[str]) -> bool:
    """Verify cryptographic developer token integrity and expiration."""
    if not token:
        return False
    
    parts = token.strip().split(".")
    if len(parts) != 3:
        return False
    
    ts_str, name, sig = parts
    try:
        ts = int(ts_str)
    except ValueError:
        return False
    
    # Check expiration
    if time.time() - ts > TOKEN_EXPIRY_SECONDS:
        return False
    
    # Check expected signature
    payload = f"{ts}:{name}:{settings.DEVELOPER_PASSWORD}"
    expected_sig = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(sig, expected_sig)

async def require_developer(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> str:
    """Dependency that enforces developer-only authentication."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Developer authentication required. Please log in with the developer key.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    if not verify_developer_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired developer session. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return settings.DEVELOPER_NAME
