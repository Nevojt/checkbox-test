from typing import Any

from fastapi import APIRouter, HTTPException, status
from app.schemas import  users
from app.api.deps import SessionDep, CurrentUser
from app.core import crud

router = APIRouter()

@router.post("/create-user", response_model=users.UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user(*, session: SessionDep, user_in: users.UserCreate) -> Any:
    user = await crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    user = await crud.create_user(session=session, user_create=user_in)
    return user





@router.get("/me", response_model=users.UserPublic)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    Get current user.
    """
    return current_user