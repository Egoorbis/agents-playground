"""Tests for iam_rbac_reviewer.config."""

from __future__ import annotations

import pytest

from iam_rbac_reviewer.config import Settings, get_settings


class TestSettings:
    def test_defaults_are_correct(self) -> None:
        s = Settings()
        assert s.azure_openai_model == "gpt-4o"
        assert s.owner_threshold == 3
        assert s.log_level == "INFO"

    def test_foundry_not_configured_by_default(self) -> None:
        s = Settings()
        assert s.foundry_configured is False

    def test_foundry_configured_when_endpoint_set(self) -> None:
        s = Settings(
            AZURE_AI_PROJECT_ENDPOINT="https://example.azure.com/projects/my-project"
        )
        assert s.foundry_configured is True

    def test_log_level_normalised_to_uppercase(self) -> None:
        s = Settings(IAM_REVIEWER_LOG_LEVEL="debug")
        assert s.log_level == "DEBUG"

    def test_invalid_log_level_raises(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Settings(IAM_REVIEWER_LOG_LEVEL="VERBOSE")

    def test_custom_owner_threshold(self) -> None:
        s = Settings(IAM_REVIEWER_OWNER_THRESHOLD=5)
        assert s.owner_threshold == 5


class TestGetSettings:
    def test_returns_settings_instance(self) -> None:
        s = get_settings()
        assert isinstance(s, Settings)

    def test_is_cached(self) -> None:
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
