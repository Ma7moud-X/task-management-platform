from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import urllib.parse
import requests

from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, OTPVerify, Token, TokenResponse, RefreshTokenRequest, GoogleLogin
from app.services.auth import get_or_create_user_from_google, register_organization_and_admin, authenticate_user, generate_otp, store_otp, verify_and_consume_otp
from app.db.session import get_db
from app.core.security import create_access_token, create_refresh_token, require_member, store_refresh_token, verify_refresh_token, revoke_refresh_token
from app.models.organization import Organization
from app.core.auth_google import verify_google_id_token
from app.core.email import send_otp_email
from app.core.logging_config import get_logger
from app.core.config import settings

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

    user = await register_organization_and_admin(
        email=data.email,
        password=data.password,
        org_name=data.organization_name,
        name=data.name,
        db=db  # Pass session to keep transaction atomic
    )

    logger.info("Registration successful", extra={"user_id": str(user.id), "org_id": str(user.org_id), "role": user.role.value})
    
    # Return different message based on role
    if user.role.value == "admin":
        message = "Organization and admin created"
    else:
        message = "User registered as member of existing organization"
    
    return {
        "msg": message,
        "user_id": str(user.id),
        "org_id": str(user.org_id),
        "role": user.role.value
    }    

@router.get("/login/google")
async def google_oauth_login():
    """Initiate Google OAuth2 flow by redirecting to Google's authorization page"""
    logger.info("Initiating Google OAuth2 flow")
    
    redirect_uri = f"{settings.BASE_URL}/auth/google/callback"
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
        "response_type=code&"
        "scope=openid%20email%20profile&"
        "access_type=offline&"
        "prompt=select_account"
    )
    
    return RedirectResponse(url=google_auth_url)

@router.get("/google/callback")
async def google_oauth_callback(code: str, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth2 callback and exchange code for tokens"""
    logger.info("Processing Google OAuth2 callback")
    
    try:
        # Exchange authorization code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": f"{settings.BASE_URL}/auth/google/callback",
            "grant_type": "authorization_code"
        }
        
        token_response = requests.post(token_url, data=token_data)
        if token_response.status_code != 200:
            logger.error("Failed to exchange code for tokens", extra={"error": token_response.text})
            return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/login?error=oauth_failed")
        
        tokens = token_response.json()
        id_token = tokens.get("id_token")
        
        # Verify ID token
        google_payload = verify_google_id_token(id_token)
        email = google_payload["email"]
        name = google_payload.get("name", email.split("@")[0])
        logger.info("Google token verified", extra={"email": email})
        
        # Get or create user
        user = await get_or_create_user_from_google(db, email, name)
        logger.info("Google login successful", extra={"user_id": str(user.id), "email": email})
        
        # Create JWT tokens
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "org_id": str(user.org_id),
                "role": user.role.value
            }
        )
        
        refresh_token = create_refresh_token()
        await store_refresh_token(db, user.id, refresh_token)
        
        # Redirect to frontend with tokens
        redirect_url = (
            f"{settings.FRONTEND_URL}/auth/google/success?"
            f"access_token={access_token}&"
            f"refresh_token={refresh_token}"
        )
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error("Google OAuth2 callback failed", extra={"error": str(e)})
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/login?error=oauth_failed")

@router.post("/login/google", response_model=TokenResponse)
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

    logger.info("OTP sent", extra={"email": data.email})
    
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

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_member)):
    logger.info("Logout attempt", extra={"user_id": current_user["user_id"]})
    
    # Revoke the refresh token
    revoked = await revoke_refresh_token(db, data.refresh_token)
    
    if not revoked:
        logger.warning("Logout failed - token not found", extra={"user_id": current_user["user_id"]})
        # Don't throw error, just return success (token might already be invalid)
    
    logger.info("Logout successful", extra={"user_id": current_user["user_id"]})
    return {"msg": "Logged out successfully"}
