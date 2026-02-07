"""
Export routes - Export data to Excel/CSV
"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime
from io import BytesIO

from sqlalchemy import select
from database import async_session, User, Transaction, RFIDCard, PricingGroup

from routes.auth import require_role, UserResponse

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/users")
async def export_users(
    format: str = "xlsx",
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Export all users to Excel/CSV"""
    import pandas as pd
    
    async with async_session() as session:
        # Get all users with their pricing groups
        result = await session.execute(
            select(User).order_by(User.name)
        )
        users = result.scalars().all()
        
        # Get all pricing groups for lookup
        groups_result = await session.execute(select(PricingGroup))
        groups = {g.id: g.name for g in groups_result.scalars().all()}
        
        # Build data
        data = []
        for user in users:
            data.append({
                "Name": user.name,
                "Email": user.email,
                "Role": user.role,
                "Pricing Group": groups.get(user.pricing_group_id, ""),
                "Created At": user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else ""
            })
        
        df = pd.DataFrame(data)
        
        output = BytesIO()
        if format == "csv":
            df.to_csv(output, index=False)
            media_type = "text/csv"
            filename = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            df.to_excel(output, index=False, engine='openpyxl')
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )


@router.get("/transactions")
async def export_transactions(
    format: str = "xlsx",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Export transactions to Excel/CSV"""
    import pandas as pd
    
    async with async_session() as session:
        query = select(Transaction).order_by(Transaction.start_time.desc())
        
        if start_date:
            query = query.where(Transaction.start_time >= start_date)
        if end_date:
            query = query.where(Transaction.start_time <= end_date)
        
        result = await session.execute(query)
        transactions = result.scalars().all()
        
        data = []
        for tx in transactions:
            data.append({
                "TxID": tx.tx_id,
                "Station": tx.station,
                "Connector": tx.connector,
                "Connector Type": tx.connector_type or "",
                "Account": tx.account,
                "Start Time": tx.start_time or "",
                "End Time": tx.end_time or "",
                "Duration": tx.charging_duration or "",
                "Meter Value (kWh)": tx.meter_value or 0,
                "Cost (COP)": tx.cost or 0,
                "Payment Status": tx.payment_status or "UNPAID",
                "Payment Type": tx.payment_type or "",
                "Payment Date": tx.payment_date or ""
            })
        
        df = pd.DataFrame(data)
        
        output = BytesIO()
        if format == "csv":
            df.to_csv(output, index=False)
            media_type = "text/csv"
            filename = f"transactions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            df.to_excel(output, index=False, engine='openpyxl')
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"transactions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )


@router.get("/rfid-cards")
async def export_rfid_cards(
    format: str = "xlsx",
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Export RFID cards to Excel/CSV"""
    import pandas as pd
    
    async with async_session() as session:
        result = await session.execute(
            select(RFIDCard).order_by(RFIDCard.card_number)
        )
        cards = result.scalars().all()
        
        # Get users for lookup
        users_result = await session.execute(select(User))
        users = {u.id: u.email for u in users_result.scalars().all()}
        
        data = []
        for card in cards:
            data.append({
                "Card Number": card.card_number,
                "User Email": users.get(card.user_id, ""),
                "Balance (COP)": card.balance or 0,
                "Status": card.status or "active",
                "Active": "Yes" if card.is_active else "No",
                "Created At": card.created_at.strftime("%Y-%m-%d %H:%M") if card.created_at else ""
            })
        
        df = pd.DataFrame(data)
        
        output = BytesIO()
        if format == "csv":
            df.to_csv(output, index=False)
            media_type = "text/csv"
            filename = f"rfid_cards_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            df.to_excel(output, index=False, engine='openpyxl')
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"rfid_cards_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )


@router.get("/template/users")
async def download_user_template():
    """Download user import template"""
    import pandas as pd
    
    df = pd.DataFrame({
        "Name": ["John Doe", "Jane Smith"],
        "Email": ["john@example.com", "jane@example.com"],
        "Role": ["user", "admin"],
        "Password": ["Password123", "Password456"],
        "Group": ["Default", "Premium"]
    })
    
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=user_import_template.xlsx"}
    )


@router.get("/template/rfid-cards")
async def download_rfid_template():
    """Download RFID card import template"""
    import pandas as pd
    
    df = pd.DataFrame({
        "Card Number": ["RFID001", "RFID002"],
        "User Email": ["john@example.com", "jane@example.com"],
        "Balance": [50000, 100000]
    })
    
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=rfid_import_template.xlsx"}
    )


@router.get("/template/transactions")
async def download_transactions_template():
    """Download transactions import template"""
    import pandas as pd
    
    df = pd.DataFrame({
        "TxID": ["TX001", "TX002"],
        "Station": ["Station A", "Station B"],
        "Connector": ["1", "2"],
        "Account": ["User1", "User2"],
        "Start Time": ["2026-01-01 10:00:00", "2026-01-01 11:00:00"],
        "End Time": ["2026-01-01 10:30:00", "2026-01-01 12:00:00"],
        "Meter value(kW.h)": [15.5, 25.0]
    })
    
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=transactions_import_template.xlsx"}
    )
