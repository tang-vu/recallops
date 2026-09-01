from recallops.api.logging import redact


def test_secret_redaction_is_recursive() -> None:
    payload = {
        "authorization": "Bearer visible-secret",
        "nested": {
            "wallet_private_key": "0xsecret",
            "safe": "provider metadata",
            "items": [{"otp": "123456"}, {"amount": "1.00"}],
        },
    }

    redacted = redact(payload)

    assert redacted["authorization"] == "[REDACTED]"
    assert redacted["nested"]["wallet_private_key"] == "[REDACTED]"
    assert redacted["nested"]["items"][0]["otp"] == "[REDACTED]"
    assert redacted["nested"]["safe"] == "provider metadata"
