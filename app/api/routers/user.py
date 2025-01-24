from fastapi import APIRouter
from app.schemas import  users



router = APIRouter()

@router.post("/create-user", response_model=users.UserPublic)
async def create_user(user: users.UserCreate):

    return user