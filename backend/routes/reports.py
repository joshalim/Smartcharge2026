"""
Reports routes - Generate reports and analytics
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, func, and_

from database import async_session, Transaction
from routes.auth import UserResponse, get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportFilters(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    account: Optional[str] = None
    connector_type: Optional[str] = None
    payment_type: Optional[str] = None
    payment_status: Optional[str] = None


class TransactionData(BaseModel):
    id: str
    tx_id: str
    station: str
    connector: Optional[str] = None
    connector_type: Optional[str] = None
    account: str
    start_time: str
    end_time: str
    charging_duration: Optional[str] = None
    meter_value: float
    cost: float
    payment_status: str
    payment_type: Optional[str] = None
    payment_date: Optional[str] = None


class StationSummary(BaseModel):
    station: str
    total_sessions: int
    total_energy: float
    total_revenue: float


class AccountSummary(BaseModel):
    account: str
    total_sessions: int
    total_energy: float
    total_revenue: float


class PaymentSummary(BaseModel):
    status: str
    count: int
    total: float


class ReportData(BaseModel):
    total_transactions: int
    total_revenue: float
    total_energy: float
    paid_count: int
    unpaid_count: int
    transactions: List[TransactionData]
    by_station: List[StationSummary]
    by_account: List[AccountSummary]
    by_payment_status: List[PaymentSummary]


def parse_date(date_str: str, end_of_day: bool = False):
    """Parse date string and return datetime object"""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if end_of_day:
            dt = dt.replace(hour=23, minute=59, second=59)
        return dt
    except:
        return None


@router.post("/generate", response_model=ReportData)
async def generate_report(
    filters: ReportFilters,
    current_user: UserResponse = Depends(get_current_user)
):
    """Generate a comprehensive report with filters"""
    try:
        async with async_session() as session:
            # Build query with filters
            query = select(Transaction)
            conditions = []
            
            # Date filters - check against start_time field
            if filters.start_date:
                conditions.append(Transaction.start_time >= filters.start_date)
            
            if filters.end_date:
                conditions.append(Transaction.start_time <= filters.end_date + "T23:59:59")
            
            if filters.account:
                conditions.append(Transaction.account.ilike(f"%{filters.account}%"))
            
            if filters.connector_type:
                conditions.append(
                    (Transaction.connector == filters.connector_type) |
                    (Transaction.connector_type == filters.connector_type)
                )
            
            if filters.payment_type:
                conditions.append(Transaction.payment_type == filters.payment_type)
            
            if filters.payment_status:
                conditions.append(Transaction.payment_status == filters.payment_status)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Limit to 1000 transactions max for performance
            query = query.order_by(Transaction.start_time.desc()).limit(1000)
        
        result = await session.execute(query)
        transactions = result.scalars().all()
        
        # Calculate totals
        total_revenue = sum(tx.cost or 0 for tx in transactions)
        total_energy = sum(tx.meter_value or 0 for tx in transactions)
        paid_count = sum(1 for tx in transactions if tx.payment_status == "PAID")
        unpaid_count = sum(1 for tx in transactions if tx.payment_status == "UNPAID")
        
        # Group by station
        station_data = {}
        for tx in transactions:
            station = tx.station or "Unknown"
            if station not in station_data:
                station_data[station] = {"total_sessions": 0, "total_energy": 0, "total_revenue": 0}
            station_data[station]["total_sessions"] += 1
            station_data[station]["total_energy"] += tx.meter_value or 0
            station_data[station]["total_revenue"] += tx.cost or 0
        
        by_station = [
            StationSummary(station=k, **v) 
            for k, v in sorted(station_data.items(), key=lambda x: x[1]["total_revenue"], reverse=True)
        ]
        
        # Group by account
        account_data = {}
        for tx in transactions:
            account = tx.account or "Unknown"
            if account not in account_data:
                account_data[account] = {"total_sessions": 0, "total_energy": 0, "total_revenue": 0}
            account_data[account]["total_sessions"] += 1
            account_data[account]["total_energy"] += tx.meter_value or 0
            account_data[account]["total_revenue"] += tx.cost or 0
        
        by_account = [
            AccountSummary(account=k, **v) 
            for k, v in sorted(account_data.items(), key=lambda x: x[1]["total_revenue"], reverse=True)
        ]
        
        # Group by payment status
        payment_status_data = {"PAID": {"count": 0, "total": 0}, "UNPAID": {"count": 0, "total": 0}}
        for tx in transactions:
            status = tx.payment_status or "UNPAID"
            if status not in payment_status_data:
                payment_status_data[status] = {"count": 0, "total": 0}
            payment_status_data[status]["count"] += 1
            payment_status_data[status]["total"] += tx.cost or 0
        
        by_payment_status = [
            PaymentSummary(status=k, **v) for k, v in payment_status_data.items()
        ]
        
        # Convert transactions to response model
        tx_list = [
            TransactionData(
                id=tx.id,
                tx_id=tx.tx_id,
                station=tx.station,
                connector=tx.connector,
                connector_type=tx.connector_type,
                account=tx.account,
                start_time=tx.start_time or "",
                end_time=tx.end_time or "",
                charging_duration=tx.charging_duration,
                meter_value=tx.meter_value or 0,
                cost=tx.cost or 0,
                payment_status=tx.payment_status or "UNPAID",
                payment_type=tx.payment_type,
                payment_date=tx.payment_date
            )
            for tx in transactions
        ]
        
        return ReportData(
            total_transactions=len(transactions),
            total_revenue=total_revenue,
            total_energy=total_energy,
            paid_count=paid_count,
            unpaid_count=unpaid_count,
            transactions=tx_list,
            by_station=by_station,
            by_account=by_account,
            by_payment_status=by_payment_status
        )
