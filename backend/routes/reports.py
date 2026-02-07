"""
Reports routes - Generate reports and analytics with PDF export
"""
from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import select, func, and_
import io

from database import async_session, Transaction
from routes.auth import UserResponse, get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportFilters(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    account: Optional[str] = None
    station: Optional[str] = None
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


class SummaryData(BaseModel):
    total_transactions: int
    total_energy: float
    total_revenue: float
    paid_transactions: int
    paid_revenue: float
    unpaid_revenue: float
    avg_session_energy: float
    avg_session_revenue: float


class GroupedData(BaseModel):
    name: str
    transactions: int
    energy: float
    revenue: float


class DailyData(BaseModel):
    date: str
    transactions: int
    energy: float
    revenue: float


class ReportResponse(BaseModel):
    summary: SummaryData
    by_account: List[GroupedData]
    by_station: List[GroupedData]
    by_connector: List[GroupedData]
    by_payment_type: List[GroupedData]
    daily_trend: List[DailyData]
    transactions: List[TransactionData]


@router.post("/generate", response_model=ReportResponse)
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
            
            # Date filters
            if filters.start_date:
                conditions.append(Transaction.start_time >= filters.start_date)
            
            if filters.end_date:
                conditions.append(Transaction.start_time <= filters.end_date + "T23:59:59")
            
            if filters.account:
                conditions.append(Transaction.account.ilike(f"%{filters.account}%"))
            
            if filters.station:
                conditions.append(Transaction.station.ilike(f"%{filters.station}%"))
            
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
            
            # Limit for performance
            query = query.order_by(Transaction.start_time.desc()).limit(2000)
            
            result = await session.execute(query)
            transactions = result.scalars().all()
        
        if not transactions:
            return ReportResponse(
                summary=SummaryData(
                    total_transactions=0, total_energy=0, total_revenue=0,
                    paid_transactions=0, paid_revenue=0, unpaid_revenue=0,
                    avg_session_energy=0, avg_session_revenue=0
                ),
                by_account=[], by_station=[], by_connector=[],
                by_payment_type=[], daily_trend=[], transactions=[]
            )
        
        # Calculate summary
        total_revenue = sum(tx.cost or 0 for tx in transactions)
        total_energy = sum(tx.meter_value or 0 for tx in transactions)
        paid_txs = [tx for tx in transactions if tx.payment_status == "PAID"]
        paid_revenue = sum(tx.cost or 0 for tx in paid_txs)
        unpaid_revenue = total_revenue - paid_revenue
        
        summary = SummaryData(
            total_transactions=len(transactions),
            total_energy=round(total_energy, 2),
            total_revenue=round(total_revenue, 2),
            paid_transactions=len(paid_txs),
            paid_revenue=round(paid_revenue, 2),
            unpaid_revenue=round(unpaid_revenue, 2),
            avg_session_energy=round(total_energy / len(transactions), 2) if transactions else 0,
            avg_session_revenue=round(total_revenue / len(transactions), 2) if transactions else 0
        )
        
        # Group by account
        account_data = {}
        for tx in transactions:
            key = tx.account or "Unknown"
            if key not in account_data:
                account_data[key] = {"transactions": 0, "energy": 0, "revenue": 0}
            account_data[key]["transactions"] += 1
            account_data[key]["energy"] += tx.meter_value or 0
            account_data[key]["revenue"] += tx.cost or 0
        
        by_account = sorted([
            GroupedData(name=k, **{kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()})
            for k, v in account_data.items()
        ], key=lambda x: x.revenue, reverse=True)[:15]
        
        # Group by station
        station_data = {}
        for tx in transactions:
            key = tx.station or "Unknown"
            if key not in station_data:
                station_data[key] = {"transactions": 0, "energy": 0, "revenue": 0}
            station_data[key]["transactions"] += 1
            station_data[key]["energy"] += tx.meter_value or 0
            station_data[key]["revenue"] += tx.cost or 0
        
        by_station = sorted([
            GroupedData(name=k, **{kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()})
            for k, v in station_data.items()
        ], key=lambda x: x.revenue, reverse=True)[:15]
        
        # Group by connector type
        connector_data = {}
        for tx in transactions:
            key = tx.connector_type or tx.connector or "Unknown"
            if key not in connector_data:
                connector_data[key] = {"transactions": 0, "energy": 0, "revenue": 0}
            connector_data[key]["transactions"] += 1
            connector_data[key]["energy"] += tx.meter_value or 0
            connector_data[key]["revenue"] += tx.cost or 0
        
        by_connector = sorted([
            GroupedData(name=k, **{kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()})
            for k, v in connector_data.items()
        ], key=lambda x: x.revenue, reverse=True)
        
        # Group by payment type
        payment_type_data = {}
        for tx in transactions:
            key = tx.payment_type or "Not Specified"
            if key not in payment_type_data:
                payment_type_data[key] = {"transactions": 0, "energy": 0, "revenue": 0}
            payment_type_data[key]["transactions"] += 1
            payment_type_data[key]["energy"] += tx.meter_value or 0
            payment_type_data[key]["revenue"] += tx.cost or 0
        
        by_payment_type = sorted([
            GroupedData(name=k, **{kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()})
            for k, v in payment_type_data.items()
        ], key=lambda x: x.revenue, reverse=True)
        
        # Daily trend
        daily_data = {}
        for tx in transactions:
            if tx.start_time:
                date_key = tx.start_time[:10]  # YYYY-MM-DD
                if date_key not in daily_data:
                    daily_data[date_key] = {"transactions": 0, "energy": 0, "revenue": 0}
                daily_data[date_key]["transactions"] += 1
                daily_data[date_key]["energy"] += tx.meter_value or 0
                daily_data[date_key]["revenue"] += tx.cost or 0
        
        daily_trend = sorted([
            DailyData(date=k, **{kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()})
            for k, v in daily_data.items()
        ], key=lambda x: x.date)[-30:]  # Last 30 days
        
        # Transaction list (limited)
        tx_list = [
            TransactionData(
                id=tx.id,
                tx_id=tx.tx_id or "",
                station=tx.station or "",
                connector=tx.connector,
                connector_type=tx.connector_type,
                account=tx.account or "",
                start_time=tx.start_time or "",
                end_time=tx.end_time or "",
                charging_duration=tx.charging_duration,
                meter_value=round(tx.meter_value or 0, 2),
                cost=round(tx.cost or 0, 2),
                payment_status=tx.payment_status or "UNPAID",
                payment_type=tx.payment_type,
                payment_date=tx.payment_date
            )
            for tx in transactions[:100]
        ]
        
        return ReportResponse(
            summary=summary,
            by_account=by_account,
            by_station=by_station,
            by_connector=by_connector,
            by_payment_type=by_payment_type,
            daily_trend=daily_trend,
            transactions=tx_list
        )
        
    except Exception as e:
        import logging
        logging.error(f"Report generation error: {e}")
        raise


@router.get("/quick-stats")
async def get_quick_stats(current_user: UserResponse = Depends(get_current_user)):
    """Get quick stats for dashboard without filters"""
    try:
        async with async_session() as session:
            # Get last 30 days of data
            thirty_days_ago = datetime.now(timezone.utc).isoformat()[:10]
            
            result = await session.execute(
                select(Transaction).order_by(Transaction.start_time.desc()).limit(500)
            )
            transactions = result.scalars().all()
        
        total_revenue = sum(tx.cost or 0 for tx in transactions)
        total_energy = sum(tx.meter_value or 0 for tx in transactions)
        paid_txs = [tx for tx in transactions if tx.payment_status == "PAID"]
        
        return {
            "total_transactions": len(transactions),
            "total_energy": round(total_energy, 2),
            "total_revenue": round(total_revenue, 2),
            "paid_count": len(paid_txs),
            "collection_rate": round(len(paid_txs) / len(transactions) * 100, 1) if transactions else 0
        }
    except Exception as e:
        return {
            "total_transactions": 0,
            "total_energy": 0,
            "total_revenue": 0,
            "paid_count": 0,
            "collection_rate": 0
        }
