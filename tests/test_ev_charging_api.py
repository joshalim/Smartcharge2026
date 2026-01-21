"""
EV Charging Transaction Management API Tests
Tests: Auth, Dashboard, Chargers CRUD, Reports, OCPP Remote Control, Transactions
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication endpoint tests"""
    
    def test_login_admin_success(self):
        """Test admin login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@evcharge.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == "admin@evcharge.com"
        assert data["user"]["role"] == "admin"
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401


class TestDashboard:
    """Dashboard statistics tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@evcharge.com",
            "password": "admin123"
        })
        return response.json()["access_token"]
    
    def test_dashboard_stats(self, auth_token):
        """Test dashboard statistics endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_transactions" in data
        assert "total_energy" in data
        assert "total_revenue" in data
        assert "paid_revenue" in data
        assert "unpaid_revenue" in data
        assert "active_stations" in data
        assert "unique_accounts" in data


class TestChargersCRUD:
    """Chargers CRUD operations tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@evcharge.com",
            "password": "admin123"
        })
        return response.json()["access_token"]
    
    def test_get_chargers(self, auth_token):
        """Test get all chargers"""
        response = requests.get(
            f"{BASE_URL}/api/chargers",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_charger_with_ccs2_chademo(self, auth_token):
        """Test create charger with CCS2 and CHADEMO connectors"""
        charger_data = {
            "name": "TEST_Station_Alpha",
            "location": "Building A, Floor 1",
            "model": "ABB Terra HP",
            "serial_number": "TEST-THP-2024-001",
            "connector_types": ["CCS2", "CHADEMO"],
            "max_power": 150.0,
            "status": "Available"
        }
        response = requests.post(
            f"{BASE_URL}/api/chargers",
            json=charger_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TEST_Station_Alpha"
        assert "CCS2" in data["connector_types"]
        assert "CHADEMO" in data["connector_types"]
        assert data["max_power"] == 150.0
        assert "id" in data
        
        # Cleanup - delete the created charger
        charger_id = data["id"]
        requests.delete(
            f"{BASE_URL}/api/chargers/{charger_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_update_charger(self, auth_token):
        """Test update charger"""
        # First create a charger
        charger_data = {
            "name": "TEST_Station_Beta",
            "location": "Building B",
            "model": "ChargePoint",
            "serial_number": "TEST-CP-2024-002",
            "connector_types": ["J1772"],
            "max_power": 50.0,
            "status": "Available"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/chargers",
            json=charger_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        charger_id = create_response.json()["id"]
        
        # Update the charger
        update_data = {
            "status": "Charging",
            "max_power": 75.0
        }
        update_response = requests.patch(
            f"{BASE_URL}/api/chargers/{charger_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["status"] == "Charging"
        assert updated["max_power"] == 75.0
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/chargers/{charger_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_delete_charger(self, auth_token):
        """Test delete charger"""
        # Create a charger to delete
        charger_data = {
            "name": "TEST_Station_Delete",
            "location": "Building C",
            "model": "Tesla Supercharger",
            "serial_number": "TEST-TS-2024-003",
            "connector_types": ["CCS2"],
            "max_power": 250.0,
            "status": "Available"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/chargers",
            json=charger_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        charger_id = create_response.json()["id"]
        
        # Delete the charger
        delete_response = requests.delete(
            f"{BASE_URL}/api/chargers/{charger_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert delete_response.status_code == 200
        
        # Verify deletion - should return empty or not contain the deleted charger
        get_response = requests.get(
            f"{BASE_URL}/api/chargers",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        chargers = get_response.json()
        charger_ids = [c["id"] for c in chargers]
        assert charger_id not in charger_ids


class TestReports:
    """Reports generation tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@evcharge.com",
            "password": "admin123"
        })
        return response.json()["access_token"]
    
    def test_generate_report_no_filters(self, auth_token):
        """Test generate report without filters"""
        response = requests.post(
            f"{BASE_URL}/api/reports/generate",
            json={},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "by_account" in data
        assert "by_connector" in data
        assert "by_payment_type" in data
        assert "transactions" in data
        
        # Verify summary structure
        summary = data["summary"]
        assert "total_transactions" in summary
        assert "total_energy" in summary
        assert "total_revenue" in summary
    
    def test_generate_report_with_filters(self, auth_token):
        """Test generate report with filters"""
        response = requests.post(
            f"{BASE_URL}/api/reports/generate",
            json={
                "payment_status": "PAID"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # All transactions should be PAID
        for tx in data["transactions"]:
            assert tx["payment_status"] == "PAID"


class TestOCPPRemoteControl:
    """OCPP Remote Control tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@evcharge.com",
            "password": "admin123"
        })
        return response.json()["access_token"]
    
    def test_ocpp_status(self, auth_token):
        """Test OCPP status endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/ocpp/status",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "active_transactions" in data
        assert "total_boots" in data
        assert "ocpp_version" in data
        assert data["ocpp_version"] == "1.6"
    
    def test_ocpp_boots(self, auth_token):
        """Test get OCPP boot notifications"""
        response = requests.get(
            f"{BASE_URL}/api/ocpp/boots",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_ocpp_active_transactions(self, auth_token):
        """Test get active OCPP transactions"""
        response = requests.get(
            f"{BASE_URL}/api/ocpp/active-transactions",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_remote_start_transaction(self, auth_token):
        """Test remote start transaction"""
        # First create a charger
        charger_data = {
            "name": "TEST_OCPP_Charger",
            "location": "OCPP Test Location",
            "model": "OCPP Test Model",
            "serial_number": "TEST-OCPP-001",
            "connector_types": ["CCS2"],
            "max_power": 100.0,
            "status": "Available"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/chargers",
            json=charger_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        charger_id = create_response.json()["id"]
        
        # Remote start
        start_response = requests.post(
            f"{BASE_URL}/api/ocpp/remote-start",
            json={
                "charger_id": charger_id,
                "connector_id": 1,
                "id_tag": "TEST_USER_001"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert start_response.status_code == 200
        data = start_response.json()
        assert data["status"] == "Accepted"
        assert "transactionId" in data
        
        transaction_id = data["transactionId"]
        
        # Remote stop
        stop_response = requests.post(
            f"{BASE_URL}/api/ocpp/remote-stop",
            json={"transaction_id": transaction_id},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert stop_response.status_code == 200
        assert stop_response.json()["status"] == "Accepted"
        
        # Cleanup charger
        requests.delete(
            f"{BASE_URL}/api/chargers/{charger_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )


class TestTransactions:
    """Transaction operations tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@evcharge.com",
            "password": "admin123"
        })
        return response.json()["access_token"]
    
    def test_get_transactions(self, auth_token):
        """Test get transactions"""
        response = requests.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_update_transaction_payment_status(self, auth_token):
        """Test update transaction payment status (bulk payment update simulation)"""
        # Get existing transactions
        get_response = requests.get(
            f"{BASE_URL}/api/transactions?payment_status=UNPAID&limit=1",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        transactions = get_response.json()
        
        if len(transactions) > 0:
            tx_id = transactions[0]["id"]
            
            # Update payment status
            update_response = requests.patch(
                f"{BASE_URL}/api/transactions/{tx_id}",
                json={
                    "payment_status": "PAID",
                    "payment_type": "NEQUI",
                    "payment_date": "2025-01-22"
                },
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            assert update_response.status_code == 200
            updated = update_response.json()
            assert updated["payment_status"] == "PAID"
            assert updated["payment_type"] == "NEQUI"
            
            # Revert back to UNPAID for other tests
            requests.patch(
                f"{BASE_URL}/api/transactions/{tx_id}",
                json={"payment_status": "UNPAID", "payment_type": None, "payment_date": None},
                headers={"Authorization": f"Bearer {auth_token}"}
            )
        else:
            pytest.skip("No unpaid transactions available for testing")
    
    def test_invoice_generation_for_paid_transaction(self, auth_token):
        """Test invoice download for paid transaction"""
        # Get a paid transaction
        get_response = requests.get(
            f"{BASE_URL}/api/transactions?payment_status=PAID&limit=1",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        transactions = get_response.json()
        
        if len(transactions) > 0:
            tx_id = transactions[0]["id"]
            
            # Download invoice
            invoice_response = requests.get(
                f"{BASE_URL}/api/transactions/{tx_id}/invoice",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            assert invoice_response.status_code == 200
            assert invoice_response.headers.get("content-type") == "application/pdf"
        else:
            pytest.skip("No paid transactions available for invoice testing")
    
    def test_invoice_fails_for_unpaid_transaction(self, auth_token):
        """Test invoice download fails for unpaid transaction"""
        # Get an unpaid transaction
        get_response = requests.get(
            f"{BASE_URL}/api/transactions?payment_status=UNPAID&limit=1",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        transactions = get_response.json()
        
        if len(transactions) > 0:
            tx_id = transactions[0]["id"]
            
            # Try to download invoice - should fail
            invoice_response = requests.get(
                f"{BASE_URL}/api/transactions/{tx_id}/invoice",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            assert invoice_response.status_code == 400
        else:
            pytest.skip("No unpaid transactions available for testing")


class TestFilters:
    """Filter endpoints tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@evcharge.com",
            "password": "admin123"
        })
        return response.json()["access_token"]
    
    def test_get_stations(self, auth_token):
        """Test get stations filter"""
        response = requests.get(
            f"{BASE_URL}/api/filters/stations",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_accounts(self, auth_token):
        """Test get accounts filter"""
        response = requests.get(
            f"{BASE_URL}/api/filters/accounts",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
