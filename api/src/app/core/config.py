import os

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..utils.path_utils import find_git_root
from ..utils.pulumi_utils import create_pulumi_dir

env_path = os.path.join(str(find_git_root(marker=".env")), ".env")
settings_config = SettingsConfigDict(
    # Provide the full, absolute path to your file
    env_file=env_path,
    env_file_encoding="utf-8",
    extra="ignore",
)


class AppSettings(BaseSettings):
    """FastAPI app settings."""

    model_config = settings_config

    APP_NAME: str = "OpenLabs API"
    APP_DESCRIPTION: str | None = "OpenLabs backend API."
    APP_VERSION: str | None = "dev"
    LICENSE_NAME: str | None = "AGPL-3.0"
    LICENSE_URL: str | None = "https://github.com/OpenLabsHQ/OpenLabs/blob/main/LICENSE"
    CONTACT_NAME: str | None = "OpenLabs Support"
    CONTACT_EMAIL: str | None = "support@openlabs.sh"

    # CORS settings
    CORS_ORIGINS: str = "http://localhost:3000"
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: str = "*"
    CORS_HEADERS: str = "*"


class AuthSettings(BaseSettings):
    """Authentication settings."""

    model_config = settings_config

    SECRET_KEY: str = "ChangeMe123!"  # noqa: S105 (Default)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # One week

    ADMIN_EMAIL: str = "admin@test.com"
    ADMIN_PASSWORD: str = "admin123"  # noqa: S105 (Default)
    ADMIN_NAME: str = "Administrator"


class DatabaseSettings(BaseSettings):
    """Base class for database settings."""

    model_config = settings_config

    pass


class PostgresSettings(DatabaseSettings):
    """Postgres database settings."""

    model_config = settings_config

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "ChangeMe123!"  # noqa: S105 (Default)
    POSTGRES_SERVER: str = "postgres"  # Internal compose DNS
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "openlabs"
    POSTGRES_SYNC_PREFIX: str = "postgresql://"
    POSTGRES_ASYNC_PREFIX: str = "postgresql+asyncpg://"

    # Built after .env loaded to prevent only using defaults
    @computed_field
    def POSTGRES_URI(self) -> str:  # noqa: N802
        """Postgres connection string."""
        return (
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


class RedisQueueSettings(BaseSettings):
    """Redis queue settings."""

    model_config = settings_config

    REDIS_QUEUE_HOST: str = "redis"  # Internal compose DNS
    REDIS_QUEUE_PORT: int = 6379
    REDIS_QUEUE_PASSWORD: str = "ChangeMe123!"  # noqa: S105 (Default)


class PulumiSettings(BaseSettings):
    """Pulumi settings."""

    model_config = settings_config

    PULUMI_DIR: str = create_pulumi_dir()
    PULUMI_CONFIG_PASSPHRASE: str = "ChangeMe123!"  # noqa: S105


class Settings(
    AppSettings, PostgresSettings, PulumiSettings, AuthSettings, RedisQueueSettings
):
    """FastAPI app settings."""

    # Pulumi settings
    @computed_field
    def PULUMI_BACKEND_URL(self) -> str:  # noqa: N802
        """Pulumi Postgres state backend URL."""
        return f"postgres://{self.POSTGRES_URI}?sslmode=disable"


settings = Settings()
