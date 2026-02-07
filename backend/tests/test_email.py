"""
Email Templates API Tests
Tests for email service endpoints including:
- Email status endpoint
- Email templates CRUD operations
- Email template preview
- Email sending (expected to fail without SendGrid config)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@evcharge.com"
ADMIN_PASSWORD = "admin123"


class TestEmailAuth:
    """Test authentication requirements for email endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_auth_token(self):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]
    
    def test_email_status_requires_auth(self):
        """Email status endpoint requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/email/status")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Email status endpoint requires authentication")
    
    def test_email_templates_requires_auth(self):
        """Email templates endpoint requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/email/templates")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Email templates endpoint requires authentication")
    
    def test_email_preview_requires_auth(self):
        """Email preview endpoint requires authentication"""
        response = self.session.post(f"{BASE_URL}/api/email/preview", json={
            "template_name": "welcome",
            "variables": {}
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Email preview endpoint requires authentication")


class TestEmailStatus:
    """Test email status endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login and get token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_email_status(self):
        """GET /api/email/status returns correct structure"""
        response = self.session.get(f"{BASE_URL}/api/email/status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "enabled" in data, "Response should contain 'enabled' field"
        assert "configured" in data, "Response should contain 'configured' field"
        assert isinstance(data["enabled"], bool), "'enabled' should be boolean"
        assert isinstance(data["configured"], bool), "'configured' should be boolean"
        
        # Since SendGrid is not configured, expect disabled
        assert data["enabled"] == False, "Email should be disabled without SendGrid config"
        assert data["configured"] == False, "Email should not be configured without API key"
        
        print(f"✓ Email status: enabled={data['enabled']}, configured={data['configured']}")
    
    def test_initialize_email_service(self):
        """POST /api/email/initialize returns appropriate message"""
        response = self.session.post(f"{BASE_URL}/api/email/initialize")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message' field"
        assert "enabled" in data, "Response should contain 'enabled' field"
        
        # Without SendGrid config, should return not configured message
        assert data["enabled"] == False, "Should be disabled without SendGrid config"
        print(f"✓ Initialize email service: {data['message']}")


class TestEmailTemplates:
    """Test email templates CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login and get token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_all_templates(self):
        """GET /api/email/templates returns all default templates"""
        response = self.session.get(f"{BASE_URL}/api/email/templates")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        templates = response.json()
        assert isinstance(templates, list), "Response should be a list"
        assert len(templates) >= 4, f"Expected at least 4 default templates, got {len(templates)}"
        
        # Verify default templates exist
        template_names = [t["name"] for t in templates]
        expected_templates = ["low_balance", "transaction_complete", "welcome", "password_reset"]
        
        for expected in expected_templates:
            assert expected in template_names, f"Missing default template: {expected}"
        
        # Verify template structure
        for template in templates:
            assert "name" in template, "Template should have 'name' field"
            assert "subject" in template, "Template should have 'subject' field"
            assert "html" in template, "Template should have 'html' field"
        
        print(f"✓ Found {len(templates)} templates: {template_names}")
    
    def test_get_single_template_low_balance(self):
        """GET /api/email/templates/low_balance returns correct template"""
        response = self.session.get(f"{BASE_URL}/api/email/templates/low_balance")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        template = response.json()
        assert template["name"] == "low_balance"
        assert "Low Balance Alert" in template["subject"]
        assert "{{user_name}}" in template["html"], "Template should contain user_name variable"
        assert "{{balance}}" in template["html"], "Template should contain balance variable"
        
        print(f"✓ Low balance template: subject='{template['subject']}'")
    
    def test_get_single_template_transaction_complete(self):
        """GET /api/email/templates/transaction_complete returns correct template"""
        response = self.session.get(f"{BASE_URL}/api/email/templates/transaction_complete")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        template = response.json()
        assert template["name"] == "transaction_complete"
        assert "Charging Complete" in template["subject"]
        assert "{{tx_id}}" in template["html"], "Template should contain tx_id variable"
        
        print(f"✓ Transaction complete template: subject='{template['subject']}'")
    
    def test_get_single_template_welcome(self):
        """GET /api/email/templates/welcome returns correct template"""
        response = self.session.get(f"{BASE_URL}/api/email/templates/welcome")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        template = response.json()
        assert template["name"] == "welcome"
        assert "Welcome" in template["subject"]
        
        print(f"✓ Welcome template: subject='{template['subject']}'")
    
    def test_get_single_template_password_reset(self):
        """GET /api/email/templates/password_reset returns correct template"""
        response = self.session.get(f"{BASE_URL}/api/email/templates/password_reset")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        template = response.json()
        assert template["name"] == "password_reset"
        assert "Password Reset" in template["subject"]
        assert "{{reset_url}}" in template["html"], "Template should contain reset_url variable"
        
        print(f"✓ Password reset template: subject='{template['subject']}'")
    
    def test_get_nonexistent_template(self):
        """GET /api/email/templates/nonexistent returns 404"""
        response = self.session.get(f"{BASE_URL}/api/email/templates/nonexistent_template")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Nonexistent template returns 404")
    
    def test_create_custom_template(self):
        """POST /api/email/templates creates new template"""
        template_data = {
            "name": "TEST_custom_template",
            "subject": "Test Subject - {{test_var}}",
            "html": "<html><body>Hello {{user_name}}, this is a test.</body></html>"
        }
        
        response = self.session.post(f"{BASE_URL}/api/email/templates", json=template_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert "TEST_custom_template" in data["message"]
        
        # Verify template was created
        get_response = self.session.get(f"{BASE_URL}/api/email/templates/TEST_custom_template")
        assert get_response.status_code == 200, "Created template should be retrievable"
        
        created = get_response.json()
        assert created["name"] == "TEST_custom_template"
        assert created["subject"] == template_data["subject"]
        
        print(f"✓ Created custom template: {template_data['name']}")
    
    def test_create_duplicate_template(self):
        """POST /api/email/templates with existing name returns 400"""
        template_data = {
            "name": "low_balance",  # Already exists
            "subject": "Duplicate Subject",
            "html": "<html><body>Duplicate</body></html>"
        }
        
        response = self.session.post(f"{BASE_URL}/api/email/templates", json=template_data)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Duplicate template creation returns 400")
    
    def test_update_template(self):
        """PUT /api/email/templates/{name} updates template"""
        # First create a test template
        create_data = {
            "name": "TEST_update_template",
            "subject": "Original Subject",
            "html": "<html><body>Original content</body></html>"
        }
        self.session.post(f"{BASE_URL}/api/email/templates", json=create_data)
        
        # Update the template
        update_data = {
            "subject": "Updated Subject - {{new_var}}",
            "html": "<html><body>Updated content with {{variable}}</body></html>"
        }
        
        response = self.session.put(f"{BASE_URL}/api/email/templates/TEST_update_template", json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify update
        get_response = self.session.get(f"{BASE_URL}/api/email/templates/TEST_update_template")
        updated = get_response.json()
        assert updated["subject"] == update_data["subject"]
        assert updated["html"] == update_data["html"]
        
        print("✓ Template updated successfully")
    
    def test_update_nonexistent_template(self):
        """PUT /api/email/templates/nonexistent returns 404"""
        update_data = {
            "subject": "New Subject"
        }
        
        response = self.session.put(f"{BASE_URL}/api/email/templates/nonexistent_template_xyz", json=update_data)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Update nonexistent template returns 404")
    
    def test_delete_custom_template(self):
        """DELETE /api/email/templates/{name} deletes custom template"""
        # First create a test template
        create_data = {
            "name": "TEST_delete_template",
            "subject": "To Be Deleted",
            "html": "<html><body>Delete me</body></html>"
        }
        self.session.post(f"{BASE_URL}/api/email/templates", json=create_data)
        
        # Delete the template
        response = self.session.delete(f"{BASE_URL}/api/email/templates/TEST_delete_template")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify deletion
        get_response = self.session.get(f"{BASE_URL}/api/email/templates/TEST_delete_template")
        assert get_response.status_code == 404, "Deleted template should return 404"
        
        print("✓ Custom template deleted successfully")
    
    def test_delete_default_template_not_allowed(self):
        """DELETE /api/email/templates/{default} returns 400"""
        default_templates = ["low_balance", "transaction_complete", "welcome", "password_reset"]
        
        for template_name in default_templates:
            response = self.session.delete(f"{BASE_URL}/api/email/templates/{template_name}")
            assert response.status_code == 400, f"Expected 400 for {template_name}, got {response.status_code}"
        
        print("✓ Default templates cannot be deleted (returns 400)")
    
    def test_delete_nonexistent_template(self):
        """DELETE /api/email/templates/nonexistent returns 404"""
        response = self.session.delete(f"{BASE_URL}/api/email/templates/nonexistent_template_xyz")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Delete nonexistent template returns 404")


class TestEmailPreview:
    """Test email template preview functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login and get token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_preview_low_balance_template(self):
        """POST /api/email/preview renders low_balance template with variables"""
        preview_data = {
            "template_name": "low_balance",
            "variables": {
                "user_name": "John Doe",
                "card_number": "RFID-12345",
                "balance": "5,000",
                "topup_url": "https://example.com/topup"
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/email/preview", json=preview_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "subject" in data, "Response should contain 'subject'"
        assert "html" in data, "Response should contain 'html'"
        
        # Verify variables were substituted
        assert "John Doe" in data["html"], "user_name should be substituted"
        assert "RFID-12345" in data["html"], "card_number should be substituted"
        assert "5,000" in data["html"], "balance should be substituted"
        assert "{{user_name}}" not in data["html"], "Variables should be replaced"
        
        print(f"✓ Low balance preview rendered with variables")
    
    def test_preview_transaction_complete_template(self):
        """POST /api/email/preview renders transaction_complete template"""
        preview_data = {
            "template_name": "transaction_complete",
            "variables": {
                "user_name": "Jane Smith",
                "tx_id": "TX-2024-001",
                "station": "Station Alpha",
                "connector": "Connector 1",
                "duration": "45 minutes",
                "energy": "25.5",
                "cost": "12,750"
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/email/preview", json=preview_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "TX-2024-001" in data["html"], "tx_id should be substituted"
        assert "Station Alpha" in data["html"], "station should be substituted"
        assert "25.5" in data["html"], "energy should be substituted"
        
        print(f"✓ Transaction complete preview rendered with variables")
    
    def test_preview_welcome_template(self):
        """POST /api/email/preview renders welcome template"""
        preview_data = {
            "template_name": "welcome",
            "variables": {
                "user_name": "New User",
                "login_url": "https://example.com/login"
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/email/preview", json=preview_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "New User" in data["html"], "user_name should be substituted"
        assert "https://example.com/login" in data["html"], "login_url should be substituted"
        
        print(f"✓ Welcome preview rendered with variables")
    
    def test_preview_password_reset_template(self):
        """POST /api/email/preview renders password_reset template"""
        preview_data = {
            "template_name": "password_reset",
            "variables": {
                "user_name": "Reset User",
                "reset_url": "https://example.com/reset?token=abc123"
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/email/preview", json=preview_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "Reset User" in data["html"], "user_name should be substituted"
        assert "https://example.com/reset?token=abc123" in data["html"], "reset_url should be substituted"
        
        print(f"✓ Password reset preview rendered with variables")
    
    def test_preview_nonexistent_template(self):
        """POST /api/email/preview with nonexistent template returns 404"""
        preview_data = {
            "template_name": "nonexistent_template",
            "variables": {}
        }
        
        response = self.session.post(f"{BASE_URL}/api/email/preview", json=preview_data)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Preview nonexistent template returns 404")
    
    def test_preview_with_empty_variables(self):
        """POST /api/email/preview with empty variables keeps placeholders"""
        preview_data = {
            "template_name": "welcome",
            "variables": {}
        }
        
        response = self.session.post(f"{BASE_URL}/api/email/preview", json=preview_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Without variables, placeholders should remain
        assert "{{user_name}}" in data["html"], "Unreplaced variables should remain as placeholders"
        
        print("✓ Preview with empty variables keeps placeholders")


class TestEmailSending:
    """Test email sending functionality (expected to fail without SendGrid config)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login and get token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_send_template_email_without_config(self):
        """POST /api/email/send returns 400 without SendGrid config"""
        send_data = {
            "to_email": "test@example.com",
            "template_name": "welcome",
            "variables": {
                "user_name": "Test User",
                "login_url": "https://example.com"
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/email/send", json=send_data)
        # Should return 400 because SendGrid is not configured
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data, "Response should contain error detail"
        assert "not configured" in data["detail"].lower() or "sendgrid" in data["detail"].lower(), \
            f"Error should mention configuration issue: {data['detail']}"
        
        print(f"✓ Send email without config returns 400: {data['detail']}")
    
    def test_send_custom_email_without_config(self):
        """POST /api/email/send-custom returns 400 without SendGrid config"""
        send_data = {
            "to_email": "test@example.com",
            "subject": "Test Subject",
            "html_content": "<html><body>Test content</body></html>"
        }
        
        response = self.session.post(f"{BASE_URL}/api/email/send-custom", json=send_data)
        # Should return 400 because SendGrid is not configured
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data, "Response should contain error detail"
        
        print(f"✓ Send custom email without config returns 400: {data['detail']}")
    
    def test_send_test_email_without_config(self):
        """POST /api/email/test returns 400 without SendGrid config"""
        response = self.session.post(f"{BASE_URL}/api/email/test?to_email=test@example.com")
        # Should return 400 because SendGrid is not configured
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data, "Response should contain error detail"
        
        print(f"✓ Send test email without config returns 400: {data['detail']}")
    
    def test_send_email_invalid_email_format(self):
        """POST /api/email/send with invalid email returns 422"""
        send_data = {
            "to_email": "invalid-email",  # Invalid email format
            "template_name": "welcome",
            "variables": {}
        }
        
        response = self.session.post(f"{BASE_URL}/api/email/send", json=send_data)
        # Should return 422 for validation error
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ Send email with invalid email format returns 422")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login and get token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            token = response.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_cleanup_test_templates(self):
        """Clean up TEST_ prefixed templates"""
        # Get all templates
        response = self.session.get(f"{BASE_URL}/api/email/templates")
        if response.status_code == 200:
            templates = response.json()
            test_templates = [t["name"] for t in templates if t["name"].startswith("TEST_")]
            
            for template_name in test_templates:
                delete_response = self.session.delete(f"{BASE_URL}/api/email/templates/{template_name}")
                if delete_response.status_code == 200:
                    print(f"  Cleaned up: {template_name}")
        
        print("✓ Test templates cleanup complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
