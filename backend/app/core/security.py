from fastapi import Depends, HTTPException, status, Request
from passlib.context import CryptContext
import jwt
import secrets
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from uuid import UUID
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import UserRole
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.refresh_token import RefreshToken
from app.core.logging_config import get_logger

logger = get_logger(__name__)


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")  # deprecated: Automatically handles scheme migration

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    try:
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create access token"
        )

def verify_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError as e:
        logger.warning("Invalid access token", extra={"error": str(e)})
        raise ValueError("Invalid token") 

def create_refresh_token() -> str:
    return secrets.token_urlsafe(32)

async def store_refresh_token(db: AsyncSession, user_id: UUID, token: str) -> None:
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)  # 30 days expiry
    
    refresh_token = RefreshToken(
        token=token,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(refresh_token)
    await db.commit()

async def verify_refresh_token(db: AsyncSession, token: str) -> Optional[User]:
    
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == token)
    )
    refresh_token = result.scalars().first()
    
    if not refresh_token:
        return None
    
    if refresh_token.revoked:
        return None
    
    if datetime.now(timezone.utc) > refresh_token.expires_at:
        return None
    
    # Get user
    result = await db.execute(
        select(User).where(User.id == refresh_token.user_id)
    )
    user = result.scalars().first()
    
    return user

async def revoke_refresh_token(db: AsyncSession, token: str) -> bool:
    
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == token)
    )
    refresh_token = result.scalars().first()
    
    if not refresh_token:
        return False
    
    refresh_token.revoked = True
    await db.commit()
    return True 

# Fast token-only auth for most endpoints
async def get_current_user_light(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        logger.warning("No access token in cookies")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        payload = verify_access_token(token)
        return {
            "user_id": payload["sub"],
            "org_id": payload["org_id"],
            "role": payload["role"],
            "email": payload.get("email")
        }
    except ValueError:
        logger.warning("Unauthorized access attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Full database lookup only when needed
async def get_current_user_full(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        logger.warning("No access token in cookies")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        payload = verify_access_token(token)

        result = await db.execute(select(User).where(User.id == payload["sub"]))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
            
        return user
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


def require_admin(current_user: dict = Depends(get_current_user_light)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def require_member(current_user: dict = Depends(get_current_user_light)):
    if current_user["role"] not in (UserRole.ADMIN, UserRole.MEMBER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return current_user