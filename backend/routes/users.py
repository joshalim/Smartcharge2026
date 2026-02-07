"""
User management routes - CRUD operations for users
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, timezone
import bcrypt
import uuid
from io import BytesIO

from sqlalchemy import select, delete
from database import async_session, User, PricingGroup

from routes.auth import get_current_user, require_role, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


# Pydantic Models
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "user"
    rfid_card_number: Optional[str] = None
    rfid_balance: Optional[float] = 0.0


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    rfid_card_number: Optional[str] = None
    rfid_balance: Optional[float] = None
    rfid_status: Optional[str] = None


class UserImportResult(BaseModel):
    imported: int
    skipped: int
    errors: List[dict]


# Routes
@router.get("", response_model=List[UserResponse])
async def get_users(current_user: UserResponse = Depends(require_role("admin"))):
    """Get all users (Admin only)"""
    async with async_session() as session:
        result = await session.execute(
            select(User).order_by(User.created_at.desc())
        )
        users = result.scalars().all()
        
        return [
            UserResponse(
                id=u.id,
                email=u.email,
                name=u.name,
                role=u.role,
                pricing_group_id=u.pricing_group_id,
                rfid_card_number=u.rfid_card_number,
                rfid_balance=u.rfid_balance or 0.0,
                rfid_status=u.rfid_status or "active",
                created_at=u.created_at.isoformat() if u.created_at else None
            )
            for u in users
        ]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Get a single user by ID"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            pricing_group_id=user.pricing_group_id,
            rfid_card_number=user.rfid_card_number,
            rfid_balance=user.rfid_balance or 0.0,
            rfid_status=user.rfid_status or "active",
            created_at=user.created_at.isoformat() if user.created_at else None
        )


@router.post("", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Create a new user (Admin only)"""
    async with async_session() as session:
        # Check if email exists
        result = await session.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        if user_data.role not in ["admin", "user", "viewer"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        
        password_hash = bcrypt.hashpw(
            user_data.password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
        
        new_user = User(
            id=str(uuid.uuid4()),
            email=user_data.email,
            name=user_data.name,
            password_hash=password_hash,
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


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Update user details (Admin only)"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user_data.name:
            user.name = user_data.name
        
        if user_data.email:
            # Check if email is used by another user
            email_check = await session.execute(
                select(User).where(User.email == user_data.email, User.id != user_id)
            )
            if email_check.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Email already in use")
            user.email = user_data.email
        
        if user_data.password:
            user.password_hash = bcrypt.hashpw(
                user_data.password.encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')
        
        await session.commit()
        await session.refresh(user)
        
        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            pricing_group_id=user.pricing_group_id,
            created_at=user.created_at.isoformat() if user.created_at else None
        )


@router.patch("/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: str,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Update user role (Admin only)"""
    if role not in ["admin", "user", "viewer"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.role = role
        await session.commit()
        
        return {"message": "Role updated successfully"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Delete a user (Admin only)"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    async with async_session() as session:
        result = await session.execute(
            delete(User).where(User.id == user_id)
        )
        await session.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"message": "User deleted successfully"}


@router.post("/import", response_model=UserImportResult)
async def import_users(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Import users from Excel/CSV file (Admin only)"""
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="File must be Excel (.xlsx, .xls) or CSV (.csv)")
    
    try:
        import pandas as pd
        contents = await file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(contents))
        else:
            df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")
    
    # Create case-insensitive column mapping
    df_columns_lower = {col.lower().strip(): col for col in df.columns}
    
    # Map columns
    name_col = email_col = role_col = password_col = group_col = None
    
    for col_lower, col_orig in df_columns_lower.items():
        if col_lower in ['name', 'nombre', 'full name', 'fullname']:
            name_col = col_orig
        elif col_lower in ['email', 'correo', 'e-mail', 'email address']:
            email_col = col_orig
        elif col_lower in ['role', 'rol', 'user role']:
            role_col = col_orig
        elif col_lower in ['password', 'contraseña', 'pass']:
            password_col = col_orig
        elif col_lower in ['group', 'grupo', 'pricing group', 'pricing_group']:
            group_col = col_orig
    
    if not name_col:
        raise HTTPException(status_code=400, detail="Missing required column: Name")
    if not email_col:
        raise HTTPException(status_code=400, detail="Missing required column: Email")
    
    # Get all pricing groups for mapping
    async with async_session() as session:
        result = await session.execute(select(PricingGroup))
        groups = {g.name.lower(): g.id for g in result.scalars().all()}
    
    imported = 0
    skipped = 0
    errors = []
    default_password = "ChangeMeNow123!"
    
    import pandas as pd
    
    for idx, row in df.iterrows():
        row_num = idx + 2
        
        name = str(row[name_col]).strip() if not pd.isna(row[name_col]) else ""
        email = str(row[email_col]).strip().lower() if not pd.isna(row[email_col]) else ""
        
        if not name:
            errors.append({"row": row_num, "field": "Name", "message": "Name is required"})
            continue
        
        if not email or '@' not in email:
            errors.append({"row": row_num, "field": "Email", "message": "Valid email is required"})
            continue
        
        async with async_session() as session:
            # Check for existing user
            result = await session.execute(
                select(User).where(User.email == email)
            )
            if result.scalar_one_or_none():
                skipped += 1
                continue
            
            # Get role
            role = "user"
            if role_col and not pd.isna(row.get(role_col)):
                role_value = str(row[role_col]).strip().lower()
                if role_value in ['admin', 'administrador']:
                    role = "admin"
                elif role_value in ['viewer', 'visor', 'view']:
                    role = "viewer"
            
            # Get password
            password = default_password
            if password_col and not pd.isna(row.get(password_col)):
                pwd = str(row[password_col]).strip()
                if len(pwd) >= 6:
                    password = pwd
            
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Get pricing group
            pricing_group_id = None
            if group_col and not pd.isna(row.get(group_col)):
                group_name = str(row[group_col]).strip().lower()
                pricing_group_id = groups.get(group_name)
            
            new_user = User(
                id=str(uuid.uuid4()),
                name=name,
                email=email,
                password_hash=password_hash,
                role=role,
                pricing_group_id=pricing_group_id
            )
            
            try:
                session.add(new_user)
                await session.commit()
                imported += 1
            except Exception as e:
                errors.append({"row": row_num, "field": "Database", "message": str(e)})
    
    return UserImportResult(imported=imported, skipped=skipped, errors=errors)
