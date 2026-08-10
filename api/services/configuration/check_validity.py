from typing import Optional, TypedDict

# try:
#     from pyneuphonic import Neuphonic
# except ImportError:
#     Neuphonic = None
from api.schemas.user_configuration import (
    UserConfiguration,
)
from api.services.configuration.registry import ServiceConfig, ServiceProviders

AuthContext = TypedDict(
    "AuthContext",
    {"organization_id": Optional[int], "created_by": Optional[str]},
    total=False,
)


class APIKeyStatus(TypedDict):
    model: str
    message: str


class APIKeyStatusResponse(TypedDict):
    status: list[APIKeyStatus]


class UserConfigurationValidator:
    def __init__(self):
        self._validator_map = {
            ServiceProviders.OPENAI.value: self._check_openai_api_key,
            ServiceProviders.DEEPGRAM.value: self._check_deepgram_api_key,
            ServiceProviders.GROQ.value: self._check_groq_api_key,
            ServiceProviders.OPENROUTER.value: self._check_openrouter_api_key,
            ServiceProviders.ELEVENLABS.value: self._validate_elevenlabs_api_key,
            ServiceProviders.GOOGLE.value: self._check_google_api_key,
            ServiceProviders.AZURE.value: self._check_azure_api_key,
            ServiceProviders.CARTESIA.value: self._check_cartesia_api_key,
            ServiceProviders.SARVAM.value: self._check_sarvam_api_key,
            ServiceProviders.SPEECHMATICS.value: self._check_speechmatics_api_key,
            ServiceProviders.CAMB.value: self._check_camb_api_key,
            ServiceProviders.AWS_BEDROCK.value: self._check_aws_bedrock_api_key,
            ServiceProviders.SPEACHES.value: self._check_speaches_api_key,
            ServiceProviders.GOOGLE_VERTEX.value: self._check_google_vertex_llm_api_key,
            ServiceProviders.OPENAI_REALTIME.value: self._check_openai_api_key,
            ServiceProviders.GROK_REALTIME.value: self._check_grok_realtime_api_key,
            ServiceProviders.ULTRAVOX_REALTIME.value: self._check_ultravox_realtime_api_key,
            ServiceProviders.GOOGLE_REALTIME.value: self._check_google_api_key,
            ServiceProviders.GOOGLE_VERTEX_REALTIME.value: self._check_google_vertex_realtime_api_key,
            ServiceProviders.ASSEMBLYAI.value: self._check_assemblyai_api_key,
            ServiceProviders.GLADIA.value: self._check_gladia_api_key,
            ServiceProviders.RIME.value: self._check_rime_api_key,
            ServiceProviders.MINIMAX.value: self._check_minimax_api_key,
            ServiceProviders.DEEPSEEK.value: self._check_deepseek_api_key,
        }

    async def validate(
        self,
        configuration: UserConfiguration,
        organization_id: Optional[int] = None,
        created_by: Optional[str] = None,
    ) -> APIKeyStatusResponse:
        self._auth_context: AuthContext = {
            "organization_id": organization_id,
            "created_by": created_by,
        }
        status_list = []

        status_list.extend(self._validate_service(configuration.llm, "llm"))
        status_list.extend(self._validate_service(configuration.stt, "stt"))
        status_list.extend(self._validate_service(configuration.tts, "tts"))
        # Embeddings is optional - only validate if configured
        status_list.extend(
            self._validate_service(
                configuration.embeddings, "embeddings", required=False
            )
        )
        # Realtime is optional - only validate if is_realtime is enabled
        if configuration.is_realtime:
            status_list.extend(
                self._validate_service(
                    configuration.realtime, "realtime", required=True
                )
            )

        if status_list:
            raise ValueError(status_list)

        return {"status": [{"model": "all", "message": "ok"}]}

    def _validate_service(
        self,
        service_config: Optional[ServiceConfig],
        service_name: str,
        required: bool = True,
    ) -> list[APIKeyStatus]:
        """Validate a service configuration and return any error statuses."""
        if not service_config:
            if required:
                return [{"model": service_name, "message": "API key is missing"}]
            return []  # Optional service not configured is OK

        provider = service_config.provider

        # Piper runs in-process: no API key, no endpoint, nothing to reach.
        # Without this early return it falls through to _check_api_key, which
        # returns False for any provider absent from _validator_map and would
        # report the default TTS as invalid.
        if provider == ServiceProviders.PIPER.value:
            return []

        # Speaches doesn't require an API key
        if provider == ServiceProviders.SPEACHES.value:
            try:
                if not self._check_speaches_api_key(provider, service_config):
                    return [
                        {
                            "model": service_name,
                            "message": f"Invalid {provider} configuration",
                        }
                    ]
            except ValueError as e:
                return [{"model": service_name, "message": str(e)}]
            return []

        # Vertex Realtime uses service-account credentials (or ADC) instead of api_key
        if provider == ServiceProviders.GOOGLE_VERTEX_REALTIME.value:
            try:
                if not self._check_google_vertex_realtime_api_key(
                    provider, service_config
                ):
                    return [
                        {
                            "model": service_name,
                            "message": f"Invalid {provider} configuration",
                        }
                    ]
            except ValueError as e:
                return [{"model": service_name, "message": str(e)}]
            return []

        # Vertex LLM uses service-account credentials (or ADC) instead of api_key
        if provider == ServiceProviders.GOOGLE_VERTEX.value:
            try:
                if not self._check_google_vertex_llm_api_key(provider, service_config):
                    return [
                        {
                            "model": service_name,
                            "message": f"Invalid {provider} configuration",
                        }
                    ]
            except ValueError as e:
                return [{"model": service_name, "message": str(e)}]
            return []

        # AWS Bedrock uses AWS credentials instead of api_key
        if provider == ServiceProviders.AWS_BEDROCK.value:
            try:
                if not self._check_aws_bedrock_api_key(provider, service_config):
                    return [
                        {
                            "model": service_name,
                            "message": f"Invalid {provider} credentials",
                        }
                    ]
            except ValueError as e:
                return [{"model": service_name, "message": str(e)}]
            return []

        # MiniMax TTS requires a group_id alongside the API key.
        # LLM configs don't expose group_id, so only check when the field exists.
        if provider == ServiceProviders.MINIMAX.value and hasattr(
            service_config, "group_id"
        ):
            if not getattr(service_config, "group_id", None):
                return [
                    {
                        "model": service_name,
                        "message": "group_id is required for MiniMax TTS",
                    }
                ]

        api_key = service_config.api_key

        try:
            if not self._check_api_key(provider, api_key):
                return [
                    {"model": service_name, "message": f"Invalid {provider} API key"}
                ]
        except ValueError as e:
            return [{"model": service_name, "message": str(e)}]

        return []

    def _check_api_key(self, provider: str, api_key: str) -> bool:
        """Check if an API key for a provider is valid."""
        validator = self._validator_map.get(provider)
        if not validator:
            return False

        return validator(provider, api_key)

    # OpenAI / Deepgram / Groq previously verified the key with a live API call
    # (models.list / projects.list). Behind the corporate MITM proxy that call
    # fails on cert/TLS interception even when the key is valid, so it rejected
    # good keys at save time. Trust the key's presence here and let a real auth
    # error surface at first call — same approach as _check_deepseek_api_key.
    # bool(api_key) still catches the common "forgot to paste a key" case
    # offline, without a network round-trip.
    def _check_openai_api_key(self, model: str, api_key: str) -> bool:
        return bool(api_key)

    def _check_deepgram_api_key(self, model: str, api_key: str) -> bool:
        return bool(api_key)

    def _check_groq_api_key(self, model: str, api_key: str) -> bool:
        return bool(api_key)

    def _validate_elevenlabs_api_key(self, model: str, api_key: str) -> bool:
        return True

    def _check_google_api_key(self, model: str, api_key: str) -> bool:
        return True

    def _check_azure_api_key(self, model: str, api_key: str) -> bool:
        return True

    def _check_cartesia_api_key(self, model: str, api_key: str) -> bool:
        return True


    def _check_sarvam_api_key(self, model: str, api_key: str) -> bool:
        return True

    def _check_openrouter_api_key(self, model: str, api_key: str) -> bool:
        return True

    def _check_grok_realtime_api_key(self, model: str, api_key: str) -> bool:
        return True

    def _check_ultravox_realtime_api_key(self, model: str, api_key: str) -> bool:
        return True

    def _check_speechmatics_api_key(self, model: str, api_key: str) -> bool:
        return True

    def _check_camb_api_key(self, model: str, api_key: str) -> bool:
        return True

    def _check_speaches_api_key(self, model: str, service_config) -> bool:
        if not getattr(service_config, "base_url", None):
            raise ValueError("base_url is required for Speaches services")
        return True

    def _check_google_vertex_realtime_api_key(self, model: str, service_config) -> bool:
        if not getattr(service_config, "project_id", None):
            raise ValueError("project_id is required for Google Vertex Realtime")
        if not getattr(service_config, "location", None):
            raise ValueError("location is required for Google Vertex Realtime")
        return True

    def _check_google_vertex_llm_api_key(self, model: str, service_config) -> bool:
        if not getattr(service_config, "project_id", None):
            raise ValueError("project_id is required for Google Vertex")
        if not getattr(service_config, "location", None):
            raise ValueError("location is required for Google Vertex")
        return True

    def _check_aws_bedrock_api_key(self, model: str, service_config) -> bool:
        if not service_config.aws_access_key or not service_config.aws_secret_key:
            raise ValueError("AWS access key and secret key are required for Bedrock")
        return True

    def _check_assemblyai_api_key(self, model: str, service_config) -> bool:
        return True

    def _check_gladia_api_key(self, model: str, api_key: str) -> bool:
        return True

    def _check_rime_api_key(self, model: str, api_key: str) -> bool:
        return True

    def _check_minimax_api_key(self, model: str, api_key: str) -> bool:
        # MiniMax doesn't publish a cheap key-validation endpoint; trust the key
        # at save time and surface auth errors at first call (same as Rime/Sarvam).
        return True

    def _check_deepseek_api_key(self, model: str, api_key: str) -> bool:
        # Trust the key at save time and surface auth errors at first call. A live
        # check (GET /models) would tunnel through the corporate MITM proxy and
        # can fail on cert/TLS interception even when the key is valid, so we don't
        # gate config-save on it (same approach as MiniMax/OpenRouter).
        return True
