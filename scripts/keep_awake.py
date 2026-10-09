"""
Keep the live site awake, and wake it if it has fallen asleep.

Streamlit Community Cloud puts an app to sleep after 12 hours without
visitors, and the next person sees a "wake this app up" screen instead of the
site. A plain HTTP ping does NOT prevent this: it gets back Streamlit's outer
page with status 200 whether the app is awake or asleep, and never reaches the
app itself. Only a real browser session counts as a visit, so this opens the
site in a headless browser.

Run on a schedule by .github/workflows/keep-awake.yml. Exits non-zero if the
app doesn't come up, so a failing run doubles as an outage alert.

    APP_URL=https://mycarbon.streamlit.app/ python scripts/keep_awake.py
"""

import os
import re
import sys
import time

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

URL = os.environ.get("APP_URL", "https://mycarbon.streamlit.app/")
# Something only the running app renders — not Streamlit's outer page, which
# looks the same awake or asleep. ui.hero() draws this class on every page.
READY_SELECTOR = ".mc-hero"
WAKE_BUTTON = re.compile(r"get this app back up", re.I)
TIMEOUT_S = float(os.environ.get("WAKE_TIMEOUT_S", 240))   # a cold start can take minutes
LINGER_S = float(os.environ.get("LINGER_S", 20))           # stay long enough to count as a visit
SCREENSHOT = os.environ.get("SCREENSHOT_PATH", "keep-awake.png")


def app_is_up(page) -> bool:
    # On Community Cloud the app runs inside an iframe, so check every frame.
    for frame in page.frames:
        try:
            if frame.locator(READY_SELECTOR).count() > 0:
                return True
        except PlaywrightError:
            continue          # frame navigated or detached mid-check
    return False


def click_wake_button(page) -> bool:
    for frame in page.frames:
        try:
            button = frame.get_by_role("button", name=WAKE_BUTTON)
            if button.count() > 0 and button.first.is_visible():
                button.first.click()
                return True
        except PlaywrightError:
            continue
    return False


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        except PlaywrightError as exc:
            print(f"::error::Could not load {URL}: {exc}")
            browser.close()
            return 1

        deadline = time.monotonic() + TIMEOUT_S
        woke = False
        while time.monotonic() < deadline:
            if app_is_up(page):
                print(f"App is up{' (it was asleep — woke it)' if woke else ''}: {URL}")
                page.wait_for_timeout(LINGER_S * 1000)
                browser.close()
                return 0
            if not woke and click_wake_button(page):
                woke = True
                print("App was asleep — clicked the wake button, waiting for it to start…")
            page.wait_for_timeout(3_000)

        page.screenshot(path=SCREENSHOT, full_page=True)
        print(f"::error::The app did not come up within {TIMEOUT_S:.0f}s. "
              f"Screenshot saved to {SCREENSHOT}.")
        browser.close()
        return 1


if __name__ == "__main__":
    sys.exit(main())
