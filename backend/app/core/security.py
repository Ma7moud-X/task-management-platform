from fastapi import Depends, HTTPException, status
from passlib.context import CryptContext
import jwt
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from app.core.config import settings
from app.models.user import User, UserRole
from app.db.session import get_db
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto") # deprecated: Automatically handles scheme migration

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
    except jwt.PyJWTError:
        raise ValueError("Invalid token") 

# Fast token-only auth for most endpoints
async def get_current_user_light(cred: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    try:
        payload = verify_access_token(cred.credentials)
        return {
            "user_id": payload["sub"],
            "org_id": payload["org_id"],
            "role": payload["role"]
        }
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Full database lookup only when needed
async def get_current_user_full(cred: HTTPAuthorizationCredentials = Depends(HTTPBearer()), db: AsyncSession = Depends(get_db)):
    try:
        payload = verify_access_token(cred.credentials)

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