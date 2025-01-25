from fastapi import APIRouter
from .routers import user, login, products

api_router = APIRouter()

api_router.include_router(login.router, tags=["login"])
api_router.include_router(user.router, prefix="/users", tags=["users"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
