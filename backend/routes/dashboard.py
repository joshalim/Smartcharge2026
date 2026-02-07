"""
Dashboard and statistics routes
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone

from sqlalchemy import select, func
from database import async_session, Transaction

from routes.auth import get_current_user, UserResponse
from routes.transactions import TransactionResponse, transaction_to_response

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# Pydantic Models
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
    async with async_session() as session:
        # Total transactions
        count_result = await session.execute(
            select(func.count()).select_from(Transaction)
        )
        total_transactions = count_result.scalar() or 0
        
        # Total energy and revenue
        totals_result = await session.execute(
            select(
                func.sum(Transaction.meter_value),
                func.sum(Transaction.cost)
            )
        )
        totals = totals_result.fetchone()
        total_energy = float(totals[0] or 0)
        total_revenue = float(totals[1] or 0)
        
        # Paid revenue
        paid_result = await session.execute(
            select(func.sum(Transaction.cost)).where(Transaction.payment_status == "PAID")
        )
        paid_revenue = float(paid_result.scalar() or 0)
        unpaid_revenue = total_revenue - paid_revenue
        
        # Unique stations
        stations_result = await session.execute(
            select(Transaction.station).distinct()
        )
        stations = [row[0] for row in stations_result.fetchall() if row[0]]
        active_stations = len(stations)
        
        # Unique accounts
        accounts_result = await session.execute(
            select(Transaction.account).distinct()
        )
        accounts = [row[0] for row in accounts_result.fetchall() if row[0]]
        unique_accounts = len(accounts)
        
        # Payment breakdown
        payment_result = await session.execute(
            select(
                Transaction.payment_type,
                func.count(),
                func.sum(Transaction.cost)
            ).where(Transaction.payment_status == "PAID")
            .group_by(Transaction.payment_type)
        )
        payment_breakdown = {}
        for row in payment_result.fetchall():
            if row[0]:
                payment_breakdown[row[0]] = {
                    "count": row[1],
                    "amount": float(row[2] or 0)
                }
        
        # Recent transactions
        recent_result = await session.execute(
            select(Transaction)
            .order_by(Transaction.start_time.desc())
            .limit(5)
        )
        recent_transactions = [
            transaction_to_response(tx) for tx in recent_result.scalars().all()
        ]
        
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
    async with async_session() as session:
        result = await session.execute(
            select(Transaction.station).distinct()
        )
        stations = [row[0] for row in result.fetchall() if row[0]]
        return sorted(stations)


@router.get("/filters/accounts")
async def get_accounts(current_user: UserResponse = Depends(get_current_user)):
    """Get list of unique accounts"""
    async with async_session() as session:
        result = await session.execute(
            select(Transaction.account).distinct()
        )
        accounts = [row[0] for row in result.fetchall() if row[0]]
        return sorted(accounts)
