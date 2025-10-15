from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import urllib.parse
import requests

from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, OTPVerify, TokenResponse, GoogleLogin
from app.services.auth import get_or_create_user_from_google, register_organization_and_admin, authenticate_user, generate_otp, store_otp, verify_and_consume_otp
from app.db.session import get_db
from app.core.security import create_access_token, create_refresh_token, require_member, store_refresh_token, verify_refresh_token, revoke_refresh_token, verify_access_token
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
        
        # For cross-origin scenarios (different ports in dev), redirect to success page with tokens
        # Frontend will then call /auth/google/complete to set cookies properly
        redirect_url = (
            f"{settings.FRONTEND_URL}/auth/google/success?"
            f"access_token={access_token}&"
            f"refresh_token={refresh_token}"
        )
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error("Google OAuth2 callback failed", extra={"error": str(e)})
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/login?error=oauth_failed")

@router.post("/login/google")
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
    
    # Set cookies and return success
    response = JSONResponse(content={"message": "Login successful"})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,  # Set to True in production
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,  # Set to True in production
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
        path="/"
    )
    return response

@router.post("/google/complete")
async def google_complete_login(data: TokenResponse, db: AsyncSession = Depends(get_db)):
    """
    Exchange Google OAuth tokens for HttpOnly cookies.
    This handles cross-origin cookie setting after Google redirect.
    """
    logger.info("Completing Google OAuth with cookie exchange")
    
    # Verify the access token is valid
    try:
        payload = verify_access_token(data.access_token)
    except ValueError:
        logger.error("Invalid access token provided")
        raise HTTPException(status_code=400, detail="Invalid access token")
    
    # Set cookies and return success
    response = JSONResponse(content={"message": "Login successful"})
    response.set_cookie(
        key="access_token",
        value=data.access_token,
        httponly=True,
        secure=True,  # Set to True in production
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=data.refresh_token,
        httponly=True,
        secure=True,  # Set to True in production
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
        path="/"
    )
    
    logger.info("Google OAuth cookies set successfully", extra={"user_id": payload.get("sub")})
    return response

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

@router.post("/verify-otp")
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
    
    # Set cookies and return success
    response = JSONResponse(content={"message": "OTP verified successfully"})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,  # Set to True in production
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,  # Set to True in production
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
        path="/"
    )
    return response

@router.post("/refresh")
async def refresh_access_token(request: Request, db: AsyncSession = Depends(get_db)):
    logger.info("Refresh token attempt")
    
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        logger.warning("No refresh token in cookies")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided"
        )

    user = await verify_refresh_token(db, refresh_token)
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
    new_refresh_token = create_refresh_token()
    await store_refresh_token(db, user.id, new_refresh_token)
    
    logger.info("Token refreshed successfully", extra={"user_id": str(user.id)})
    
    # Set new cookies
    response = JSONResponse(content={"message": "Tokens refreshed successfully"})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,  # Set to True in production
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,  # Set to True in production
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
        path="/"
    )
    return response

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_member)):
    logger.info("Logout attempt", extra={"user_id": current_user["user_id"]})
    
    refresh_token = request.cookies.get("refresh_token")
    
    # Revoke the refresh token if it exists
    if refresh_token:
        revoked = await revoke_refresh_token(db, refresh_token)
        if not revoked:
            logger.warning("Logout - token not found", extra={"user_id": current_user["user_id"]})
    
    logger.info("Logout successful", extra={"user_id": current_user["user_id"]})
    
    # Clear cookies
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    return response

@router.get("/me")
async def get_me(current_user: dict = Depends(require_member)):
    logger.info("Get current user", extra={"user_id": current_user["user_id"]})
    return {
        "id": current_user["user_id"],
        "email": current_user.get("email"),
        "role": current_user["role"],
        "org_id": current_user["org_id"]
    }

