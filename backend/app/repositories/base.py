"""
Base Repository Pattern
Provides common database operations for all repositories.

Version: 1.0.0
"""

from typing import TypeVar, Generic, Type, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations.

    Provides generic methods for Create, Read, Update, Delete operations
    that can be used by all model-specific repositories.
    """

    def __init__(self, model: Type[ModelType], db: Session):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db

    def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        Get a single record by ID.

        Args:
            id: Record ID

        Returns:
            Model instance or None if not found
        """
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Get all records with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of model instances
        """
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, **kwargs) -> ModelType:
        """
        Create a new record.

        Args:
            **kwargs: Model field values

        Returns:
            Created model instance
        """
        instance = self.model(**kwargs)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """
        Update an existing record.

        Args:
            id: Record ID
            **kwargs: Fields to update

        Returns:
            Updated model instance or None if not found
        """
        instance = self.get_by_id(id)
        if instance:
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            self.db.commit()
            self.db.refresh(instance)
        return instance

    def delete(self, id: int) -> bool:
        """
        Delete a record by ID.

        Args:
            id: Record ID

        Returns:
            True if deleted, False if not found
        """
        instance = self.get_by_id(id)
        if instance:
            self.db.delete(instance)
            self.db.commit()
            return True
        return False

    def count(self) -> int:
        """
        Count total records.

        Returns:
            Total number of records
        """
        return self.db.query(self.model).count()

    def exists(self, id: int) -> bool:
        """
        Check if a record exists.

        Args:
            id: Record ID

        Returns:
            True if exists, False otherwise
        """
        return self.db.query(self.model).filter(self.model.id == id).count() > 0
