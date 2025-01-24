from pydantic import BaseModel, EmailStr, UUID4, ConfigDict, Strict
from typing import Optional, Annotated

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserPublic(BaseModel):
    # id: Annotated[UUID4, Strict(False)]
    username: str

class UserMe(BaseModel):
    id: Annotated[UUID4, Strict(False)]
    username: str
    email: EmailStr