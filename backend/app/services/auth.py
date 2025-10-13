import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.user import User
from app.core.security import get_password_hash, verify_password
from app.schemas.auth import UserRole

async def register_organization_and_admin(email: str, password: str, org_name: str, db: AsyncSession, name: Optional[str] = None) -> User:
    # Create organization
    org = Organization(id=uuid.uuid4(), name=org_name)
    db.add(org)
    await db.flush()  # Get org.id which is needed to create a user 
    # Create admin user
    # Use provided name or extract from email (part before @)
    user_name = name if name else email.split('@')[0]
    user = User(
        email=email,
        name=user_name,
        hashed_password=get_password_hash(password),
        role=UserRole.ADMIN,
        org_id=org.id
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

# In-memory OTP store (replace with Redis in production)
OTP_STORE: dict[str, dict] = {}

def generate_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"  # 6-digit zero-padded

def store_otp(email: str, otp: str, user_id: str, org_id: str) -> None:
    OTP_STORE[email] = {
        "otp": otp,
        "user_id": user_id,
        "org_id": org_id,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5)
    }

def verify_and_consume_otp(email: str, otp: str) -> Optional[dict]:
    record = OTP_STORE.get(email)
    if not record:
        return None
    if record["otp"] != otp:
        return None
    if datetime.now(timezone.utc) > record["expires_at"]:
        del OTP_STORE[email]
        return None
    # Consume OTP (one-time use)
    user_data = {
        "user_id": record["user_id"],
        "org_id": record["org_id"]
    }
    del OTP_STORE[email]
    return user_data

