"""
Charger management routes (MongoDB)
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from database import get_db, Charger

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


def charger_to_response(charger: dict) -> ChargerResponse:
    last_heartbeat = charger.get('last_heartbeat')
    if isinstance(last_heartbeat, datetime):
        last_heartbeat = last_heartbeat.isoformat()
    
    created_at = charger.get('created_at')
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    
    return ChargerResponse(
        id=charger.get('id', ''),
        charger_id=charger.get('charger_id', ''),
        name=charger.get('name', ''),
        location=charger.get('location'),
        status=charger.get('status', 'Available'),
        connectors=charger.get('connectors', []),
        last_heartbeat=last_heartbeat,
        created_at=created_at
    )


# Routes
@router.get("", response_model=List[ChargerResponse])
async def get_chargers(current_user: UserResponse = Depends(get_current_user)):
    """Get all chargers"""
    db = await get_db()
    chargers = await db.chargers.find().sort("created_at", -1).to_list(1000)
    return [charger_to_response(c) for c in chargers]


@router.get("/{charger_id}", response_model=ChargerResponse)
async def get_charger(
    charger_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get a single charger by ID"""
    db = await get_db()
    charger = await db.chargers.find_one({"id": charger_id})
    
    if not charger:
        raise HTTPException(status_code=404, detail="Charger not found")
    
    return charger_to_response(charger)


@router.post("", response_model=ChargerResponse)
async def create_charger(
    charger_data: ChargerCreate,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Create a new charger (Admin only)"""
    db = await get_db()
    
    # Check if charger_id exists
    existing = await db.chargers.find_one({"charger_id": charger_data.charger_id})
    if existing:
        raise HTTPException(status_code=400, detail="Charger ID already exists")
    
    new_charger = Charger(
        id=str(uuid.uuid4()),
        charger_id=charger_data.charger_id,
        name=charger_data.name,
        location=charger_data.location,
        connectors=charger_data.connectors or [],
        status=charger_data.status
    )
    
    await db.chargers.insert_one(new_charger.to_dict())
    
    return charger_to_response(new_charger.to_dict())


@router.patch("/{charger_id}", response_model=ChargerResponse)
async def update_charger(
    charger_id: str,
    charger_data: ChargerUpdate,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Update a charger (Admin only)"""
    db = await get_db()
    charger = await db.chargers.find_one({"id": charger_id})
    
    if not charger:
        raise HTTPException(status_code=404, detail="Charger not found")
    
    update_data = {}
    if charger_data.name is not None:
        update_data['name'] = charger_data.name
    if charger_data.location is not None:
        update_data['location'] = charger_data.location
    if charger_data.connectors is not None:
        update_data['connectors'] = charger_data.connectors
    if charger_data.status is not None:
        update_data['status'] = charger_data.status
    
    if update_data:
        await db.chargers.update_one({"id": charger_id}, {"$set": update_data})
    
    updated = await db.chargers.find_one({"id": charger_id})
    return charger_to_response(updated)


@router.delete("/{charger_id}")
async def delete_charger(
    charger_id: str,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Delete a charger (Admin only)"""
    db = await get_db()
    result = await db.chargers.delete_one({"id": charger_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Charger not found")
    
    return {"message": "Charger deleted successfully"}


@router.post("/{charger_id}/heartbeat")
async def charger_heartbeat(charger_id: str):
    """Update charger heartbeat timestamp"""
    db = await get_db()
    await db.chargers.update_one(
        {"charger_id": charger_id},
        {"$set": {"last_heartbeat": datetime.now(timezone.utc)}}
    )
    return {"currentTime": datetime.now(timezone.utc).isoformat()}
