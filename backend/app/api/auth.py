from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, OTPVerify, Token, TokenResponse, RefreshTokenRequest
from app.services.auth import register_organization_and_admin, authenticate_user, generate_otp, store_otp, verify_and_consume_otp
from app.db.session import get_db
from app.core.security import create_access_token, create_refresh_token, store_refresh_token, verify_refresh_token
from app.models.organization import Organization

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    
    # Check if email already exists globally
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
        
    result = await db.execute(select(Organization).where(Organization.name == data.organization_name))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization already registered"
        )

    user = await register_organization_and_admin(
        email=data.email,
        password=data.password,
        org_name=data.organization_name,
        name=data.name,
        db=db  # Pass session to keep transaction atomic
    )

    return {
        "msg": "Organization and admin created",
        "user_id": str(user.id),
        "org_id": str(user.org_id)
    }
    
@router.post("/login", status_code=status.HTTP_202_ACCEPTED)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)): # In Postman, the inputs are in form-data, not raw JSON @@@@@@@@@@@@@@@@@@@@@@@@@@@
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    otp = generate_otp()
    store_otp(data.email, otp, str(user.id), str(user.org_id))
    
    # In real life: send via email/SMS. For now, log for testing.
    print(f"[OTP for {data.email}]: {otp}")  # Remove in prod; use logger
    
    return {"msg": "OTP sent", "email": data.email}

@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(data: OTPVerify, db: AsyncSession = Depends(get_db)):
    user_data = verify_and_consume_otp(data.email, data.otp)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )
    
    # Fetch user to get role
    result = await db.execute(select(User).where(User.id == user_data["user_id"]))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Issue JWT with tenant context
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "org_id": str(user.org_id),
            "role": user.role
        }
    )
    
    # Create and store refresh token
    refresh_token = create_refresh_token()
    await store_refresh_token(db, user.id, refresh_token)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=Token)
async def refresh_access_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):

    user = await verify_refresh_token(db, data.refresh_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Issue new access token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "org_id": str(user.org_id),
            "role": user.role
        }
    )
    
    return {"access_token": access_token, "token_type": "bearer"}