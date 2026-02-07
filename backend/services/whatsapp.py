"""
WhatsApp Messaging Service using Twilio
Sends notifications for: payment confirmation, charging started, charging completed, low balance alerts
"""
import os
import asyncio
from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')  # Twilio sandbox number

# Message templates
TEMPLATES = {
    'payment_confirmed': {
        'es': '✅ *Pago Confirmado*\n\nHola {name}!\nTu pago de ${amount:,.0f} COP ha sido confirmado.\n\nSesión: {session_id}\nCargador: {charger}\nConector: {connector}\n\nGracias por usar SmartCharge! ⚡',
        'en': '✅ *Payment Confirmed*\n\nHi {name}!\nYour payment of ${amount:,.0f} COP has been confirmed.\n\nSession: {session_id}\nCharger: {charger}\nConnector: {connector}\n\nThank you for using SmartCharge! ⚡'
    },
    'charging_started': {
        'es': '⚡ *Carga Iniciada*\n\nHola {name}!\nTu sesión de carga ha comenzado.\n\nSesión: {session_id}\nCargador: {charger}\nConector: {connector}\n\nTe notificaremos cuando termine. 🔋',
        'en': '⚡ *Charging Started*\n\nHi {name}!\nYour charging session has started.\n\nSession: {session_id}\nCharger: {charger}\nConnector: {connector}\n\nWe\'ll notify you when it\'s done. 🔋'
    },
    'charging_completed': {
        'es': '🔋 *Carga Completada*\n\nHola {name}!\nTu carga ha finalizado.\n\nSesión: {session_id}\nEnergía: {energy:.2f} kWh\nCosto: ${cost:,.0f} COP\nDuración: {duration}\n\nGracias por cargar con nosotros! 🚗⚡',
        'en': '🔋 *Charging Completed*\n\nHi {name}!\nYour charging session has finished.\n\nSession: {session_id}\nEnergy: {energy:.2f} kWh\nCost: ${cost:,.0f} COP\nDuration: {duration}\n\nThank you for charging with us! 🚗⚡'
    },
    'low_balance': {
        'es': '⚠️ *Saldo Bajo*\n\nHola {name}!\nTu saldo RFID está bajo.\n\nSaldo actual: ${balance:,.0f} COP\nTarjeta: {card_number}\n\nRecarga tu saldo para seguir cargando sin interrupciones.',
        'en': '⚠️ *Low Balance*\n\nHi {name}!\nYour RFID balance is low.\n\nCurrent balance: ${balance:,.0f} COP\nCard: {card_number}\n\nTop up to continue charging without interruptions.'
    },
    'balance_topped_up': {
        'es': '💰 *Recarga Exitosa*\n\nHola {name}!\nTu saldo ha sido recargado.\n\nMonto: +${amount:,.0f} COP\nNuevo saldo: ${new_balance:,.0f} COP\nTarjeta: {card_number}\n\n¡Listo para cargar! ⚡',
        'en': '💰 *Top-up Successful*\n\nHi {name}!\nYour balance has been topped up.\n\nAmount: +${amount:,.0f} COP\nNew balance: ${new_balance:,.0f} COP\nCard: {card_number}\n\nReady to charge! ⚡'
    },
    'welcome': {
        'es': '👋 *Bienvenido a SmartCharge*\n\nHola {name}!\nTu cuenta ha sido creada exitosamente.\n\nAhora puedes:\n• Cargar tu vehículo con código QR\n• Administrar tu tarjeta RFID\n• Ver tu historial de cargas\n\n¡Gracias por unirte! 🚗⚡',
        'en': '👋 *Welcome to SmartCharge*\n\nHi {name}!\nYour account has been created successfully.\n\nYou can now:\n• Charge your vehicle with QR code\n• Manage your RFID card\n• View your charging history\n\nThanks for joining! 🚗⚡'
    }
}


def format_phone_for_whatsapp(phone: str) -> str:
    """Format phone number for WhatsApp (must include country code)"""
    if not phone:
        return None
    
    # Remove spaces, dashes, parentheses
    phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    # Ensure it starts with +
    if not phone.startswith('+'):
        # Assume Colombia if no country code
        if phone.startswith('57'):
            phone = '+' + phone
        else:
            phone = '+57' + phone
    
    return f"whatsapp:{phone}"


def get_twilio_client() -> Optional[Client]:
    """Get Twilio client if credentials are configured"""
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        try:
            return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        except Exception as e:
            print(f"Failed to create Twilio client: {e}")
    return None


async def send_whatsapp_message(
    to_phone: str,
    template: str,
    language: str = 'es',
    **kwargs
) -> dict:
    """
    Send a WhatsApp message using Twilio
    
    Args:
        to_phone: Recipient phone number (with or without country code)
        template: Template name (payment_confirmed, charging_started, etc.)
        language: 'es' for Spanish, 'en' for English
        **kwargs: Variables to fill in the template
    
    Returns:
        dict with status and message_sid or error
    """
    client = get_twilio_client()
    if not client:
        return {"success": False, "error": "Twilio not configured"}
    
    # Format phone number
    whatsapp_to = format_phone_for_whatsapp(to_phone)
    if not whatsapp_to:
        return {"success": False, "error": "Invalid phone number"}
    
    # Get template
    template_data = TEMPLATES.get(template)
    if not template_data:
        return {"success": False, "error": f"Unknown template: {template}"}
    
    message_template = template_data.get(language, template_data.get('es'))
    
    try:
        # Format message with provided data
        message_body = message_template.format(**kwargs)
        
        # Send via Twilio (run in executor to not block async)
        loop = asyncio.get_event_loop()
        message = await loop.run_in_executor(
            None,
            lambda: client.messages.create(
                body=message_body,
                from_=TWILIO_WHATSAPP_NUMBER,
                to=whatsapp_to
            )
        )
        
        return {
            "success": True,
            "message_sid": message.sid,
            "status": message.status
        }
        
    except TwilioRestException as e:
        print(f"Twilio error: {e}")
        return {"success": False, "error": str(e)}
    except KeyError as e:
        return {"success": False, "error": f"Missing template variable: {e}"}
    except Exception as e:
        print(f"WhatsApp send error: {e}")
        return {"success": False, "error": str(e)}


# Convenience functions for specific message types
async def send_payment_confirmed(phone: str, name: str, amount: float, session_id: str, charger: str, connector: str, language: str = 'es'):
    return await send_whatsapp_message(
        phone, 'payment_confirmed', language,
        name=name, amount=amount, session_id=session_id, charger=charger, connector=connector
    )


async def send_charging_started(phone: str, name: str, session_id: str, charger: str, connector: str, language: str = 'es'):
    return await send_whatsapp_message(
        phone, 'charging_started', language,
        name=name, session_id=session_id, charger=charger, connector=connector
    )


async def send_charging_completed(phone: str, name: str, session_id: str, energy: float, cost: float, duration: str, language: str = 'es'):
    return await send_whatsapp_message(
        phone, 'charging_completed', language,
        name=name, session_id=session_id, energy=energy, cost=cost, duration=duration
    )


async def send_low_balance_alert(phone: str, name: str, balance: float, card_number: str, language: str = 'es'):
    return await send_whatsapp_message(
        phone, 'low_balance', language,
        name=name, balance=balance, card_number=card_number
    )


async def send_balance_topped_up(phone: str, name: str, amount: float, new_balance: float, card_number: str, language: str = 'es'):
    return await send_whatsapp_message(
        phone, 'balance_topped_up', language,
        name=name, amount=amount, new_balance=new_balance, card_number=card_number
    )


async def send_welcome_message(phone: str, name: str, language: str = 'es'):
    return await send_whatsapp_message(
        phone, 'welcome', language,
        name=name
    )
