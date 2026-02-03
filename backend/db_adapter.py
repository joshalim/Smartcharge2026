"""
Database Abstraction Layer - Provides MongoDB-like interface over PostgreSQL
This allows minimal changes to existing code while using PostgreSQL
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, or_, and_, text
from sqlalchemy.dialects.postgresql import insert
from typing import Dict, List, Any, Optional
import json

from database import (
    async_session, 
    User, Transaction, Charger,
    PricingRule, PricingGroup, RFIDCard, 
    RFIDHistory, OCPPSession, AppConfig
)

# Model mapping
MODEL_MAP = {
    'users': User,
    'transactions': Transaction,
    'chargers': Charger,
    'pricing_rules': PricingRule,
    'pricing_groups': PricingGroup,
    'rfid_cards': RFIDCard,
    'rfid_history': RFIDHistory,
    'ocpp_sessions': OCPPSession,
    'app_config': AppConfig,
    'payu_config': AppConfig,
    'sendgrid_config': AppConfig,
    'invoice_webhook_config': AppConfig,
}


def model_to_dict(model) -> dict:
    """Convert SQLAlchemy model to dictionary"""
    if model is None:
        return None
    result = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        if hasattr(value, 'isoformat'):
            value = value.isoformat()
        result[column.name] = value
    return result


class PostgresCollection:
    """Mimics MongoDB collection interface for PostgreSQL"""
    
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.model = MODEL_MAP.get(collection_name)
    
    async def find_one(self, filter_dict: dict, projection: dict = None) -> Optional[dict]:
        """Find a single document"""
        async with async_session() as session:
            query = select(self.model)
            
            for key, value in filter_dict.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
            
            result = await session.execute(query)
            row = result.scalar_one_or_none()
            
            if row is None:
                return None
            
            doc = model_to_dict(row)
            
            # Handle projection (exclude fields)
            if projection:
                for field, include in projection.items():
                    if include == 0 and field in doc:
                        del doc[field]
            
            return doc
    
    def find(self, filter_dict: dict = None, projection: dict = None):
        """Find multiple documents - returns cursor (not async)"""
        return PostgresCursor(self.model, filter_dict, projection)
    
    async def insert_one(self, document: dict):
        """Insert a single document"""
        async with async_session() as session:
            # Remove _id if present (MongoDB artifact)
            document.pop('_id', None)
            
            obj = self.model(**document)
            session.add(obj)
            await session.commit()
            return type('InsertResult', (), {'inserted_id': document.get('id')})()
    
    async def update_one(self, filter_dict: dict, update_dict: dict):
        """Update a single document"""
        async with async_session() as session:
            # Handle $set operator
            if '$set' in update_dict:
                update_data = update_dict['$set']
            else:
                update_data = update_dict
            
            query = update(self.model)
            for key, value in filter_dict.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
            
            query = query.values(**update_data)
            result = await session.execute(query)
            await session.commit()
            
            return type('UpdateResult', (), {
                'modified_count': result.rowcount,
                'matched_count': result.rowcount
            })()
    
    async def delete_one(self, filter_dict: dict):
        """Delete a single document"""
        async with async_session() as session:
            query = delete(self.model)
            for key, value in filter_dict.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
            
            result = await session.execute(query)
            await session.commit()
            
            return type('DeleteResult', (), {'deleted_count': result.rowcount})()
    
    async def delete_many(self, filter_dict: dict):
        """Delete multiple documents"""
        async with async_session() as session:
            query = delete(self.model)
            
            # Handle $in operator
            for key, value in filter_dict.items():
                if isinstance(value, dict) and '$in' in value:
                    if hasattr(self.model, key):
                        query = query.where(getattr(self.model, key).in_(value['$in']))
                elif hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
            
            result = await session.execute(query)
            await session.commit()
            
            return type('DeleteResult', (), {'deleted_count': result.rowcount})()
    
    async def update_many(self, filter_dict: dict, update_dict: dict):
        """Update multiple documents"""
        async with async_session() as session:
            # Handle $set operator
            if '$set' in update_dict:
                update_data = update_dict['$set']
            else:
                update_data = update_dict
            
            query = update(self.model)
            for key, value in filter_dict.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
            
            query = query.values(**update_data)
            result = await session.execute(query)
            await session.commit()
            
            return type('UpdateResult', (), {
                'modified_count': result.rowcount,
                'matched_count': result.rowcount
            })()
    
    async def count_documents(self, filter_dict: dict = None) -> int:
        """Count documents matching filter"""
        async with async_session() as session:
            query = select(func.count()).select_from(self.model)
            
            if filter_dict:
                for key, value in filter_dict.items():
                    if hasattr(self.model, key):
                        query = query.where(getattr(self.model, key) == value)
            
            result = await session.execute(query)
            return result.scalar() or 0
    
    async def distinct(self, field: str, filter_dict: dict = None) -> List:
        """Get distinct values for a field"""
        async with async_session() as session:
            if not hasattr(self.model, field):
                return []
            
            query = select(getattr(self.model, field)).distinct()
            
            if filter_dict:
                for key, value in filter_dict.items():
                    if hasattr(self.model, key):
                        query = query.where(getattr(self.model, key) == value)
            
            result = await session.execute(query)
            return [row[0] for row in result.fetchall() if row[0] is not None]


class PostgresCursor:
    """Async cursor for iterating results"""
    
    def __init__(self, model, filter_dict: dict = None, projection: dict = None):
        self.model = model
        self.filter_dict = filter_dict or {}
        self.projection = projection
        self._sort_field = None
        self._sort_order = 1
        self._limit_value = None
        self._skip_value = None
    
    def sort(self, field: str, order: int = 1):
        """Set sort order"""
        self._sort_field = field
        self._sort_order = order
        return self
    
    def limit(self, n: int):
        """Limit results"""
        self._limit_value = n
        return self
    
    def skip(self, n: int):
        """Skip results"""
        self._skip_value = n
        return self
    
    async def to_list(self, length: int = None) -> List[dict]:
        """Convert cursor to list"""
        results = []
        async for doc in self:
            results.append(doc)
            if length and len(results) >= length:
                break
        return results
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if not hasattr(self, '_results'):
            await self._execute()
        
        if self._index >= len(self._results):
            raise StopAsyncIteration
        
        result = self._results[self._index]
        self._index += 1
        return result
    
    async def _execute(self):
        """Execute the query"""
        async with async_session() as session:
            query = select(self.model)
            
            # Apply filters
            for key, value in self.filter_dict.items():
                if isinstance(value, dict):
                    # Handle operators
                    if '$gte' in value:
                        if hasattr(self.model, key):
                            query = query.where(getattr(self.model, key) >= value['$gte'])
                    if '$lte' in value:
                        if hasattr(self.model, key):
                            query = query.where(getattr(self.model, key) <= value['$lte'])
                    if '$in' in value:
                        if hasattr(self.model, key):
                            query = query.where(getattr(self.model, key).in_(value['$in']))
                    if '$ne' in value:
                        if hasattr(self.model, key):
                            query = query.where(getattr(self.model, key) != value['$ne'])
                elif hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
            
            # Apply sort
            if self._sort_field and hasattr(self.model, self._sort_field):
                if self._sort_order == -1:
                    query = query.order_by(getattr(self.model, self._sort_field).desc())
                else:
                    query = query.order_by(getattr(self.model, self._sort_field).asc())
            
            # Apply skip
            if self._skip_value:
                query = query.offset(self._skip_value)
            
            # Apply limit
            if self._limit_value:
                query = query.limit(self._limit_value)
            
            result = await session.execute(query)
            rows = result.scalars().all()
            
            self._results = []
            for row in rows:
                doc = model_to_dict(row)
                # Handle projection
                if self.projection:
                    for field, include in self.projection.items():
                        if include == 0 and field in doc:
                            del doc[field]
                self._results.append(doc)
            
            self._index = 0


class PostgresDB:
    """Main database class mimicking MongoDB interface"""
    
    def __getattr__(self, name: str) -> PostgresCollection:
        return PostgresCollection(name)


# Global database instance
db = PostgresDB()
