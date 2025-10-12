import uuid
from app.models.organization import Organization
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_password_hash

async def register_organization_and_admin(email: str, password: str, org_name: str, db: AsyncSession) -> User:
    # Create organization
    org = Organization(id=uuid.uuid4(), name=org_name)
    db.add(org)
    await db.flush()  # Get org.id which is needed to create a user 
    # Create admin user
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        role="admin",
        org_id=org.id
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
