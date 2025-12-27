"""
SQLAlchemy Base Configuration
Provides the declarative base for all database models.

Version: 1.0.0
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData

# Naming convention for constraints
# This ensures consistent naming across different databases
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)

# Create declarative base
Base = declarative_base(metadata=metadata)
