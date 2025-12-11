"""
Authentication schemas.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token payload data"""
    username: Optional[str] = None


class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema"""
    password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    """User response schema"""
    user_id: int
    is_active: bool
    role: str
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }
