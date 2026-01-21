"""Pricing Groups routes"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
import uuid
from datetime import datetime, timezone
from database import db
from models import PricingGroup, PricingGroupCreate, PricingGroupUpdate, UserRole
from utils.auth import get_current_user, require_role

router = APIRouter(prefix="/pricing-groups", tags=["Pricing Groups"])

@router.get("", response_model=List[PricingGroup])
async def get_pricing_groups(current_user = Depends(require_role(UserRole.ADMIN))):
    """Get all pricing groups"""
    groups = await db.pricing_groups.find({}, {"_id": 0}).to_list(100)
    return [PricingGroup(**g) for g in groups]

@router.get("/{group_id}", response_model=PricingGroup)
async def get_pricing_group(
    group_id: str,
    current_user = Depends(require_role(UserRole.ADMIN))
):
    """Get a single pricing group"""
    group = await db.pricing_groups.find_one({"id": group_id}, {"_id": 0})
    if not group:
        raise HTTPException(status_code=404, detail="Pricing group not found")
    return PricingGroup(**group)

@router.post("", response_model=PricingGroup)
async def create_pricing_group(
    group_data: PricingGroupCreate,
    current_user = Depends(require_role(UserRole.ADMIN))
):
    """Create a new pricing group"""
    # Check if name already exists
    existing = await db.pricing_groups.find_one({"name": group_data.name})
    if existing:
        raise HTTPException(status_code=400, detail="Group name already exists")
    
    group = {
        "id": str(uuid.uuid4()),
        "name": group_data.name,
        "description": group_data.description,
        "connector_pricing": group_data.connector_pricing.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.pricing_groups.insert_one(group)
    return PricingGroup(**{k: v for k, v in group.items() if k != "_id"})

@router.patch("/{group_id}", response_model=PricingGroup)
async def update_pricing_group(
    group_id: str,
    update_data: PricingGroupUpdate,
    current_user = Depends(require_role(UserRole.ADMIN))
):
    """Update a pricing group"""
    existing = await db.pricing_groups.find_one({"id": group_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Pricing group not found")
    
    update_dict = {}
    
    if update_data.name:
        # Check for duplicate name
        name_check = await db.pricing_groups.find_one({"name": update_data.name, "id": {"$ne": group_id}})
        if name_check:
            raise HTTPException(status_code=400, detail="Group name already exists")
        update_dict["name"] = update_data.name
    
    if update_data.description is not None:
        update_dict["description"] = update_data.description
    
    if update_data.connector_pricing:
        update_dict["connector_pricing"] = update_data.connector_pricing.model_dump()
    
    if update_dict:
        update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.pricing_groups.update_one({"id": group_id}, {"$set": update_dict})
        existing.update(update_dict)
    
    return PricingGroup(**existing)

@router.delete("/{group_id}")
async def delete_pricing_group(
    group_id: str,
    current_user = Depends(require_role(UserRole.ADMIN))
):
    """Delete a pricing group"""
    # Check if group has users
    user_count = await db.users.count_documents({"pricing_group_id": group_id})
    if user_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete group with {user_count} assigned users. Reassign users first."
        )
    
    result = await db.pricing_groups.delete_one({"id": group_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Pricing group not found")
    return {"message": "Pricing group deleted successfully"}

@router.get("/{group_id}/users")
async def get_group_users(
    group_id: str,
    current_user = Depends(require_role(UserRole.ADMIN))
):
    """Get all users in a pricing group"""
    users = await db.users.find(
        {"pricing_group_id": group_id}, 
        {"_id": 0, "password_hash": 0}
    ).to_list(500)
    return users

@router.post("/{group_id}/users/{user_id}")
async def assign_user_to_group(
    group_id: str,
    user_id: str,
    current_user = Depends(require_role(UserRole.ADMIN))
):
    """Assign a user to a pricing group"""
    # Verify group exists
    group = await db.pricing_groups.find_one({"id": group_id})
    if not group:
        raise HTTPException(status_code=404, detail="Pricing group not found")
    
    # Verify user exists
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.users.update_one({"id": user_id}, {"$set": {"pricing_group_id": group_id}})
    return {"message": f"User assigned to group '{group['name']}'"}

@router.delete("/{group_id}/users/{user_id}")
async def remove_user_from_group(
    group_id: str,
    user_id: str,
    current_user = Depends(require_role(UserRole.ADMIN))
):
    """Remove a user from a pricing group"""
    result = await db.users.update_one(
        {"id": user_id, "pricing_group_id": group_id},
        {"$unset": {"pricing_group_id": ""}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found in this group")
    return {"message": "User removed from group"}
