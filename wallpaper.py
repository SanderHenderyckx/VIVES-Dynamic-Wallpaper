
import json
import requests
import ctypes
import base64
import subprocess
import re
import sys

from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# ---------- INSTELLINGEN ----------

BASE = Path.home() / "VivesWallpaper"
TOKEN_FILE = BASE / "jwt.json"
OUTPUT = BASE / "vives_wallpaper.png"
CONFIG_FILE = BASE / "config.json"

TITLE = "VIVES"
TEST_FORCE_RELOGIN = False

# Gebruik de gewone Python-interpreter voor de interactieve login.
# Dit werkt ook wanneer wallpaper.py via pythonw.exe wordt gestart.
PYTHON_EXE = Path(sys.executable).with_name("python.exe")


# ---------- CONFIGURATIE ----------

with open(CONFIG_FILE, encoding="utf-8") as f:
    config = json.load(f)


# ---------- DPI / SCHERMFORMAAT ----------

# Zorgt ervoor dat Windows echte pixels teruggeeft
# in plaats van eventueel door DPI geschaalde waarden.
ctypes.windll.user32.SetProcessDPIAware()

# Referentieformaat waarop het ontwerp oorspronkelijk is gemaakt.
BASE_WIDTH = 1920
BASE_HEIGHT = 1080

# Werkelijk schermformaat.
WIDTH = ctypes.windll.user32.GetSystemMetrics(0)
HEIGHT = ctypes.windll.user32.GetSystemMetrics(1)

# Proportionele schaal ten opzichte van 1920x1080.
SCALE = min(
    WIDTH / BASE_WIDTH,
    HEIGHT / BASE_HEIGHT
)


def s(value):
    """Schaalt een waarde volgens het huidige schermformaat."""
    return max(1, int(round(value * SCALE)))


# ---------- VIVES DATA ----------

def load_token():
    token = None

    # Probeer bestaande token te lezen en te controleren.
    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE, encoding="utf-8") as f:
                token = json.load(f)["id_token"]

            # JWT payload proberen te lezen.
            payload = token.split(".")[1]
            payload += "=" * (-len(payload) % 4)

            claims = json.loads(
                base64.urlsafe_b64decode(payload).decode("utf-8")
            )

            expires_at = datetime.fromtimestamp(claims["exp"])

        except (json.JSONDecodeError, KeyError, IndexError,
                ValueError, UnicodeDecodeError, TypeError):
            print("Ongeldige VIVES-token gevonden.")
            token = None

    # Geen bruikbare token? Opnieuw inloggen.
    if not token:
        print("VIVES-login wordt gestart...")

        subprocess.run(
            [
                str(PYTHON_EXE),
                str(BASE / "vives_login.py")
            ],
            check=True
        )

        # Nieuwe token opnieuw lezen.
        with open(TOKEN_FILE, encoding="utf-8") as f:
            token = json.load(f)["id_token"]

        # Nieuwe token controleren.
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)

        claims = json.loads(
            base64.urlsafe_b64decode(payload).decode("utf-8")
        )

        expires_at = datetime.fromtimestamp(claims["exp"])

    # 10 minuten marge.
    if (
        TEST_FORCE_RELOGIN
        or datetime.now() >= expires_at - timedelta(minutes=10)
    ):
        print("VIVES-token verlopen of bijna verlopen.")
        print("VIVES-login wordt gestart...")

        subprocess.run(
            [
                str(PYTHON_EXE),
                str(BASE / "vives_login.py")
            ],
            check=True
        )

        # Nieuwe token opnieuw lezen.
        with open(TOKEN_FILE, encoding="utf-8") as f:
            token = json.load(f)["id_token"]

    return token

token = load_token()


# ---------- DATUM ----------

# TIJDELIJK VOOR TEST:
# woensdag 30/09, donderdag 01/10 en vrijdag 02/10.
#
# Na de test terugzetten naar:
# today = datetime.now().date()

today = datetime.now().date()

end_date = today + timedelta(days=3)


# ---------- ROOSTER OPHALEN ----------

response = requests.get(
    "https://plus.vives.be/api/events",
    params={
        "from": today.isoformat(),
        "to": end_date.isoformat()
    },
    headers={
        "Authorization": f"Bearer {token}"
    },
    timeout=15
)

response.raise_for_status()
events = response.json()


# ---------- AFBEELDING ----------

img = Image.new(
    "RGB",
    (WIDTH, HEIGHT),
    (0, 0, 0)
)

draw = ImageDraw.Draw(img)


# ---------- LETTERTYPES ----------

# Windows heeft meestal Segoe UI.
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


# ---------- POSITIE RECHTERKOLOM ----------

# Dit zijn ontwerpkeuzes en geen gebruikersinstellingen.
panel_width = s(500)
right_margin = s(100)

x = WIDTH - panel_width - right_margin
y = s(20)


# ---------- KLEUREN ----------

WHITE = (175, 175, 175)
GREY = (105, 105, 105)
LINE = (35, 35, 35)

ACCENT = tuple(config["accent"])


# ---------- HEADER ----------

draw.text(
    (x, y),
    TITLE,
    font=title_font,
    fill=WHITE
)

y += s(60)


# ---------- LANGE TEKST AFKAPPEN ----------

def shorten_text(text, font, max_width):
    """
    Kort tekst af wanneer die niet binnen de beschikbare breedte past.
    """
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


# ---------- LESSEN PER DAG ----------

days = [
    "VANDAAG",
    "MORGEN",
    "OVERMORGEN"
]

for day_offset, day_name in enumerate(days):

    current = today + timedelta(days=day_offset)

    # ---------- DAG ----------

    draw.text(
        (x, y),
        f"{day_name} {current.day:02d}/{current.month:02d}",
        font=day_font,
        fill=ACCENT
    )

    y += s(42)

    # ---------- EVENTS VAN DEZE DAG ----------

    day_events = [
        event
        for event in events
        if event.get("startDateTime", "").startswith(
            current.isoformat()
        )
        and event.get("type") == "course"
    ]

    day_events.sort(
        key=lambda event: event["startDateTime"]
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

            start = datetime.fromisoformat(
                event["startDateTime"]
            )

            end = datetime.fromisoformat(
                event["endDateTime"]
            )

            time_text = (
                f"{start:%H:%M}–{end:%H:%M}"
            )

            # Officiële vaknaam.
            title = (
                event.get("description")
                or event.get("title", "")
            )

            # Alleen de eerste regel gebruiken.
            title = title.split("\n")[0]

            # Vaknaam afkappen indien nodig.
            title = shorten_text(
                title,
                text_font,
                panel_width
            )

            location = event.get(
                "location",
                ""
            )

            # ---------- LOKAAL OPSCHONEN ----------

            short_location = location

            if short_location:

                short_location = re.split(
                    r"\s+(?:leslokaal|aula|computerlokaal)\b|\s+\(",
                    short_location,
                    maxsplit=1
                )[0].strip()

            # ---------- TIJD ----------

            draw.text(
                (x, y),
                time_text,
                font=time_font,
                fill=WHITE
            )

            # ---------- LOKAAL ----------

            if config["show_location"] and short_location:

                draw.text(
                    (x + s(150), y),
                    short_location,
                    font=small_font,
                    fill=GREY
                )

            y += s(30)

            # ---------- VAKNAAM ----------

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


# ---------- UPDATE TIJDSTIP ----------

if config["show_update_time"]:

    now = datetime.now()

    draw.text(
        (x, HEIGHT - s(100)),
        f"Bijgewerkt {now:%H:%M}",
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


# ---------- RESULTAAT ----------

print()
print("Wallpaper gemaakt:")
print(OUTPUT)
print()
print(f"Scherm: {WIDTH}x{HEIGHT}")
print(f"Schaalfactor: {SCALE:.3f}")
print()


