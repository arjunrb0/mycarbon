"""Tests for scripts/keep_awake.py, using local pages only — no network.

The fake sleep screen mimics Streamlit Cloud: a "Yes, get this app back up!"
button that, after a delay, loads the app inside an iframe.
"""

import os
import subprocess
import sys

import pytest

pytest.importorskip("playwright.sync_api")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "keep_awake.py")

SLEEP_PAGE = """<!doctype html><html><body>
<p>This app has gone to sleep due to inactivity.</p>
<button onclick="setTimeout(() => {
  document.body.innerHTML = '<iframe id=app></iframe>';
  const d = document.getElementById('app').contentDocument;
  d.open(); d.write('<div class=mc-hero>MyCarbon</div>'); d.close();
}, 1500)">Yes, get this app back up!</button>
</body></html>"""


def _browser_available():
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _browser_available(),
                                reason="Playwright's Chromium is not installed")


def run(url, tmp_path, timeout="20"):
    env = {**os.environ, "APP_URL": url, "LINGER_S": "0", "WAKE_TIMEOUT_S": timeout,
           "SCREENSHOT_PATH": str(tmp_path / "shot.png")}
    return subprocess.run([sys.executable, SCRIPT], env=env, capture_output=True,
                          text=True, timeout=120)


def test_awake_app_passes_without_clicking(tmp_path):
    page = tmp_path / "awake.html"
    page.write_text("<div class='mc-hero'>MyCarbon</div>")
    r = run(page.as_uri(), tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "woke it" not in r.stdout


def test_sleeping_app_is_woken(tmp_path):
    page = tmp_path / "sleep.html"
    page.write_text(SLEEP_PAGE)
    r = run(page.as_uri(), tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "woke it" in r.stdout


def test_app_that_never_starts_fails_with_a_screenshot(tmp_path):
    page = tmp_path / "stuck.html"
    page.write_text("<p>Your app is in the oven</p>")
    r = run(page.as_uri(), tmp_path, timeout="5")
    assert r.returncode == 1
    assert "did not come up" in r.stdout
    assert (tmp_path / "shot.png").exists()


def test_streamlit_outer_page_alone_does_not_count_as_up(tmp_path):
    """The whole point: a page that loads fine but isn't the app is a failure."""
    page = tmp_path / "shell.html"
    page.write_text("<title>MyCarbon</title><div id=root>Streamlit</div>")
    assert run(page.as_uri(), tmp_path, timeout="5").returncode == 1
