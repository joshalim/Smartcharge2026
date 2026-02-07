"""
Email Service with Customizable Templates
Supports SendGrid for sending emails with HTML templates
"""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent

from sqlalchemy import select
from database import async_session, Settings

logger = logging.getLogger(__name__)


# Default email templates
DEFAULT_TEMPLATES = {
    "low_balance": {
        "subject": "⚡ Low Balance Alert - SmartCharge",
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #f97316, #ea580c); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }
        .balance-box { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; }
        .btn { display: inline-block; background: #f97316; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin-top: 20px; }
        .footer { text-align: center; color: #64748b; font-size: 12px; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ SmartCharge</h1>
            <p>Low Balance Alert</p>
        </div>
        <div class="content">
            <p>Hello <strong>{{user_name}}</strong>,</p>
            <p>Your RFID card balance is running low. Please top up to continue using our charging services.</p>
            
            <div class="balance-box">
                <p><strong>Card Number:</strong> {{card_number}}</p>
                <p><strong>Current Balance:</strong> ${{balance}} COP</p>
                <p><strong>Minimum Recommended:</strong> $10,000 COP</p>
            </div>
            
            <p>Top up your card now to avoid any interruption in your charging sessions.</p>
            
            <a href="{{topup_url}}" class="btn">Top Up Now</a>
            
            <div class="footer">
                <p>This is an automated message from SmartCharge.</p>
                <p>If you have any questions, please contact support.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
    },
    
    "transaction_complete": {
        "subject": "✅ Charging Complete - SmartCharge",
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }
        .summary-box { background: white; border: 1px solid #e2e8f0; padding: 20px; margin: 20px 0; border-radius: 8px; }
        .summary-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f1f5f9; }
        .summary-row:last-child { border-bottom: none; }
        .total { font-size: 1.2em; font-weight: bold; color: #f97316; }
        .footer { text-align: center; color: #64748b; font-size: 12px; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Charging Complete</h1>
            <p>Transaction #{{tx_id}}</p>
        </div>
        <div class="content">
            <p>Hello <strong>{{user_name}}</strong>,</p>
            <p>Your charging session has been completed successfully.</p>
            
            <div class="summary-box">
                <div class="summary-row">
                    <span>Station</span>
                    <span><strong>{{station}}</strong></span>
                </div>
                <div class="summary-row">
                    <span>Connector</span>
                    <span>{{connector}}</span>
                </div>
                <div class="summary-row">
                    <span>Duration</span>
                    <span>{{duration}}</span>
                </div>
                <div class="summary-row">
                    <span>Energy Consumed</span>
                    <span>{{energy}} kWh</span>
                </div>
                <div class="summary-row total">
                    <span>Total Cost</span>
                    <span>${{cost}} COP</span>
                </div>
            </div>
            
            <p>Thank you for using SmartCharge!</p>
            
            <div class="footer">
                <p>This is an automated receipt from SmartCharge.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
    },
    
    "welcome": {
        "subject": "🎉 Welcome to SmartCharge!",
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #f97316, #ea580c); color: white; padding: 40px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }
        .feature { display: flex; align-items: center; margin: 15px 0; }
        .feature-icon { font-size: 24px; margin-right: 15px; }
        .btn { display: inline-block; background: #f97316; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin-top: 20px; }
        .footer { text-align: center; color: #64748b; font-size: 12px; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Welcome to SmartCharge!</h1>
            <p>Your EV Charging Management Solution</p>
        </div>
        <div class="content">
            <p>Hello <strong>{{user_name}}</strong>,</p>
            <p>Welcome to SmartCharge! Your account has been created successfully.</p>
            
            <h3>Getting Started:</h3>
            <div class="feature">
                <span class="feature-icon">🔌</span>
                <span>Find nearby charging stations</span>
            </div>
            <div class="feature">
                <span class="feature-icon">💳</span>
                <span>Register your RFID card</span>
            </div>
            <div class="feature">
                <span class="feature-icon">⚡</span>
                <span>Start charging your EV</span>
            </div>
            <div class="feature">
                <span class="feature-icon">📊</span>
                <span>Track your charging history</span>
            </div>
            
            <a href="{{login_url}}" class="btn">Login to Dashboard</a>
            
            <div class="footer">
                <p>If you have any questions, please contact our support team.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
    },
    
    "password_reset": {
        "subject": "🔐 Password Reset Request - SmartCharge",
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #6366f1, #4f46e5); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }
        .btn { display: inline-block; background: #6366f1; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .warning { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; }
        .footer { text-align: center; color: #64748b; font-size: 12px; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Password Reset</h1>
        </div>
        <div class="content">
            <p>Hello <strong>{{user_name}}</strong>,</p>
            <p>We received a request to reset your password. Click the button below to set a new password:</p>
            
            <center>
                <a href="{{reset_url}}" class="btn">Reset Password</a>
            </center>
            
            <div class="warning">
                <p><strong>Note:</strong> This link will expire in 1 hour.</p>
                <p>If you didn't request this, please ignore this email or contact support.</p>
            </div>
            
            <div class="footer">
                <p>This is an automated message from SmartCharge.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
    }
}


class EmailService:
    """Email service with SendGrid integration"""
    
    def __init__(self):
        self._client = None
        self._sender_email = None
        self._sender_name = None
        self._enabled = False
        self._templates = DEFAULT_TEMPLATES.copy()
    
    async def initialize(self):
        """Initialize SendGrid client from database settings"""
        async with async_session() as session:
            result = await session.execute(
                select(Settings).where(Settings.type == "sendgrid")
            )
            settings = result.scalar_one_or_none()
            
            if settings and settings.api_key:
                self._client = SendGridAPIClient(settings.api_key)
                self._sender_email = settings.sender_email or "noreply@smartcharge.com"
                self._sender_name = settings.sender_name or "SmartCharge"
                self._enabled = settings.enabled if settings.enabled is not None else True
                logger.info("SendGrid initialized successfully")
                return True
            else:
                logger.warning("SendGrid not configured")
                return False
    
    def is_enabled(self) -> bool:
        """Check if email service is enabled"""
        return self._enabled and self._client is not None
    
    def get_template(self, template_name: str) -> Optional[Dict]:
        """Get email template by name"""
        return self._templates.get(template_name)
    
    def set_template(self, template_name: str, subject: str, html: str):
        """Set or update email template"""
        self._templates[template_name] = {
            "subject": subject,
            "html": html
        }
    
    def get_all_templates(self) -> Dict[str, Dict]:
        """Get all available templates"""
        return self._templates.copy()
    
    def render_template(self, template_name: str, variables: Dict[str, Any]) -> Optional[Dict]:
        """Render template with variables"""
        template = self.get_template(template_name)
        if not template:
            return None
        
        subject = template["subject"]
        html = template["html"]
        
        # Replace variables
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            subject = subject.replace(placeholder, str(value))
            html = html.replace(placeholder, str(value))
        
        return {"subject": subject, "html": html}
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None
    ) -> bool:
        """Send email via SendGrid"""
        if not self.is_enabled():
            logger.warning("Email service not enabled")
            return False
        
        try:
            message = Mail(
                from_email=Email(from_email or self._sender_email, from_name or self._sender_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=HtmlContent(html_content)
            )
            
            response = self._client.send(message)
            logger.info(f"Email sent to {to_email}: {response.status_code}")
            return response.status_code in [200, 201, 202]
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def send_template_email(
        self, 
        to_email: str, 
        template_name: str, 
        variables: Dict[str, Any]
    ) -> bool:
        """Send email using a template"""
        rendered = self.render_template(template_name, variables)
        if not rendered:
            logger.error(f"Template not found: {template_name}")
            return False
        
        return await self.send_email(to_email, rendered["subject"], rendered["html"])
    
    # Convenience methods for common emails
    async def send_low_balance_alert(
        self, 
        to_email: str, 
        user_name: str, 
        card_number: str, 
        balance: float,
        topup_url: str = "#"
    ) -> bool:
        """Send low balance alert email"""
        return await self.send_template_email(
            to_email,
            "low_balance",
            {
                "user_name": user_name,
                "card_number": card_number,
                "balance": f"{balance:,.0f}",
                "topup_url": topup_url
            }
        )
    
    async def send_transaction_receipt(
        self, 
        to_email: str, 
        user_name: str,
        tx_id: str,
        station: str,
        connector: str,
        duration: str,
        energy: float,
        cost: float
    ) -> bool:
        """Send transaction receipt email"""
        return await self.send_template_email(
            to_email,
            "transaction_complete",
            {
                "user_name": user_name,
                "tx_id": tx_id,
                "station": station,
                "connector": connector,
                "duration": duration,
                "energy": f"{energy:.2f}",
                "cost": f"{cost:,.0f}"
            }
        )
    
    async def send_welcome_email(
        self, 
        to_email: str, 
        user_name: str,
        login_url: str = "#"
    ) -> bool:
        """Send welcome email to new user"""
        return await self.send_template_email(
            to_email,
            "welcome",
            {
                "user_name": user_name,
                "login_url": login_url
            }
        )
    
    async def send_password_reset(
        self, 
        to_email: str, 
        user_name: str,
        reset_url: str
    ) -> bool:
        """Send password reset email"""
        return await self.send_template_email(
            to_email,
            "password_reset",
            {
                "user_name": user_name,
                "reset_url": reset_url
            }
        )


# Global email service instance
email_service = EmailService()
