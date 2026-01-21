"""Utility functions"""
import logging
import httpx
from datetime import datetime, timezone
import uuid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

async def send_low_balance_email(db, card: dict, user_email: str, user_name: str):
    """Send low balance notification email via SendGrid"""
    settings = await db.settings.find_one({"type": "sendgrid"}, {"_id": 0})
    
    if not settings or not settings.get("enabled") or not settings.get("api_key"):
        logging.warning("SendGrid not configured, skipping email notification")
        return False
    
    try:
        sg = SendGridAPIClient(settings["api_key"])
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #EA580C; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">⚡ EV Charging System</h1>
            </div>
            <div style="padding: 30px; background-color: #f8f9fa;">
                <h2 style="color: #333;">Low Balance Alert</h2>
                <p>Hello {user_name},</p>
                <p>Your RFID card <strong>{card.get('card_number')}</strong> has a low balance.</p>
                
                <div style="background-color: #fff; border: 1px solid #ddd; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0; font-size: 14px; color: #666;">Current Balance</p>
                    <p style="margin: 5px 0 0 0; font-size: 32px; font-weight: bold; color: #DC2626;">
                        $ {card.get('balance', 0):,.0f} COP
                    </p>
                    <p style="margin: 10px 0 0 0; font-size: 12px; color: #999;">
                        Threshold: $ {card.get('low_balance_threshold', 10000):,.0f} COP
                    </p>
                </div>
                
                <p>Please top up your card to continue using the charging service without interruption.</p>
                
                <p style="color: #666; font-size: 12px; margin-top: 30px;">
                    This is an automated notification from EV Charging System.<br>
                    Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        message = Mail(
            from_email=(settings.get("sender_email"), settings.get("sender_name", "EV Charging System")),
            to_emails=user_email,
            subject=f"⚠️ Low Balance Alert - RFID Card {card.get('card_number')}",
            html_content=html_content
        )
        
        response = sg.send(message)
        logging.info(f"Low balance email sent to {user_email}, status: {response.status_code}")
        return response.status_code == 202
        
    except Exception as e:
        logging.error(f"Failed to send low balance email: {str(e)}")
        return False

async def trigger_invoice_webhook(db, ocpp_tx: dict, energy: float, cost: float, 
                                 connector_type: str, stop_time: str, rfid_card: dict = None):
    """Send transaction data to configured webhook endpoint"""
    webhook_config = await db.invoice_webhook_config.find_one({}, {"_id": 0})
    
    if not webhook_config or not webhook_config.get("enabled"):
        return
    
    webhook_url = webhook_config.get("webhook_url")
    if not webhook_url:
        return
    
    # Get user info if RFID card linked
    user_email = None
    if rfid_card:
        user = await db.users.find_one({"id": rfid_card.get("user_id")}, {"_id": 0, "email": 1})
        user_email = user.get("email") if user else None
    
    payload = {
        "event_type": "transaction_completed",
        "transaction_id": str(ocpp_tx.get("transaction_id")),
        "tx_id": f"OCPP-{ocpp_tx.get('transaction_id')}",
        "account": rfid_card.get("card_number") if rfid_card else ocpp_tx.get("id_tag"),
        "station": ocpp_tx.get("charger_id", "Unknown"),
        "connector": str(ocpp_tx.get("connector_id", 1)),
        "connector_type": connector_type,
        "start_time": ocpp_tx.get("start_timestamp"),
        "end_time": stop_time,
        "charging_duration": None,
        "meter_value": energy,
        "cost": cost,
        "payment_status": "PAID" if rfid_card else "UNPAID",
        "payment_type": "RFID" if rfid_card else None,
        "payment_date": stop_time if rfid_card else None,
        "rfid_card_number": rfid_card.get("card_number") if rfid_card else None,
        "user_email": user_email,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        headers = {"Content-Type": "application/json"}
        if webhook_config.get("api_key"):
            headers["X-API-Key"] = webhook_config["api_key"]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, headers=headers, timeout=10.0)
            
            await db.invoice_webhook_logs.insert_one({
                "id": str(uuid.uuid4()),
                "transaction_id": str(ocpp_tx.get("transaction_id")),
                "webhook_url": webhook_url,
                "payload": payload,
                "response_status": response.status_code,
                "response_body": response.text[:500],
                "created_at": datetime.now(timezone.utc).isoformat()
            })
    except Exception as e:
        logging.error(f"Invoice webhook error: {str(e)}")
        await db.invoice_webhook_logs.insert_one({
            "id": str(uuid.uuid4()),
            "transaction_id": str(ocpp_tx.get("transaction_id")),
            "webhook_url": webhook_url,
            "payload": payload,
            "error": str(e),
            "created_at": datetime.now(timezone.utc).isoformat()
        })

async def log_rfid_history(db, card_id: str, card_number: str, history_type: str, 
                          amount: float, balance_before: float, balance_after: float,
                          description: str, reference_id: str = None):
    """Log RFID card transaction history"""
    history_record = {
        "id": str(uuid.uuid4()),
        "card_id": card_id,
        "card_number": card_number,
        "type": history_type,
        "amount": amount,
        "balance_before": balance_before,
        "balance_after": balance_after,
        "description": description,
        "reference_id": reference_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.rfid_history.insert_one(history_record)
    return history_record

async def get_pricing_for_user(db, user_id: str, connector_type: str) -> float:
    """Get pricing for user based on their pricing group"""
    from database import CONNECTOR_TYPE_PRICING
    
    # Get user's pricing group
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "pricing_group_id": 1})
    
    if user and user.get("pricing_group_id"):
        group = await db.pricing_groups.find_one({"id": user["pricing_group_id"]}, {"_id": 0})
        if group and group.get("connector_pricing"):
            pricing = group["connector_pricing"]
            return pricing.get(connector_type, CONNECTOR_TYPE_PRICING.get(connector_type, 2000.0))
    
    # Fall back to default pricing
    return CONNECTOR_TYPE_PRICING.get(connector_type, 2000.0)
