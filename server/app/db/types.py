"""Database type definitions with dialect compatibility."""

from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.dialects import postgresql


class DialectJSON(TypeDecorator):
    """JSON type that uses JSONB for PostgreSQL and JSON for SQLite."""
    
    impl = JSON
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(postgresql.JSONB())
        elif dialect.name == 'sqlite':
            return dialect.type_descriptor(JSON())
        else:
            return dialect.type_descriptor(JSON())

