from unittest.mock import patch

import pytest
from pydantic import ValidationError

from pipecat.services.deepseek.llm import DeepSeekLLMService as RealDeepSeekLLMService

from api.services.configuration.registry import (
    REGISTRY,
    DeepSeekLLMConfiguration,
    ServiceProviders,
    ServiceType,
)
from api.services.pipecat.service_factory import create_llm_service_from_provider


class TestDeepSeekLLMConfiguration:
    def test_default_values(self):
        config = DeepSeekLLMConfiguration(api_key="test-key")
        assert config.provider == ServiceProviders.DEEPSEEK
        assert config.model == "deepseek-chat"
        assert config.base_url == "https://api.deepseek.com/v1"

    def test_custom_model(self):
        config = DeepSeekLLMConfiguration(api_key="test-key", model="deepseek-reasoner")
        assert config.model == "deepseek-reasoner"

    def test_custom_base_url(self):
        # Migrating off DeepSeek onto a self-hosted GPU cluster is a base_url
        # change only — the provider/config type stays the same, no code change.
        config = DeepSeekLLMConfiguration(
            api_key="test-key", base_url="https://gpu.internal/v1"
        )
        assert config.base_url == "https://gpu.internal/v1"

    def test_api_key_required(self):
        # DeepSeek authenticates with a bearer key; unlike the BeeCall gateway
        # there's no mTLS/VPC fallback, so the key must be present.
        with pytest.raises(ValidationError):
            DeepSeekLLMConfiguration()


class TestDeepSeekRegistryEntry:
    def test_registered_under_deepseek_provider(self):
        # @register_llm wires the class into REGISTRY at import time. If the
        # decorator is removed or the provider literal mismatches, the schema
        # endpoint won't list DeepSeek and the UI won't render it.
        assert (
            REGISTRY[ServiceType.LLM][ServiceProviders.DEEPSEEK]
            is DeepSeekLLMConfiguration
        )


class TestDeepSeekLLMServiceFactory:
    def test_factory_passes_base_url_and_api_key(self):
        with patch(
            "api.services.pipecat.service_factory.DeepSeekLLMService"
        ) as mock_service:
            mock_service.Settings = RealDeepSeekLLMService.Settings
            create_llm_service_from_provider(
                provider=ServiceProviders.DEEPSEEK.value,
                model="deepseek-chat",
                api_key="test-key",
                base_url="https://gpu.internal/v1",
            )

        assert mock_service.call_count == 1
        kwargs = mock_service.call_args.kwargs
        assert kwargs["api_key"] == "test-key"
        assert kwargs["base_url"] == "https://gpu.internal/v1"
        assert kwargs["settings"].model == "deepseek-chat"
        # Low default temperature for deterministic voice responses.
        assert kwargs["settings"].temperature == 0.1

    def test_factory_falls_back_to_default_base_url(self):
        # When call sites bypass create_llm_service() and pass base_url=None,
        # the factory must still target DeepSeek's public endpoint.
        with patch(
            "api.services.pipecat.service_factory.DeepSeekLLMService"
        ) as mock_service:
            mock_service.Settings = RealDeepSeekLLMService.Settings
            create_llm_service_from_provider(
                provider=ServiceProviders.DEEPSEEK.value,
                model="deepseek-chat",
                api_key="test-key",
                base_url=None,
            )

        kwargs = mock_service.call_args.kwargs
        assert kwargs["base_url"] == "https://api.deepseek.com/v1"

    def test_factory_honors_custom_temperature(self):
        with patch(
            "api.services.pipecat.service_factory.DeepSeekLLMService"
        ) as mock_service:
            mock_service.Settings = RealDeepSeekLLMService.Settings
            create_llm_service_from_provider(
                provider=ServiceProviders.DEEPSEEK.value,
                model="deepseek-chat",
                api_key="test-key",
                temperature=0.3,
            )

        kwargs = mock_service.call_args.kwargs
        assert kwargs["settings"].temperature == 0.3
