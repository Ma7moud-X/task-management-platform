from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.schemas.auth import UserRegister
from app.services.auth import register_organization_and_admin
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    
    # Check if email already exists globally
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user = await register_organization_and_admin(
        email=data.email,
        password=data.password,
        org_name=data.organization_name,
        db=db  # Pass session to keep transaction atomic
    )

    return {
        "msg": "Organization and admin created",
        "user_id": str(user.id),
        "org_id": str(user.org_id)
    }