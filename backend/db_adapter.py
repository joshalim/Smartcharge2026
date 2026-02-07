"""
PostgreSQL Database Adapter for SmartCharge
Pure PostgreSQL implementation - no MongoDB compatibility layer
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, or_, and_
from sqlalchemy.dialects.postgresql import insert
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from database import (
    async_session, 
    User, Transaction, Charger,
    PricingRule, PricingGroup, RFIDCard, 
    RFIDHistory, OCPPSession, AppConfig,
    Settings, PayUPayment, PayUWebhookLog,
    OCPPBoot, OCPPTransaction, InvoiceWebhookConfig, InvoiceWebhookLog
)

# Model mapping
MODEL_MAP = {
    'users': User,
    'transactions': Transaction,
    'chargers': Charger,
    'pricing': PricingRule,  # Map db.pricing to PricingRule
    'pricing_rules': PricingRule,
    'pricing_groups': PricingGroup,
    'rfid_cards': RFIDCard,
    'rfid_history': RFIDHistory,
    'ocpp_sessions': OCPPSession,
    'app_config': AppConfig,
    'settings': Settings,
    'payu_payments': PayUPayment,
    'payu_webhook_logs': PayUWebhookLog,
    'ocpp_boots': OCPPBoot,
    'ocpp_transactions': OCPPTransaction,
    'invoice_webhook_config': InvoiceWebhookConfig,
    'invoice_webhook_logs': InvoiceWebhookLog,
}

# Datetime fields that need conversion
DATETIME_FIELDS = ['created_at', 'updated_at', 'timestamp', 'last_heartbeat', 'payment_date']


def to_datetime(value):
    """Convert string to datetime if needed"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            if 'T' in value:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except:
            return datetime.now(timezone.utc)
    return value


def prepare_data(data: dict, model) -> dict:
    """Prepare data for database insertion/update - only include valid model fields"""
    result = {}
    # Get valid column names for this model
    valid_columns = {col.name for col in model.__table__.columns}
    
    for key, value in data.items():
        if key == '_id':
            continue
        # Only include fields that exist in the model
        if key not in valid_columns:
            continue
        if key in DATETIME_FIELDS:
            result[key] = to_datetime(value)
        else:
            result[key] = value
    return result


def model_to_dict(obj) -> dict:
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


class PostgresCollection:
    """PostgreSQL table wrapper"""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.model = MODEL_MAP.get(table_name)
    
    async def find_one(self, filters: dict, projection: dict = None) -> Optional[dict]:
        """Find single record"""
        async with async_session() as session:
            query = select(self.model)
            query = self._apply_filters(query, filters)
            
            result = await session.execute(query)
            row = result.scalar_one_or_none()
            return model_to_dict(row)
    
    def _apply_filters(self, query, filters: dict):
        """Apply filters to query, handling MongoDB-style operators"""
        for key, value in filters.items():
            if not hasattr(self.model, key):
                continue
            column = getattr(self.model, key)
            
            if isinstance(value, dict):
                # Handle MongoDB-style operators
                for op, op_value in value.items():
                    if op == '$ne':
                        query = query.where(column != op_value)
                    elif op == '$gt':
                        query = query.where(column > op_value)
                    elif op == '$gte':
                        query = query.where(column >= op_value)
                    elif op == '$lt':
                        query = query.where(column < op_value)
                    elif op == '$lte':
                        query = query.where(column <= op_value)
                    elif op == '$in':
                        query = query.where(column.in_(op_value))
                    elif op == '$nin':
                        query = query.where(~column.in_(op_value))
            else:
                query = query.where(column == value)
        return query
    
    async def find_all(self, filters: dict = None, sort_by: str = None, 
                       sort_desc: bool = False, limit: int = None, skip: int = None) -> List[dict]:
        """Find multiple records"""
        async with async_session() as session:
            query = select(self.model)
            
            if filters:
                query = self._apply_filters(query, filters)
            
            if sort_by and hasattr(self.model, sort_by):
                col = getattr(self.model, sort_by)
                query = query.order_by(col.desc() if sort_desc else col)
            
            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)
            
            result = await session.execute(query)
            # Filter out None values
            return [model_to_dict(row) for row in result.scalars().all() if row is not None]
    
    async def insert_one(self, data: dict):
        """Insert single record"""
        async with async_session() as session:
            prepared = prepare_data(data, self.model)
            obj = self.model(**prepared)
            session.add(obj)
            await session.commit()
            return {'inserted_id': data.get('id')}
    
    async def update_one(self, filters: dict, data: dict):
        """Update single record"""
        async with async_session() as session:
            # Handle $set operator for compatibility
            if '$set' in data:
                update_data = data['$set']
            else:
                update_data = data
            
            prepared = prepare_data(update_data, self.model)
            
            query = update(self.model)
            # Apply filters with operator support
            for key, value in filters.items():
                if not hasattr(self.model, key):
                    continue
                column = getattr(self.model, key)
                
                if isinstance(value, dict):
                    for op, op_value in value.items():
                        if op == '$ne':
                            query = query.where(column != op_value)
                        elif op == '$gt':
                            query = query.where(column > op_value)
                        elif op == '$gte':
                            query = query.where(column >= op_value)
                        elif op == '$lt':
                            query = query.where(column < op_value)
                        elif op == '$lte':
                            query = query.where(column <= op_value)
                        elif op == '$in':
                            query = query.where(column.in_(op_value))
                else:
                    query = query.where(column == value)
            
            query = query.values(**prepared)
            result = await session.execute(query)
            await session.commit()
            return {'modified_count': result.rowcount}
    
    async def update_many(self, filters: dict, data: dict):
        """Update multiple records"""
        return await self.update_one(filters, data)
    
    async def delete_one(self, filters: dict):
        """Delete single record"""
        async with async_session() as session:
            query = delete(self.model)
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
            
            result = await session.execute(query)
            await session.commit()
            return {'deleted_count': result.rowcount}
    
    async def delete_many(self, filters: dict):
        """Delete multiple records"""
        return await self.delete_one(filters)
    
    async def count(self, filters: dict = None) -> int:
        """Count records"""
        if self.model is None:
            return 0
        async with async_session() as session:
            query = select(func.count()).select_from(self.model)
            if filters:
                for key, value in filters.items():
                    if not hasattr(self.model, key):
                        continue
                    column = getattr(self.model, key)
                    if isinstance(value, dict):
                        for op, op_value in value.items():
                            if op == '$ne':
                                query = query.where(column != op_value)
                            elif op == '$in':
                                query = query.where(column.in_(op_value))
                    else:
                        query = query.where(column == value)
            result = await session.execute(query)
            return result.scalar() or 0
    
    async def distinct(self, field: str, filters: dict = None) -> List:
        """Get distinct values"""
        async with async_session() as session:
            if not hasattr(self.model, field):
                return []
            
            query = select(getattr(self.model, field)).distinct()
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        query = query.where(getattr(self.model, key) == value)
            
            result = await session.execute(query)
            return [row[0] for row in result.fetchall() if row[0] is not None]
    
    async def sum(self, field: str, filters: dict = None) -> float:
        """Sum a field"""
        async with async_session() as session:
            if not hasattr(self.model, field):
                return 0
            
            query = select(func.sum(getattr(self.model, field)))
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        query = query.where(getattr(self.model, key) == value)
            
            result = await session.execute(query)
            return result.scalar() or 0
    
    # Compatibility methods for existing code
    def find(self, filters: dict = None, projection: dict = None):
        """Returns a cursor-like object for compatibility"""
        return QueryBuilder(self, filters)
    
    async def count_documents(self, filters: dict = None) -> int:
        """Alias for count()"""
        return await self.count(filters)
    
    def aggregate(self, pipeline: list):
        """Aggregation support"""
        return AggregationBuilder(self, pipeline)


class QueryBuilder:
    """Query builder for chained operations"""
    
    def __init__(self, collection: PostgresCollection, filters: dict = None):
        self.collection = collection
        self.filters = filters or {}
        self._sort_by = None
        self._sort_desc = False
        self._limit_val = None
        self._skip_val = None
    
    def sort(self, field_or_list, direction=1):
        """Set sort order"""
        if isinstance(field_or_list, list):
            # Handle [(field, direction)] format
            if field_or_list:
                self._sort_by = field_or_list[0][0]
                self._sort_desc = field_or_list[0][1] == -1
        else:
            self._sort_by = field_or_list
            self._sort_desc = direction == -1
        return self
    
    def limit(self, n: int):
        self._limit_val = n
        return self
    
    def skip(self, n: int):
        self._skip_val = n
        return self
    
    async def to_list(self, length: int = None) -> List[dict]:
        return await self.collection.find_all(
            filters=self.filters,
            sort_by=self._sort_by,
            sort_desc=self._sort_desc,
            limit=self._limit_val or length,
            skip=self._skip_val
        )
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if not hasattr(self, '_results'):
            self._results = await self.to_list()
            self._index = 0
        if self._index >= len(self._results):
            raise StopAsyncIteration
        result = self._results[self._index]
        self._index += 1
        return result


class AggregationBuilder:
    """Simple aggregation support"""
    
    def __init__(self, collection: PostgresCollection, pipeline: list):
        self.collection = collection
        self.pipeline = pipeline
    
    async def to_list(self, length: int = None) -> List[dict]:
        """Execute aggregation"""
        # Parse pipeline stages
        match_filters = {}
        group_fields = {}
        
        for stage in self.pipeline:
            if '$match' in stage:
                match_filters = stage['$match']
            if '$group' in stage:
                group_fields = stage['$group']
        
        # Simple aggregation - get totals
        result = {'_id': None}
        
        for field_name, operation in group_fields.items():
            if field_name == '_id':
                continue
            if isinstance(operation, dict):
                if '$sum' in operation:
                    sum_target = operation['$sum']
                    if isinstance(sum_target, str) and sum_target.startswith('$'):
                        db_field = sum_target[1:]
                        result[field_name] = await self.collection.sum(db_field, match_filters)
                    elif sum_target == 1:
                        result[field_name] = await self.collection.count(match_filters)
        
        return [result]


class PostgresDB:
    """Database interface"""
    
    def __init__(self):
        self._collections = {}
    
    def __getattr__(self, name: str) -> PostgresCollection:
        if name.startswith('_'):
            raise AttributeError(name)
        if name not in self._collections:
            self._collections[name] = PostgresCollection(name)
        return self._collections[name]


# Global database instance
db = PostgresDB()
