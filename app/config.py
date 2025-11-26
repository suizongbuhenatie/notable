from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from the environment."""

    app_name: str = Field(default="Notable API", validation_alias="APP_NAME")
    cors_origins: List[str] = Field(default_factory=lambda: ["*"], validation_alias="CORS_ORIGINS")

    db_user: str = Field(default="postgres", validation_alias="DB_USER")
    db_password: str = Field(default="postgres", validation_alias="DB_PASSWORD")
    db_host: str = Field(default="localhost", validation_alias="DB_HOST")
    db_port: int = Field(default=5432, validation_alias="DB_PORT")
    db_name: str = Field(default="app", validation_alias="DB_NAME")
    database_url: PostgresDsn | str | None = Field(default=None, validation_alias="DATABASE_URL")

    s3_endpoint_url: str = Field(default="http://localhost:9000", validation_alias="S3_ENDPOINT_URL")
    s3_bucket: str = Field(default="notable", validation_alias="S3_BUCKET")
    s3_region: str = Field(default="us-east-1", validation_alias="S3_REGION")
    s3_access_key_id: str = Field(default="minioadmin", validation_alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str = Field(default="minioadmin", validation_alias="S3_SECRET_ACCESS_KEY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        """Parse comma-separated CORS origins."""

        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def assembled_database_url(self) -> str:
        """Return a full database URL based on env values."""

        if self.database_url:
            return str(self.database_url)
        return f"postgresql+psycopg2://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()
