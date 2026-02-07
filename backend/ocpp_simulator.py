#!/usr/bin/env python3
"""
OCPP 1.6 Charger Simulator
Simulates a charge point connecting to the central system via WebSocket
"""
import asyncio
import logging
from datetime import datetime, timezone

import websockets
from ocpp.v16 import call, ChargePoint as cp
from ocpp.v16.enums import RegistrationStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('charger_simulator')


class ChargerSimulator(cp):
    """Simulated charge point"""
    
    async def send_boot_notification(self):
        """Send BootNotification to central system"""
        request = call.BootNotification(
            charge_point_vendor="SimulatorVendor",
            charge_point_model="SimulatorModel",
            charge_point_serial_number=self.id,
            firmware_version="1.0.0"
        )
        response = await self.call(request)
        logger.info(f"BootNotification response: {response.status}")
        return response
    
    async def send_heartbeat(self):
        """Send Heartbeat to central system"""
        request = call.Heartbeat()
        response = await self.call(request)
        logger.info(f"Heartbeat response: {response.current_time}")
        return response
    
    async def send_status_notification(self, connector_id: int, status: str):
        """Send StatusNotification to central system"""
        request = call.StatusNotification(
            connector_id=connector_id,
            error_code="NoError",
            status=status
        )
        response = await self.call(request)
        logger.info(f"StatusNotification sent: connector={connector_id}, status={status}")
        return response
    
    async def send_authorize(self, id_tag: str):
        """Send Authorize request"""
        request = call.Authorize(id_tag=id_tag)
        response = await self.call(request)
        logger.info(f"Authorize response: {response.id_tag_info}")
        return response
    
    async def send_start_transaction(self, connector_id: int, id_tag: str, meter_start: int):
        """Send StartTransaction"""
        request = call.StartTransaction(
            connector_id=connector_id,
            id_tag=id_tag,
            meter_start=meter_start,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        response = await self.call(request)
        logger.info(f"StartTransaction response: tx_id={response.transaction_id}")
        return response
    
    async def send_stop_transaction(self, transaction_id: int, meter_stop: int):
        """Send StopTransaction"""
        request = call.StopTransaction(
            transaction_id=transaction_id,
            meter_stop=meter_stop,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        response = await self.call(request)
        logger.info(f"StopTransaction response: {response.id_tag_info}")
        return response
    
    async def send_meter_values(self, connector_id: int, transaction_id: int, value: int):
        """Send MeterValues"""
        request = call.MeterValues(
            connector_id=connector_id,
            transaction_id=transaction_id,
            meter_value=[{
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sampledValue": [{"value": str(value), "unit": "Wh"}]
            }]
        )
        response = await self.call(request)
        logger.info(f"MeterValues sent: value={value}")
        return response


async def simulate_charger(charger_id: str, ws_url: str):
    """Run a simulated charger"""
    full_url = f"{ws_url}{charger_id}"
    logger.info(f"Connecting to {full_url}")
    
    async with websockets.connect(
        full_url,
        subprotocols=['ocpp1.6']
    ) as ws:
        charger = ChargerSimulator(charger_id, ws)
        
        # Start message handling in background
        asyncio.create_task(charger.start())
        
        # Send BootNotification
        boot_response = await charger.send_boot_notification()
        
        if boot_response.status == RegistrationStatus.accepted:
            logger.info("Boot accepted! Starting normal operation...")
            
            # Send initial status
            await charger.send_status_notification(0, "Available")
            await charger.send_status_notification(1, "Available")
            
            # Simulate a charging session
            logger.info("Simulating charging session...")
            
            # Authorize
            await charger.send_authorize("RFID-001")
            
            # Start transaction
            await charger.send_status_notification(1, "Preparing")
            start_response = await charger.send_start_transaction(
                connector_id=1,
                id_tag="RFID-001",
                meter_start=0
            )
            
            tx_id = start_response.transaction_id
            await charger.send_status_notification(1, "Charging")
            
            # Send meter values periodically
            for i in range(3):
                await asyncio.sleep(2)
                await charger.send_meter_values(1, tx_id, (i + 1) * 1000)
            
            # Stop transaction
            await charger.send_status_notification(1, "Finishing")
            await charger.send_stop_transaction(tx_id, 3000)
            await charger.send_status_notification(1, "Available")
            
            logger.info("Charging session complete!")
            
            # Keep sending heartbeats
            while True:
                await asyncio.sleep(30)
                await charger.send_heartbeat()
        else:
            logger.error(f"Boot rejected: {boot_response.status}")


async def main():
    """Main entry point"""
    import sys
    
    charger_id = sys.argv[1] if len(sys.argv) > 1 else "SIM-001"
    ws_url = sys.argv[2] if len(sys.argv) > 2 else "ws://localhost:9000/ocpp/1.6/"
    
    try:
        await simulate_charger(charger_id, ws_url)
    except KeyboardInterrupt:
        logger.info("Simulator stopped")
    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
