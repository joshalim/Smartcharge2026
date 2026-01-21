#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for EV Charging Transactions App
Tests authentication, role-based access, CRUD operations, Excel import, and data validation
"""

import requests
import sys
import json
from datetime import datetime
from pathlib import Path

class EVChargingAPITester:
    def __init__(self, base_url="https://evbill-manager.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.user_token = None
        self.viewer_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    Details: {details}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if headers:
            test_headers.update(headers)
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                if files:
                    # Remove Content-Type for file uploads
                    test_headers.pop('Content-Type', None)
                    response = requests.post(url, files=files, headers=test_headers)
                else:
                    response = requests.post(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=test_headers)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if not success:
                details += f", Expected: {expected_status}"
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            self.log_test(name, success, details)
            
            return success, response.json() if success and response.content else {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_authentication(self):
        """Test user authentication with all roles"""
        print("\n🔐 Testing Authentication...")
        
        # Test admin login
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@evcharge.com", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
        
        # Test user login
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data={"email": "user@evcharge.com", "password": "user123"}
        )
        if success and 'access_token' in response:
            self.user_token = response['access_token']
        
        # Test viewer login
        success, response = self.run_test(
            "Viewer Login",
            "POST",
            "auth/login",
            200,
            data={"email": "viewer@evcharge.com", "password": "viewer123"}
        )
        if success and 'access_token' in response:
            self.viewer_token = response['access_token']
        
        # Test invalid login
        self.run_test(
            "Invalid Login",
            "POST",
            "auth/login",
            401,
            data={"email": "invalid@test.com", "password": "wrongpass"}
        )

    def test_protected_routes(self):
        """Test protected routes and role-based access"""
        print("\n🛡️ Testing Protected Routes & Role-Based Access...")
        
        if not self.admin_token:
            self.log_test("Protected Routes Test", False, "No admin token available")
            return
        
        # Test /auth/me endpoint
        self.run_test(
            "Get Current User (Admin)",
            "GET",
            "auth/me",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        # Test unauthorized access
        self.run_test(
            "Unauthorized Access",
            "GET",
            "auth/me",
            401
        )
        
        # Test viewer access to admin-only endpoint
        if self.viewer_token:
            self.run_test(
                "Viewer Access to Admin Endpoint",
                "GET",
                "users",
                403,
                headers={'Authorization': f'Bearer {self.viewer_token}'}
            )

    def test_dashboard_stats(self):
        """Test dashboard statistics endpoint"""
        print("\n📊 Testing Dashboard Stats...")
        
        if not self.admin_token:
            self.log_test("Dashboard Stats Test", False, "No admin token available")
            return
        
        success, response = self.run_test(
            "Get Dashboard Stats",
            "GET",
            "dashboard/stats",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if success:
            required_fields = ['total_transactions', 'total_energy', 'active_stations', 'unique_accounts', 'recent_transactions']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                self.log_test("Dashboard Stats Structure", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("Dashboard Stats Structure", True, "All required fields present")

    def test_transactions_crud(self):
        """Test transaction CRUD operations"""
        print("\n📝 Testing Transaction CRUD Operations...")
        
        if not self.admin_token:
            self.log_test("Transaction CRUD Test", False, "No admin token available")
            return
        
        # Create transaction
        transaction_data = {
            "tx_id": f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "station": "TEST_STATION_01",
            "connector": "Type2",
            "account": "test_account",
            "start_time": "2025-01-21T10:00:00",
            "end_time": "2025-01-21T11:00:00",
            "meter_value": 25.5
        }
        
        success, response = self.run_test(
            "Create Transaction",
            "POST",
            "transactions",
            200,
            data=transaction_data,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        transaction_id = response.get('id') if success else None
        
        # Get transactions
        self.run_test(
            "Get Transactions",
            "GET",
            "transactions",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        # Test filtering
        self.run_test(
            "Filter Transactions by Station",
            "GET",
            "transactions?station=TEST_STATION_01",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        # Delete transaction (admin only)
        if transaction_id:
            self.run_test(
                "Delete Transaction (Admin)",
                "DELETE",
                f"transactions/{transaction_id}",
                200,
                headers={'Authorization': f'Bearer {self.admin_token}'}
            )
        
        # Test viewer cannot create transaction
        if self.viewer_token:
            self.run_test(
                "Viewer Cannot Create Transaction",
                "POST",
                "transactions",
                403,
                data=transaction_data,
                headers={'Authorization': f'Bearer {self.viewer_token}'}
            )

    def test_excel_import(self):
        """Test Excel import functionality"""
        print("\n📤 Testing Excel Import...")
        
        if not self.admin_token:
            self.log_test("Excel Import Test", False, "No admin token available")
            return
        
        # Check if sample file exists
        sample_file = Path("/tmp/sample_ev_transactions.xlsx")
        if not sample_file.exists():
            self.log_test("Excel Import Test", False, "Sample Excel file not found")
            return
        
        # Test Excel import
        try:
            with open(sample_file, 'rb') as f:
                files = {'file': ('sample_ev_transactions.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                success, response = self.run_test(
                    "Import Excel File",
                    "POST",
                    "transactions/import",
                    200,
                    files=files,
                    headers={'Authorization': f'Bearer {self.admin_token}'}
                )
                
                if success:
                    imported = response.get('imported_count', 0)
                    skipped = response.get('skipped_count', 0)
                    errors = response.get('errors', [])
                    
                    self.log_test("Excel Import Results", True, 
                                f"Imported: {imported}, Skipped: {skipped}, Errors: {len(errors)}")
        except Exception as e:
            self.log_test("Excel Import Test", False, f"File handling error: {str(e)}")
        
        # Test invalid file format
        try:
            files = {'file': ('test.txt', b'invalid content', 'text/plain')}
            self.run_test(
                "Invalid File Format",
                "POST",
                "transactions/import",
                400,
                files=files,
                headers={'Authorization': f'Bearer {self.admin_token}'}
            )
        except Exception as e:
            self.log_test("Invalid File Format Test", False, f"Error: {str(e)}")

    def test_user_management(self):
        """Test user management (admin only)"""
        print("\n👥 Testing User Management...")
        
        if not self.admin_token:
            self.log_test("User Management Test", False, "No admin token available")
            return
        
        # Get users (admin only)
        success, response = self.run_test(
            "Get Users (Admin)",
            "GET",
            "users",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if success and response:
            users = response
            self.log_test("Users List Structure", True, f"Found {len(users)} users")
            
            # Test role update on first user (if exists)
            if users and len(users) > 0:
                user_id = users[0]['id']
                current_role = users[0]['role']
                
                # Don't change admin role to avoid losing access
                if current_role != 'admin':
                    self.run_test(
                        "Update User Role",
                        "PATCH",
                        f"users/{user_id}/role?role=user",
                        200,
                        headers={'Authorization': f'Bearer {self.admin_token}'}
                    )
        
        # Test non-admin cannot access users
        if self.user_token:
            self.run_test(
                "User Cannot Access User Management",
                "GET",
                "users",
                403,
                headers={'Authorization': f'Bearer {self.user_token}'}
            )

    def test_filter_endpoints(self):
        """Test filter endpoints for stations and accounts"""
        print("\n🔍 Testing Filter Endpoints...")
        
        if not self.admin_token:
            self.log_test("Filter Endpoints Test", False, "No admin token available")
            return
        
        self.run_test(
            "Get Stations Filter",
            "GET",
            "filters/stations",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        self.run_test(
            "Get Accounts Filter",
            "GET",
            "filters/accounts",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting EV Charging API Tests...")
        print(f"Testing against: {self.base_url}")
        
        # Run test suites
        self.test_authentication()
        self.test_protected_routes()
        self.test_dashboard_stats()
        self.test_transactions_crud()
        self.test_excel_import()
        self.test_user_management()
        self.test_filter_endpoints()
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Save detailed results
        results_file = "/app/test_reports/backend_test_results.json"
        with open(results_file, 'w') as f:
            json.dump({
                "summary": {
                    "tests_run": self.tests_run,
                    "tests_passed": self.tests_passed,
                    "success_rate": round(self.tests_passed/self.tests_run*100, 1)
                },
                "results": self.test_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = EVChargingAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())