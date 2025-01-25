
from typing import Annotated
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError

from app.settings.config import settings
from app.database.async_connect import get_async_session
from app.models.user import User
from app.schemas.users import TokenData

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


SessionDep = Annotated[AsyncSession, Depends(get_async_session)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


async def verify_access_token(token: str, credentials_exception, db: AsyncSession):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: UUID = payload.get("user_id")

        if user_id is None:
            raise credentials_exception

        user = await db.execute(select(User).where(User.id == user_id))
        user = user.scalar_one_or_none()

        if user is None:
            raise credentials_exception

        token_data = TokenData(id=user_id)
        return token_data

    except InvalidTokenError:
        # oauth2_logger.error(f"Invalid JWT token: {token}")
        print("Invalid JWT token")
    except Exception as e:
        # oauth2_logger.error(f"Error verifying access token: {e}")
        raise HTTPException(status_code=404, detail=f"User not found: {e}")
        # raise credentials_exception

async def get_current_user(session: SessionDep, token: TokenDep) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = await verify_access_token(token, credentials_exception, session)

        user = await session.execute(
            select(User).where(User.id == token.id)
        )
        user = user.scalar_one_or_none()
        if not user:
            print("User not found")
            # oauth2_logger.error("Could not find user")

        return user
    except Exception as e:
        # oauth2_logger.error(f"Error getting current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting current user",
        )


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user