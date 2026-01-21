"""
Pricing Groups API Tests
Tests: CRUD operations, User Assignment/Removal, Pricing Logic
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPricingGroupsCRUD:
    """Pricing Groups CRUD operations tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@evcharge.com",
            "password": "admin123"
        })
        return response.json()["access_token"]
    
    def test_get_pricing_groups(self, auth_token):
        """Test get all pricing groups"""
        response = requests.get(
            f"{BASE_URL}/api/pricing-groups",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Verify structure of pricing group
        if len(data) > 0:
            group = data[0]
            assert "id" in group
            assert "name" in group
            assert "connector_pricing" in group
            assert "user_count" in group
            assert "created_at" in group
    
    def test_create_pricing_group(self, auth_token):
        """Test create pricing group with custom connector pricing"""
        group_data = {
            "name": "TEST_Enterprise_Plan",
            "description": "Enterprise pricing for large fleets",
            "connector_pricing": {
                "CCS2": 1600.0,
                "CHADEMO": 1400.0,
                "J1772": 950.0
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/pricing-groups",
            json=group_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response data
        assert data["name"] == "TEST_Enterprise_Plan"
        assert data["description"] == "Enterprise pricing for large fleets"
        assert data["connector_pricing"]["CCS2"] == 1600.0
        assert data["connector_pricing"]["CHADEMO"] == 1400.0
        assert data["connector_pricing"]["J1772"] == 950.0
        assert data["user_count"] == 0
        assert "id" in data
        
        # Cleanup
        group_id = data["id"]
        requests.delete(
            f"{BASE_URL}/api/pricing-groups/{group_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_get_single_pricing_group(self, auth_token):
        """Test get single pricing group by ID"""
        # First create a group
        group_data = {
            "name": "TEST_Single_Group",
            "description": "Test single group retrieval",
            "connector_pricing": {"CCS2": 2000, "CHADEMO": 1800, "J1772": 1200}
        }
        create_response = requests.post(
            f"{BASE_URL}/api/pricing-groups",
            json=group_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        group_id = create_response.json()["id"]
        
        # Get single group
        response = requests.get(
            f"{BASE_URL}/api/pricing-groups/{group_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == group_id
        assert data["name"] == "TEST_Single_Group"
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/pricing-groups/{group_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_update_pricing_group(self, auth_token):
        """Test update pricing group name, description, and connector pricing"""
        # Create a group
        group_data = {
            "name": "TEST_Update_Group",
            "description": "Original description",
            "connector_pricing": {"CCS2": 2500, "CHADEMO": 2000, "J1772": 1500}
        }
        create_response = requests.post(
            f"{BASE_URL}/api/pricing-groups",
            json=group_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        group_id = create_response.json()["id"]
        
        # Update the group
        update_data = {
            "name": "TEST_Update_Group_Modified",
            "description": "Updated description",
            "connector_pricing": {"CCS2": 2200, "CHADEMO": 1900, "J1772": 1300}
        }
        update_response = requests.patch(
            f"{BASE_URL}/api/pricing-groups/{group_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert update_response.status_code == 200
        data = update_response.json()
        
        # Verify updates
        assert data["name"] == "TEST_Update_Group_Modified"
        assert data["description"] == "Updated description"
        assert data["connector_pricing"]["CCS2"] == 2200.0
        assert data["connector_pricing"]["CHADEMO"] == 1900.0
        assert data["connector_pricing"]["J1772"] == 1300.0
        assert "updated_at" in data
        
        # Verify persistence with GET
        get_response = requests.get(
            f"{BASE_URL}/api/pricing-groups/{group_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert get_response.json()["name"] == "TEST_Update_Group_Modified"
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/pricing-groups/{group_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_delete_pricing_group(self, auth_token):
        """Test delete pricing group"""
        # Create a group
        group_data = {
            "name": "TEST_Delete_Group",
            "description": "To be deleted",
            "connector_pricing": {"CCS2": 2500, "CHADEMO": 2000, "J1772": 1500}
        }
        create_response = requests.post(
            f"{BASE_URL}/api/pricing-groups",
            json=group_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        group_id = create_response.json()["id"]
        
        # Delete the group
        delete_response = requests.delete(
            f"{BASE_URL}/api/pricing-groups/{group_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["message"] == "Pricing group deleted successfully"
        
        # Verify deletion - should return 404
        get_response = requests.get(
            f"{BASE_URL}/api/pricing-groups/{group_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert get_response.status_code == 404
    
    def test_duplicate_group_name_rejected(self, auth_token):
        """Test that duplicate group names are rejected"""
        # Create first group
        group_data = {
            "name": "TEST_Unique_Name",
            "description": "First group",
            "connector_pricing": {"CCS2": 2500, "CHADEMO": 2000, "J1772": 1500}
        }
        create_response = requests.post(
            f"{BASE_URL}/api/pricing-groups",
            json=group_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        group_id = create_response.json()["id"]
        
        # Try to create second group with same name
        duplicate_response = requests.post(
            f"{BASE_URL}/api/pricing-groups",
            json=group_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert duplicate_response.status_code == 400
        assert "already exists" in duplicate_response.json()["detail"]
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/pricing-groups/{group_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )


class TestUserAssignment:
    """User assignment to pricing groups tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@evcharge.com",
            "password": "admin123"
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def test_group(self, auth_token):
        """Create a test group for user assignment tests"""
        group_data = {
            "name": "TEST_User_Assignment_Group",
            "description": "For user assignment testing",
            "connector_pricing": {"CCS2": 1800, "CHADEMO": 1600, "J1772": 1100}
        }
        response = requests.post(
            f"{BASE_URL}/api/pricing-groups",
            json=group_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        group = response.json()
        yield group
        
        # Cleanup - remove all users first, then delete group
        users_response = requests.get(
            f"{BASE_URL}/api/pricing-groups/{group['id']}/users",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        for user in users_response.json():
            requests.delete(
                f"{BASE_URL}/api/pricing-groups/{group['id']}/users/{user['id']}",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
        requests.delete(
            f"{BASE_URL}/api/pricing-groups/{group['id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_get_group_users_empty(self, auth_token, test_group):
        """Test get users in group - initially empty"""
        response = requests.get(
            f"{BASE_URL}/api/pricing-groups/{test_group['id']}/users",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert response.json() == []
    
    def test_assign_user_to_group(self, auth_token, test_group):
        """Test assigning a user to a pricing group"""
        # Get available users
        users_response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        users = users_response.json()
        
        # Find a user without a pricing group (viewer user)
        test_user = None
        for user in users:
            if user.get("email") == "viewer@evcharge.com":
                test_user = user
                break
        
        if not test_user:
            pytest.skip("No suitable test user found")
        
        # Assign user to group
        assign_response = requests.post(
            f"{BASE_URL}/api/pricing-groups/{test_group['id']}/users/{test_user['id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert assign_response.status_code == 200
        assert "assigned" in assign_response.json()["message"]
        
        # Verify user is in group
        group_users_response = requests.get(
            f"{BASE_URL}/api/pricing-groups/{test_group['id']}/users",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        group_users = group_users_response.json()
        user_ids = [u["id"] for u in group_users]
        assert test_user["id"] in user_ids
    
    def test_remove_user_from_group(self, auth_token, test_group):
        """Test removing a user from a pricing group"""
        # Get available users
        users_response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        users = users_response.json()
        
        # Find test user
        test_user = None
        for user in users:
            if user.get("email") == "test@example.com":
                test_user = user
                break
        
        if not test_user:
            pytest.skip("No suitable test user found")
        
        # First assign user
        requests.post(
            f"{BASE_URL}/api/pricing-groups/{test_group['id']}/users/{test_user['id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Remove user from group
        remove_response = requests.delete(
            f"{BASE_URL}/api/pricing-groups/{test_group['id']}/users/{test_user['id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert remove_response.status_code == 200
        assert "removed" in remove_response.json()["message"]
        
        # Verify user is no longer in group
        group_users_response = requests.get(
            f"{BASE_URL}/api/pricing-groups/{test_group['id']}/users",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        group_users = group_users_response.json()
        user_ids = [u["id"] for u in group_users]
        assert test_user["id"] not in user_ids
    
    def test_cannot_delete_group_with_users(self, auth_token, test_group):
        """Test that groups with assigned users cannot be deleted"""
        # Get available users
        users_response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        users = users_response.json()
        
        # Find test user
        test_user = None
        for user in users:
            if user.get("email") == "test@example.com":
                test_user = user
                break
        
        if not test_user:
            pytest.skip("No suitable test user found")
        
        # Assign user to group
        requests.post(
            f"{BASE_URL}/api/pricing-groups/{test_group['id']}/users/{test_user['id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Try to delete group - should fail
        delete_response = requests.delete(
            f"{BASE_URL}/api/pricing-groups/{test_group['id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert delete_response.status_code == 400
        assert "assigned users" in delete_response.json()["detail"]
        
        # Cleanup - remove user first
        requests.delete(
            f"{BASE_URL}/api/pricing-groups/{test_group['id']}/users/{test_user['id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )


class TestPricingLogic:
    """Test pricing logic with group pricing"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@evcharge.com",
            "password": "admin123"
        })
        return response.json()["access_token"]
    
    def test_existing_premium_group_pricing(self, auth_token):
        """Test that existing Premium Users group has correct pricing"""
        # Get the Premium Users group
        response = requests.get(
            f"{BASE_URL}/api/pricing-groups",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        groups = response.json()
        
        premium_group = None
        for group in groups:
            if group["name"] == "Premium Users":
                premium_group = group
                break
        
        if not premium_group:
            pytest.skip("Premium Users group not found")
        
        # Verify pricing
        assert premium_group["connector_pricing"]["CCS2"] == 2000.0
        assert premium_group["connector_pricing"]["CHADEMO"] == 1800.0
        assert premium_group["connector_pricing"]["J1772"] == 1200.0
        assert premium_group["user_count"] >= 1


class TestAuthentication:
    """Test authentication requirements for pricing groups"""
    
    def test_get_pricing_groups_requires_auth(self):
        """Test that pricing groups endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/pricing-groups")
        assert response.status_code == 403 or response.status_code == 401
    
    def test_create_pricing_group_requires_admin(self):
        """Test that creating pricing groups requires admin role"""
        # Login as viewer (non-admin)
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "viewer@evcharge.com",
            "password": "viewer123"
        })
        
        if login_response.status_code != 200:
            pytest.skip("Viewer user not available")
        
        token = login_response.json()["access_token"]
        
        # Try to create group
        group_data = {
            "name": "TEST_Unauthorized_Group",
            "description": "Should fail",
            "connector_pricing": {"CCS2": 2500, "CHADEMO": 2000, "J1772": 1500}
        }
        response = requests.post(
            f"{BASE_URL}/api/pricing-groups",
            json=group_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
