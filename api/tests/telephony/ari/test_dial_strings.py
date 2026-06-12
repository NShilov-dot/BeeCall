"""Unit tests for outbound dial-string construction (trunk routing).

One rule for calls and transfers alike: bare numbers go through the
configured outbound trunk, full PJSIP/SIP dial strings pass through
unchanged, and with no trunk configured the legacy PJSIP/<number> form
is preserved.
"""

from api.services.telephony.providers.ari.provider import ARIProvider


def _provider(trunk_name="") -> ARIProvider:
    return ARIProvider(
        {
            "ari_endpoint": "http://asterisk:8088",
            "app_name": "dograh",
            "app_password": "dograh_dev_password",
            "trunk_name": trunk_name,
        }
    )


class TestBuildSipEndpoint:
    def test_bare_number_with_trunk_routes_through_trunk(self):
        assert (
            _provider("beeline")._build_sip_endpoint("+998901234567")
            == "PJSIP/+998901234567@beeline"
        )

    def test_bare_number_without_trunk_keeps_legacy_local_form(self):
        assert _provider()._build_sip_endpoint("6001") == "PJSIP/6001"

    def test_full_pjsip_dial_string_bypasses_trunk(self):
        # Escape hatch for internal extensions when a trunk is configured.
        assert (
            _provider("beeline")._build_sip_endpoint("PJSIP/6001")
            == "PJSIP/6001"
        )

    def test_explicit_trunk_in_dial_string_passes_through(self):
        assert (
            _provider("beeline")._build_sip_endpoint("PJSIP/+998900000000@other")
            == "PJSIP/+998900000000@other"
        )

    def test_sip_technology_passes_through(self):
        assert (
            _provider("beeline")._build_sip_endpoint("SIP/legacy-endpoint")
            == "SIP/legacy-endpoint"
        )
