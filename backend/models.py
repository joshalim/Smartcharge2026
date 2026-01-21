"""Pydantic models for the application"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional

class UserRole:
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"

# Auth Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = UserRole.USER

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str
    pricing_group_id: Optional[str] = None
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: User

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    pricing_group_id: Optional[str] = None

# Pricing Models
class PricingRule(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    account: str
    connector: str
    price_per_kwh: float
    created_at: str

class PricingRuleCreate(BaseModel):
    account: str
    connector: str
    price_per_kwh: float

# Pricing Group Models
class ConnectorPricing(BaseModel):
    CCS2: float = 2500.0
    CHADEMO: float = 2000.0
    J1772: float = 1500.0

class PricingGroup(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    description: Optional[str] = None
    connector_pricing: ConnectorPricing
    created_at: str
    updated_at: Optional[str] = None

class PricingGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    connector_pricing: ConnectorPricing

class PricingGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    connector_pricing: Optional[ConnectorPricing] = None

# Transaction Models
class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    tx_id: str
    station: str
    connector: str
    connector_type: Optional[str] = None
    account: str
    start_time: str
    end_time: str
    meter_value: float
    cost: float
    payment_status: str
    payment_type: Optional[str] = None
    payment_date: Optional[str] = None
    charging_duration: Optional[str] = None
    created_at: str

class TransactionUpdate(BaseModel):
    payment_status: Optional[str] = None
    payment_type: Optional[str] = None
    payment_date: Optional[str] = None
    cost: Optional[float] = None

class BulkPaymentUpdate(BaseModel):
    transaction_ids: List[str]
    payment_status: str
    payment_type: str
    payment_date: str

# Charger Models
class Charger(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    location: str
    model: Optional[str] = None
    serial_number: Optional[str] = None
    connector_types: List[str] = []
    max_power: float = 0
    status: str = "Available"
    created_at: str

class ChargerCreate(BaseModel):
    name: str
    location: str
    model: Optional[str] = None
    serial_number: Optional[str] = None
    connector_types: List[str] = []
    max_power: float = 0
    status: str = "Available"

class ChargerUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    connector_types: Optional[List[str]] = None
    max_power: Optional[float] = None
    status: Optional[str] = None

# RFID Card Models
class RFIDCard(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    card_number: str
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    balance: float
    status: str
    low_balance_threshold: float = 10000.0
    created_at: str

class RFIDCardCreate(BaseModel):
    card_number: str
    user_id: str
    balance: float = 0.0
    status: str = "active"
    low_balance_threshold: float = 10000.0

class RFIDCardUpdate(BaseModel):
    card_number: Optional[str] = None
    status: Optional[str] = None
    low_balance_threshold: Optional[float] = None

class RFIDTopUp(BaseModel):
    amount: float

class RFIDHistory(BaseModel):
    id: str
    card_id: str
    card_number: str
    type: str
    amount: float
    balance_before: float
    balance_after: float
    description: str
    reference_id: Optional[str] = None
    created_at: str

# OCPP Models
class BootNotification(BaseModel):
    chargePointVendor: str
    chargePointModel: str
    chargePointSerialNumber: Optional[str] = None
    firmwareVersion: Optional[str] = None

class StartTransactionRequest(BaseModel):
    connectorId: int
    idTag: str
    meterStart: int
    timestamp: str

class StopTransactionRequest(BaseModel):
    transactionId: int
    meterStop: int
    timestamp: str
    idTag: Optional[str] = None

class RemoteStartRequest(BaseModel):
    charger_id: str
    connector_id: int
    id_tag: str

class RemoteStopRequest(BaseModel):
    transaction_id: int

class MeterValuesRequest(BaseModel):
    connectorId: int
    transactionId: Optional[int] = None
    meterValue: List[dict]

class StatusNotificationRequest(BaseModel):
    connectorId: int
    errorCode: str
    status: str
    timestamp: Optional[str] = None

# PayU Models
class PayUTopUpRequest(BaseModel):
    rfid_card_id: str
    amount: float
    buyer_name: str
    buyer_email: str
    buyer_phone: str

# Settings Models
class PayUSettings(BaseModel):
    api_key: str
    api_login: str
    merchant_id: str
    account_id: str
    test_mode: bool = True

class SendGridSettings(BaseModel):
    api_key: str
    sender_email: str
    sender_name: str = "EV Charging System"
    enabled: bool = True

class InvoiceWebhookConfig(BaseModel):
    webhook_url: str
    api_key: Optional[str] = None
    enabled: bool = True

# Report Models
class ReportFilters(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    account: Optional[str] = None
    connector_type: Optional[str] = None
    payment_type: Optional[str] = None
    payment_status: Optional[str] = None

class ReportData(BaseModel):
    summary: dict
    by_account: List[dict]
    by_connector: List[dict]
    by_payment_type: List[dict]
    transactions: List[Transaction]
