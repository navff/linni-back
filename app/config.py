from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://linny:linny@db:5432/linny"
    BOT_TOKEN: str = ""
    BOT_NAME: str = "LinnyBot"
    S3_ENDPOINT: str = "https://storage.yandexcloud.net"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "linny-files"
    CORS_ORIGINS: list[str] = ["*"]
    DEBUG: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
