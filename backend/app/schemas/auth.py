from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr

class UserRegister(UserBase):
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=1)

class UserLogin(UserBase):
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    is_admin: bool
    email: str

class ProfileBase(BaseModel):
    full_name: Optional[str] = None
    education: Optional[str] = None
    skills: List[str] = []
    experience_level: Optional[str] = None
    preferred_roles: List[str] = []

class ProfileUpdate(ProfileBase):
    pass

class ProfileResponse(ProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserResponse(UserBase):
    id: int
    is_admin: bool
    created_at: datetime
    profile: Optional[ProfileResponse] = None

    class Config:
        from_attributes = True
