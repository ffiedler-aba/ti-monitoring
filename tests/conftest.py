import os
import pytest

# Register dash testing fixtures (fallback to skip if not available)
pytest_plugins = ("dash.testing.plugin",)


def pytest_collection_modifyitems(config, items):
    """Skip UI tests using dash_duo unless explicitly enabled.

    Export DASH_E2E=1 to run UI tests locally/CI with a working WebDriver.
    """
    if os.environ.get("DASH_E2E", "0") != "1":
        skip_ui = pytest.mark.skip(reason="UI tests skipped. Set DASH_E2E=1 to run.")
        for item in items:
            if "dash_duo" in getattr(item, "fixturenames", ()):  # dash UI tests
                item.add_marker(skip_ui)


