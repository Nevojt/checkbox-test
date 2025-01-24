from pydantic_settings import BaseSettings, SettingsConfigDict
import secrets

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/swagger/api/v1"
    PROJECT_NAME: str

    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    # ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    # ALGORITHM: str
    # SECRET_KEY: str = secrets.token_urlsafe(32)






settings = Settings()