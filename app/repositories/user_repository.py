from typing import Optional, List
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.models.user import User, UserRole


class UserRepository:
    """Repository for User model operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        username: str,
        email: str,
        hashed_password: str,
        full_name: Optional[str] = None,
        role: str = "user"
    ) -> User:
        """Create new user"""
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await self.db.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_username_or_email(self, username: str, email: str) -> Optional[User]:
        """Get user by username or email"""
        result = await self.db.execute(
            select(User).where(
                or_(User.username == username, User.email == email)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, active_only: bool = True) -> List[User]:
        """Get all users"""
        query = select(User)
        
        if active_only:
            query = query.where(User.is_active == True)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_last_login(self, user_id: int) -> Optional[User]:
        """Update user last login timestamp"""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        user.last_login = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def update_password(self, user_id: int, hashed_password: str) -> Optional[User]:
        """Update user password"""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        user.hashed_password = hashed_password
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def update_role(self, user_id: int, role: UserRole) -> Optional[User]:
        """Update user role"""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        user.role = role
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def deactivate(self, user_id: int) -> Optional[User]:
        """Deactivate user account"""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        user.is_active = False
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def activate(self, user_id: int) -> Optional[User]:
        """Activate user account"""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        user.is_active = True
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def verify_email(self, user_id: int) -> Optional[User]:
        """Mark user email as verified"""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        user.is_verified = True
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def delete(self, user_id: int) -> bool:
        """Delete user"""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        await self.db.delete(user)
        await self.db.commit()
        return True
    
    async def exists(self, username: str, email: str) -> bool:
        """Check if username or email already exists"""
        user = await self.get_by_username_or_email(username, email)
        return user is not None
