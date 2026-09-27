import base64
import ctypes
import json
import re
import subprocess
import sys

from datetime import datetime, timedelta
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont


# ---------- INSTELLINGEN ----------

BASE = Path.home() / "VivesWallpaper"

TOKEN_FILE = BASE / "jwt.json"
CONFIG_FILE = BASE / "config.json"
EVENTS_FILE = BASE / "last_events.json"
OUTPUT = BASE / "vives_wallpaper.png"

API_URL = "https://plus.vives.be/api/events"

TITLE = "VIVES"

# Alleen gebruiken voor handmatige tests.
TEST_FORCE_RELOGIN = False

# Gebruik de gewone Python-interpreter voor de interactieve login.
# Dit werkt ook wanneer wallpaper.py via pythonw.exe wordt gestart.
PYTHON_EXE = Path(sys.executable).with_name("python.exe")


# ---------- CONFIGURATIE ----------

DEFAULT_CONFIG = {
    "accent": [165, 35, 35],
    "show_location": True,
    "show_update_time": True
}


def load_config():
    """Laad de configuratie en gebruik defaults wanneer nodig."""
    config = DEFAULT_CONFIG.copy()

    if not CONFIG_FILE.exists():
        return config

    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            saved_config = json.load(f)

        if isinstance(saved_config, dict):
            config.update(saved_config)

    except (json.JSONDecodeError, OSError):
        print(
            "Ongeldige config.json gevonden. "
            "Standaardinstellingen worden gebruikt."
        )

    return config


config = load_config()


# ---------- DPI / SCHERMFORMAAT ----------

# Zorgt ervoor dat Windows echte pixels teruggeeft
# in plaats van eventueel door DPI geschaalde waarden.
ctypes.windll.user32.SetProcessDPIAware()

BASE_WIDTH = 1920
BASE_HEIGHT = 1080

WIDTH = ctypes.windll.user32.GetSystemMetrics(0)
HEIGHT = ctypes.windll.user32.GetSystemMetrics(1)

SCALE = min(
    WIDTH / BASE_WIDTH,
    HEIGHT / BASE_HEIGHT
)


def s(value):
    """Schaal een waarde volgens het huidige schermformaat."""
    return max(1, int(round(value * SCALE)))


# ---------- TOKEN ----------

def read_token_file():
    """Lees de token uit jwt.json."""
    with open(TOKEN_FILE, encoding="utf-8") as f:
        return json.load(f)["id_token"]


def validate_token(token):
    """
    Controleer de JWT-structuur en geef het vervaltijdstip terug.

    De handtekening wordt hier niet cryptografisch gecontroleerd.
    De VIVES API valideert de token bij de daadwerkelijke aanvraag.
    """
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)

    claims = json.loads(
        base64.urlsafe_b64decode(payload).decode("utf-8")
    )

    return datetime.fromtimestamp(claims["exp"])


def run_login():
    """Start de interactieve VIVES-login."""
    print("VIVES-login wordt gestart...")

    subprocess.run(
        [
            str(PYTHON_EXE),
            str(BASE / "vives_login.py")
        ],
        check=True
    )


def refresh_token():
    """Voer opnieuw de VIVES-login uit en geef de nieuwe token terug."""
    run_login()

    token = read_token_file()
    validate_token(token)

    return token


def load_token():
    """Laad een bruikbare token of start indien nodig opnieuw de login."""
    token = None
    expires_at = None

    if TOKEN_FILE.exists():

        try:
            token = read_token_file()
            expires_at = validate_token(token)

        except (
            json.JSONDecodeError,
            KeyError,
            IndexError,
            ValueError,
            UnicodeDecodeError,
            TypeError
        ):
            print("Ongeldige VIVES-token gevonden.")

    # Geen bruikbare token gevonden.
    if not token:

        run_login()

        token = read_token_file()
        expires_at = validate_token(token)

    # 10 minuten veiligheidsmarge.
    if (
        TEST_FORCE_RELOGIN
        or datetime.now() >= expires_at - timedelta(minutes=10)
    ):

        print("VIVES-token verlopen of bijna verlopen.")

        run_login()

        token = read_token_file()
        validate_token(token)

    return token


# ---------- LAATSTE SUCCESVOLLE ROOSTER ----------

def save_events(events):
    """Bewaar de laatst succesvol opgehaalde roosterdata."""
    data = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "events": events
    }

    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )


def load_saved_events():
    """
    Laad de laatst succesvolle roosterdata.

    Geeft (events, saved_at) terug.
    """
    if not EVENTS_FILE.exists():
        return None, None

    try:

        with open(EVENTS_FILE, encoding="utf-8") as f:
            data = json.load(f)

        events = data["events"]
        saved_at = data["saved_at"]

        if not isinstance(events, list):
            raise ValueError

        return events, saved_at

    except (
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        OSError
    ):
        print("Ongeldige last_events.json gevonden.")
        return None, None


# ---------- VIVES API ----------

def get_events(token, today, end_date):
    """Haal het VIVES-rooster op."""
    response = requests.get(
        API_URL,
        params={
            "from": today.isoformat(),
            "to": end_date.isoformat()
        },
        headers={
            "Authorization": f"Bearer {token}"
        },
        timeout=15
    )

    if response.status_code == 401:
        raise PermissionError("VIVES-token geweigerd.")

    response.raise_for_status()

    events = response.json()

    if not isinstance(events, list):
        raise ValueError(
            "VIVES API gaf geen lijst met events terug."
        )

    return events


def fetch_events(token, today, end_date):
    """
    Haal het rooster op.

    Bij een 401 wordt één keer opnieuw ingelogd en opnieuw geprobeerd.
    """
    try:

        return get_events(
            token,
            today,
            end_date
        )

    except PermissionError:

        print(
            "VIVES-token geweigerd. "
            "Opnieuw inloggen..."
        )

        new_token = refresh_token()

        print(
            "Nieuwe token ontvangen. "
            "API wordt opnieuw geprobeerd."
        )

        # Tweede poging.
        return get_events(
            new_token,
            today,
            end_date
        )


# ---------- LETTERTYPES ----------

font_path = r"C:\Windows\Fonts\segoeui.ttf"
font_bold_path = r"C:\Windows\Fonts\segoeuib.ttf"

title_font = ImageFont.truetype(
    font_bold_path,
    s(34)
)

day_font = ImageFont.truetype(
    font_bold_path,
    s(25)
)

time_font = ImageFont.truetype(
    font_bold_path,
    s(22)
)

text_font = ImageFont.truetype(
    font_path,
    s(21)
)

small_font = ImageFont.truetype(
    font_path,
    s(16)
)

error_font = ImageFont.truetype(
    font_bold_path,
    s(18)
)


# ---------- POSITIE ----------

panel_width = s(500)
right_margin = s(100)

x = WIDTH - panel_width - right_margin


# ---------- KLEUREN ----------

WHITE = (175, 175, 175)
GREY = (105, 105, 105)
LINE = (35, 35, 35)

ACCENT = tuple(config["accent"])


# ---------- HULPFUNCTIES ----------

def shorten_text(text, font, max_width, draw):
    """Kort tekst af wanneer die niet binnen de beschikbare breedte past."""
    if draw.textlength(text, font=font) <= max_width:
        return text

    suffix = "..."
    text = text.strip()

    while (
        text
        and draw.textlength(text + suffix, font=font) > max_width
    ):
        text = text[:-1].rstrip()

    return text + suffix


def clean_location(location):
    """Maak een lokaalnaam compacter."""
    if not location:
        return ""

    return re.split(
        r"\s+(?:leslokaal|aula|computerlokaal)\b|\s+\(",
        location,
        maxsplit=1
    )[0].strip()


def format_saved_time(saved_at):
    """Maak het opgeslagen tijdstip leesbaar."""
    if not saved_at:
        return "Laatste succesvolle gegevens beschikbaar"

    try:
        saved_datetime = datetime.fromisoformat(saved_at)

        return (
            f"Laatst succesvol bijgewerkt "
            f"{saved_datetime:%d/%m %H:%M}"
        )

    except ValueError:
        return "Laatste succesvolle gegevens beschikbaar"


# ---------- WALLPAPER MAKEN ----------

def create_wallpaper(
    events,
    today,
    stale=False,
    saved_at=None,
    error_message=None
):
    """Maak en stel de VIVES-wallpaper in."""
    img = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (0, 0, 0)
    )

    draw = ImageDraw.Draw(img)

    y = s(20)

    # ---------- HEADER ----------

    draw.text(
        (x, y),
        TITLE,
        font=title_font,
        fill=WHITE
    )

    y += s(60)

    # ---------- STATUS ----------

    if stale:

        draw.text(
            (x, y),
            "VIVES-rooster kon niet worden bijgewerkt",
            font=error_font,
            fill=ACCENT
        )

        y += s(28)

        draw.text(
            (x, y),
            format_saved_time(saved_at),
            font=small_font,
            fill=GREY
        )

        y += s(35)

        if error_message:

            draw.text(
                (x, y),
                error_message,
                font=small_font,
                fill=GREY
            )

            y += s(35)

    # ---------- LESSEN ----------

    days = [
        "VANDAAG",
        "MORGEN",
        "OVERMORGEN"
    ]

    for day_offset, day_name in enumerate(days):

        current = today + timedelta(days=day_offset)

        draw.text(
            (x, y),
            f"{day_name} {current.day:02d}/{current.month:02d}",
            font=day_font,
            fill=ACCENT
        )

        y += s(42)

        # ---------- EVENTS ----------

        day_events = [
            event
            for event in events
            if event.get("startDateTime", "").startswith(
                current.isoformat()
            )
            and event.get("type") == "course"
        ]

        day_events.sort(
            key=lambda event: event.get(
                "startDateTime",
                ""
            )
        )

        # ---------- GEEN LESSEN ----------

        if not day_events:

            draw.text(
                (x, y),
                "Geen lessen",
                font=text_font,
                fill=GREY
            )

            y += s(45)

        # ---------- LESSEN ----------

        else:

            for event in day_events:

                try:

                    start = datetime.fromisoformat(
                        event["startDateTime"]
                    )

                    end = datetime.fromisoformat(
                        event["endDateTime"]
                    )

                except (
                    KeyError,
                    TypeError,
                    ValueError
                ):
                    continue

                time_text = (
                    f"{start:%H:%M}–{end:%H:%M}"
                )

                title = (
                    event.get("description")
                    or event.get("title", "")
                )

                title = title.split("\n")[0]

                title = shorten_text(
                    title,
                    text_font,
                    panel_width,
                    draw
                )

                location = clean_location(
                    event.get("location", "")
                )

                # ---------- TIJD ----------

                draw.text(
                    (x, y),
                    time_text,
                    font=time_font,
                    fill=WHITE
                )

                # ---------- LOKAAL ----------

                if config["show_location"] and location:

                    draw.text(
                        (x + s(150), y),
                        location,
                        font=small_font,
                        fill=GREY
                    )

                y += s(30)

                # ---------- VAK ----------

                draw.text(
                    (x, y),
                    title,
                    font=text_font,
                    fill=WHITE
                )

                y += s(35)

        # ---------- SCHEIDINGSLIJN ----------

        draw.line(
            (
                x,
                y,
                x + panel_width,
                y
            ),
            fill=LINE,
            width=max(1, s(1))
        )

        y += s(28)

    # ---------- UPDATE TIJD ----------

    if config["show_update_time"]:

        if stale and saved_at:

            try:
                update_datetime = datetime.fromisoformat(saved_at)

                update_text = (
                    f"Laatste data "
                    f"{update_datetime:%H:%M}"
                )

            except ValueError:
                update_text = "Laatste succesvolle data"

        else:

            update_text = (
                f"Bijgewerkt "
                f"{datetime.now():%H:%M}"
            )

        draw.text(
            (x, HEIGHT - s(100)),
            update_text,
            font=small_font,
            fill=GREY
        )

    # ---------- OPSLAAN ----------

    img.save(OUTPUT)

    ctypes.windll.user32.SystemParametersInfoW(
        20,
        0,
        str(OUTPUT),
        3
    )


# ---------- HOOFDPROGRAMMA ----------

def main():
    """Voer de wallpaper-update uit."""
    today = datetime.now().date()
    end_date = today + timedelta(days=3)

    token = load_token()

    try:

        events = fetch_events(
            token,
            today,
            end_date
        )

        # Alleen opslaan wanneer de API succesvol was.
        save_events(events)

        create_wallpaper(
            events,
            today
        )

        print()
        print("Wallpaper gemaakt:")
        print(OUTPUT)
        print()
        print(f"Scherm: {WIDTH}x{HEIGHT}")
        print(f"Schaalfactor: {SCALE:.3f}")
        print()

    except PermissionError:

        # Ook de tweede 401 na een nieuwe login
        # komt hier terecht.
        print(
            "Nieuwe VIVES-token wordt nog steeds geweigerd."
        )

        use_saved_events(
            today,
            "VIVES-token geweigerd - rooster niet bijgewerkt"
        )

    except requests.RequestException as e:

        print(
            f"VIVES API niet bereikbaar: {e}"
        )

        use_saved_events(
            today,
            "API-fout - rooster niet bijgewerkt"
        )

    except ValueError as e:

        print(
            f"Ongeldig antwoord van de VIVES API: {e}"
        )

        use_saved_events(
            today,
            "Ongeldig API-antwoord"
        )


def use_saved_events(today, error_message):
    """Gebruik het laatst succesvol opgeslagen rooster."""
    events, saved_at = load_saved_events()

    if events is None:

        print(
            "Geen eerdere roostergegevens beschikbaar."
        )

        return

    create_wallpaper(
        events,
        today,
        stale=True,
        saved_at=saved_at,
        error_message=error_message
    )

    print(
        "Laatste succesvolle roostergegevens "
        "worden gebruikt."
    )


# ---------- START ----------

if __name__ == "__main__":
    main()