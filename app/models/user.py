from sqlalchemy import Column, String, Integer, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    """User roles for authentication/authorization"""
    ADMIN = "admin"
    USER = "user"


class User(Base):
    """
    User model for authentication.
    Stores user credentials and roles.
    """
    __tablename__ = "users"
    
    # Primary key
    user_id = Column(Integer, primary_key=True, autoincrement=True, doc="Unique user ID")
    
    # Authentication
    username = Column(String(50), unique=True, nullable=False, index=True, doc="Unique username")
    email = Column(String(100), unique=True, nullable=False, index=True, doc="User email")
    hashed_password = Column(String(255), nullable=False, doc="Bcrypt hashed password")
    
    # User information
    full_name = Column(String(100), nullable=True, doc="Full name")
    role = Column(String(20), default="user", index=True, doc="User role (admin/user)")
    
    # Account status
    is_active = Column(Boolean, default=True, doc="Account active status")
    is_verified = Column(Boolean, default=False, doc="Email verified")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), doc="Account creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), doc="Last update timestamp")
    last_login = Column(DateTime(timezone=True), nullable=True, doc="Last login timestamp")
    
    def __repr__(self):
        return f"<User(id={self.user_id}, username={self.username}, role={self.role})>"
    
    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return self.role == "admin"
