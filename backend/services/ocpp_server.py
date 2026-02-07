"""
OCPP 1.6 WebSocket Central System Implementation
Handles real-time communication with EV charging stations
"""
import asyncio
import logging
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Set
from dataclasses import dataclass, field

import websockets
from websockets.server import WebSocketServerProtocol

from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp, call, call_result
from ocpp.v16.enums import (
    Action, RegistrationStatus, AuthorizationStatus,
    ChargePointStatus, ChargePointErrorCode, ResetType, ResetStatus,
    RemoteStartStopStatus, UnlockStatus, AvailabilityType, AvailabilityStatus
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ocpp')


@dataclass
class ChargerConnection:
    """Represents a connected charge point"""
    charger_id: str
    websocket: WebSocketServerProtocol
    charge_point: 'ChargePointHandler'
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    vendor: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None
    status: str = "Available"
    connector_status: Dict[int, str] = field(default_factory=dict)
    last_heartbeat: Optional[datetime] = None
    active_transaction_id: Optional[int] = None


class OCPPCentralSystem:
    """Central System managing all OCPP connections"""
    
    def __init__(self):
        self.connections: Dict[str, ChargerConnection] = {}
        self.transaction_counter: int = 0
        self.transactions: Dict[int, dict] = {}
        self._db_callback = None
        self._lock = asyncio.Lock()
    
    def set_db_callback(self, callback):
        """Set callback for database operations"""
        self._db_callback = callback
    
    async def get_next_transaction_id(self) -> int:
        """Generate next transaction ID"""
        async with self._lock:
            self.transaction_counter += 1
            return self.transaction_counter
    
    def get_connection(self, charger_id: str) -> Optional[ChargerConnection]:
        """Get connection by charger ID"""
        return self.connections.get(charger_id)
    
    def get_all_connections(self) -> Dict[str, ChargerConnection]:
        """Get all active connections"""
        return self.connections.copy()
    
    def get_online_chargers(self) -> int:
        """Count online chargers"""
        return len(self.connections)
    
    def get_active_transactions(self) -> list:
        """Get all active transactions"""
        return [
            {**tx, 'charger_id': charger_id}
            for charger_id, conn in self.connections.items()
            if conn.active_transaction_id
            for tx in [self.transactions.get(conn.active_transaction_id)]
            if tx
        ]
    
    async def register_charger(self, charger_id: str, websocket: WebSocketServerProtocol, 
                                charge_point: 'ChargePointHandler'):
        """Register a new charger connection"""
        connection = ChargerConnection(
            charger_id=charger_id,
            websocket=websocket,
            charge_point=charge_point
        )
        self.connections[charger_id] = connection
        logger.info(f"Charger {charger_id} connected")
        
        # Notify database if callback set
        if self._db_callback:
            await self._db_callback('charger_connected', {
                'charger_id': charger_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
    
    async def unregister_charger(self, charger_id: str):
        """Unregister a charger connection"""
        if charger_id in self.connections:
            del self.connections[charger_id]
            logger.info(f"Charger {charger_id} disconnected")
            
            if self._db_callback:
                await self._db_callback('charger_disconnected', {
                    'charger_id': charger_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
    
    async def update_charger_info(self, charger_id: str, **kwargs):
        """Update charger information"""
        if charger_id in self.connections:
            conn = self.connections[charger_id]
            for key, value in kwargs.items():
                if hasattr(conn, key):
                    setattr(conn, key, value)
    
    async def start_transaction(self, charger_id: str, connector_id: int, 
                                 id_tag: str, meter_start: int) -> int:
        """Record transaction start"""
        tx_id = await self.get_next_transaction_id()
        
        self.transactions[tx_id] = {
            'transaction_id': tx_id,
            'charger_id': charger_id,
            'connector_id': connector_id,
            'id_tag': id_tag,
            'meter_start': meter_start,
            'start_timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'active'
        }
        
        if charger_id in self.connections:
            self.connections[charger_id].active_transaction_id = tx_id
        
        if self._db_callback:
            await self._db_callback('transaction_started', self.transactions[tx_id])
        
        return tx_id
    
    async def stop_transaction(self, transaction_id: int, meter_stop: int, 
                                reason: str = "Local") -> dict:
        """Record transaction stop"""
        if transaction_id not in self.transactions:
            return {'status': 'Invalid'}
        
        tx = self.transactions[transaction_id]
        tx['meter_stop'] = meter_stop
        tx['stop_timestamp'] = datetime.now(timezone.utc).isoformat()
        tx['reason'] = reason
        tx['status'] = 'completed'
        tx['energy_kwh'] = (meter_stop - tx['meter_start']) / 1000.0
        
        # Clear active transaction from charger
        charger_id = tx.get('charger_id')
        if charger_id and charger_id in self.connections:
            self.connections[charger_id].active_transaction_id = None
        
        if self._db_callback:
            await self._db_callback('transaction_stopped', tx)
        
        return {'status': 'Accepted'}
    
    # Remote commands
    async def remote_start_transaction(self, charger_id: str, connector_id: int = 1, 
                                        id_tag: str = "REMOTE") -> str:
        """Send RemoteStartTransaction to charger"""
        conn = self.get_connection(charger_id)
        if not conn:
            return "Rejected"
        
        try:
            request = call.RemoteStartTransaction(
                id_tag=id_tag,
                connector_id=connector_id
            )
            response = await conn.charge_point.call(request)
            return response.status
        except Exception as e:
            logger.error(f"RemoteStartTransaction failed: {e}")
            return "Rejected"
    
    async def remote_stop_transaction(self, charger_id: str, transaction_id: int) -> str:
        """Send RemoteStopTransaction to charger"""
        conn = self.get_connection(charger_id)
        if not conn:
            return "Rejected"
        
        try:
            request = call.RemoteStopTransaction(transaction_id=transaction_id)
            response = await conn.charge_point.call(request)
            return response.status
        except Exception as e:
            logger.error(f"RemoteStopTransaction failed: {e}")
            return "Rejected"
    
    async def reset_charger(self, charger_id: str, reset_type: str = "Soft") -> str:
        """Send Reset command to charger"""
        conn = self.get_connection(charger_id)
        if not conn:
            return "Rejected"
        
        try:
            request = call.Reset(type=ResetType(reset_type.lower()))
            response = await conn.charge_point.call(request)
            return response.status
        except Exception as e:
            logger.error(f"Reset failed: {e}")
            return "Rejected"
    
    async def unlock_connector(self, charger_id: str, connector_id: int = 1) -> str:
        """Send UnlockConnector to charger"""
        conn = self.get_connection(charger_id)
        if not conn:
            return "Rejected"
        
        try:
            request = call.UnlockConnector(connector_id=connector_id)
            response = await conn.charge_point.call(request)
            return response.status
        except Exception as e:
            logger.error(f"UnlockConnector failed: {e}")
            return "Rejected"
    
    async def change_availability(self, charger_id: str, connector_id: int, 
                                   availability_type: str) -> str:
        """Send ChangeAvailability to charger"""
        conn = self.get_connection(charger_id)
        if not conn:
            return "Rejected"
        
        try:
            request = call.ChangeAvailability(
                connector_id=connector_id,
                type=AvailabilityType(availability_type.lower())
            )
            response = await conn.charge_point.call(request)
            return response.status
        except Exception as e:
            logger.error(f"ChangeAvailability failed: {e}")
            return "Rejected"


class ChargePointHandler(cp):
    """Handler for individual charge point connections"""
    
    def __init__(self, charger_id: str, connection, central_system: OCPPCentralSystem):
        super().__init__(charger_id, connection)
        self.central_system = central_system
        self.charger_id = charger_id
    
    @on(Action.boot_notification)
    async def on_boot_notification(self, charge_point_vendor: str, charge_point_model: str, 
                                    **kwargs):
        """Handle BootNotification from charger"""
        logger.info(f"BootNotification from {self.charger_id}: {charge_point_vendor} {charge_point_model}")
        
        await self.central_system.update_charger_info(
            self.charger_id,
            vendor=charge_point_vendor,
            model=charge_point_model,
            serial_number=kwargs.get('charge_point_serial_number'),
            firmware_version=kwargs.get('firmware_version'),
            last_heartbeat=datetime.now(timezone.utc)
        )
        
        return call_result.BootNotification(
            current_time=datetime.now(timezone.utc).isoformat(),
            interval=300,  # Heartbeat interval in seconds
            status=RegistrationStatus.accepted
        )
    
    @on(Action.heartbeat)
    async def on_heartbeat(self):
        """Handle Heartbeat from charger"""
        logger.debug(f"Heartbeat from {self.charger_id}")
        
        await self.central_system.update_charger_info(
            self.charger_id,
            last_heartbeat=datetime.now(timezone.utc)
        )
        
        return call_result.Heartbeat(
            current_time=datetime.now(timezone.utc).isoformat()
        )
    
    @on(Action.status_notification)
    async def on_status_notification(self, connector_id: int, error_code: str, 
                                      status: str, **kwargs):
        """Handle StatusNotification from charger"""
        logger.info(f"StatusNotification from {self.charger_id} connector {connector_id}: {status}")
        
        conn = self.central_system.get_connection(self.charger_id)
        if conn:
            conn.connector_status[connector_id] = status
            if connector_id == 0:  # Overall charger status
                conn.status = status
        
        return call_result.StatusNotification()
    
    @on(Action.authorize)
    async def on_authorize(self, id_tag: str):
        """Handle Authorize request from charger"""
        logger.info(f"Authorize request from {self.charger_id} for tag: {id_tag}")
        
        # Check if RFID tag is valid (integrate with database later)
        # For now, accept all tags
        return call_result.Authorize(
            id_tag_info={'status': AuthorizationStatus.accepted}
        )
    
    @on(Action.start_transaction)
    async def on_start_transaction(self, connector_id: int, id_tag: str, 
                                    meter_start: int, timestamp: str, **kwargs):
        """Handle StartTransaction from charger"""
        logger.info(f"StartTransaction from {self.charger_id} connector {connector_id}")
        
        tx_id = await self.central_system.start_transaction(
            charger_id=self.charger_id,
            connector_id=connector_id,
            id_tag=id_tag,
            meter_start=meter_start
        )
        
        return call_result.StartTransaction(
            transaction_id=tx_id,
            id_tag_info={'status': AuthorizationStatus.accepted}
        )
    
    @on(Action.stop_transaction)
    async def on_stop_transaction(self, meter_stop: int, timestamp: str, 
                                   transaction_id: int, **kwargs):
        """Handle StopTransaction from charger"""
        logger.info(f"StopTransaction from {self.charger_id}: tx_id={transaction_id}")
        
        reason = kwargs.get('reason', 'Local')
        result = await self.central_system.stop_transaction(
            transaction_id=transaction_id,
            meter_stop=meter_stop,
            reason=reason
        )
        
        return call_result.StopTransaction(
            id_tag_info={'status': AuthorizationStatus.accepted}
        )
    
    @on(Action.meter_values)
    async def on_meter_values(self, connector_id: int, meter_value: list, **kwargs):
        """Handle MeterValues from charger"""
        logger.debug(f"MeterValues from {self.charger_id} connector {connector_id}")
        
        # Process meter values (can be stored for detailed analytics)
        # For now, just acknowledge
        return call_result.MeterValues()
    
    @on(Action.data_transfer)
    async def on_data_transfer(self, vendor_id: str, **kwargs):
        """Handle DataTransfer from charger"""
        logger.info(f"DataTransfer from {self.charger_id}: vendor={vendor_id}")
        
        return call_result.DataTransfer(status='Accepted')


# Global central system instance
central_system = OCPPCentralSystem()


async def on_connect(websocket):
    """Handle new WebSocket connection"""
    # Get path from the websocket
    path = websocket.request.path if hasattr(websocket, 'request') else websocket.path
    
    # Extract charger ID from path (e.g., /ocpp/1.6/CHARGER001)
    path_parts = path.strip('/').split('/')
    
    if len(path_parts) < 3:
        logger.warning(f"Invalid connection path: {path}")
        await websocket.close(1008, "Invalid path")
        return
    
    charger_id = path_parts[-1]
    logger.info(f"New connection attempt from {charger_id}")
    
    try:
        # Create charge point handler
        charge_point = ChargePointHandler(charger_id, websocket, central_system)
        
        # Register connection
        await central_system.register_charger(charger_id, websocket, charge_point)
        
        # Start message handling
        await charge_point.start()
        
    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"Connection closed for {charger_id}: {e}")
    except Exception as e:
        logger.error(f"Error handling connection for {charger_id}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await central_system.unregister_charger(charger_id)


async def start_ocpp_server(host: str = "0.0.0.0", port: int = 9000):
    """Start the OCPP WebSocket server"""
    logger.info(f"Starting OCPP 1.6 WebSocket server on ws://{host}:{port}")
    
    server = await websockets.serve(
        on_connect,
        host,
        port,
        subprotocols=['ocpp1.6', 'ocpp1.6j'],
        ping_interval=30,
        ping_timeout=10
    )
    
    logger.info(f"OCPP WebSocket server running on ws://{host}:{port}")
    return server


# For standalone testing
if __name__ == "__main__":
    async def main():
        server = await start_ocpp_server()
        await server.wait_closed()
    
    asyncio.run(main())
