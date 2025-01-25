from pydantic import BaseModel, EmailStr, UUID4, ConfigDict, Strict
from typing import Annotated

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserPublic(BaseModel):
    id: Annotated[UUID4, Strict(False)]
    username: str
    email: EmailStr

class UserMe(BaseModel):
    id: Annotated[UUID4, Strict(False)]
    username: str
    email: EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    id: Annotated[UUID4, Strict(False)]