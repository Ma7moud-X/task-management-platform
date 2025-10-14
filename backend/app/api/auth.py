from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, OTPVerify, Token, TokenResponse, RefreshTokenRequest, GoogleLogin
from app.services.auth import get_or_create_user_from_google, register_organization_and_admin, authenticate_user, generate_otp, store_otp, verify_and_consume_otp
from app.db.session import get_db
from app.core.security import create_access_token, create_refresh_token, store_refresh_token, verify_refresh_token
from app.models.organization import Organization
from app.core.auth_google import verify_google_id_token
from app.core.email import send_otp_email
from app.core.logging_config import get_logger

logger = get_logger(__name__)


router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    logger.info("Registration attempt", extra={"email": data.email, "org_name": data.organization_name})
    
    # Check if email already exists globally
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalars().first():
        logger.warning("Registration failed - email exists", extra={"email": data.email})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
        
    result = await db.execute(select(Organization).where(Organization.name == data.organization_name))
    if result.scalars().first():
        logger.warning("Registration failed - org exists", extra={"org_name": data.organization_name})
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

    logger.info("Registration successful", extra={"user_id": str(user.id), "org_id": str(user.org_id)})
    return {
        "msg": "Organization and admin created",
        "user_id": str(user.id),
        "org_id": str(user.org_id)
    }    

@router.post("/login/google", response_model=TokenResponse)  # Change from Token to TokenResponse
async def google_login(data: GoogleLogin, db: AsyncSession = Depends(get_db)):
    logger.info("Google login attempt")
    
    try:
        # Verify Google ID token
        google_payload = verify_google_id_token(data.id_token)
        email = google_payload["email"]
        name = google_payload.get("name", email.split("@")[0])
        logger.info("Google token verified", extra={"email": email})
    except ValueError as e:
        logger.error("Google token verification failed", extra={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))

    try:
        user = await get_or_create_user_from_google(db, email, name)
        logger.info("Google login successful", extra={"user_id": str(user.id), "email": email})
    except ValueError as e:
        logger.error("Google login failed", extra={"error": str(e), "email": email})
        raise HTTPException(status_code=400, detail=str(e))

    # Issue JWT
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "org_id": str(user.org_id),
            "role": user.role.value  # Convert enum to string value
        }
    )
    
    refresh_token = create_refresh_token()
    await store_refresh_token(db, user.id, refresh_token)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/login", status_code=status.HTTP_202_ACCEPTED)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    logger.info("Login attempt", extra={"email": data.email})
    
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        logger.warning("Login failed - invalid credentials", extra={"email": data.email})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    otp = generate_otp()
    await store_otp(data.email, otp, str(user.id), str(user.org_id))
    
    send_otp_email(data.email, otp)

    logger.info("OTP sent", extra={"email": data.email, "otp": otp})
    
    return {"msg": "OTP sent", "email": data.email}

@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(data: OTPVerify, db: AsyncSession = Depends(get_db)):
    logger.info("OTP verification attempt", extra={"email": data.email})
    
    user_data = await verify_and_consume_otp(data.email, data.otp)
    if not user_data:
        logger.warning("OTP verification failed", extra={"email": data.email})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )
    
    # Fetch user to get role
    result = await db.execute(select(User).where(User.id == user_data["user_id"]))
    user = result.scalars().first()
    if not user:
        logger.error("User not found after OTP verification", extra={"user_id": user_data["user_id"]})
        raise HTTPException(status_code=404, detail="User not found")
    
    # Issue JWT with tenant context
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "org_id": str(user.org_id),
            "role": user.role.value  # Convert enum to string value
        }
    )
    
    # Create and store refresh token
    refresh_token = create_refresh_token()
    await store_refresh_token(db, user.id, refresh_token)
    
    logger.info("OTP verification successful", extra={"user_id": str(user.id)})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    logger.info("Refresh token attempt")

    user = await verify_refresh_token(db, data.refresh_token)
    if not user:
        logger.warning("Refresh token verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Issue new access token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "org_id": str(user.org_id),
            "role": user.role.value  # Convert enum to string value
        }
    )
    
    # Create and store new refresh token
    refresh_token = create_refresh_token()
    await store_refresh_token(db, user.id, refresh_token)
    
    logger.info("Token refreshed successfully", extra={"user_id": str(user.id)})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

