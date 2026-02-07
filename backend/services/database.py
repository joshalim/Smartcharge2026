"""
Database service with direct SQLAlchemy operations
Replaces db_adapter.py with cleaner, more maintainable code
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from database import async_session


class DatabaseService:
    """Base database service with common operations"""
    
    def __init__(self, model):
        self.model = model
    
    async def get_by_id(self, id: str) -> Optional[Dict]:
        """Get single record by ID"""
        async with async_session() as session:
            result = await session.execute(
                select(self.model).where(self.model.id == id)
            )
            obj = result.scalar_one_or_none()
            return self._to_dict(obj) if obj else None
    
    async def get_one(self, **filters) -> Optional[Dict]:
        """Get single record by filters"""
        async with async_session() as session:
            query = select(self.model)
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
            result = await session.execute(query)
            obj = result.scalar_one_or_none()
            return self._to_dict(obj) if obj else None
    
    async def get_all(
        self, 
        filters: Dict = None,
        order_by: str = None,
        order_desc: bool = False,
        limit: int = None,
        offset: int = None
    ) -> List[Dict]:
        """Get multiple records with optional filtering and pagination"""
        async with async_session() as session:
            query = select(self.model)
            
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key) and value is not None:
                        query = query.where(getattr(self.model, key) == value)
            
            if order_by and hasattr(self.model, order_by):
                col = getattr(self.model, order_by)
                query = query.order_by(col.desc() if order_desc else col)
            
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            result = await session.execute(query)
            return [self._to_dict(obj) for obj in result.scalars().all()]
    
    async def create(self, data: Dict) -> Dict:
        """Create new record"""
        async with async_session() as session:
            # Filter to only valid columns
            valid_data = self._filter_valid_fields(data)
            obj = self.model(**valid_data)
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            return self._to_dict(obj)
    
    async def update_by_id(self, id: str, data: Dict) -> Optional[Dict]:
        """Update record by ID"""
        async with async_session() as session:
            result = await session.execute(
                select(self.model).where(self.model.id == id)
            )
            obj = result.scalar_one_or_none()
            if not obj:
                return None
            
            valid_data = self._filter_valid_fields(data)
            for key, value in valid_data.items():
                setattr(obj, key, value)
            
            await session.commit()
            await session.refresh(obj)
            return self._to_dict(obj)
    
    async def delete_by_id(self, id: str) -> bool:
        """Delete record by ID"""
        async with async_session() as session:
            result = await session.execute(
                delete(self.model).where(self.model.id == id)
            )
            await session.commit()
            return result.rowcount > 0
    
    async def count(self, filters: Dict = None) -> int:
        """Count records with optional filters"""
        async with async_session() as session:
            query = select(func.count()).select_from(self.model)
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key) and value is not None:
                        query = query.where(getattr(self.model, key) == value)
            result = await session.execute(query)
            return result.scalar() or 0
    
    async def sum_field(self, field: str, filters: Dict = None) -> float:
        """Sum a numeric field"""
        async with async_session() as session:
            if not hasattr(self.model, field):
                return 0.0
            query = select(func.sum(getattr(self.model, field)))
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key) and value is not None:
                        query = query.where(getattr(self.model, key) == value)
            result = await session.execute(query)
            return float(result.scalar() or 0)
    
    async def distinct_values(self, field: str, filters: Dict = None) -> List:
        """Get distinct values for a field"""
        async with async_session() as session:
            if not hasattr(self.model, field):
                return []
            query = select(getattr(self.model, field)).distinct()
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key) and value is not None:
                        query = query.where(getattr(self.model, key) == value)
            result = await session.execute(query)
            return [row[0] for row in result.fetchall() if row[0] is not None]
    
    def _filter_valid_fields(self, data: Dict) -> Dict:
        """Filter data to only include valid model columns"""
        valid_columns = {col.name for col in self.model.__table__.columns}
        return {k: v for k, v in data.items() if k in valid_columns and k != '_id'}
    
    def _to_dict(self, obj) -> Dict:
        """Convert SQLAlchemy model to dictionary"""
        if obj is None:
            return None
        result = {}
        for column in obj.__table__.columns:
            value = getattr(obj, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result


# Convenience function for raw queries
async def execute_query(query):
    """Execute a raw SQLAlchemy query"""
    async with async_session() as session:
        result = await session.execute(query)
        return result
