"""
Authentication routes - Login, Register, Token validation
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import uuid
import os

from sqlalchemy import select
from database import async_session, User

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours


# Pydantic Models
class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "user"


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    phone: Optional[str] = None
    pricing_group_id: Optional[str] = None
    rfid_card_number: Optional[str] = None
    rfid_balance: Optional[float] = 0.0
    rfid_status: Optional[str] = "active"
    placa: Optional[str] = None
    whatsapp_enabled: Optional[bool] = True
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
    """Validate JWT token and return current user"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user is None:
                raise HTTPException(status_code=401, detail="User not found")
            
            return UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
                pricing_group_id=user.pricing_group_id,
                created_at=user.created_at.isoformat() if user.created_at else None
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(*allowed_roles: str):
    """Dependency for role-based access control"""
    async def role_checker(current_user: UserResponse = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker


# Routes
@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login with email and password"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.email == credentials.email)
        )
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(credentials.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        access_token = create_access_token({"sub": user.id})
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
                pricing_group_id=user.pricing_group_id,
                created_at=user.created_at.isoformat() if user.created_at else None
            )
        )


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister):
    """Register a new user"""
    async with async_session() as session:
        # Check if email exists
        result = await session.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user
        new_user = User(
            id=str(uuid.uuid4()),
            email=user_data.email,
            name=user_data.name,
            password_hash=hash_password(user_data.password),
            role=user_data.role
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        
        return UserResponse(
            id=new_user.id,
            email=new_user.email,
            name=new_user.name,
            role=new_user.role,
            pricing_group_id=new_user.pricing_group_id,
            created_at=new_user.created_at.isoformat() if new_user.created_at else None
        )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """Get current user info"""
    return current_user


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Change password for the current user"""
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == current_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not verify_password(request.current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        user.password_hash = hash_password(request.new_password)
        await session.commit()
        
        return {"message": "Password changed successfully"}
