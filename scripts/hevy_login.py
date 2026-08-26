#!/usr/bin/env python3
"""
One-time manual login for hevy_unofficial, bypassing its automated-browser
login path — Google actively detects and blocks OAuth logins from
Playwright/Selenium-driven browsers, so if your Hevy account uses "Sign in
with Google" (or any account, really), automated login is unreliable.

Instead: log into hevy.com completely normally in your own regular browser,
then copy one cookie value here. Nothing is typed into an automated browser
and no password ever touches this script.

Steps:
  1. Open https://hevy.com in Chrome/Safari/whatever you normally use, and
     log in as usual (Google sign-in works fine here — it's just your
     regular browser, not an automated one).
  2. Open DevTools (Cmd+Option+I on Mac) -> Application tab -> Cookies ->
     https://hevy.com -> find the cookie named "auth2.0-token" -> copy its
     Value.
  3. Run this script and paste that value when prompted:
       python3 scripts/hevy_login.py

Tokens are cached to ~/.config/hevy-unofficial/credentials.json and
auto-refresh after this — you shouldn't need to do this again unless the
refresh token itself gets revoked.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hevy_unofficial import CredentialStore, parse_auth20_cookie_value  # noqa: E402


def main() -> None:
    email = input("Hevy account email (used only as a local cache key): ").strip()
    if not email:
        print("Email is required.")
        sys.exit(1)

    raw_cookie = input("Paste the auth2.0-token cookie value: ").strip()
    if not raw_cookie:
        print("Cookie value is required.")
        sys.exit(1)

    tokens = parse_auth20_cookie_value(raw_cookie)
    store = CredentialStore()
    store.save(email, tokens)
    print(f"Saved credentials for {email} -> {store.path}")


if __name__ == "__main__":
    main()
