from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class User(BaseModel):
    username: str
    full_name: str
    role: str = Field(default="teacher", pattern="^(teacher|admin|root)$")
    disabled: bool = False


class UserInDB(User):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos


class TokenPayload(BaseModel):
    sub: str  # username
    exp: datetime
    iat: datetime
    role: str


class SocioCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    dni: str = Field(pattern=r"^\d{8}[A-Z]$")  # 8 dígitos + letra


class SocioResponse(BaseModel):
    id: int
    nombre: str
    email: str
    dni: str
    created_by: str
    created_at: datetime


class LoginRequest(BaseModel):
    username: str
    password: str
