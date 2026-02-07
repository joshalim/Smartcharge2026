"""
Iteration 5 - Comprehensive Backend Tests
Testing: Login, Charger CRUD, Transaction Import, Dashboard, OCPP, Settings, User CRUD
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@evcharge.com"
ADMIN_PASSWORD = "admin123"


class TestAuth:
    """Authentication tests"""
    
    def test_health_check(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "postgresql"
        assert data["admin_exists"] == True
        print(f"✓ Health check passed: {data}")
    
    def test_login_admin(self):
        """Test admin login with correct credentials"""
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
        print(f"✓ Admin login successful: {data['user']['email']}")
    
    def test_login_invalid_credentials(self):
        """Test login with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials rejected correctly")


@pytest.fixture(scope="class")
def auth_token():
    """Get auth token for authenticated requests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Authentication failed")


@pytest.fixture(scope="class")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestChargers:
    """Charger CRUD tests"""
    
    def test_create_charger_with_charger_id(self, auth_headers):
        """Test creating charger with required charger_id field"""
        unique_id = f"TEST-CHG-{uuid.uuid4().hex[:8].upper()}"
        response = requests.post(f"{BASE_URL}/api/chargers", 
            headers=auth_headers,
            json={
                "charger_id": unique_id,
                "name": "Test Charger",
                "location": "Test Location",
                "connectors": ["CCS2", "CHADEMO"],
                "status": "Available"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["charger_id"] == unique_id
        assert data["name"] == "Test Charger"
        print(f"✓ Charger created with charger_id: {unique_id}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/chargers/{data['id']}", headers=auth_headers)
    
    def test_create_charger_without_charger_id_fails(self, auth_headers):
        """Test that charger creation fails without charger_id"""
        response = requests.post(f"{BASE_URL}/api/chargers",
            headers=auth_headers,
            json={
                "name": "Test Charger No ID",
                "location": "Test Location"
            }
        )
        assert response.status_code == 422, f"Expected 422 validation error, got {response.status_code}"
        print("✓ Charger creation without charger_id correctly rejected with 422")
    
    def test_get_chargers(self, auth_headers):
        """Test getting list of chargers"""
        response = requests.get(f"{BASE_URL}/api/chargers", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} chargers")


class TestDashboard:
    """Dashboard stats tests"""
    
    def test_dashboard_stats(self, auth_headers):
        """Test dashboard stats endpoint"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields
        assert "total_transactions" in data
        assert "total_energy" in data
        assert "total_revenue" in data
        assert "paid_revenue" in data
        assert "unpaid_revenue" in data
        assert "active_stations" in data
        assert "unique_accounts" in data
        assert "payment_breakdown" in data
        assert "recent_transactions" in data
        
        print(f"✓ Dashboard stats: {data['total_transactions']} transactions, {data['total_energy']} kWh, ${data['total_revenue']} revenue")


class TestOCPP:
    """OCPP endpoint tests"""
    
    def test_ocpp_status(self, auth_headers):
        """Test OCPP status endpoint"""
        response = requests.get(f"{BASE_URL}/api/ocpp/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "active_transactions" in data
        assert "total_boots" in data
        assert data.get("ocpp_version") == "1.6"
        print(f"✓ OCPP status: {data}")
    
    def test_ocpp_boots(self, auth_headers):
        """Test OCPP boots endpoint"""
        response = requests.get(f"{BASE_URL}/api/ocpp/boots", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ OCPP boots: {len(data)} boot records")
    
    def test_ocpp_active_transactions(self, auth_headers):
        """Test OCPP active transactions endpoint"""
        response = requests.get(f"{BASE_URL}/api/ocpp/active-transactions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ OCPP active transactions: {len(data)} active")
    
    def test_ocpp_boot_notification(self):
        """Test OCPP boot notification (no auth required)"""
        response = requests.post(f"{BASE_URL}/api/ocpp/boot-notification", json={
            "chargePointVendor": "TestVendor",
            "chargePointModel": "TestModel",
            "chargePointSerialNumber": "TEST-001",
            "firmwareVersion": "1.0.0"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "Accepted"
        print(f"✓ OCPP boot notification accepted")


class TestSettings:
    """Settings endpoints tests"""
    
    def test_get_payu_settings(self, auth_headers):
        """Test getting PayU settings"""
        response = requests.get(f"{BASE_URL}/api/settings/payu", headers=auth_headers)
        # Can be 200 with data or 404 if not configured
        assert response.status_code in [200, 404]
        print(f"✓ PayU settings endpoint: {response.status_code}")
    
    def test_get_sendgrid_settings(self, auth_headers):
        """Test getting SendGrid settings"""
        response = requests.get(f"{BASE_URL}/api/settings/sendgrid", headers=auth_headers)
        # Can be 200 with data or 404 if not configured
        assert response.status_code in [200, 404]
        print(f"✓ SendGrid settings endpoint: {response.status_code}")


class TestUsers:
    """User CRUD tests"""
    
    def test_get_users(self, auth_headers):
        """Test getting list of users"""
        response = requests.get(f"{BASE_URL}/api/users", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least admin user
        print(f"✓ Got {len(data)} users")
    
    def test_create_user(self, auth_headers):
        """Test creating a new user"""
        unique_email = f"test_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(f"{BASE_URL}/api/users",
            headers=auth_headers,
            json={
                "name": "Test User",
                "email": unique_email,
                "password": "testpass123",
                "role": "user"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["email"] == unique_email
        assert data["role"] == "user"
        print(f"✓ User created: {unique_email}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/users/{data['id']}", headers=auth_headers)
    
    def test_update_user(self, auth_headers):
        """Test updating a user"""
        # First create a user
        unique_email = f"test_update_{uuid.uuid4().hex[:8]}@test.com"
        create_response = requests.post(f"{BASE_URL}/api/users",
            headers=auth_headers,
            json={
                "name": "Original Name",
                "email": unique_email,
                "password": "testpass123",
                "role": "user"
            }
        )
        assert create_response.status_code == 200
        user_id = create_response.json()["id"]
        
        # Update the user
        update_response = requests.patch(f"{BASE_URL}/api/users/{user_id}",
            headers=auth_headers,
            json={"name": "Updated Name"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Name"
        print(f"✓ User updated successfully")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=auth_headers)
    
    def test_delete_user(self, auth_headers):
        """Test deleting a user"""
        # First create a user
        unique_email = f"test_delete_{uuid.uuid4().hex[:8]}@test.com"
        create_response = requests.post(f"{BASE_URL}/api/users",
            headers=auth_headers,
            json={
                "name": "To Delete",
                "email": unique_email,
                "password": "testpass123",
                "role": "user"
            }
        )
        assert create_response.status_code == 200
        user_id = create_response.json()["id"]
        
        # Delete the user
        delete_response = requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/users/{user_id}", headers=auth_headers)
        assert get_response.status_code == 404
        print(f"✓ User deleted and verified")


class TestTransactions:
    """Transaction tests"""
    
    def test_get_transactions(self, auth_headers):
        """Test getting transactions list"""
        response = requests.get(f"{BASE_URL}/api/transactions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} transactions")
    
    def test_create_transaction(self, auth_headers):
        """Test creating a transaction"""
        unique_tx_id = f"TEST-TX-{uuid.uuid4().hex[:8].upper()}"
        response = requests.post(f"{BASE_URL}/api/transactions",
            headers=auth_headers,
            json={
                "tx_id": unique_tx_id,
                "station": "Test Station",
                "connector": "1",
                "connector_type": "CCS2",
                "account": "Test Account",
                "start_time": "2026-01-01T10:00:00Z",
                "end_time": "2026-01-01T11:00:00Z",
                "meter_value": 25.5
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["tx_id"] == unique_tx_id
        assert data["meter_value"] == 25.5
        assert data["cost"] > 0  # Cost should be calculated
        print(f"✓ Transaction created: {unique_tx_id}, cost: {data['cost']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/transactions/{data['id']}", headers=auth_headers)


class TestPricingGroups:
    """Pricing groups tests"""
    
    def test_get_pricing_groups(self, auth_headers):
        """Test getting pricing groups"""
        response = requests.get(f"{BASE_URL}/api/pricing-groups", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} pricing groups")
    
    def test_create_pricing_group(self, auth_headers):
        """Test creating a pricing group"""
        unique_name = f"Test Group {uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/pricing-groups",
            headers=auth_headers,
            json={
                "name": unique_name,
                "description": "Test pricing group",
                "connector_pricing": {
                    "CCS2": 2500.0,
                    "CHADEMO": 2000.0,
                    "J1772": 1500.0
                }
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["name"] == unique_name
        print(f"✓ Pricing group created: {unique_name}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/pricing-groups/{data['id']}", headers=auth_headers)


class TestRFIDCards:
    """RFID card tests"""
    
    def test_get_rfid_cards(self, auth_headers):
        """Test getting RFID cards"""
        response = requests.get(f"{BASE_URL}/api/rfid-cards", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} RFID cards")


class TestFilters:
    """Filter endpoints tests"""
    
    def test_get_stations_filter(self, auth_headers):
        """Test getting stations for filter"""
        response = requests.get(f"{BASE_URL}/api/filters/stations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} stations for filter")
    
    def test_get_accounts_filter(self, auth_headers):
        """Test getting accounts for filter"""
        response = requests.get(f"{BASE_URL}/api/filters/accounts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} accounts for filter")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
