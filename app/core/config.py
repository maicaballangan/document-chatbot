import warnings
from typing import Annotated
from typing import Any
from typing import Literal

from pydantic import AnyUrl
from pydantic import BeforeValidator
from pydantic import computed_field
from pydantic import HttpUrl
from pydantic import model_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith('['):
        return [i.strip() for i in v.split(',')]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file='.env',
        env_ignore_empty=True,
        extra='ignore',
    )
    API_V1_STR: str = '/api/v1'
    SECRET_KEY: str
    # 60 minutes
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 1
    FRONTEND_HOST: str = 'http://localhost:5173'
    ENVIRONMENT: Literal['local', 'staging', 'production'] = 'local'
    STUB_MODE: bool = False

    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip('/') for origin in self.BACKEND_CORS_ORIGINS] + [self.FRONTEND_HOST]

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ''
    POSTGRES_DB: str = ''
    REDIS_URL: str = 'redis://localhost:6379/0'
    MEDIA_PROCESSOR_URL: str
    MEDIA_PROCESSOR_KEY: str

    LEGAL_DATA_INDEX: str
    ELASTIC_API_KEY_ID: str
    ELASTIC_CLOUD_ID: str
    LEGAL_DATA_INDEX: str

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    # TODO: update type to EmailStr when sqlmodel supports it
    EMAILS_FROM_EMAIL: str | None = None
    EMAILS_FROM_NAME: str | None = None

    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str

    # AWS secrets
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_SESSION_TOKEN: str | None = None
    AWS_REGION_NAME: str

    # AWS s3 buckets
    GENERAL_BUCKET_DOMAIN: str
    GENERAL_BUCKET: str
    POLICY_BUCKET_DOMAIN: str
    POLICY_BUCKET: str
    DISCOVERY_BUCKET_DOMAIN: str
    DISCOVERY_BUCKET: str
    ARCHIVE_BUCKET_DOMAIN: str
    ARCHIVE_BUCKET: str

    # LLM config
    SELECTED_LLM: str
    OPENAI_API_KEY: str
    OPENAI_EMBEDDING_MODEL: str
    OPENAI_LLM: str

    GOOGLE_API_KEY: str
    GOOGLE_EMBEDDING_MODEL: str
    GOOGLE_LLM: str

    @model_validator(mode='after')
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_TOKEN_EXPIRE_HOURS: int = 72

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == 'changethis':
            message = (
                f'The value of {var_name} is "changethis", ' 'for security, please change it, at least for deployments.'
            )
            if self.ENVIRONMENT == 'local':
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode='after')
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret('SECRET_KEY', self.SECRET_KEY)
        self._check_default_secret('POSTGRES_PASSWORD', self.POSTGRES_PASSWORD)

        return self


settings = Settings()  # type: ignore
