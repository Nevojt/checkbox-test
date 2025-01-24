from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware
from app.api.main import api_router
from app.settings.config import settings
from app.database.async_connect import engine_async
from app.models import user

def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"

async def init_db():
    async with engine_async.begin() as conn:
        try:
            await conn.run_sync(user.Base.metadata.create_all)
            print("All tables created successfully.")
        except Exception as e:
            print(f"Error during table creation: {e}")

app = FastAPI( title=settings.PROJECT_NAME,
    docs_url="/swagger/docs",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    on_startup=[init_db])

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)