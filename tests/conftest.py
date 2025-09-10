import os
import time
import pytest

# Keine explizite Plugin-Registrierung; dash.testing.plugin wird ggf. bereits von pytest geladen


def pytest_collection_modifyitems(config, items):
    """Skip UI tests using dash_duo unless explicitly enabled.

    Export DASH_E2E=1 to run UI tests locally/CI with a working WebDriver.
    """
    if os.environ.get("DASH_E2E", "0") != "1":
        skip_ui = pytest.mark.skip(reason="UI tests skipped. Set DASH_E2E=1 to run.")
        for item in items:
            if "dash_duo" in getattr(item, "fixturenames", ()):  # dash UI tests
                item.add_marker(skip_ui)


def pytest_setup_options():
    """Provide Selenium Chrome options for dash.testing to avoid profile conflicts.
    """
    from selenium.webdriver.chrome.options import Options

    options = Options()
    # Headless & stability flags
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")

    # Unique user-data-dir per run to avoid 'profile in use' errors
    unique_profile = f"/tmp/chrome-profile-{os.getpid()}-{int(time.time()*1000)}"
    options.add_argument(f"--user-data-dir={unique_profile}")

    # If chromium binary exists, point to it explicitly (optional)
    for candidate in ("/usr/bin/chromium-browser", "/usr/bin/chromium"):
        if os.path.exists(candidate):
            options.binary_location = candidate
            break

    return options


