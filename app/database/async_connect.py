from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import AsyncGenerator
from sqlalchemy.orm import declarative_base
import psycopg2
from psycopg2.extras import RealDictCursor
import time


from app.settings.config import settings


ASYNC_SQLALCHEMY_DATABASE_URL = (f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
                           f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:"
                           f"{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")
# Створення асинхронного двигуна
engine_async = create_async_engine(ASYNC_SQLALCHEMY_DATABASE_URL)
async_session_maker = async_sessionmaker(bind=engine_async, expire_on_commit=False)

Base = declarative_base()


# Асинхронна функція для отримання сесії
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

while True:
    try:
        conn = psycopg2.connect(
            host=settings.POSTGRES_SERVER,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            cursor_factory=RealDictCursor,
        )
        cursor = conn.cursor()
        print("Database connection was successful")
        break

    except Exception as error:
        print("Connection to database failed")
        print("Error:", error)
        time.sleep(2)
