import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path.home() / "VivesWallpaper"
TOKEN_FILE = BASE / "jwt.json"
BROWSER_PROFILE = BASE / "vives_browser"

LOGIN_URL = "https://plus.vives.be/mobile/login"
JWT_URL = "https://plus.vives.be/mobile/jwt"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(BROWSER_PROFILE),
        headless=False,
    )

    page = context.pages[0] if context.pages else context.new_page()

    print("VIVES-login openen...")

    page.goto(
        LOGIN_URL,
        wait_until="commit",
        timeout=30000
    )

    print()
    print("Log in met je VIVES-account.")
    print("Bevestig de KU Leuven Authenticator.")
    input("Druk daarna op Enter in dit CMD-venster...")

    print("Nieuwe JWT ophalen...")

    response = context.request.get(
        JWT_URL,
        timeout=30000
    )

    print("Status:", response.status)

    if not response.ok:
        print("JWT ophalen mislukt.")
        context.close()
        raise SystemExit(1)

    try:
        data = response.json()
    except Exception:
        print("Geen JSON ontvangen.")
        print(response.text()[:500])
        context.close()
        raise SystemExit(1)

    if "id_token" not in data:
        print("Geen id_token gevonden.")
        print("Velden:", list(data.keys()))
        context.close()
        raise SystemExit(1)

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"id_token": data["id_token"]},
            f,
            indent=2
        )

    print()
    print("Nieuwe VIVES-token opgeslagen.")
    print(TOKEN_FILE)

    context.close()