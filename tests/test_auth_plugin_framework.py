from app.auth_plugins.base import AuthenticationPlugin, AuthPluginMetadata, AuthResult
from app.auth_plugins.registry import installed_plugin


def test_rfid_plugin_is_installed():
    plugin = installed_plugin("rfid")
    assert plugin is not None
    assert plugin.metadata.key == "rfid"
    assert "rfid" in plugin.metadata.credential_types
    assert "rfid" in plugin.metadata.required_capabilities


def test_unknown_plugin_is_not_installed():
    assert installed_plugin("does-not-exist") is None


def test_metadata_serialization_uses_lists():
    metadata = AuthPluginMetadata(
        key="test",
        name="Test",
        version="1.0",
        description="Testplugin",
        credential_types=("test",),
        required_capabilities=("display",),
    )
    data = metadata.as_dict()
    assert data["credential_types"] == ["test"]
    assert data["required_capabilities"] == ["display"]
