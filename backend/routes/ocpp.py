"""
OCPP WebSocket routes and REST API endpoints
Integrates WebSocket server with FastAPI for real-time and REST control
"""
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import asyncio
import json

from sqlalchemy import select, func
from database import async_session, OCPPBoot, OCPPTransaction, OCPPSession, Charger, RFIDCard

from routes.auth import get_current_user, require_role, UserResponse
from services.ocpp_server import central_system

router = APIRouter(prefix="/ocpp", tags=["OCPP"])


# Pydantic Models
class OCPPStatusResponse(BaseModel):
    active_transactions: int
    total_boots: int
    online_chargers: int
    total_chargers: int
    websocket_port: int = 9000
    websocket_url: str = "ws://localhost:9000/ocpp/1.6/"


class ChargerStatusResponse(BaseModel):
    charger_id: str
    status: str
    vendor: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None
    connected: bool
    last_heartbeat: Optional[str] = None
    connector_status: Dict[int, str] = {}
    active_transaction_id: Optional[int] = None


class ActiveTransactionResponse(BaseModel):
    transaction_id: int
    charger_id: str
    connector_id: int
    id_tag: str
    meter_start: int
    start_timestamp: str
    status: str


class BootNotificationResponse(BaseModel):
    id: str
    vendor: str
    model: str
    serial: str
    firmware: Optional[str] = None
    timestamp: str
    status: str


class RemoteCommandRequest(BaseModel):
    connector_id: int = 1
    id_tag: str = "REMOTE"


class RemoteCommandResponse(BaseModel):
    status: str
    message: str


# WebSocket for real-time updates to frontend
class ConnectionManager:
    """Manage WebSocket connections for real-time frontend updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


ws_manager = ConnectionManager()


# Database callback for OCPP events
async def ocpp_db_callback(event_type: str, data: dict):
    """Handle OCPP events and persist to database"""
    async with async_session() as session:
        if event_type == 'charger_connected':
            # Update charger status in database
            result = await session.execute(
                select(Charger).where(Charger.charger_id == data['charger_id'])
            )
            charger = result.scalar_one_or_none()
            if charger:
                charger.status = 'Available'
                charger.last_heartbeat = datetime.now(timezone.utc)
                await session.commit()
        
        elif event_type == 'charger_disconnected':
            result = await session.execute(
                select(Charger).where(Charger.charger_id == data['charger_id'])
            )
            charger = result.scalar_one_or_none()
            if charger:
                charger.status = 'Unavailable'
                await session.commit()
        
        elif event_type == 'transaction_started':
            tx = OCPPTransaction(
                id=str(uuid.uuid4()),
                transaction_id=data['transaction_id'],
                charger_id=data['charger_id'],
                connector_id=data['connector_id'],
                id_tag=data['id_tag'],
                meter_start=data['meter_start'],
                start_timestamp=data['start_timestamp'],
                status='active'
            )
            session.add(tx)
            
            # Update charger status
            result = await session.execute(
                select(Charger).where(Charger.charger_id == data['charger_id'])
            )
            charger = result.scalar_one_or_none()
            if charger:
                charger.status = 'Charging'
            
            await session.commit()
        
        elif event_type == 'transaction_stopped':
            result = await session.execute(
                select(OCPPTransaction).where(
                    OCPPTransaction.transaction_id == data['transaction_id'],
                    OCPPTransaction.status == 'active'
                )
            )
            tx = result.scalar_one_or_none()
            if tx:
                tx.meter_stop = data['meter_stop']
                tx.stop_timestamp = data['stop_timestamp']
                tx.status = 'completed'
            
            # Update charger status
            result = await session.execute(
                select(Charger).where(Charger.charger_id == data['charger_id'])
            )
            charger = result.scalar_one_or_none()
            if charger:
                charger.status = 'Available'
            
            # Deduct from RFID card balance if applicable
            if data.get('id_tag'):
                card_result = await session.execute(
                    select(RFIDCard).where(RFIDCard.card_number == data['id_tag'])
                )
                card = card_result.scalar_one_or_none()
                if card:
                    energy_kwh = data.get('energy_kwh', 0)
                    # Calculate cost (default 500 COP per kWh)
                    cost = energy_kwh * 500
                    card.balance = max(0, (card.balance or 0) - cost)
            
            await session.commit()
    
    # Broadcast to frontend websocket clients
    await ws_manager.broadcast({
        'event': event_type,
        'data': data,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


# Set up database callback
central_system.set_db_callback(ocpp_db_callback)


# REST Endpoints
@router.get("/status", response_model=OCPPStatusResponse)
async def get_ocpp_status(current_user: UserResponse = Depends(get_current_user)):
    """Get OCPP system status including WebSocket info"""
    async with async_session() as session:
        # Count active transactions from WebSocket
        active_from_ws = len(central_system.get_active_transactions())
        
        # Also count from database
        active_result = await session.execute(
            select(func.count()).select_from(OCPPTransaction).where(
                OCPPTransaction.status == "active"
            )
        )
        active_from_db = active_result.scalar() or 0
        
        # Total boots
        boots_result = await session.execute(
            select(func.count()).select_from(OCPPBoot)
        )
        total_boots = boots_result.scalar() or 0
        
        # Total chargers in database
        chargers_result = await session.execute(
            select(func.count()).select_from(Charger)
        )
        total_chargers = chargers_result.scalar() or 0
        
        # Online chargers from WebSocket connections
        online_chargers = central_system.get_online_chargers()
        
        return OCPPStatusResponse(
            active_transactions=max(active_from_ws, active_from_db),
            total_boots=total_boots,
            online_chargers=online_chargers,
            total_chargers=total_chargers,
            websocket_port=9000,
            websocket_url="ws://localhost:9000/ocpp/1.6/"
        )


@router.get("/chargers/status", response_model=List[ChargerStatusResponse])
async def get_chargers_status(current_user: UserResponse = Depends(get_current_user)):
    """Get real-time status of all chargers"""
    async with async_session() as session:
        # Get all chargers from database
        result = await session.execute(select(Charger))
        chargers = result.scalars().all()
        
        response = []
        for charger in chargers:
            # Check if connected via WebSocket
            ws_conn = central_system.get_connection(charger.charger_id)
            
            if ws_conn:
                response.append(ChargerStatusResponse(
                    charger_id=charger.charger_id,
                    status=ws_conn.status,
                    vendor=ws_conn.vendor,
                    model=ws_conn.model,
                    serial_number=ws_conn.serial_number,
                    firmware_version=ws_conn.firmware_version,
                    connected=True,
                    last_heartbeat=ws_conn.last_heartbeat.isoformat() if ws_conn.last_heartbeat else None,
                    connector_status=ws_conn.connector_status,
                    active_transaction_id=ws_conn.active_transaction_id
                ))
            else:
                response.append(ChargerStatusResponse(
                    charger_id=charger.charger_id,
                    status=charger.status or "Unavailable",
                    connected=False,
                    last_heartbeat=charger.last_heartbeat.isoformat() if charger.last_heartbeat else None
                ))
        
        return response


@router.get("/active-transactions", response_model=List[ActiveTransactionResponse])
async def get_active_transactions(current_user: UserResponse = Depends(get_current_user)):
    """Get active charging transactions"""
    # Get from WebSocket central system first
    ws_transactions = central_system.get_active_transactions()
    
    if ws_transactions:
        return [
            ActiveTransactionResponse(
                transaction_id=tx['transaction_id'],
                charger_id=tx['charger_id'],
                connector_id=tx['connector_id'],
                id_tag=tx['id_tag'],
                meter_start=tx['meter_start'],
                start_timestamp=tx['start_timestamp'],
                status=tx['status']
            )
            for tx in ws_transactions
        ]
    
    # Fallback to database
    async with async_session() as session:
        result = await session.execute(
            select(OCPPTransaction).where(OCPPTransaction.status == "active")
        )
        transactions = result.scalars().all()
        
        return [
            ActiveTransactionResponse(
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


# Remote Control Endpoints
@router.post("/remote-start/{charger_id}", response_model=RemoteCommandResponse)
async def remote_start_transaction(
    charger_id: str,
    request: RemoteCommandRequest = RemoteCommandRequest(),
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Send RemoteStartTransaction command to charger"""
    conn = central_system.get_connection(charger_id)
    
    if not conn:
        # Check if charger exists but not connected
        async with async_session() as session:
            result = await session.execute(
                select(Charger).where(Charger.charger_id == charger_id)
            )
            charger = result.scalar_one_or_none()
            
            if not charger:
                raise HTTPException(status_code=404, detail="Charger not found")
            
            return RemoteCommandResponse(
                status="Rejected",
                message=f"Charger {charger_id} is not connected via WebSocket"
            )
    
    status = await central_system.remote_start_transaction(
        charger_id=charger_id,
        connector_id=request.connector_id,
        id_tag=request.id_tag
    )
    
    return RemoteCommandResponse(
        status=status,
        message=f"RemoteStartTransaction {'sent successfully' if status == 'Accepted' else 'rejected'}"
    )


@router.post("/remote-stop/{charger_id}", response_model=RemoteCommandResponse)
async def remote_stop_transaction(
    charger_id: str,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Send RemoteStopTransaction command to charger"""
    conn = central_system.get_connection(charger_id)
    
    if not conn:
        raise HTTPException(status_code=400, detail="Charger not connected via WebSocket")
    
    if not conn.active_transaction_id:
        raise HTTPException(status_code=400, detail="No active transaction on this charger")
    
    status = await central_system.remote_stop_transaction(
        charger_id=charger_id,
        transaction_id=conn.active_transaction_id
    )
    
    return RemoteCommandResponse(
        status=status,
        message=f"RemoteStopTransaction {'sent successfully' if status == 'Accepted' else 'rejected'}"
    )


@router.post("/reset/{charger_id}", response_model=RemoteCommandResponse)
async def reset_charger(
    charger_id: str,
    reset_type: str = "Soft",
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Send Reset command to charger"""
    if reset_type not in ["Soft", "Hard"]:
        raise HTTPException(status_code=400, detail="Invalid reset type. Use 'Soft' or 'Hard'")
    
    conn = central_system.get_connection(charger_id)
    
    if not conn:
        raise HTTPException(status_code=400, detail="Charger not connected via WebSocket")
    
    status = await central_system.reset_charger(charger_id, reset_type)
    
    return RemoteCommandResponse(
        status=status,
        message=f"{reset_type} reset {'sent successfully' if status == 'Accepted' else 'rejected'}"
    )


@router.post("/unlock/{charger_id}", response_model=RemoteCommandResponse)
async def unlock_connector(
    charger_id: str,
    connector_id: int = 1,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Send UnlockConnector command to charger"""
    conn = central_system.get_connection(charger_id)
    
    if not conn:
        raise HTTPException(status_code=400, detail="Charger not connected via WebSocket")
    
    status = await central_system.unlock_connector(charger_id, connector_id)
    
    return RemoteCommandResponse(
        status=status,
        message=f"UnlockConnector {'sent successfully' if status == 'Unlocked' else 'failed'}"
    )


@router.post("/availability/{charger_id}", response_model=RemoteCommandResponse)
async def change_availability(
    charger_id: str,
    connector_id: int = 0,
    availability_type: str = "Operative",
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Send ChangeAvailability command to charger"""
    if availability_type not in ["Operative", "Inoperative"]:
        raise HTTPException(status_code=400, detail="Invalid type. Use 'Operative' or 'Inoperative'")
    
    conn = central_system.get_connection(charger_id)
    
    if not conn:
        raise HTTPException(status_code=400, detail="Charger not connected via WebSocket")
    
    status = await central_system.change_availability(charger_id, connector_id, availability_type)
    
    return RemoteCommandResponse(
        status=status,
        message=f"ChangeAvailability {'accepted' if status == 'Accepted' else 'rejected or scheduled'}"
    )


# OCPP Simulation endpoints (for testing without real chargers)
@router.post("/simulate/boot")
async def simulate_boot_notification(
    charger_id: str,
    vendor: str = "TestVendor",
    model: str = "TestModel",
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Simulate a BootNotification (for testing)"""
    async with async_session() as session:
        boot = OCPPBoot(
            id=str(uuid.uuid4()),
            vendor=vendor,
            model=model,
            serial=charger_id,
            status="Accepted"
        )
        session.add(boot)
        
        # Update charger status
        result = await session.execute(
            select(Charger).where(Charger.charger_id == charger_id)
        )
        charger = result.scalar_one_or_none()
        if charger:
            charger.status = "Available"
            charger.last_heartbeat = datetime.now(timezone.utc)
        
        await session.commit()
    
    return {
        "status": "Accepted",
        "currentTime": datetime.now(timezone.utc).isoformat(),
        "interval": 300
    }


@router.post("/simulate/start-transaction")
async def simulate_start_transaction(
    charger_id: str,
    connector_id: int = 1,
    id_tag: str = "TEST-TAG",
    meter_start: int = 0,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Simulate a StartTransaction (for testing)"""
    async with async_session() as session:
        # Get max transaction ID
        result = await session.execute(
            select(func.max(OCPPTransaction.transaction_id))
        )
        max_id = result.scalar() or 0
        transaction_id = max_id + 1
        
        tx = OCPPTransaction(
            id=str(uuid.uuid4()),
            transaction_id=transaction_id,
            charger_id=charger_id,
            connector_id=connector_id,
            id_tag=id_tag,
            meter_start=meter_start,
            start_timestamp=datetime.now(timezone.utc).isoformat(),
            status="active"
        )
        session.add(tx)
        
        # Update charger status
        result = await session.execute(
            select(Charger).where(Charger.charger_id == charger_id)
        )
        charger = result.scalar_one_or_none()
        if charger:
            charger.status = "Charging"
        
        await session.commit()
        
        return {
            "idTagInfo": {"status": "Accepted"},
            "transactionId": transaction_id
        }


@router.post("/simulate/stop-transaction")
async def simulate_stop_transaction(
    transaction_id: int,
    meter_stop: int,
    reason: str = "Local",
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Simulate a StopTransaction (for testing)"""
    async with async_session() as session:
        result = await session.execute(
            select(OCPPTransaction).where(
                OCPPTransaction.transaction_id == transaction_id,
                OCPPTransaction.status == "active"
            )
        )
        tx = result.scalar_one_or_none()
        
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found or not active")
        
        tx.meter_stop = meter_stop
        tx.stop_timestamp = datetime.now(timezone.utc).isoformat()
        tx.status = "completed"
        
        # Update charger status
        result = await session.execute(
            select(Charger).where(Charger.charger_id == tx.charger_id)
        )
        charger = result.scalar_one_or_none()
        if charger:
            charger.status = "Available"
        
        await session.commit()
        
        return {
            "idTagInfo": {"status": "Accepted"}
        }


# WebSocket endpoint for frontend real-time updates
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time OCPP updates to frontend"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            
            # Handle ping/pong or other commands
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "status":
                # Send current status
                connections = central_system.get_all_connections()
                await websocket.send_json({
                    "event": "status",
                    "online_chargers": len(connections),
                    "chargers": [
                        {
                            "charger_id": cid,
                            "status": conn.status,
                            "connected": True
                        }
                        for cid, conn in connections.items()
                    ]
                })
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
