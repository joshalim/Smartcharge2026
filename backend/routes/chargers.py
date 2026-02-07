"""
Charger management routes
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from sqlalchemy import select, delete
from database import async_session, Charger

from routes.auth import get_current_user, require_role, UserResponse

router = APIRouter(prefix="/chargers", tags=["Chargers"])


# Pydantic Models
class ChargerResponse(BaseModel):
    id: str
    charger_id: str
    name: str
    location: Optional[str] = None
    status: str = "Available"
    connectors: Optional[List[str]] = []
    last_heartbeat: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ChargerCreate(BaseModel):
    charger_id: str
    name: str
    location: Optional[str] = None
    connectors: Optional[List[str]] = []
    status: str = "Available"


class ChargerUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    connectors: Optional[List[str]] = None
    status: Optional[str] = None


def charger_to_response(charger: Charger) -> ChargerResponse:
    return ChargerResponse(
        id=charger.id,
        charger_id=charger.charger_id,
        name=charger.name,
        location=charger.location,
        status=charger.status,
        connectors=charger.connectors or [],
        last_heartbeat=charger.last_heartbeat.isoformat() if charger.last_heartbeat else None,
        created_at=charger.created_at.isoformat() if charger.created_at else None
    )


# Routes
@router.get("", response_model=List[ChargerResponse])
async def get_chargers(current_user: UserResponse = Depends(get_current_user)):
    """Get all chargers"""
    async with async_session() as session:
        result = await session.execute(
            select(Charger).order_by(Charger.created_at.desc())
        )
        chargers = result.scalars().all()
        return [charger_to_response(c) for c in chargers]


@router.get("/{charger_id}", response_model=ChargerResponse)
async def get_charger(
    charger_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get a single charger by ID"""
    async with async_session() as session:
        result = await session.execute(
            select(Charger).where(Charger.id == charger_id)
        )
        charger = result.scalar_one_or_none()
        
        if not charger:
            raise HTTPException(status_code=404, detail="Charger not found")
        
        return charger_to_response(charger)


@router.post("", response_model=ChargerResponse)
async def create_charger(
    charger_data: ChargerCreate,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Create a new charger (Admin only)"""
    async with async_session() as session:
        # Check if charger_id exists
        result = await session.execute(
            select(Charger).where(Charger.charger_id == charger_data.charger_id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Charger ID already exists")
        
        new_charger = Charger(
            id=str(uuid.uuid4()),
            charger_id=charger_data.charger_id,
            name=charger_data.name,
            location=charger_data.location,
            connectors=charger_data.connectors or [],
            status=charger_data.status
        )
        session.add(new_charger)
        await session.commit()
        await session.refresh(new_charger)
        
        return charger_to_response(new_charger)


@router.patch("/{charger_id}", response_model=ChargerResponse)
async def update_charger(
    charger_id: str,
    charger_data: ChargerUpdate,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Update a charger (Admin only)"""
    async with async_session() as session:
        result = await session.execute(
            select(Charger).where(Charger.id == charger_id)
        )
        charger = result.scalar_one_or_none()
        
        if not charger:
            raise HTTPException(status_code=404, detail="Charger not found")
        
        if charger_data.name is not None:
            charger.name = charger_data.name
        if charger_data.location is not None:
            charger.location = charger_data.location
        if charger_data.connectors is not None:
            charger.connectors = charger_data.connectors
        if charger_data.status is not None:
            charger.status = charger_data.status
        
        await session.commit()
        await session.refresh(charger)
        
        return charger_to_response(charger)


@router.delete("/{charger_id}")
async def delete_charger(
    charger_id: str,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Delete a charger (Admin only)"""
    async with async_session() as session:
        result = await session.execute(
            delete(Charger).where(Charger.id == charger_id)
        )
        await session.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Charger not found")
        
        return {"message": "Charger deleted successfully"}


@router.post("/{charger_id}/heartbeat")
async def charger_heartbeat(charger_id: str):
    """Update charger heartbeat timestamp"""
    async with async_session() as session:
        result = await session.execute(
            select(Charger).where(Charger.charger_id == charger_id)
        )
        charger = result.scalar_one_or_none()
        
        if charger:
            charger.last_heartbeat = datetime.now(timezone.utc)
            await session.commit()
        
        return {"currentTime": datetime.now(timezone.utc).isoformat()}
