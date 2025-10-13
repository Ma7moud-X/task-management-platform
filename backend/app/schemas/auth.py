from pydantic import BaseModel, EmailStr, Field
from enum import Enum
from typing import Optional

class UserRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"
    
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    organization_name: str
    name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str