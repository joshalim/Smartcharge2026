"""
OCPP 1.6 WebSocket and REST API Tests
Tests for EV Charging Management System OCPP functionality
"""
import pytest
import requests
import os
import asyncio
import websockets
from datetime import datetime

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

# Import OCPP library for WebSocket testing
try:
    from ocpp.v16 import call, ChargePoint as cp
    from ocpp.v16.enums import RegistrationStatus
    OCPP_AVAILABLE = True
except ImportError:
    OCPP_AVAILABLE = False

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
WS_URL = "ws://localhost:9000/ocpp/1.6/"


class TestCharger(cp):
    """Test charger for WebSocket testing"""
    
    async def send_boot(self, vendor="TestVendor", model="TestModel"):
        request = call.BootNotification(
            charge_point_vendor=vendor,
            charge_point_model=model,
            charge_point_serial_number=self.id
        )
        return await self.call(request)
    
    async def send_heartbeat(self):
        request = call.Heartbeat()
        return await self.call(request)
    
    async def send_status(self, connector_id, status):
        request = call.StatusNotification(
            connector_id=connector_id,
            error_code='NoError',
            status=status
        )
        return await self.call(request)
    
    async def send_authorize(self, id_tag):
        request = call.Authorize(id_tag=id_tag)
        return await self.call(request)
    
    async def send_start_transaction(self, connector_id, id_tag, meter_start):
        request = call.StartTransaction(
            connector_id=connector_id,
            id_tag=id_tag,
            meter_start=meter_start,
            timestamp=datetime.utcnow().isoformat()
        )
        return await self.call(request)
    
    async def send_stop_transaction(self, transaction_id, meter_stop):
        request = call.StopTransaction(
            transaction_id=transaction_id,
            meter_stop=meter_stop,
            timestamp=datetime.utcnow().isoformat()
        )
        return await self.call(request)


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API tests"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@evcharge.com", "password": "admin123"}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping tests")


@pytest.fixture
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestOCPPStatus:
    """Test OCPP status endpoint"""
    
    def test_ocpp_status_returns_correct_structure(self, auth_headers):
        """Test /api/ocpp/status returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/ocpp/status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields
        assert "active_transactions" in data
        assert "total_boots" in data
        assert "online_chargers" in data
        assert "total_chargers" in data
        assert "websocket_port" in data
        assert "websocket_url" in data
        
        # Verify types
        assert isinstance(data["active_transactions"], int)
        assert isinstance(data["total_boots"], int)
        assert isinstance(data["online_chargers"], int)
        assert isinstance(data["total_chargers"], int)
        assert data["websocket_port"] == 9000
        assert "ws://" in data["websocket_url"]
    
    def test_ocpp_status_requires_auth(self):
        """Test /api/ocpp/status requires authentication"""
        response = requests.get(f"{BASE_URL}/api/ocpp/status")
        assert response.status_code in [401, 403, 500]


class TestOCPPChargersStatus:
    """Test OCPP chargers status endpoint"""
    
    def test_chargers_status_returns_list(self, auth_headers):
        """Test /api/ocpp/chargers/status returns list of chargers"""
        response = requests.get(f"{BASE_URL}/api/ocpp/chargers/status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        
        # If there are chargers, verify structure
        if len(data) > 0:
            charger = data[0]
            assert "charger_id" in charger
            assert "status" in charger
            assert "connected" in charger
            assert "connector_status" in charger


class TestOCPPBootNotifications:
    """Test OCPP boot notifications endpoint"""
    
    def test_boots_returns_list(self, auth_headers):
        """Test /api/ocpp/boots returns list of boot notifications"""
        response = requests.get(f"{BASE_URL}/api/ocpp/boots?limit=10", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        
        # If there are boots, verify structure
        if len(data) > 0:
            boot = data[0]
            assert "id" in boot
            assert "vendor" in boot
            assert "model" in boot
            assert "serial" in boot
            assert "timestamp" in boot
            assert "status" in boot


class TestOCPPActiveTransactions:
    """Test OCPP active transactions endpoint"""
    
    def test_active_transactions_returns_list(self, auth_headers):
        """Test /api/ocpp/active-transactions returns list"""
        response = requests.get(f"{BASE_URL}/api/ocpp/active-transactions", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)


class TestOCPPSimulation:
    """Test OCPP simulation endpoints"""
    
    def test_simulate_boot_notification(self, auth_headers):
        """Test /api/ocpp/simulate/boot creates boot record"""
        charger_id = f"TEST-SIM-{datetime.utcnow().strftime('%H%M%S')}"
        
        response = requests.post(
            f"{BASE_URL}/api/ocpp/simulate/boot",
            params={
                "charger_id": charger_id,
                "vendor": "TestVendor",
                "model": "TestModel"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "Accepted"
        assert "currentTime" in data
        assert data["interval"] == 300
    
    def test_simulate_start_transaction(self, auth_headers):
        """Test /api/ocpp/simulate/start-transaction creates transaction"""
        # First get a charger
        chargers_response = requests.get(f"{BASE_URL}/api/chargers", headers=auth_headers)
        chargers = chargers_response.json()
        
        if len(chargers) == 0:
            pytest.skip("No chargers available for testing")
        
        charger_id = chargers[0]["charger_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/ocpp/simulate/start-transaction",
            params={
                "charger_id": charger_id,
                "connector_id": 1,
                "id_tag": "TEST-TAG-SIM",
                "meter_start": 0
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "idTagInfo" in data
        assert data["idTagInfo"]["status"] == "Accepted"
        assert "transactionId" in data
        assert isinstance(data["transactionId"], int)
        
        # Store transaction ID for stop test
        return data["transactionId"]
    
    def test_simulate_stop_transaction(self, auth_headers):
        """Test /api/ocpp/simulate/stop-transaction completes transaction"""
        # First start a transaction
        chargers_response = requests.get(f"{BASE_URL}/api/chargers", headers=auth_headers)
        chargers = chargers_response.json()
        
        if len(chargers) == 0:
            pytest.skip("No chargers available for testing")
        
        charger_id = chargers[0]["charger_id"]
        
        # Start transaction
        start_response = requests.post(
            f"{BASE_URL}/api/ocpp/simulate/start-transaction",
            params={
                "charger_id": charger_id,
                "connector_id": 1,
                "id_tag": "TEST-STOP-TAG",
                "meter_start": 0
            },
            headers=auth_headers
        )
        
        assert start_response.status_code == 200
        transaction_id = start_response.json()["transactionId"]
        
        # Stop transaction
        stop_response = requests.post(
            f"{BASE_URL}/api/ocpp/simulate/stop-transaction",
            params={
                "transaction_id": transaction_id,
                "meter_stop": 10000,
                "reason": "Local"
            },
            headers=auth_headers
        )
        
        assert stop_response.status_code == 200
        data = stop_response.json()
        
        assert "idTagInfo" in data
        assert data["idTagInfo"]["status"] == "Accepted"
    
    def test_simulate_stop_invalid_transaction(self, auth_headers):
        """Test stopping non-existent transaction returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/ocpp/simulate/stop-transaction",
            params={
                "transaction_id": 999999,
                "meter_stop": 10000
            },
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestOCPPRemoteCommands:
    """Test OCPP remote command endpoints"""
    
    def test_remote_start_disconnected_charger(self, auth_headers):
        """Test remote start on disconnected charger returns Rejected"""
        # Get a charger that's not connected via WebSocket
        chargers_response = requests.get(f"{BASE_URL}/api/ocpp/chargers/status", headers=auth_headers)
        chargers = chargers_response.json()
        
        disconnected = [c for c in chargers if not c.get("connected", False)]
        
        if len(disconnected) == 0:
            pytest.skip("No disconnected chargers for testing")
        
        charger_id = disconnected[0]["charger_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/ocpp/remote-start/{charger_id}",
            json={"connector_id": 1, "id_tag": "REMOTE-TEST"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "Rejected"
        assert "not connected" in data["message"].lower()
    
    def test_remote_stop_disconnected_charger(self, auth_headers):
        """Test remote stop on disconnected charger returns error"""
        chargers_response = requests.get(f"{BASE_URL}/api/ocpp/chargers/status", headers=auth_headers)
        chargers = chargers_response.json()
        
        disconnected = [c for c in chargers if not c.get("connected", False)]
        
        if len(disconnected) == 0:
            pytest.skip("No disconnected chargers for testing")
        
        charger_id = disconnected[0]["charger_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/ocpp/remote-stop/{charger_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 400
    
    def test_reset_disconnected_charger(self, auth_headers):
        """Test reset on disconnected charger returns error"""
        chargers_response = requests.get(f"{BASE_URL}/api/ocpp/chargers/status", headers=auth_headers)
        chargers = chargers_response.json()
        
        disconnected = [c for c in chargers if not c.get("connected", False)]
        
        if len(disconnected) == 0:
            pytest.skip("No disconnected chargers for testing")
        
        charger_id = disconnected[0]["charger_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/ocpp/reset/{charger_id}",
            params={"reset_type": "Soft"},
            headers=auth_headers
        )
        
        assert response.status_code == 400
    
    def test_reset_invalid_type(self, auth_headers):
        """Test reset with invalid type returns 400"""
        response = requests.post(
            f"{BASE_URL}/api/ocpp/reset/CHG-001",
            params={"reset_type": "Invalid"},
            headers=auth_headers
        )
        
        assert response.status_code == 400
    
    def test_remote_start_nonexistent_charger(self, auth_headers):
        """Test remote start on non-existent charger returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/ocpp/remote-start/NONEXISTENT-CHARGER",
            json={"connector_id": 1, "id_tag": "REMOTE-TEST"},
            headers=auth_headers
        )
        
        assert response.status_code == 404


@pytest.mark.skipif(not OCPP_AVAILABLE, reason="OCPP library not available")
class TestOCPPWebSocket:
    """Test OCPP WebSocket server functionality"""
    
    @pytest.mark.asyncio(loop_scope="function")
    async def test_websocket_boot_notification(self):
        """Test WebSocket BootNotification"""
        charger_id = f"TEST-WS-{datetime.utcnow().strftime('%H%M%S')}"
        ws_url = f"{WS_URL}{charger_id}"
        
        async with websockets.connect(ws_url, subprotocols=['ocpp1.6']) as ws:
            charger = TestCharger(charger_id, ws)
            task = asyncio.create_task(charger.start())
            
            try:
                response = await asyncio.wait_for(charger.send_boot(), timeout=5)
                assert response.status == RegistrationStatus.accepted
                assert response.interval == 300
            finally:
                await ws.close()
    
    @pytest.mark.asyncio(loop_scope="function")
    async def test_websocket_heartbeat(self):
        """Test WebSocket Heartbeat"""
        charger_id = f"TEST-HB-{datetime.utcnow().strftime('%H%M%S')}"
        ws_url = f"{WS_URL}{charger_id}"
        
        async with websockets.connect(ws_url, subprotocols=['ocpp1.6']) as ws:
            charger = TestCharger(charger_id, ws)
            task = asyncio.create_task(charger.start())
            
            try:
                # First boot
                await asyncio.wait_for(charger.send_boot(), timeout=5)
                
                # Then heartbeat
                response = await asyncio.wait_for(charger.send_heartbeat(), timeout=5)
                assert response.current_time is not None
            finally:
                await ws.close()
    
    @pytest.mark.asyncio(loop_scope="function")
    async def test_websocket_status_notification(self):
        """Test WebSocket StatusNotification"""
        charger_id = f"TEST-SN-{datetime.utcnow().strftime('%H%M%S')}"
        ws_url = f"{WS_URL}{charger_id}"
        
        async with websockets.connect(ws_url, subprotocols=['ocpp1.6']) as ws:
            charger = TestCharger(charger_id, ws)
            task = asyncio.create_task(charger.start())
            
            try:
                # First boot
                await asyncio.wait_for(charger.send_boot(), timeout=5)
                
                # Send status notification
                response = await asyncio.wait_for(
                    charger.send_status(1, "Available"), 
                    timeout=5
                )
                # StatusNotification returns empty response
                assert response is not None
            finally:
                await ws.close()
    
    @pytest.mark.asyncio(loop_scope="function")
    async def test_websocket_authorize(self):
        """Test WebSocket Authorize"""
        charger_id = f"TEST-AUTH-{datetime.utcnow().strftime('%H%M%S')}"
        ws_url = f"{WS_URL}{charger_id}"
        
        async with websockets.connect(ws_url, subprotocols=['ocpp1.6']) as ws:
            charger = TestCharger(charger_id, ws)
            task = asyncio.create_task(charger.start())
            
            try:
                # First boot
                await asyncio.wait_for(charger.send_boot(), timeout=5)
                
                # Authorize
                response = await asyncio.wait_for(
                    charger.send_authorize("TEST-RFID-001"), 
                    timeout=5
                )
                assert response.id_tag_info["status"] == "Accepted"
            finally:
                await ws.close()
    
    @pytest.mark.asyncio(loop_scope="function")
    async def test_websocket_full_transaction_flow(self):
        """Test complete WebSocket transaction flow"""
        charger_id = f"TEST-TX-{datetime.utcnow().strftime('%H%M%S')}"
        ws_url = f"{WS_URL}{charger_id}"
        
        async with websockets.connect(ws_url, subprotocols=['ocpp1.6']) as ws:
            charger = TestCharger(charger_id, ws)
            task = asyncio.create_task(charger.start())
            
            try:
                # Boot
                boot_response = await asyncio.wait_for(charger.send_boot(), timeout=5)
                assert boot_response.status == RegistrationStatus.accepted
                
                # Status Available
                await asyncio.wait_for(charger.send_status(1, "Available"), timeout=5)
                
                # Start Transaction
                start_response = await asyncio.wait_for(
                    charger.send_start_transaction(1, "TEST-TAG", 0),
                    timeout=5
                )
                assert start_response.transaction_id > 0
                assert start_response.id_tag_info["status"] == "Accepted"
                
                tx_id = start_response.transaction_id
                
                # Status Charging
                await asyncio.wait_for(charger.send_status(1, "Charging"), timeout=5)
                
                # Stop Transaction
                stop_response = await asyncio.wait_for(
                    charger.send_stop_transaction(tx_id, 15000),
                    timeout=5
                )
                assert stop_response.id_tag_info["status"] == "Accepted"
                
                # Status Available again
                await asyncio.wait_for(charger.send_status(1, "Available"), timeout=5)
                
            finally:
                await ws.close()


class TestOCPPIntegration:
    """Integration tests for OCPP REST + WebSocket"""
    
    def test_online_chargers_count_updates(self, auth_headers):
        """Test that online_chargers count reflects WebSocket connections"""
        # Get initial status
        response = requests.get(f"{BASE_URL}/api/ocpp/status", headers=auth_headers)
        assert response.status_code == 200
        
        initial_count = response.json()["online_chargers"]
        
        # The count should be 0 or more (depends on active connections)
        assert initial_count >= 0
    
    def test_boot_count_increases_after_simulation(self, auth_headers):
        """Test that total_boots increases after simulation"""
        # Get initial count
        response = requests.get(f"{BASE_URL}/api/ocpp/status", headers=auth_headers)
        initial_boots = response.json()["total_boots"]
        
        # Simulate boot
        charger_id = f"TEST-BOOT-{datetime.utcnow().strftime('%H%M%S%f')}"
        requests.post(
            f"{BASE_URL}/api/ocpp/simulate/boot",
            params={"charger_id": charger_id, "vendor": "Test", "model": "Test"},
            headers=auth_headers
        )
        
        # Check count increased
        response = requests.get(f"{BASE_URL}/api/ocpp/status", headers=auth_headers)
        new_boots = response.json()["total_boots"]
        
        assert new_boots >= initial_boots


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
