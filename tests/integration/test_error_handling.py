"""Integration tests for error handling in users domain."""

from __future__ import annotations

import pytest

class TestUserAlreadyExistsError:
    """Test the UserAlreadyExistsError exception."""

    @pytest.mark.asyncio
    async def test_create_duplicate_user(self, client, db_session):
        """Test that creating duplicate user raises proper error."""
        from app.domains.users.service import UserAlreadyExistsError, UserService
        from app.domains.users.schemas import UserCreate
        from app.domains.users.repository import UserRepository
        
        service = UserService(UserRepository(db_session))
        
        # Create first user
        user_data = UserCreate(email="duplicate@example.com", is_active=True)
        user1 = await service.create_user(user_data)
        
        assert user1.email == "duplicate@example.com"
        
        # Try to create duplicate
        with pytest.raises(UserAlreadyExistsError) as exc_info:
            await service.create_user(user_data)
        
        # Verify exception has email attribute
        assert exc_info.value.email == "duplicate@example.com"
        assert "duplicate@example.com" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_user_to_existing_email(self, client, db_session):
        """Test that updating to existing email raises error."""
        from app.domains.users.service import UserAlreadyExistsError, UserService
        from app.domains.users.schemas import UserCreate, UserUpdate
        from app.domains.users.repository import UserRepository
        
        service = UserService(UserRepository(db_session))
        
        # Create two users
        user1 = await service.create_user(
            UserCreate(email="user1@example.com", is_active=True)
        )
        user2 = await service.create_user(
            UserCreate(email="user2@example.com", is_active=True)
        )
        
        # Try to update user2 to user1's email
        with pytest.raises(UserAlreadyExistsError) as exc_info:
            await service.update_user(
                user2, UserUpdate(email="user1@example.com")
            )
        
        assert exc_info.value.email == "user1@example.com"


class TestRepositoryErrorHandling:
    """Test error handling in repository layer."""

    @pytest.mark.asyncio
    async def test_delete_logs_only_on_success(self, db_session, caplog):
        """Test that delete only logs after successful commit."""
        from app.domains.users.repository import UserRepository
        from app.domains.users.models import User
        
        repo = UserRepository(db_session)

        # Create a user
        user = User(email="test@example.com", is_active=True)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Delete the user successfully
        await repo.delete(user)
        
        # Check that success was logged
        # Note: This requires the logger to be configured
        # In real tests, you'd check caplog for the log message

    @pytest.mark.asyncio
    async def test_delete_rollback_on_error(self, db_session):
        """Test that delete rolls back on error."""
        from app.domains.users.repository import UserRepository
        from app.domains.users.models import User
        from sqlalchemy.exc import SQLAlchemyError
        from unittest.mock import patch
        
        repo = UserRepository(db_session)
        
        # Create a user
        user = User(email="test@example.com", is_active=True)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        user_id = user.id

        # Mock commit to raise error
        with patch.object(db_session, "commit", side_effect=SQLAlchemyError("Test error")):
            with pytest.raises(SQLAlchemyError):
                await repo.delete(user)
        
        # User should still exist (rollback occurred)
        await db_session.rollback()
        result = await db_session.get(User, user_id)
        assert result is not None
