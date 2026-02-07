"""
Expenses routes - Track business expenses for financial reporting
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, extract
from sqlalchemy.orm import selectinload

from database import async_session, Expense, Transaction
from routes.auth import UserResponse, get_current_user

router = APIRouter(prefix="/expenses", tags=["expenses"])


class ExpenseCreate(BaseModel):
    name: str
    date: str  # YYYY-MM-DD
    cost: float
    reason: Optional[str] = None


class ExpenseUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[str] = None
    cost: Optional[float] = None
    reason: Optional[str] = None


class ExpenseResponse(BaseModel):
    id: str
    name: str
    date: str
    cost: float
    reason: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class MonthlyFinancials(BaseModel):
    month: str  # YYYY-MM
    income: float
    expenses: float
    profit: float
    profit_margin: float


class FinancialSummary(BaseModel):
    total_income: float
    total_expenses: float
    total_profit: float
    overall_profit_margin: float
    monthly_data: List[MonthlyFinancials]


@router.get("", response_model=List[ExpenseResponse])
async def get_expenses(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get all expenses with optional date filtering"""
    async with async_session() as session:
        query = select(Expense).order_by(Expense.date.desc())
        
        conditions = []
        if start_date:
            conditions.append(Expense.date >= start_date)
        if end_date:
            conditions.append(Expense.date <= end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await session.execute(query)
        expenses = result.scalars().all()
        
        return [
            ExpenseResponse(
                id=exp.id,
                name=exp.name,
                date=exp.date,
                cost=exp.cost,
                reason=exp.reason,
                created_by=exp.created_by,
                created_at=exp.created_at.isoformat() if exp.created_at else None
            )
            for exp in expenses
        ]


@router.post("", response_model=ExpenseResponse)
async def create_expense(
    expense: ExpenseCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Create a new expense"""
    if current_user.role not in ['admin', 'user']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    async with async_session() as session:
        new_expense = Expense(
            name=expense.name,
            date=expense.date,
            cost=expense.cost,
            reason=expense.reason,
            created_by=current_user.id
        )
        session.add(new_expense)
        await session.commit()
        await session.refresh(new_expense)
        
        return ExpenseResponse(
            id=new_expense.id,
            name=new_expense.name,
            date=new_expense.date,
            cost=new_expense.cost,
            reason=new_expense.reason,
            created_by=new_expense.created_by,
            created_at=new_expense.created_at.isoformat() if new_expense.created_at else None
        )


@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get a specific expense"""
    async with async_session() as session:
        result = await session.execute(
            select(Expense).where(Expense.id == expense_id)
        )
        expense = result.scalar_one_or_none()
        
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        return ExpenseResponse(
            id=expense.id,
            name=expense.name,
            date=expense.date,
            cost=expense.cost,
            reason=expense.reason,
            created_by=expense.created_by,
            created_at=expense.created_at.isoformat() if expense.created_at else None
        )


@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: str,
    expense_data: ExpenseUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update an expense"""
    if current_user.role not in ['admin', 'user']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    async with async_session() as session:
        result = await session.execute(
            select(Expense).where(Expense.id == expense_id)
        )
        expense = result.scalar_one_or_none()
        
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        if expense_data.name is not None:
            expense.name = expense_data.name
        if expense_data.date is not None:
            expense.date = expense_data.date
        if expense_data.cost is not None:
            expense.cost = expense_data.cost
        if expense_data.reason is not None:
            expense.reason = expense_data.reason
        
        await session.commit()
        await session.refresh(expense)
        
        return ExpenseResponse(
            id=expense.id,
            name=expense.name,
            date=expense.date,
            cost=expense.cost,
            reason=expense.reason,
            created_by=expense.created_by,
            created_at=expense.created_at.isoformat() if expense.created_at else None
        )


@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Delete an expense"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can delete expenses")
    
    async with async_session() as session:
        result = await session.execute(
            select(Expense).where(Expense.id == expense_id)
        )
        expense = result.scalar_one_or_none()
        
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        await session.delete(expense)
        await session.commit()
        
        return {"message": "Expense deleted successfully"}


@router.get("/financials/summary", response_model=FinancialSummary)
async def get_financial_summary(
    months: int = 12,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get monthly financial summary (income, expenses, profit)"""
    async with async_session() as session:
        # Get all transactions grouped by month
        tx_result = await session.execute(
            select(Transaction).order_by(Transaction.start_time.desc())
        )
        transactions = tx_result.scalars().all()
        
        # Get all expenses
        exp_result = await session.execute(
            select(Expense).order_by(Expense.date.desc())
        )
        expenses = exp_result.scalars().all()
    
    # Group income by month (from paid transactions)
    monthly_income = {}
    for tx in transactions:
        if tx.start_time and tx.payment_status == 'PAID':
            month_key = tx.start_time[:7]  # YYYY-MM
            if month_key not in monthly_income:
                monthly_income[month_key] = 0
            monthly_income[month_key] += tx.cost or 0
    
    # Group expenses by month
    monthly_expenses = {}
    for exp in expenses:
        if exp.date:
            month_key = exp.date[:7]  # YYYY-MM
            if month_key not in monthly_expenses:
                monthly_expenses[month_key] = 0
            monthly_expenses[month_key] += exp.cost or 0
    
    # Combine all months
    all_months = set(list(monthly_income.keys()) + list(monthly_expenses.keys()))
    sorted_months = sorted(all_months, reverse=True)[:months]
    
    monthly_data = []
    total_income = 0
    total_expenses = 0
    
    for month in sorted_months:
        income = monthly_income.get(month, 0)
        expense = monthly_expenses.get(month, 0)
        profit = income - expense
        margin = (profit / income * 100) if income > 0 else 0
        
        total_income += income
        total_expenses += expense
        
        monthly_data.append(MonthlyFinancials(
            month=month,
            income=round(income, 2),
            expenses=round(expense, 2),
            profit=round(profit, 2),
            profit_margin=round(margin, 1)
        ))
    
    # Reverse to show oldest to newest for charts
    monthly_data.reverse()
    
    total_profit = total_income - total_expenses
    overall_margin = (total_profit / total_income * 100) if total_income > 0 else 0
    
    return FinancialSummary(
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        total_profit=round(total_profit, 2),
        overall_profit_margin=round(overall_margin, 1),
        monthly_data=monthly_data
    )
