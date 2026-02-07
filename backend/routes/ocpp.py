"""
OCPP HTTP routes (to be replaced with WebSocket in next phase)
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from sqlalchemy import select, func
from database import async_session, OCPPBoot, OCPPTransaction, OCPPSession, Charger

from routes.auth import get_current_user, require_role, UserResponse

router = APIRouter(prefix="/ocpp", tags=["OCPP"])


# Pydantic Models
class BootNotificationResponse(BaseModel):
    id: str
    vendor: str
    model: str
    serial: str
    firmware: Optional[str] = None
    timestamp: str
    status: str

    class Config:
        from_attributes = True


class OCPPStatusResponse(BaseModel):
    active_transactions: int
    total_boots: int
    online_chargers: int
    total_chargers: int


class ActiveTransactionResponse(BaseModel):
    id: str
    transaction_id: int
    charger_id: str
    connector_id: int
    id_tag: str
    meter_start: int
    start_timestamp: str
    status: str

    class Config:
        from_attributes = True


# Simulated OCPP data storage (will be replaced by WebSocket)
class BootNotificationRequest(BaseModel):
    chargePointVendor: str
    chargePointModel: str
    chargePointSerialNumber: Optional[str] = None
    firmwareVersion: Optional[str] = None
    charger_id: Optional[str] = None


class StartTransactionRequest(BaseModel):
    connectorId: int
    idTag: str
    meterStart: int
    timestamp: Optional[str] = None
    charger_id: str


class StopTransactionRequest(BaseModel):
    transactionId: int
    meterStop: int
    timestamp: Optional[str] = None
    reason: Optional[str] = None


class StatusNotificationRequest(BaseModel):
    connectorId: int
    status: str
    errorCode: Optional[str] = None
    timestamp: Optional[str] = None
    charger_id: str


# Routes
@router.get("/status", response_model=OCPPStatusResponse)
async def get_ocpp_status(current_user: UserResponse = Depends(get_current_user)):
    """Get OCPP system status"""
    async with async_session() as session:
        # Count active transactions
        active_result = await session.execute(
            select(func.count()).select_from(OCPPTransaction).where(OCPPTransaction.status == "active")
        )
        active_transactions = active_result.scalar() or 0
        
        # Count total boots
        boots_result = await session.execute(
            select(func.count()).select_from(OCPPBoot)
        )
        total_boots = boots_result.scalar() or 0
        
        # Count chargers
        chargers_result = await session.execute(
            select(func.count()).select_from(Charger)
        )
        total_chargers = chargers_result.scalar() or 0
        
        # Online chargers (those with recent heartbeat)
        online_result = await session.execute(
            select(func.count()).select_from(Charger).where(
                Charger.status.in_(["Available", "Charging", "Preparing"])
            )
        )
        online_chargers = online_result.scalar() or 0
        
        return OCPPStatusResponse(
            active_transactions=active_transactions,
            total_boots=total_boots,
            online_chargers=online_chargers,
            total_chargers=total_chargers
        )


@router.get("/boots", response_model=List[BootNotificationResponse])
async def get_boot_notifications(
    limit: int = 50,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get recent boot notifications"""
    async with async_session() as session:
        result = await session.execute(
            select(OCPPBoot).order_by(OCPPBoot.timestamp.desc()).limit(limit)
        )
        boots = result.scalars().all()
        
        return [
            BootNotificationResponse(
                id=b.id,
                vendor=b.vendor or "",
                model=b.model or "",
                serial=b.serial or "",
                firmware=b.firmware,
                timestamp=b.timestamp.isoformat() if b.timestamp else "",
                status=b.status or "Accepted"
            )
            for b in boots
        ]


@router.get("/active-transactions", response_model=List[ActiveTransactionResponse])
async def get_active_transactions(current_user: UserResponse = Depends(get_current_user)):
    """Get active charging transactions"""
    async with async_session() as session:
        result = await session.execute(
            select(OCPPTransaction).where(OCPPTransaction.status == "active")
        )
        transactions = result.scalars().all()
        
        return [
            ActiveTransactionResponse(
                id=t.id,
                transaction_id=t.transaction_id or 0,
                charger_id=t.charger_id or "",
                connector_id=t.connector_id or 1,
                id_tag=t.id_tag or "",
                meter_start=t.meter_start or 0,
                start_timestamp=t.start_timestamp or "",
                status=t.status or "active"
            )
            for t in transactions
        ]


# OCPP Simulation Endpoints (HTTP-based)
@router.post("/boot")
async def boot_notification(request: BootNotificationRequest):
    """Simulate OCPP BootNotification"""
    async with async_session() as session:
        boot = OCPPBoot(
            id=str(uuid.uuid4()),
            vendor=request.chargePointVendor,
            model=request.chargePointModel,
            serial=request.chargePointSerialNumber,
            firmware=request.firmwareVersion,
            status="Accepted"
        )
        session.add(boot)
        await session.commit()
        
        return {
            "status": "Accepted",
            "currentTime": datetime.now(timezone.utc).isoformat(),
            "interval": 300
        }


@router.post("/start-transaction")
async def start_transaction(request: StartTransactionRequest):
    """Simulate OCPP StartTransaction"""
    async with async_session() as session:
        # Generate transaction ID
        result = await session.execute(
            select(func.max(OCPPTransaction.transaction_id))
        )
        max_id = result.scalar() or 0
        transaction_id = max_id + 1
        
        tx = OCPPTransaction(
            id=str(uuid.uuid4()),
            transaction_id=transaction_id,
            charger_id=request.charger_id,
            connector_id=request.connectorId,
            id_tag=request.idTag,
            meter_start=request.meterStart,
            start_timestamp=request.timestamp or datetime.now(timezone.utc).isoformat(),
            status="active"
        )
        session.add(tx)
        
        # Update charger status
        charger_result = await session.execute(
            select(Charger).where(Charger.charger_id == request.charger_id)
        )
        charger = charger_result.scalar_one_or_none()
        if charger:
            charger.status = "Charging"
        
        await session.commit()
        
        return {
            "idTagInfo": {"status": "Accepted"},
            "transactionId": transaction_id
        }


@router.post("/stop-transaction")
async def stop_transaction(request: StopTransactionRequest):
    """Simulate OCPP StopTransaction"""
    async with async_session() as session:
        result = await session.execute(
            select(OCPPTransaction).where(
                OCPPTransaction.transaction_id == request.transactionId,
                OCPPTransaction.status == "active"
            )
        )
        tx = result.scalar_one_or_none()
        
        if tx:
            tx.meter_stop = request.meterStop
            tx.stop_timestamp = request.timestamp or datetime.now(timezone.utc).isoformat()
            tx.status = "completed"
            
            # Update charger status
            charger_result = await session.execute(
                select(Charger).where(Charger.charger_id == tx.charger_id)
            )
            charger = charger_result.scalar_one_or_none()
            if charger:
                charger.status = "Available"
            
            await session.commit()
        
        return {
            "idTagInfo": {"status": "Accepted"}
        }


@router.post("/status-notification")
async def status_notification(request: StatusNotificationRequest):
    """Simulate OCPP StatusNotification"""
    async with async_session() as session:
        charger_result = await session.execute(
            select(Charger).where(Charger.charger_id == request.charger_id)
        )
        charger = charger_result.scalar_one_or_none()
        
        if charger:
            charger.status = request.status
            charger.last_heartbeat = datetime.now(timezone.utc)
            await session.commit()
        
        return {}


@router.post("/heartbeat/{charger_id}")
async def heartbeat(charger_id: str):
    """Simulate OCPP Heartbeat"""
    async with async_session() as session:
        result = await session.execute(
            select(Charger).where(Charger.charger_id == charger_id)
        )
        charger = result.scalar_one_or_none()
        
        if charger:
            charger.last_heartbeat = datetime.now(timezone.utc)
            await session.commit()
        
        return {
            "currentTime": datetime.now(timezone.utc).isoformat()
        }


# Remote control endpoints
@router.post("/remote-start/{charger_id}")
async def remote_start(
    charger_id: str,
    connector_id: int = 1,
    id_tag: str = "REMOTE",
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Send remote start command (simulated)"""
    async with async_session() as session:
        result = await session.execute(
            select(Charger).where(Charger.charger_id == charger_id)
        )
        charger = result.scalar_one_or_none()
        
        if not charger:
            raise HTTPException(status_code=404, detail="Charger not found")
        
        if charger.status == "Charging":
            raise HTTPException(status_code=400, detail="Charger is already in use")
        
        return {
            "status": "Accepted",
            "message": f"Remote start command sent to {charger_id}"
        }


@router.post("/remote-stop/{charger_id}")
async def remote_stop(
    charger_id: str,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Send remote stop command (simulated)"""
    async with async_session() as session:
        result = await session.execute(
            select(Charger).where(Charger.charger_id == charger_id)
        )
        charger = result.scalar_one_or_none()
        
        if not charger:
            raise HTTPException(status_code=404, detail="Charger not found")
        
        return {
            "status": "Accepted",
            "message": f"Remote stop command sent to {charger_id}"
        }


@router.post("/reset/{charger_id}")
async def reset_charger(
    charger_id: str,
    reset_type: str = "Soft",
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Send reset command (simulated)"""
    if reset_type not in ["Soft", "Hard"]:
        raise HTTPException(status_code=400, detail="Invalid reset type")
    
    async with async_session() as session:
        result = await session.execute(
            select(Charger).where(Charger.charger_id == charger_id)
        )
        charger = result.scalar_one_or_none()
        
        if not charger:
            raise HTTPException(status_code=404, detail="Charger not found")
        
        return {
            "status": "Accepted",
            "message": f"{reset_type} reset command sent to {charger_id}"
        }
