from epe.adapters.identity import LocalIdentityAdapter


def test_local_identity_is_explicitly_untrusted():
    fact = LocalIdentityAdapter("displayed-user").current_identity()
    assert fact["trusted"] is False
    assert fact["source"] == "local-process"
    assert fact["kind"] == "unknown"
    assert fact["id"] == "displayed-user"
    assert fact["risk_scope"] == []
