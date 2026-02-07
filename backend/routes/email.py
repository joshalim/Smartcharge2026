"""
Email routes - Template management and sending
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict

from services.email_service import email_service
from routes.auth import require_role, UserResponse

router = APIRouter(prefix="/email", tags=["Email"])


# Pydantic Models
class EmailTemplate(BaseModel):
    name: str
    subject: str
    html: str


class EmailTemplateUpdate(BaseModel):
    subject: Optional[str] = None
    html: Optional[str] = None


class SendEmailRequest(BaseModel):
    to_email: EmailStr
    template_name: str
    variables: Dict[str, str] = {}


class SendCustomEmailRequest(BaseModel):
    to_email: EmailStr
    subject: str
    html_content: str


class EmailStatusResponse(BaseModel):
    enabled: bool
    configured: bool
    sender_email: Optional[str] = None
    sender_name: Optional[str] = None


class EmailPreviewRequest(BaseModel):
    template_name: str
    variables: Dict[str, str] = {}


# Routes
@router.get("/status", response_model=EmailStatusResponse)
async def get_email_status(current_user: UserResponse = Depends(require_role("admin"))):
    """Get email service status"""
    await email_service.initialize()
    
    return EmailStatusResponse(
        enabled=email_service.is_enabled(),
        configured=email_service._client is not None,
        sender_email=email_service._sender_email,
        sender_name=email_service._sender_name
    )


@router.post("/initialize")
async def initialize_email_service(current_user: UserResponse = Depends(require_role("admin"))):
    """Initialize or reinitialize email service from settings"""
    success = await email_service.initialize()
    
    if success:
        return {"message": "Email service initialized successfully", "enabled": True}
    else:
        return {"message": "Email service not configured. Please set SendGrid API key in settings.", "enabled": False}


@router.get("/templates", response_model=List[EmailTemplate])
async def get_email_templates(current_user: UserResponse = Depends(require_role("admin"))):
    """Get all email templates"""
    templates = email_service.get_all_templates()
    
    return [
        EmailTemplate(name=name, subject=data["subject"], html=data["html"])
        for name, data in templates.items()
    ]


@router.get("/templates/{template_name}", response_model=EmailTemplate)
async def get_email_template(
    template_name: str,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Get a specific email template"""
    template = email_service.get_template(template_name)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return EmailTemplate(
        name=template_name,
        subject=template["subject"],
        html=template["html"]
    )


@router.put("/templates/{template_name}")
async def update_email_template(
    template_name: str,
    template_data: EmailTemplateUpdate,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Update an email template"""
    existing = email_service.get_template(template_name)
    
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    
    subject = template_data.subject or existing["subject"]
    html = template_data.html or existing["html"]
    
    email_service.set_template(template_name, subject, html)
    
    return {"message": f"Template '{template_name}' updated successfully"}


@router.post("/templates")
async def create_email_template(
    template: EmailTemplate,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Create a new email template"""
    existing = email_service.get_template(template.name)
    
    if existing:
        raise HTTPException(status_code=400, detail="Template already exists")
    
    email_service.set_template(template.name, template.subject, template.html)
    
    return {"message": f"Template '{template.name}' created successfully"}


@router.delete("/templates/{template_name}")
async def delete_email_template(
    template_name: str,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Delete an email template"""
    # Don't allow deletion of default templates
    default_templates = ["low_balance", "transaction_complete", "welcome", "password_reset"]
    
    if template_name in default_templates:
        raise HTTPException(status_code=400, detail="Cannot delete default templates")
    
    existing = email_service.get_template(template_name)
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Remove from templates dict
    del email_service._templates[template_name]
    
    return {"message": f"Template '{template_name}' deleted successfully"}


@router.post("/preview")
async def preview_email(
    request: EmailPreviewRequest,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Preview an email template with variables"""
    rendered = email_service.render_template(request.template_name, request.variables)
    
    if not rendered:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "subject": rendered["subject"],
        "html": rendered["html"]
    }


@router.post("/send")
async def send_template_email(
    request: SendEmailRequest,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Send an email using a template"""
    await email_service.initialize()
    
    if not email_service.is_enabled():
        raise HTTPException(
            status_code=400, 
            detail="Email service not configured. Please set SendGrid API key in settings."
        )
    
    success = await email_service.send_template_email(
        request.to_email,
        request.template_name,
        request.variables
    )
    
    if success:
        return {"message": f"Email sent successfully to {request.to_email}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email")


@router.post("/send-custom")
async def send_custom_email(
    request: SendCustomEmailRequest,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Send a custom email (not using templates)"""
    await email_service.initialize()
    
    if not email_service.is_enabled():
        raise HTTPException(
            status_code=400, 
            detail="Email service not configured. Please set SendGrid API key in settings."
        )
    
    success = await email_service.send_email(
        request.to_email,
        request.subject,
        request.html_content
    )
    
    if success:
        return {"message": f"Email sent successfully to {request.to_email}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email")


@router.post("/test")
async def send_test_email(
    to_email: EmailStr,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Send a test email to verify configuration"""
    await email_service.initialize()
    
    if not email_service.is_enabled():
        raise HTTPException(
            status_code=400, 
            detail="Email service not configured. Please set SendGrid API key in settings."
        )
    
    test_html = """
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h1 style="color: #f97316;">🎉 SmartCharge Email Test</h1>
        <p>This is a test email from SmartCharge.</p>
        <p>If you received this email, your SendGrid configuration is working correctly!</p>
        <hr>
        <p style="color: #666; font-size: 12px;">
            Sent at: """ + str(email_service._sender_email) + """
        </p>
    </body>
    </html>
    """
    
    success = await email_service.send_email(
        to_email,
        "🧪 SmartCharge Email Test",
        test_html
    )
    
    if success:
        return {"message": f"Test email sent successfully to {to_email}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test email")
