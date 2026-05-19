"""Configuration management for the IAM / RBAC reviewer agent.

All configuration is read from environment variables so that secrets are
never hard-coded.  A :class:`Settings` instance is resolved once at
import time and cached.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Required for Azure AI Foundry integration:
        AZURE_AI_PROJECT_ENDPOINT   - e.g. https://<hub>.services.ai.azure.com/...
        AZURE_OPENAI_MODEL          - deployment name, e.g. "gpt-4o"

    Optional:
        AZURE_SUBSCRIPTION_ID       - default subscription to analyse
        IAM_REVIEWER_LOG_LEVEL      - DEBUG | INFO | WARNING | ERROR (default INFO)
        IAM_REVIEWER_OWNER_THRESHOLD - max Owners per scope before alerting (default 3)
    """

    # Azure AI Foundry
    azure_ai_project_endpoint: str = Field(
        default="",
        alias="AZURE_AI_PROJECT_ENDPOINT",
        description="Endpoint URL of the Azure AI Foundry project.",
    )
    azure_openai_model: str = Field(
        default="gpt-4o",
        alias="AZURE_OPENAI_MODEL",
        description="Model deployment name to use for the Foundry agent.",
    )

    # Azure subscription
    azure_subscription_id: str = Field(
        default="",
        alias="AZURE_SUBSCRIPTION_ID",
        description="Default subscription ID to query when no --source is provided.",
    )

    # Reviewer knobs
    owner_threshold: int = Field(
        default=3,
        alias="IAM_REVIEWER_OWNER_THRESHOLD",
        description="Maximum number of Owners per scope before IOAR-002 fires.",
    )
    log_level: str = Field(
        default="INFO",
        alias="IAM_REVIEWER_LOG_LEVEL",
        description="Python logging level.",
    )

    model_config = {"populate_by_name": True, "env_file": ".env", "extra": "ignore"}

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got '{v}'")
        return upper

    @property
    def foundry_configured(self) -> bool:
        """Return ``True`` when enough config exists to talk to Azure AI Foundry."""
        return bool(self.azure_ai_project_endpoint)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton :class:`Settings` instance (cached after first call)."""
    return Settings()
