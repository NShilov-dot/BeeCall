"""Key validators must stay offline.

A live API call (models.list / projects.list) dies on cert/TLS interception in
the corporate MITM proxy even for a valid key, so config-save must not gate on
one. Presence of a key is enough at save time; real auth errors surface at first
use. See _check_deepseek_api_key for the same rationale.
"""

from api.services.configuration.check_validity import UserConfigurationValidator


def test_key_presence_validators_are_offline():
    v = UserConfigurationValidator()
    for check in (
        v._check_openai_api_key,
        v._check_deepgram_api_key,
        v._check_groq_api_key,
    ):
        # Present key → ok without any network round-trip. If a live call came
        # back, this fake key would raise or return False and fail the test.
        assert check("model", "any-key") is True
        # Empty/missing key → flagged offline, no network needed.
        assert check("model", "") is False
        assert check("model", None) is False
