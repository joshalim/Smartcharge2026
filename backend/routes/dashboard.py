"""
Dashboard and statistics routes (MongoDB)
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone

from database import get_db

from routes.auth import get_current_user, UserResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# Pydantic Models
class TransactionResponse(BaseModel):
    id: str
    tx_id: Optional[str] = None
    station: Optional[str] = None
    connector: Optional[str] = None
    connector_type: Optional[str] = None
    account: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    meter_value: float = 0
    charging_duration: Optional[str] = None
    cost: float = 0
    payment_status: str = "PENDING"
    payment_type: Optional[str] = None
    payment_date: Optional[str] = None
    created_at: Optional[str] = None


def transaction_to_response(tx: dict) -> TransactionResponse:
    created_at = tx.get('created_at')
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    
    return TransactionResponse(
        id=tx.get('id', ''),
        tx_id=tx.get('tx_id'),
        station=tx.get('station'),
        connector=tx.get('connector'),
        connector_type=tx.get('connector_type'),
        account=tx.get('account'),
        start_time=tx.get('start_time'),
        end_time=tx.get('end_time'),
        meter_value=tx.get('meter_value', 0),
        charging_duration=tx.get('charging_duration'),
        cost=tx.get('cost', 0),
        payment_status=tx.get('payment_status', 'PENDING'),
        payment_type=tx.get('payment_type'),
        payment_date=tx.get('payment_date'),
        created_at=created_at
    )


class DashboardStats(BaseModel):
    total_transactions: int
    total_energy: float
    total_revenue: float
    paid_revenue: float
    unpaid_revenue: float
    active_stations: int
    unique_accounts: int
    payment_breakdown: dict
    recent_transactions: List[TransactionResponse]


# Routes
@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: UserResponse = Depends(get_current_user)):
    """Get dashboard statistics"""
    db = await get_db()
    
    # Total transactions
    total_transactions = await db.transactions.count_documents({})
    
    # Total energy and revenue using aggregation
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_energy": {"$sum": {"$ifNull": ["$meter_value", 0]}},
                "total_revenue": {"$sum": {"$ifNull": ["$cost", 0]}}
            }
        }
    ]
    totals = await db.transactions.aggregate(pipeline).to_list(1)
    total_energy = totals[0]['total_energy'] if totals else 0
    total_revenue = totals[0]['total_revenue'] if totals else 0
    
    # Paid revenue
    paid_pipeline = [
        {"$match": {"payment_status": "PAID"}},
        {
            "$group": {
                "_id": None,
                "paid_revenue": {"$sum": {"$ifNull": ["$cost", 0]}}
            }
        }
    ]
    paid_totals = await db.transactions.aggregate(paid_pipeline).to_list(1)
    paid_revenue = paid_totals[0]['paid_revenue'] if paid_totals else 0
    unpaid_revenue = total_revenue - paid_revenue
    
    # Unique stations
    stations = await db.transactions.distinct("station")
    active_stations = len([s for s in stations if s])
    
    # Unique accounts
    accounts = await db.transactions.distinct("account")
    unique_accounts = len([a for a in accounts if a])
    
    # Payment breakdown
    payment_pipeline = [
        {"$match": {"payment_status": "PAID", "payment_type": {"$ne": None}}},
        {
            "$group": {
                "_id": "$payment_type",
                "count": {"$sum": 1},
                "amount": {"$sum": {"$ifNull": ["$cost", 0]}}
            }
        }
    ]
    payment_result = await db.transactions.aggregate(payment_pipeline).to_list(100)
    payment_breakdown = {}
    for row in payment_result:
        if row['_id']:
            payment_breakdown[row['_id']] = {
                "count": row['count'],
                "amount": float(row['amount'] or 0)
            }
    
    # Recent transactions
    recent_txs = await db.transactions.find().sort("start_time", -1).limit(5).to_list(5)
    recent_transactions = [transaction_to_response(tx) for tx in recent_txs]
    
    return DashboardStats(
        total_transactions=total_transactions,
        total_energy=round(total_energy, 2),
        total_revenue=round(total_revenue, 2),
        paid_revenue=round(paid_revenue, 2),
        unpaid_revenue=round(unpaid_revenue, 2),
        active_stations=active_stations,
        unique_accounts=unique_accounts,
        payment_breakdown=payment_breakdown,
        recent_transactions=recent_transactions
    )


# Filter endpoints
@router.get("/filters/stations")
async def get_stations(current_user: UserResponse = Depends(get_current_user)):
    """Get list of unique stations"""
    db = await get_db()
    stations = await db.transactions.distinct("station")
    return sorted([s for s in stations if s])


@router.get("/filters/accounts")
async def get_accounts(current_user: UserResponse = Depends(get_current_user)):
    """Get list of unique accounts"""
    db = await get_db()
    accounts = await db.transactions.distinct("account")
    return sorted([a for a in accounts if a])
