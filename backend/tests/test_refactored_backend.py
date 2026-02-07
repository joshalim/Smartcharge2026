"""
Test suite for EV Charging Management System - Refactored Backend (Phase 1)
Tests all modular routes: auth, users, chargers, transactions, pricing, rfid, dashboard, ocpp, settings, export
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@evcharge.com"
ADMIN_PASSWORD = "admin123"


class TestHealthCheck:
    """Health check endpoint tests"""
    
    def test_health_endpoint(self):
        """Test health check returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "2.0.0"
        print(f"✓ Health check passed - version {data['version']}")


class TestAuthentication:
    """Authentication routes tests"""
    
    def test_login_success(self):
        """Test successful login with admin credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "admin"
        print(f"✓ Login successful for {ADMIN_EMAIL}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials correctly rejected")
    
    def test_get_me_authenticated(self):
        """Test /auth/me endpoint with valid token"""
        # First login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_response.json()["access_token"]
        
        # Get current user
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == ADMIN_EMAIL
        print("✓ /auth/me endpoint working")
    
    def test_get_me_unauthorized(self):
        """Test /auth/me without token returns 403"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 403
        print("✓ Unauthorized access correctly rejected")


class TestUserManagement:
    """User CRUD operations tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_users_list(self):
        """Test getting list of users"""
        response = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} users")
    
    def test_create_user(self):
        """Test creating a new user"""
        test_email = f"TEST_user_{uuid.uuid4().hex[:8]}@example.com"
        response = requests.post(f"{BASE_URL}/api/users", headers=self.headers, json={
            "name": "Test User",
            "email": test_email,
            "password": "TestPass123",
            "role": "user"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_email
        assert data["name"] == "Test User"
        assert data["role"] == "user"
        print(f"✓ Created user: {test_email}")
        
        # Cleanup - delete the user
        user_id = data["id"]
        requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=self.headers)
    
    def test_update_user(self):
        """Test updating a user"""
        # Create a user first
        test_email = f"TEST_update_{uuid.uuid4().hex[:8]}@example.com"
        create_response = requests.post(f"{BASE_URL}/api/users", headers=self.headers, json={
            "name": "Original Name",
            "email": test_email,
            "password": "TestPass123",
            "role": "user"
        })
        user_id = create_response.json()["id"]
        
        # Update the user
        response = requests.patch(f"{BASE_URL}/api/users/{user_id}", headers=self.headers, json={
            "name": "Updated Name"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        print(f"✓ Updated user name to: {data['name']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=self.headers)
    
    def test_delete_user(self):
        """Test deleting a user"""
        # Create a user first
        test_email = f"TEST_delete_{uuid.uuid4().hex[:8]}@example.com"
        create_response = requests.post(f"{BASE_URL}/api/users", headers=self.headers, json={
            "name": "To Delete",
            "email": test_email,
            "password": "TestPass123",
            "role": "user"
        })
        user_id = create_response.json()["id"]
        
        # Delete the user
        response = requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=self.headers)
        assert response.status_code == 200
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/users/{user_id}", headers=self.headers)
        assert get_response.status_code == 404
        print("✓ User deleted successfully")


class TestChargerManagement:
    """Charger CRUD operations tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_chargers_list(self):
        """Test getting list of chargers"""
        response = requests.get(f"{BASE_URL}/api/chargers", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} chargers")
    
    def test_create_charger(self):
        """Test creating a new charger"""
        charger_id = f"TEST-CHG-{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/chargers", headers=self.headers, json={
            "charger_id": charger_id,
            "name": "Test Charger",
            "location": "Test Location",
            "connectors": ["CCS2", "CHADEMO"],
            "status": "Available"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["charger_id"] == charger_id
        assert data["name"] == "Test Charger"
        assert data["status"] == "Available"
        print(f"✓ Created charger: {charger_id}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/chargers/{data['id']}", headers=self.headers)
    
    def test_create_charger_without_charger_id_fails(self):
        """Test that creating charger without charger_id fails validation"""
        response = requests.post(f"{BASE_URL}/api/chargers", headers=self.headers, json={
            "name": "Test Charger",
            "location": "Test Location"
        })
        assert response.status_code == 422  # Validation error
        print("✓ Charger creation without charger_id correctly rejected")
    
    def test_update_charger(self):
        """Test updating a charger"""
        # Create a charger first
        charger_id = f"TEST-UPD-{uuid.uuid4().hex[:8]}"
        create_response = requests.post(f"{BASE_URL}/api/chargers", headers=self.headers, json={
            "charger_id": charger_id,
            "name": "Original Name",
            "location": "Original Location"
        })
        internal_id = create_response.json()["id"]
        
        # Update the charger
        response = requests.patch(f"{BASE_URL}/api/chargers/{internal_id}", headers=self.headers, json={
            "name": "Updated Charger Name",
            "status": "Charging"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Charger Name"
        assert data["status"] == "Charging"
        print(f"✓ Updated charger: {data['name']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/chargers/{internal_id}", headers=self.headers)
    
    def test_delete_charger(self):
        """Test deleting a charger"""
        # Create a charger first
        charger_id = f"TEST-DEL-{uuid.uuid4().hex[:8]}"
        create_response = requests.post(f"{BASE_URL}/api/chargers", headers=self.headers, json={
            "charger_id": charger_id,
            "name": "To Delete"
        })
        internal_id = create_response.json()["id"]
        
        # Delete the charger
        response = requests.delete(f"{BASE_URL}/api/chargers/{internal_id}", headers=self.headers)
        assert response.status_code == 200
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/chargers/{internal_id}", headers=self.headers)
        assert get_response.status_code == 404
        print("✓ Charger deleted successfully")


class TestTransactionManagement:
    """Transaction CRUD operations tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_transactions_list(self):
        """Test getting list of transactions"""
        response = requests.get(f"{BASE_URL}/api/transactions", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} transactions")
    
    def test_create_transaction(self):
        """Test creating a new transaction with cost calculation"""
        tx_id = f"TEST-TX-{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/transactions", headers=self.headers, json={
            "tx_id": tx_id,
            "station": "Test Station",
            "connector": "1",
            "connector_type": "CCS2",
            "account": "Test Account",
            "start_time": "2026-01-01T10:00:00",
            "end_time": "2026-01-01T11:00:00",
            "meter_value": 25.5
        })
        assert response.status_code == 200
        data = response.json()
        assert data["tx_id"] == tx_id
        assert data["meter_value"] == 25.5
        assert data["cost"] > 0  # Cost should be calculated
        assert data["payment_status"] == "UNPAID"
        print(f"✓ Created transaction: {tx_id}, cost: {data['cost']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/transactions/{data['id']}", headers=self.headers)
    
    def test_update_transaction(self):
        """Test updating a transaction"""
        # Create a transaction first
        tx_id = f"TEST-UPD-TX-{uuid.uuid4().hex[:8]}"
        create_response = requests.post(f"{BASE_URL}/api/transactions", headers=self.headers, json={
            "tx_id": tx_id,
            "station": "Test Station",
            "connector": "1",
            "account": "Test Account",
            "start_time": "2026-01-01T10:00:00",
            "end_time": "2026-01-01T11:00:00",
            "meter_value": 10.0
        })
        internal_id = create_response.json()["id"]
        
        # Update the transaction
        response = requests.patch(f"{BASE_URL}/api/transactions/{internal_id}", headers=self.headers, json={
            "payment_status": "PAID",
            "payment_type": "CASH"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["payment_status"] == "PAID"
        assert data["payment_type"] == "CASH"
        print(f"✓ Updated transaction payment status to: {data['payment_status']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/transactions/{internal_id}", headers=self.headers)
    
    def test_delete_transaction(self):
        """Test deleting a transaction"""
        # Create a transaction first
        tx_id = f"TEST-DEL-TX-{uuid.uuid4().hex[:8]}"
        create_response = requests.post(f"{BASE_URL}/api/transactions", headers=self.headers, json={
            "tx_id": tx_id,
            "station": "Test Station",
            "connector": "1",
            "account": "Test Account",
            "start_time": "2026-01-01T10:00:00",
            "end_time": "2026-01-01T11:00:00",
            "meter_value": 5.0
        })
        internal_id = create_response.json()["id"]
        
        # Delete the transaction
        response = requests.delete(f"{BASE_URL}/api/transactions/{internal_id}", headers=self.headers)
        assert response.status_code == 200
        print("✓ Transaction deleted successfully")


class TestPricingManagement:
    """Pricing rules and groups tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_pricing_rules(self):
        """Test getting pricing rules"""
        response = requests.get(f"{BASE_URL}/api/pricing", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} pricing rules")
    
    def test_create_pricing_rule(self):
        """Test creating a pricing rule"""
        response = requests.post(f"{BASE_URL}/api/pricing", headers=self.headers, json={
            "account": f"TEST_ACCOUNT_{uuid.uuid4().hex[:8]}",
            "connector": "1",
            "price_per_kwh": 1500.0
        })
        assert response.status_code == 200
        data = response.json()
        assert data["price_per_kwh"] == 1500.0
        print(f"✓ Created pricing rule: {data['price_per_kwh']} COP/kWh")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/pricing/{data['id']}", headers=self.headers)
    
    def test_get_pricing_groups(self):
        """Test getting pricing groups"""
        response = requests.get(f"{BASE_URL}/api/pricing-groups", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} pricing groups")
    
    def test_create_pricing_group(self):
        """Test creating a pricing group"""
        group_name = f"TEST_GROUP_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/pricing-groups", headers=self.headers, json={
            "name": group_name,
            "description": "Test pricing group",
            "connector_pricing": {
                "CCS2": 2000.0,
                "CHADEMO": 1800.0,
                "J1772": 1200.0
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == group_name
        assert data["connector_pricing"]["CCS2"] == 2000.0
        print(f"✓ Created pricing group: {group_name}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/pricing-groups/{data['id']}", headers=self.headers)


class TestRFIDManagement:
    """RFID card management tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_rfid_cards(self):
        """Test getting RFID cards list"""
        response = requests.get(f"{BASE_URL}/api/rfid-cards", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} RFID cards")
    
    def test_create_rfid_card(self):
        """Test creating an RFID card"""
        card_number = f"TEST-RFID-{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/rfid-cards", headers=self.headers, json={
            "card_number": card_number,
            "balance": 50000.0
        })
        assert response.status_code == 200
        data = response.json()
        assert data["card_number"] == card_number
        assert data["balance"] == 50000.0
        assert data["status"] == "active"
        print(f"✓ Created RFID card: {card_number}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rfid-cards/{data['id']}", headers=self.headers)
    
    def test_topup_rfid_card(self):
        """Test topping up an RFID card"""
        # Create a card first
        card_number = f"TEST-TOPUP-{uuid.uuid4().hex[:8]}"
        create_response = requests.post(f"{BASE_URL}/api/rfid-cards", headers=self.headers, json={
            "card_number": card_number,
            "balance": 10000.0
        })
        card_id = create_response.json()["id"]
        
        # Top up the card
        response = requests.post(f"{BASE_URL}/api/rfid-cards/{card_id}/topup", headers=self.headers, json={
            "amount": 25000.0,
            "notes": "Test topup"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["balance"] == 35000.0  # 10000 + 25000
        print(f"✓ Topped up RFID card, new balance: {data['balance']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rfid-cards/{card_id}", headers=self.headers)


class TestDashboard:
    """Dashboard statistics tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_dashboard_stats(self):
        """Test getting dashboard statistics"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_transactions" in data
        assert "total_energy" in data
        assert "total_revenue" in data
        assert "paid_revenue" in data
        assert "unpaid_revenue" in data
        assert "active_stations" in data
        assert "unique_accounts" in data
        assert "payment_breakdown" in data
        assert "recent_transactions" in data
        print(f"✓ Dashboard stats: {data['total_transactions']} transactions, {data['total_energy']} kWh")
    
    def test_get_stations_filter(self):
        """Test getting stations filter list"""
        response = requests.get(f"{BASE_URL}/api/filters/stations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} stations for filter")
    
    def test_get_accounts_filter(self):
        """Test getting accounts filter list"""
        response = requests.get(f"{BASE_URL}/api/filters/accounts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} accounts for filter")


class TestOCPP:
    """OCPP endpoints tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_ocpp_status(self):
        """Test getting OCPP system status"""
        response = requests.get(f"{BASE_URL}/api/ocpp/status", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "active_transactions" in data
        assert "total_boots" in data
        assert "online_chargers" in data
        assert "total_chargers" in data
        print(f"✓ OCPP status: {data['online_chargers']}/{data['total_chargers']} chargers online")
    
    def test_get_boot_notifications(self):
        """Test getting boot notifications"""
        response = requests.get(f"{BASE_URL}/api/ocpp/boots", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} boot notifications")
    
    def test_get_active_transactions(self):
        """Test getting active OCPP transactions"""
        response = requests.get(f"{BASE_URL}/api/ocpp/active-transactions", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} active OCPP transactions")
    
    def test_boot_notification(self):
        """Test OCPP boot notification simulation"""
        response = requests.post(f"{BASE_URL}/api/ocpp/boot", json={
            "chargePointVendor": "TestVendor",
            "chargePointModel": "TestModel",
            "chargePointSerialNumber": f"TEST-{uuid.uuid4().hex[:8]}",
            "firmwareVersion": "1.0.0"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "Accepted"
        assert "currentTime" in data
        assert "interval" in data
        print("✓ Boot notification accepted")


class TestSettings:
    """Settings endpoints tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_payu_settings(self):
        """Test getting PayU settings"""
        response = requests.get(f"{BASE_URL}/api/settings/payu", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert "test_mode" in data
        print("✓ Got PayU settings")
    
    def test_get_sendgrid_settings(self):
        """Test getting SendGrid settings"""
        response = requests.get(f"{BASE_URL}/api/settings/sendgrid", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert "sender_email" in data
        print("✓ Got SendGrid settings")
    
    def test_get_invoice_webhook_settings(self):
        """Test getting invoice webhook settings"""
        response = requests.get(f"{BASE_URL}/api/settings/invoice-webhook", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "webhook_url" in data
        assert "enabled" in data
        print("✓ Got invoice webhook settings")


class TestExport:
    """Export endpoints tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_export_users(self):
        """Test exporting users to Excel"""
        response = requests.get(f"{BASE_URL}/api/export/users?format=xlsx", headers=self.headers)
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers.get("content-type", "")
        print("✓ Users export working")
    
    def test_export_transactions(self):
        """Test exporting transactions to Excel"""
        response = requests.get(f"{BASE_URL}/api/export/transactions?format=xlsx", headers=self.headers)
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers.get("content-type", "")
        print("✓ Transactions export working")
    
    def test_export_rfid_cards(self):
        """Test exporting RFID cards to Excel"""
        response = requests.get(f"{BASE_URL}/api/export/rfid-cards?format=xlsx", headers=self.headers)
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers.get("content-type", "")
        print("✓ RFID cards export working")
    
    def test_download_user_template(self):
        """Test downloading user import template"""
        response = requests.get(f"{BASE_URL}/api/export/template/users")
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers.get("content-type", "")
        print("✓ User template download working")
    
    def test_download_transactions_template(self):
        """Test downloading transactions import template"""
        response = requests.get(f"{BASE_URL}/api/export/template/transactions")
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers.get("content-type", "")
        print("✓ Transactions template download working")


class TestAdminSetup:
    """Admin setup endpoint tests"""
    
    def test_setup_admin(self):
        """Test admin setup/reset endpoint"""
        response = requests.post(f"{BASE_URL}/api/setup/admin")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ Admin setup: {data['message']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
