
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.users import UserCreate


async def create_user(*, session: AsyncSession, user_create: UserCreate) -> User:
    hashed_password = get_password_hash(user_create.password)
    db_obj = User(username=user_create.username,
                    email=user_create.email,
                    hashed_password=hashed_password
                  )
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj


async def get_user_by_email(*, session: AsyncSession, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = await session.execute(statement)
    return session_user.scalar_one_or_none()


async def authenticate(*, session: AsyncSession, email: str, password: str) -> User | None:
    db_user = await get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user

