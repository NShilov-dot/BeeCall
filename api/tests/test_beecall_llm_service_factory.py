from unittest.mock import patch

from api.services.configuration.registry import (
    REGISTRY,
    BeeCallLLMConfiguration,
    ServiceProviders,
    ServiceType,
)
from api.services.pipecat.service_factory import create_llm_service_from_provider


class TestBeeCallLLMConfiguration:
    def test_default_values(self):
        config = BeeCallLLMConfiguration(api_key="test-key")
        assert config.provider == ServiceProviders.BEECALL
        assert config.model == "default"
        assert config.base_url == "https://llm.beecall.internal/v1"

    def test_custom_model(self):
        config = BeeCallLLMConfiguration(api_key="test-key", model="beecall-pro")
        assert config.model == "beecall-pro"

    def test_custom_base_url(self):
        config = BeeCallLLMConfiguration(
            api_key="test-key", base_url="https://gw.internal/v1"
        )
        assert config.base_url == "https://gw.internal/v1"

    def test_api_key_optional(self):
        # Internal gateways often gate by mTLS / VPC and don't accept a bearer.
        # The config must allow api_key=None so those deployments aren't forced
        # to set a sentinel value.
        config = BeeCallLLMConfiguration(api_key=None)
        assert config.api_key is None


class TestBeeCallRegistryEntry:
    def test_registered_under_beecall_provider(self):
        # @register_llm wires the class into REGISTRY at import time. If the
        # decorator is removed or the provider literal mismatches, the schema
        # endpoint won't list BeeCall and the UI won't render it.
        assert (
            REGISTRY[ServiceType.LLM][ServiceProviders.BEECALL]
            is BeeCallLLMConfiguration
        )


class TestBeeCallLLMServiceFactory:
    def test_factory_passes_base_url_and_api_key(self):
        with patch(
            "api.services.pipecat.service_factory.BeeCallLLMService"
        ) as mock_service:
            create_llm_service_from_provider(
                provider=ServiceProviders.BEECALL.value,
                model="beecall-pro",
                api_key="test-key",
                base_url="https://gw.internal/v1",
            )

        assert mock_service.call_count == 1
        kwargs = mock_service.call_args.kwargs
        assert kwargs["api_key"] == "test-key"
        assert kwargs["base_url"] == "https://gw.internal/v1"
        assert kwargs["settings"].model == "beecall-pro"
        # Default temperature applied when caller omits it.
        assert kwargs["settings"].temperature == 0.1

    def test_factory_falls_back_to_default_base_url(self):
        # create_llm_service() extracts base_url from user_config. When
        # call sites bypass that helper and pass base_url=None directly,
        # the factory must still produce a working service rather than
        # raising — the configuration default is the fallback.
        with patch(
            "api.services.pipecat.service_factory.BeeCallLLMService"
        ) as mock_service:
            create_llm_service_from_provider(
                provider=ServiceProviders.BEECALL.value,
                model="default",
                api_key="test-key",
                base_url=None,
            )

        kwargs = mock_service.call_args.kwargs
        assert kwargs["base_url"] == "https://llm.beecall.internal/v1"

    def test_factory_honors_custom_temperature(self):
        with patch(
            "api.services.pipecat.service_factory.BeeCallLLMService"
        ) as mock_service:
            create_llm_service_from_provider(
                provider=ServiceProviders.BEECALL.value,
                model="beecall-pro",
                api_key="test-key",
                base_url="https://gw.internal/v1",
                temperature=0.7,
            )

        kwargs = mock_service.call_args.kwargs
        assert kwargs["settings"].temperature == 0.7
