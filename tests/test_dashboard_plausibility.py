from app.routes.dashboard_plausibility import severity_bucket


def test_severity_bucket_maps_existing_values():
    assert severity_bucket("rot") == "critical"
    assert severity_bucket("critical") == "critical"
    assert severity_bucket("gelb") == "warning"
    assert severity_bucket(None) == "warning"
    assert severity_bucket("blau") == "info"
    assert severity_bucket("hinweis") == "info"
