from app.services.authentication import AuthenticationContext, authenticate_credential


class NoQueryDatabase:
    def query(self, *_args, **_kwargs):
        raise AssertionError("Für ungültige Eingaben darf keine Datenbankabfrage erfolgen")


def test_authentication_requires_provider():
    resolved = authenticate_credential(
        NoQueryDatabase(),
        AuthenticationContext(provider="", credential="1234"),
    )
    assert resolved.success is False
    assert resolved.result.message == "Anmeldeverfahren fehlt"


def test_authentication_requires_credential():
    resolved = authenticate_credential(
        NoQueryDatabase(),
        AuthenticationContext(provider="rfid", credential=""),
    )
    assert resolved.success is False
    assert resolved.result.message == "Anmeldemedium fehlt"


def test_authentication_rejects_disabled_or_unknown_plugin():
    resolved = authenticate_credential(
        NoQueryDatabase(),
        AuthenticationContext(provider="nicht_vorhanden", credential="ABC"),
    )
    assert resolved.success is False
    assert "nicht aktiviert oder nicht installiert" in resolved.result.message
