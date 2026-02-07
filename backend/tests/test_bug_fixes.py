"""
Test Bug Fixes for EV Charging Management System
Tests for:
- P0: User update with email check using $ne operator
- P1: Charger creation with required charger_id field
- P1: OCPP status endpoint
- Dashboard stats endpoint
- Login and authentication flow
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuthentication:
    """Test login and authentication flow"""
    
    def test_health_check(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "postgresql"
        assert data["admin_exists"] == True
        print(f"✓ Health check passed: {data}")
    
    def test_login_with_admin_credentials(self):
        """Test login with admin@evcharge.com / admin123"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@evcharge.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "admin@evcharge.com"
        assert data["user"]["role"] == "admin"
        print(f"✓ Login successful for admin user")
        return data["access_token"]
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401
        print(f"✓ Invalid credentials rejected correctly")


class TestUserUpdateWithNeOperator:
    """P0 Bug Fix: User update with email check using $ne operator"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@evcharge.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_update_admin_user_name(self, auth_token):
        """Test updating admin user's name - uses $ne operator in email check"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Get admin user ID
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        admin_user = response.json()
        admin_id = admin_user["id"]
        
        # Update admin user's name
        new_name = f"Admin User Updated {uuid.uuid4().hex[:6]}"
        response = requests.patch(
            f"{BASE_URL}/api/users/{admin_id}",
            headers=headers,
            json={"name": new_name}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_name
        print(f"✓ Admin user name updated successfully to: {new_name}")
        
        # Verify the update persisted
        response = requests.get(f"{BASE_URL}/api/users/{admin_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["name"] == new_name
        print(f"✓ Name update verified via GET")
    
    def test_update_user_password(self, auth_token):
        """Test updating user password"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create a test user first
        test_email = f"test_user_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(
            f"{BASE_URL}/api/users",
            headers=headers,
            json={
                "name": "Test User",
                "email": test_email,
                "password": "oldpassword123",
                "role": "user"
            }
        )
        assert response.status_code == 200
        user_id = response.json()["id"]
        
        # Update password
        response = requests.patch(
            f"{BASE_URL}/api/users/{user_id}",
            headers=headers,
            json={"password": "newpassword456"}
        )
        assert response.status_code == 200
        print(f"✓ User password updated successfully")
        
        # Verify login with new password
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": "newpassword456"
        })
        assert response.status_code == 200
        print(f"✓ Login with new password successful")
        
        # Cleanup - delete test user
        requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=headers)
    
    def test_update_user_email_duplicate_check(self, auth_token):
        """Test that email duplicate check with $ne works correctly"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create two test users
        email1 = f"test_user1_{uuid.uuid4().hex[:8]}@test.com"
        email2 = f"test_user2_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(
            f"{BASE_URL}/api/users",
            headers=headers,
            json={"name": "User 1", "email": email1, "password": "pass123", "role": "user"}
        )
        assert response.status_code == 200
        user1_id = response.json()["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/users",
            headers=headers,
            json={"name": "User 2", "email": email2, "password": "pass123", "role": "user"}
        )
        assert response.status_code == 200
        user2_id = response.json()["id"]
        
        # Try to update user1's email to user2's email - should fail
        response = requests.patch(
            f"{BASE_URL}/api/users/{user1_id}",
            headers=headers,
            json={"email": email2}
        )
        assert response.status_code == 400
        assert "already in use" in response.json()["detail"].lower()
        print(f"✓ Duplicate email check with $ne operator working correctly")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/users/{user1_id}", headers=headers)
        requests.delete(f"{BASE_URL}/api/users/{user2_id}", headers=headers)


class TestChargerCreation:
    """P1 Bug Fix: Charger creation with required charger_id field"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@evcharge.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_create_charger_with_charger_id(self, auth_token):
        """Test creating charger with required charger_id field"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        charger_id = f"CHG-TEST-{uuid.uuid4().hex[:6]}"
        response = requests.post(
            f"{BASE_URL}/api/chargers",
            headers=headers,
            json={
                "charger_id": charger_id,
                "name": "Test Charger",
                "location": "Test Location",
                "connectors": ["CCS2", "CHADEMO"],
                "status": "Available"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["charger_id"] == charger_id
        assert data["name"] == "Test Charger"
        assert "CCS2" in data["connectors"]
        print(f"✓ Charger created successfully with charger_id: {charger_id}")
        
        # Verify via GET
        response = requests.get(f"{BASE_URL}/api/chargers", headers=headers)
        assert response.status_code == 200
        chargers = response.json()
        created_charger = next((c for c in chargers if c["charger_id"] == charger_id), None)
        assert created_charger is not None
        print(f"✓ Charger verified in list")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/chargers/{data['id']}", headers=headers)
    
    def test_create_charger_without_charger_id_fails(self, auth_token):
        """Test that creating charger without charger_id fails validation"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/chargers",
            headers=headers,
            json={
                "name": "Test Charger No ID",
                "location": "Test Location"
            }
        )
        # Should fail with 422 validation error
        assert response.status_code == 422
        print(f"✓ Charger creation without charger_id correctly rejected")
    
    def test_get_chargers_list(self, auth_token):
        """Test getting list of chargers"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(f"{BASE_URL}/api/chargers", headers=headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"✓ Chargers list retrieved: {len(response.json())} chargers")


class TestOCPPStatus:
    """P1 Bug Fix: OCPP status endpoint"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@evcharge.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_ocpp_status_endpoint(self, auth_token):
        """Test GET /api/ocpp/status returns status without errors"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(f"{BASE_URL}/api/ocpp/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "active_transactions" in data
        assert "total_boots" in data
        assert "ocpp_version" in data
        assert data["ocpp_version"] == "1.6"
        print(f"✓ OCPP status endpoint working: {data}")
    
    def test_ocpp_boots_endpoint(self, auth_token):
        """Test GET /api/ocpp/boots"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(f"{BASE_URL}/api/ocpp/boots", headers=headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"✓ OCPP boots endpoint working")
    
    def test_ocpp_active_transactions(self, auth_token):
        """Test GET /api/ocpp/active-transactions"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(f"{BASE_URL}/api/ocpp/active-transactions", headers=headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"✓ OCPP active transactions endpoint working")


class TestDashboardStats:
    """Test Dashboard stats endpoint"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@evcharge.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_dashboard_stats_endpoint(self, auth_token):
        """Test GET /api/dashboard/stats returns aggregated statistics"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
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
        
        # Verify data types
        assert isinstance(data["total_transactions"], int)
        assert isinstance(data["total_energy"], (int, float))
        assert isinstance(data["total_revenue"], (int, float))
        assert isinstance(data["recent_transactions"], list)
        
        print(f"✓ Dashboard stats endpoint working:")
        print(f"  - Total transactions: {data['total_transactions']}")
        print(f"  - Total energy: {data['total_energy']} kWh")
        print(f"  - Total revenue: ${data['total_revenue']:,.2f} COP")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
