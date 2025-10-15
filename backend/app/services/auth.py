import json
import uuid
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.user import User
from app.core.security import get_password_hash, verify_password
from app.schemas.auth import UserRole
from app.db.redis import redis_client

async def register_organization_and_admin(email: str, password: str, org_name: str, db: AsyncSession, name: Optional[str] = None) -> User:
    # Extract domain from email
    domain = email.split('@')[1]
    
    # Check if organization with this domain already exists
    result = await db.execute(select(Organization).where(Organization.domain == domain))
    existing_org = result.scalars().first()
    
    # Use provided name or extract from email (part before @)
    user_name = name if name else email.split('@')[0]
    
    if existing_org:
        # Organization exists, create user as MEMBER
        user = User(
            email=email,
            name=user_name,
            hashed_password=get_password_hash(password),
            role=UserRole.MEMBER,
            org_id=existing_org.id
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    # Organization doesn't exist, create it and make user ADMIN
    org = Organization(id=uuid.uuid4(), name=org_name, domain=domain)
    db.add(org)
    await db.flush()  # Get org.id which is needed to create a user
    
    # Create admin user
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

def generate_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"  # 6-digit zero-padded

async def store_otp(email: str, otp: str, user_id: str, org_id: str) -> None:
    key = f"otp:{email}"
    data = {
        "otp": otp,
        "user_id": user_id,
        "org_id": org_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    # Store for 5 minutes
    await redis_client.setex(key, 300, json.dumps(data))
    
async def verify_and_consume_otp(email: str, otp: str) -> Optional[dict]:
    key = f"otp:{email}"
    data_str = await redis_client.get(key)
    if not data_str:
        return None

    data = json.loads(data_str)
    if data["otp"] != otp:
        return None

    # Delete immediately (one-time use)
    await redis_client.delete(key)
    return {
        "user_id": data["user_id"],
        "org_id": data["org_id"]
    }


async def get_or_create_user_from_google(db: AsyncSession, email: str, name: str) -> User:
    
    # Check if user exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        return user

    domain = email.split("@")[-1]
    
    # Check if organization with this domain exists
    org_result = await db.execute(
        select(Organization).where(Organization.domain == domain)
    )
    org = org_result.scalars().first()
    
    if org:
        # Organization exists, create user as MEMBER
        new_user = User(
            email=email,
            hashed_password="",  # No password for Google users
            name=name,
            role=UserRole.MEMBER,
            org_id=org.id
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user
    
    # Organization doesn't exist, create it and make user ADMIN
    org_name = domain.split('.')[0].capitalize()
    
    new_org = Organization(
        id=uuid.uuid4(),
        name=org_name,
        domain=domain
    )
    db.add(new_org)
    await db.flush()  # Get org.id
    
    # Create admin user
    new_user = User(
        email=email,
        hashed_password="",  # No password for Google users
        name=name,
        role=UserRole.ADMIN,
        org_id=new_org.id
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
