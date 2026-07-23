"""Configuration management for Tessara."""

import importlib.metadata
import os
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Union, Literal

from pydantic import Field, BaseModel, field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from tessara_server.constants import PROJECT_ROOT


class DatabaseSettingsBase(BaseModel):
    echo: bool = False

    def connection_string(self) -> str:
        raise NotImplementedError


class NullDatabaseSettings(DatabaseSettingsBase):
    kind: Literal["null"] = "null"

    def connection_string(self) -> str:
        return ""


class PostgresDatabaseSettings(DatabaseSettingsBase):
    kind: Literal["postgres"] = "postgres"

    host: str = "localhost"
    port: int = 5432
    user: str = "tessara"
    password: SecretStr = SecretStr("")
    database: str = "tessara"
    driver: str = "asyncpg"

    def connection_string(self) -> str:
        return (
            f"postgresql+{self.driver}://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.database}"
        )


class SqliteDatabaseSettings(DatabaseSettingsBase):
    kind: Literal["sqlite"] = "sqlite"

    path: Path | Literal[":memory:"] = Path(
        os.path.join(PROJECT_ROOT, "data", "tessara.db")
    )
    read_only: bool = False
    timeout: float = 5.0

    @field_validator("path")
    @classmethod
    def absolute_path(cls, v: Path | str) -> Path | str:
        if v != ":memory:" and isinstance(v, Path) and not v.is_absolute():
            raise ValueError("SQLite path must be absolute")
        return v

    def connection_string(self) -> str:
        if self.path == ":memory:":
            return "sqlite+aiosqlite:///:memory:"
        uri = f"sqlite+aiosqlite:///{self.path}"
        params = []
        if self.read_only:
            params.append("mode=ro")
        if self.timeout:
            params.append(f"timeout={self.timeout}")
        if params:
            uri += "?" + "&".join(params)
        return uri


DatabaseSettings = Annotated[
    Union[PostgresDatabaseSettings, SqliteDatabaseSettings, NullDatabaseSettings],
    Field(discriminator="kind"),
]


class Common(BaseSettings):
    project_name: str = "Tessara"
    page_title: str = "Tessara"

    @property
    def application_version(self) -> str:
        try:
            pyproject = os.path.join(PROJECT_ROOT, "pyproject.toml")
            with open(pyproject, "rb") as f:
                return str(tomllib.load(f)["project"]["version"])
        except Exception:
            pass
        try:
            return importlib.metadata.version("tessara-server")
        except importlib.metadata.PackageNotFoundError:
            return "0.0.0"

    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE_PATH"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Server
    host: str = ""
    port: int = 8000
    trusted_proxy_ip: str = ""

    # Database
    database: DatabaseSettings = Field(default_factory=lambda: NullDatabaseSettings())

    # Auth
    session_secret: SecretStr = SecretStr("")
    session_max_age: int = 86400  # 24 hours
    verification_token_max_age: int = 86400 * 3  # 3 days
    password_reset_token_max_age: int = 3600  # 1 hour
    max_api_tokens_per_user: int = 20

    # Email — used for verification/password-reset links. If smtp_host is
    # unset, send_email() logs the message instead of sending it, so the
    # server still works without SMTP configured (e.g. homelab dev).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_use_tls: bool = True
    smtp_from_address: str = "noreply@tessara.local"

    # Public base URL — used to build absolute links in emails.
    public_base_url: str = "http://localhost:8000"

    # Uploads — /generate and /api/generate. Superuser keys get a larger cap;
    # regular keys are capped low since generation is open to any active key.
    upload_max_bytes: int = 2 * 1024 * 1024  # 2 MB
    upload_max_bytes_superuser: int = 20 * 1024 * 1024  # 20 MB

    # Rate limiting — applies to /generate, /api/generate, and /login.
    rate_limit_generate: str = "10/minute"
    rate_limit_login: str = "5/minute"
    rate_limit_signup: str = "5/minute"
    rate_limit_forgot_password: str = "5/minute"

    @property
    def database_connection_string(self) -> str:
        return self.database.connection_string()


class Local(Common):
    pass


class Production(Common):
    pass


@lru_cache
def load_settings(env: str) -> Common:
    if env == "lcl":
        settings: Common = Local()
    elif env == "prd":
        settings = Production()
    else:
        raise ValueError(f"Unknown environment {env}")

    import logging as _logging

    _log = _logging.getLogger(__name__)

    if not settings.session_secret.get_secret_value():
        _log.warning("SESSION_SECRET is not set — sessions will not survive restarts.")

    if not settings.smtp_host:
        _log.warning(
            "SMTP_HOST is not set — verification/password-reset emails will be "
            "logged instead of sent."
        )

    return settings


application_settings = load_settings(os.getenv("APP_ENV", "lcl"))
