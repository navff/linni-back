from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://linny:linny@db:5432/linny"
    BOT_TOKEN: str = ""
    BOT_NAME: str = "LinnyBot"
    S3_ENDPOINT: str = "https://storage.yandexcloud.net"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "linni"
    CORS_ORIGINS: list[str] = ["*"]
    DEBUG: bool = False
    MONIUM_API_KEY: str = ""
    MONIUM_PROJECT: str = ""
    N8N_SUGGESTIONS_URL: str = "https://n8n.navff.ru/webhook/linni/service-suggestions"
    N8N_DESCRIPTION_URL: str = "https://n8n.navff.ru/webhook/suggest-description"
    N8N_SUGGESTIONS_TOKEN: str = ""
    INTERNAL_API_TOKEN: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
