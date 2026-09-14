"""Keeps the FulfillSense Streamlit Community Cloud app awake 24/7.

Why this exists
---------------
Streamlit Community Cloud hibernates an app after ~12 hours without a real
viewer session and replaces it with the "Zzzz - This app has gone to sleep due
to inactivity" screen.

A plain HTTP ping (``curl https://fulfill-sense.streamlit.app/``) does NOT work:

  * The URL returns HTTP 200 even while the app is hibernating, because the
    sleep screen is rendered client-side by the Streamlit Cloud JS shell.
  * Hibernation is tracked from real viewer sessions (the ``/_stcore/stream``
    websocket), which curl never opens, so the ping resets nothing.
  * The wake-up call ``POST /api/v2/app/resume`` returns HTTP 403 for plain HTTP
    clients; it only succeeds from a real browser session.

So we drive a real headless Chromium session instead: load the app, click the
wake-up button if it is asleep, wait until the app actually renders, then hold
the session open long enough for Streamlit to count it as traffic.

Page structure note: ``https://<app>.streamlit.app/`` only serves the Streamlit
Cloud shell. The app itself is rendered inside a nested iframe served from
``/~/+/``, so readiness has to be checked inside that frame, not on the top
level document.

Exit code is 0 only if the app is confirmed up and rendering.
"""

from __future__ import annotations

import os
import sys
import time

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

APP_URL = os.environ.get("APP_URL", "https://fulfill-sense.streamlit.app/")
# How long to stay connected once the app is up, so Streamlit registers a real
# viewer session and resets the inactivity timer.
HOLD_SECONDS = int(os.environ.get("HOLD_SECONDS", "75"))
# Cold boots (dependency install + model load) can take a couple of minutes.
WAKE_TIMEOUT_SECONDS = int(os.environ.get("WAKE_TIMEOUT_SECONDS", "420"))
SCREENSHOT_PATH = os.environ.get("SCREENSHOT_PATH", "keepalive.png")

# "Yes, get this app back up!" on the hibernation screen.
WAKE_BUTTON = "button:has-text('back up')"
# The nested frame that actually hosts the Streamlit app.
APP_FRAME_MARKER = "/~/+/"
# Containers Streamlit renders inside that frame once the app is serving.
APP_READY = "[data-testid='stAppViewContainer'], [data-testid='stApp'], .stApp"
# A string rendered by app.py, used as a final sanity check.
APP_MARKER = "FulfillSense Sandbox"


def log(message: str) -> None:
  print(f"[keep-alive] {message}", flush=True)


def save_screenshot(page, why: str) -> None:
  try:
    page.screenshot(path=SCREENSHOT_PATH)
    log(f"Saved screenshot ({why}) to {SCREENSHOT_PATH}")
  except PlaywrightError as err:
    log(f"Could not save screenshot: {err}")


def app_frame(page):
  """Returns the frame hosting the Streamlit app, or None if not present yet."""
  for frame in page.frames:
    if APP_FRAME_MARKER in frame.url:
      return frame
  return None


def is_app_rendering(page) -> bool:
  frame = app_frame(page)
  if frame is None:
    return False
  try:
    return frame.locator(APP_READY).count() > 0
  except PlaywrightError:
    # The frame can be swapped out mid-boot; treat as "not ready yet".
    return False


def is_asleep(page) -> bool:
  try:
    button = page.locator(WAKE_BUTTON).first
    return bool(button.count()) and button.is_visible()
  except PlaywrightError:
    return False


def wake_and_hold() -> int:
  with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()

    log(f"Opening {APP_URL}")
    page.goto(APP_URL, wait_until="domcontentloaded", timeout=60_000)

    deadline = time.time() + WAKE_TIMEOUT_SECONDS
    was_asleep = False
    ready = False
    last_note = 0.0

    while time.time() < deadline:
      if is_asleep(page):
        was_asleep = True
        log("App is hibernating - clicking the wake-up button.")
        try:
          page.locator(WAKE_BUTTON).first.click()
        except PlaywrightError as err:
          log(f"Wake click failed, will retry: {err}")
        page.wait_for_timeout(5_000)
        continue

      if is_app_rendering(page):
        ready = True
        break

      if time.time() - last_note > 30:
        last_note = time.time()
        remaining = int(deadline - time.time())
        log(f"Still booting... ({remaining}s left before giving up)")

      page.wait_for_timeout(3_000)

    if not ready:
      log("FAILED: app did not finish booting before the timeout.")
      save_screenshot(page, "timeout")
      browser.close()
      return 1

    log(
        "App is up"
        + (
            " (it was asleep and has been woken)."
            if was_asleep
            else " (it was already awake)."
        )
    )

    # Hold the websocket session open so Streamlit counts this as real traffic.
    log(f"Holding the session open for {HOLD_SECONDS}s.")
    held = 0
    while held < HOLD_SECONDS:
      page.wait_for_timeout(15_000)
      held += 15
      page.mouse.move(200 + (held % 50), 300 + (held % 50))
      if is_asleep(page):
        log("FAILED: app fell back to the hibernation screen while holding.")
        save_screenshot(page, "regressed")
        browser.close()
        return 1

    frame = app_frame(page)
    body_text = ""
    if frame is not None:
      try:
        body_text = frame.locator("body").inner_text(timeout=15_000)
      except PlaywrightError as err:
        log(f"Could not read app text: {err}")

    if APP_MARKER in body_text:
      log(f"Verified the dashboard is rendering ('{APP_MARKER}' found).")
    else:
      log(
          f"WARNING: '{APP_MARKER}' not found in the rendered app. It is awake"
          " but may be erroring - check the screenshot artifact."
      )

    save_screenshot(page, "final state")
    browser.close()
    return 0


if __name__ == "__main__":
  sys.exit(wake_and_hold())
