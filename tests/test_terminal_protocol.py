from app.services.terminal_protocol import normalize_capabilities


def test_normalize_capabilities_accepts_strings_and_objects():
    result = normalize_capabilities([
        "rfid",
        {"name": "display", "enabled": True, "details": {"browser": "chromium"}},
        {"capability": "camera", "enabled": False},
        "RFID",
        "",
    ])

    assert result == [
        {"name": "rfid", "enabled": True, "details": None},
        {"name": "display", "enabled": True, "details": {"browser": "chromium"}},
        {"name": "camera", "enabled": False, "details": None},
    ]


def test_normalize_capabilities_rejects_non_lists():
    assert normalize_capabilities(None) == []
    assert normalize_capabilities("rfid") == []
