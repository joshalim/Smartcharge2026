"""
Pricing rules and pricing groups routes
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from sqlalchemy import select, delete, func
from database import async_session, PricingRule, PricingGroup, User

from routes.auth import get_current_user, require_role, UserResponse

router = APIRouter(tags=["Pricing"])


# Pydantic Models
class ConnectorPricing(BaseModel):
    CCS2: float = 2500.0
    CHADEMO: float = 2000.0
    J1772: float = 1500.0


class PricingRuleResponse(BaseModel):
    id: str
    account: str
    connector: str
    connector_type: Optional[str] = None
    price_per_kwh: float
    created_at: str

    class Config:
        from_attributes = True


class PricingRuleCreate(BaseModel):
    account: str
    connector: str
    price_per_kwh: float


class PricingGroupResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    connector_pricing: dict
    user_count: int = 0
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class PricingGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    connector_pricing: ConnectorPricing


class PricingGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    connector_pricing: Optional[ConnectorPricing] = None


# Pricing Rules Routes
@router.get("/pricing", response_model=List[PricingRuleResponse])
async def get_pricing_rules(current_user: UserResponse = Depends(require_role("admin"))):
    """Get all pricing rules"""
    async with async_session() as session:
        result = await session.execute(
            select(PricingRule).order_by(PricingRule.account)
        )
        rules = result.scalars().all()
        
        return [
            PricingRuleResponse(
                id=r.id,
                account=r.account,
                connector=r.connector,
                connector_type=r.connector_type,
                price_per_kwh=r.price_per_kwh,
                created_at=r.created_at.isoformat() if r.created_at else ""
            )
            for r in rules
        ]


@router.post("/pricing", response_model=PricingRuleResponse)
async def create_pricing_rule(
    rule_data: PricingRuleCreate,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Create or update a pricing rule"""
    async with async_session() as session:
        # Check if rule exists
        result = await session.execute(
            select(PricingRule).where(
                PricingRule.account == rule_data.account,
                PricingRule.connector == rule_data.connector
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.price_per_kwh = rule_data.price_per_kwh
            await session.commit()
            await session.refresh(existing)
            rule = existing
        else:
            rule = PricingRule(
                id=str(uuid.uuid4()),
                account=rule_data.account,
                connector=rule_data.connector,
                price_per_kwh=rule_data.price_per_kwh
            )
            session.add(rule)
            await session.commit()
            await session.refresh(rule)
        
        return PricingRuleResponse(
            id=rule.id,
            account=rule.account,
            connector=rule.connector,
            connector_type=rule.connector_type,
            price_per_kwh=rule.price_per_kwh,
            created_at=rule.created_at.isoformat() if rule.created_at else ""
        )


@router.delete("/pricing/{pricing_id}")
async def delete_pricing_rule(
    pricing_id: str,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Delete a pricing rule"""
    async with async_session() as session:
        result = await session.execute(
            delete(PricingRule).where(PricingRule.id == pricing_id)
        )
        await session.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Pricing rule not found")
        
        return {"message": "Pricing rule deleted successfully"}


# Pricing Groups Routes
@router.get("/pricing-groups", response_model=List[PricingGroupResponse])
async def get_pricing_groups(current_user: UserResponse = Depends(require_role("admin"))):
    """Get all pricing groups with user counts"""
    async with async_session() as session:
        result = await session.execute(
            select(PricingGroup).order_by(PricingGroup.name)
        )
        groups = result.scalars().all()
        
        response = []
        for g in groups:
            # Count users in this group
            count_result = await session.execute(
                select(func.count()).select_from(User).where(User.pricing_group_id == g.id)
            )
            user_count = count_result.scalar() or 0
            
            response.append(PricingGroupResponse(
                id=g.id,
                name=g.name,
                description=g.description,
                connector_pricing=g.connector_pricing or {},
                user_count=user_count,
                created_at=g.created_at.isoformat() if g.created_at else "",
                updated_at=g.updated_at.isoformat() if g.updated_at else None
            ))
        
        return response


@router.get("/pricing-groups/{group_id}", response_model=PricingGroupResponse)
async def get_pricing_group(
    group_id: str,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Get a single pricing group"""
    async with async_session() as session:
        result = await session.execute(
            select(PricingGroup).where(PricingGroup.id == group_id)
        )
        group = result.scalar_one_or_none()
        
        if not group:
            raise HTTPException(status_code=404, detail="Pricing group not found")
        
        count_result = await session.execute(
            select(func.count()).select_from(User).where(User.pricing_group_id == group_id)
        )
        user_count = count_result.scalar() or 0
        
        return PricingGroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            connector_pricing=group.connector_pricing or {},
            user_count=user_count,
            created_at=group.created_at.isoformat() if group.created_at else "",
            updated_at=group.updated_at.isoformat() if group.updated_at else None
        )


@router.post("/pricing-groups", response_model=PricingGroupResponse)
async def create_pricing_group(
    group_data: PricingGroupCreate,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Create a new pricing group"""
    async with async_session() as session:
        # Check if name exists
        result = await session.execute(
            select(PricingGroup).where(PricingGroup.name == group_data.name)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Group name already exists")
        
        group = PricingGroup(
            id=str(uuid.uuid4()),
            name=group_data.name,
            description=group_data.description,
            connector_pricing=group_data.connector_pricing.model_dump()
        )
        session.add(group)
        await session.commit()
        await session.refresh(group)
        
        return PricingGroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            connector_pricing=group.connector_pricing or {},
            user_count=0,
            created_at=group.created_at.isoformat() if group.created_at else "",
            updated_at=group.updated_at.isoformat() if group.updated_at else None
        )


@router.patch("/pricing-groups/{group_id}", response_model=PricingGroupResponse)
async def update_pricing_group(
    group_id: str,
    group_data: PricingGroupUpdate,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Update a pricing group"""
    async with async_session() as session:
        result = await session.execute(
            select(PricingGroup).where(PricingGroup.id == group_id)
        )
        group = result.scalar_one_or_none()
        
        if not group:
            raise HTTPException(status_code=404, detail="Pricing group not found")
        
        if group_data.name:
            # Check for duplicate name
            name_check = await session.execute(
                select(PricingGroup).where(
                    PricingGroup.name == group_data.name,
                    PricingGroup.id != group_id
                )
            )
            if name_check.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Group name already exists")
            group.name = group_data.name
        
        if group_data.description is not None:
            group.description = group_data.description
        
        if group_data.connector_pricing:
            group.connector_pricing = group_data.connector_pricing.model_dump()
        
        group.updated_at = datetime.now(timezone.utc)
        
        await session.commit()
        await session.refresh(group)
        
        count_result = await session.execute(
            select(func.count()).select_from(User).where(User.pricing_group_id == group_id)
        )
        user_count = count_result.scalar() or 0
        
        return PricingGroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            connector_pricing=group.connector_pricing or {},
            user_count=user_count,
            created_at=group.created_at.isoformat() if group.created_at else "",
            updated_at=group.updated_at.isoformat() if group.updated_at else None
        )


@router.delete("/pricing-groups/{group_id}")
async def delete_pricing_group(
    group_id: str,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Delete a pricing group"""
    async with async_session() as session:
        # Check for users in this group
        count_result = await session.execute(
            select(func.count()).select_from(User).where(User.pricing_group_id == group_id)
        )
        user_count = count_result.scalar() or 0
        
        if user_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete group with {user_count} assigned users. Reassign users first."
            )
        
        result = await session.execute(
            delete(PricingGroup).where(PricingGroup.id == group_id)
        )
        await session.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Pricing group not found")
        
        return {"message": "Pricing group deleted successfully"}


@router.get("/pricing-groups/{group_id}/users")
async def get_group_users(
    group_id: str,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Get all users in a pricing group"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.pricing_group_id == group_id)
        )
        users = result.scalars().all()
        
        return [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "role": u.role
            }
            for u in users
        ]


@router.post("/pricing-groups/{group_id}/users/{user_id}")
async def assign_user_to_group(
    group_id: str,
    user_id: str,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Assign a user to a pricing group"""
    async with async_session() as session:
        # Check group exists
        group_result = await session.execute(
            select(PricingGroup).where(PricingGroup.id == group_id)
        )
        group = group_result.scalar_one_or_none()
        if not group:
            raise HTTPException(status_code=404, detail="Pricing group not found")
        
        # Check user exists
        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.pricing_group_id = group_id
        await session.commit()
        
        return {"message": f"User assigned to group '{group.name}'"}


@router.delete("/pricing-groups/{group_id}/users/{user_id}")
async def remove_user_from_group(
    group_id: str,
    user_id: str,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Remove a user from a pricing group"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id, User.pricing_group_id == group_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found in this group")
        
        user.pricing_group_id = None
        await session.commit()
        
        return {"message": "User removed from group"}
