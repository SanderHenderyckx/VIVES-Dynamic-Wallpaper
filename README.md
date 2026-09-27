# VIVES Dynamic Wallpaper

Automatische Windows-bureaubladachtergrond op basis van het persoonlijke VIVES-lessenrooster.

Het project haalt het rooster op via de VIVES Plus API, genereert een donkere wallpaper met de lessen van **vandaag, morgen en overmorgen**, en stelt deze automatisch in als Windows-bureaubladachtergrond.

De huidige versie is specifiek gericht op VIVES-studenten. De kalenderbron en de wallpaperlogica zijn bewust grotendeels van elkaar gescheiden, zodat de architectuur later kan worden uitgebreid naar andere kalenderbronnen.

---

## 1. Wat doet het project?

`wallpaper.py` wordt automatisch uitgevoerd via Windows Taakplanner.

De normale flow:

```text
Windows Task Scheduler
        ↓
wallpaper.py
        ↓
JWT lokaal lezen en controleren
        ↓
VIVES Plus API
        ↓
Rooster ophalen
        ↓
Vandaag + morgen + overmorgen selecteren
        ↓
Wallpaper genereren
        ↓
Windows wallpaper aanpassen
```

Wanneer de JWT verlopen is of minder dan 10 minuten geldig blijft, wordt de authenticatie opnieuw uitgevoerd.

```text
wallpaper.py
        ↓
vives_login.py
        ↓
Playwright + apart Chromium-profiel
        ↓
VIVES / KU Leuven login
        ↓
KU Leuven Authenticator indien nodig
        ↓
VIVES Plus /mobile/jwt
        ↓
Nieuwe id_token
        ↓
jwt.json
        ↓
wallpaper.py gaat verder
```

Het VIVES-wachtwoord wordt nergens door het project opgeslagen.

---

## 2. Foutafhandeling en offline gedrag

Een belangrijk ontwerpprincipe is dat een tijdelijke storing niet meteen resulteert in een lege of verdwenen wallpaper.

Na iedere succesvolle API-aanvraag wordt het opgehaalde rooster lokaal opgeslagen in:

```text
last_events.json
```

Wanneer de API tijdelijk niet bereikbaar is, bijvoorbeeld door een netwerkprobleem, wordt de laatst succesvol opgehaalde dataset gebruikt.

```text
              API succesvol
                   │
                   ▼
             nieuw rooster
                   │
                   ├──────────────► wallpaper
                   │
                   ▼
          last_events.json
```

Bij een API- of netwerkfout:

```text
           API / netwerk fout
                   │
                   ▼
          last_events.json
                   │
                   ▼
        laatst bekende rooster
                   │
                   ▼
      wallpaper + waarschuwing
```

De wallpaper vermeldt daarbij dat de gegevens mogelijk verouderd zijn.

Ook wanneer een token door de API wordt geweigerd, wordt één keer opnieuw ingelogd en opnieuw geprobeerd. Als ook de nieuwe token wordt geweigerd, valt het programma terug op de laatst bekende roostergegevens.

---

## 3. Projectstructuur

De projectmap is normaal:

```text
%USERPROFILE%\VivesWallpaper
```

Belangrijkste bestanden:

```text
VivesWallpaper/
├── wallpaper.py
├── vives_login.py
├── config.json
├── README.md
└── .gitignore
```

Daarnaast bestaan lokaal enkele runtimebestanden die bewust niet in Git worden opgenomen:

```text
jwt.json
last_events.json
vives_browser/
vives_wallpaper.png
```

### `wallpaper.py`

Het hoofdprogramma.

Verantwoordelijk voor:

* JWT lezen en controleren
* herauthenticatie starten indien nodig
* rooster ophalen
* API-fouten afhandelen
* laatst succesvolle rooster lokaal bewaren
* lessen filteren
* locaties en vaknamen formatteren
* wallpaper genereren met Pillow
* Windows wallpaper aanpassen

### `vives_login.py`

Verzorgt de interactieve VIVES-authenticatie.

Playwright gebruikt hiervoor een apart persistent Chromium-profiel:

```text
%USERPROFILE%\VivesWallpaper\vives_browser
```

Na de login wordt:

```text
https://plus.vives.be/mobile/jwt
```

geopend. De response bevat een `id_token`, die lokaal wordt opgeslagen in `jwt.json`.

### `config.json`

Bevat de gebruikersinstellingen:

```json
{
    "accent": [165, 35, 35],
    "show_location": true,
    "show_update_time": true
}
```

Betekenis:

* `accent` — kleur van de dagkoppen
* `show_location` — lokaal wel of niet tonen
* `show_update_time` — laatste update wel of niet tonen

Layout, fonts en positionering blijven bewust in de Python-code.

### `.gitignore`

Sluit lokale authenticatie-, sessie- en runtimebestanden uit van Git.

---

## 4. VIVES API

Het rooster wordt opgehaald via:

```text
https://plus.vives.be/api/events
```

De aanvraag gebruikt:

```text
from = vandaag
to   = vandaag + 3 dagen
```

De API wordt daarmee vanaf vandaag tot drie dagen vooruit bevraagd. De wallpaper toont daarvan:

* vandaag
* morgen
* overmorgen

De JWT wordt als Bearer-token meegestuurd:

```python
headers={"Authorization": f"Bearer {token}"}
```

Alleen events met:

```python
event.get("type") == "course"
```

worden weergegeven.

De vaknaam komt uit `description`, met `title` als fallback.

De API kan ook informatie zoals `groupInfo` leveren. Die wordt niet gebruikt als algemene klasgroep, omdat een individuele student lessen uit verschillende groepen of trajecten kan volgen.

---

## 5. Wallpaper

De wallpaper gebruikt een zwarte achtergrond met een sobere typografische hiërarchie.

Per les:

```text
08:30–10:30   H - 4.17
BI - Data Engineering
```

De tijd is het meest prominent.

Het lokaal wordt kleiner en grijzer weergegeven. De vaknaam staat op de regel eronder.

### Locaties

Locaties worden automatisch verkort wanneer de API extra informatie bevat.

Bijvoorbeeld:

```text
H - 4.17 leslokaal met stopc. (28p)
```

wordt:

```text
H - 4.17
```

Ook informatie zoals aula's en andere lokale beschrijvingen wordt vereenvoudigd.

### Lange vaknamen

Vaknamen die niet binnen de beschikbare breedte passen, worden automatisch afgekapt met `...`.

### Dagen

De wallpaper toont:

```text
VANDAAG
MORGEN
OVERMORGEN
```

met de bijbehorende datum.

---

## 6. Schermresolutie en schaal

Het oorspronkelijke ontwerp is gebaseerd op 1920×1080, maar de applicatie leest de actuele schermresolutie automatisch uit.

Voor Windows-schermmetingen wordt DPI-awareness ingeschakeld zodat Windows geen ongewenste DPI-schaal toepast.

De layout wordt proportioneel geschaald vanaf:

```text
1920×1080 → 1.000
2560×1440 → ≈ 1.333
3840×2160 → 2.000
```

De kleinste schaalfactor van breedte en hoogte wordt gebruikt zodat de layout zijn verhoudingen behoudt.

---

## 7. Authenticatie en JWT

De authenticatie gebruikt een interactieve browserflow omdat de VIVES/KU Leuven-login niet eenvoudig door een gewone HTTP-request kan worden nagebootst.

De browserflow:

```text
VIVES Plus
    ↓
KU Leuven authenticatie
    ↓
VIVES-account
    ↓
Authenticator indien vereist
    ↓
VIVES Plus
    ↓
/mobile/jwt
    ↓
id_token
```

Het project gebruikt een **apart persistent Chromium-profiel** en niet de normale Chrome-sessie van de gebruiker.

De JWT wordt lokaal opgeslagen in:

```text
jwt.json
```

De applicatie leest de standaard JWT-claim:

```text
exp
```

en gebruikt een veiligheidsmarge van 10 minuten.

```python
datetime.now() >= expires_at - timedelta(minutes=10)
```

De JWT wordt lokaal syntactisch gecontroleerd. De daadwerkelijke geldigheid wordt uiteindelijk door de VIVES API gecontroleerd.

---

## 8. Herauthenticatie

Wanneer de token bijna verlopen is:

```text
1. wallpaper.py detecteert de exp-vervaldatum
2. vives_login.py wordt gestart
3. Chromium opent
4. gebruiker logt in bij VIVES
5. KU Leuven Authenticator wordt bevestigd indien nodig
6. gebruiker bevestigt dat de login klaar is
7. /mobile/jwt wordt opgehaald
8. nieuwe JWT wordt opgeslagen
9. wallpaper.py gebruikt de nieuwe token
10. rooster wordt opgehaald
11. wallpaper wordt bijgewerkt
```

`wallpaper.py` wacht daarbij op `vives_login.py` voordat het verdergaat.

De Python-interpreter voor de interactieve login wordt dynamisch bepaald:

```python
PYTHON_EXE = Path(sys.executable).with_name("python.exe")
```

Er wordt daardoor geen specifieke gebruikersnaam of Python-installatiepad in de code vastgelegd.

---

## 9. Handmatig testen

### Wallpaper vernieuwen

```cmd
cd %USERPROFILE%\VivesWallpaper && python wallpaper.py
```

### VIVES-login uitvoeren

```cmd
cd %USERPROFILE%\VivesWallpaper && python vives_login.py
```

Een succesvolle login eindigt bijvoorbeeld met:

```text
Nieuwe JWT ophalen...
Status: 200

Nieuwe VIVES-token opgeslagen.
```

### JWT-vervaldatum bekijken

```cmd
python -c "import json,base64,datetime; t=json.load(open(r'%USERPROFILE%\VivesWallpaper\jwt.json',encoding='utf-8'))['id_token']; p=t.split('.')[1]+'='*(-len(t.split('.')[1])%4); e=json.loads(base64.urlsafe_b64decode(p))['exp']; print('Verloopt:',datetime.datetime.fromtimestamp(e).strftime('%d/%m/%Y %H:%M:%S'))"
```

Deze opdracht toont alleen de vervaldatum en niet de token zelf.

### Herlogin testen

Voor een handmatige test kan tijdelijk worden ingesteld:

```python
TEST_FORCE_RELOGIN = True
```

Daarna:

```cmd
cd %USERPROFILE%\VivesWallpaper && python wallpaper.py
```

De loginflow wordt dan geforceerd.

Na de test moet dit opnieuw worden ingesteld op:

```python
TEST_FORCE_RELOGIN = False
```

---

## 10. Windows Task Scheduler

De wallpaper wordt automatisch uitgevoerd via Windows Taakplanner.

De taak is ingesteld om:

* dagelijks te draaien
* ieder uur opnieuw te worden uitgevoerd
* `pythonw.exe` te gebruiken

Door `pythonw.exe` wordt tijdens een normale automatische wallpaper-update geen terminalvenster geopend.

De interactieve VIVES-authenticatie vormt hierop een uitzondering. Wanneer opnieuw authenticeren nodig is, kan een browser- en/of loginvenster verschijnen omdat menselijke interactie vereist is.

De automatische uitvoering is getest vanuit Task Scheduler.

---

## 11. Installatie

Vereisten:

* Windows
* Python 3
* `requests`
* `Pillow`
* `playwright`
* Playwright Chromium

Packages installeren:

```cmd
python -m pip install requests Pillow playwright
```

Chromium installeren:

```cmd
python -m playwright install chromium
```

Daarna is een eerste interactieve VIVES-login nodig:

```cmd
cd %USERPROFILE%\VivesWallpaper && python vives_login.py
```

Vervolgens kan `wallpaper.py` handmatig worden uitgevoerd of via Windows Task Scheduler worden ingesteld.

---

## 12. Beveiliging

De volgende bestanden blijven lokaal:

```text
jwt.json
vives_browser/
last_events.json
vives_wallpaper.png
```

### `jwt.json`

Bevat een authenticatoken en mag nooit publiek worden gedeeld.

### `vives_browser/`

Kan sessie- en authenticatiegegevens bevatten en hoort daarom niet in een publieke repository.

### `last_events.json`

Bevat persoonlijk roosterinformatie en blijft daarom eveneens lokaal.

### `.gitignore`

De repository sluit deze bestanden uit.

Belangrijk: `.gitignore` voorkomt dat niet-getrackte bestanden worden toegevoegd. Een bestand dat al eerder door Git werd getrackt, moet afzonderlijk uit Git-tracking worden verwijderd.

---

## 13. AI-assisted development

This project was developed with substantial assistance from ChatGPT.

AI assistance was used for parts of the implementation, architecture, debugging and review, including the VIVES authentication flow, JWT handling, API access, wallpaper generation and Windows Task Scheduler integration.

AI-generated code was reviewed, adapted and tested during development rather than being treated as automatically correct.

---

## 14. Teststatus

De huidige versie is getest op de belangrijkste normale en foutscenario's:

* normale API-aanvraag met internet
* API/netwerkfout zonder internet
* gebruik van lokaal opgeslagen roosterdata
* verlopen/bijna verlopen JWT
* API die een `401 Unauthorized` teruggeeft
* opnieuw authenticeren na een 401
* succesvolle API-retry na nieuwe authenticatie
* fallback wanneer ook de nieuwe token wordt geweigerd
* automatische uitvoering via Windows Task Scheduler

De applicatie is daarmee getest op zowel de normale flow als verschillende failure-modes.

---

## 15. Bekende beperkingen

### VIVES-authenticatie

Het project is afhankelijk van de huidige VIVES Plus / KU Leuven authenticatieflow. Wijzigingen aan deze flow kunnen `vives_login.py` breken.

### VIVES API

Het project gebruikt de huidige structuur van:

```text
/api/events
```

Wijzigingen aan de API kunnen aanpassingen aan de code vereisen.

### Interactieve herlogin

Authenticatie is bewust interactief. Het VIVES-wachtwoord wordt niet opgeslagen.

### Windows

De wallpaper wordt ingesteld via de Windows API en de huidige versie is daarom gericht op Windows.

### Kalenderbron

De huidige versie is specifiek gekoppeld aan VIVES Plus.

### Stale roosterdata

Bij een API- of netwerkprobleem kan de wallpaper tijdelijk gegevens tonen die niet meer actueel zijn. Dit wordt expliciet op de wallpaper aangegeven.

---

## 16. Mogelijke toekomstige uitbreidingen

Mogelijke uitbreidingen zijn onder andere:

* abstractie van de kalenderprovider
* ondersteuning voor iCalendar (`.ics`)
* andere agenda's naast VIVES
* deadlines en examens
* taken of andere persoonlijke informatie
* verdere optimalisatie voor ultrawide schermen
* eenvoudigere installatie voor andere VIVES-studenten
* volledige configuratie zonder Python-code te wijzigen

Deze functies maken geen deel uit van de huidige versie.

---

## 17. Architectuur

```text
                    ┌──────────────────────────┐
                    │ Windows Task Scheduler   │
                    │ periodieke uitvoering    │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ wallpaper.py             │
                    └────────────┬─────────────┘
                                 │
                         JWT controleren
                                 │
                    ┌────────────┴─────────────┐
                    │                          │
                 geldig                bijna/verlopen
                    │                          │
                    ▼                          ▼
              VIVES API                vives_login.py
                    │                          │
                    │                    Playwright
                    │                          │
                    │                 VIVES / KU Leuven
                    │                          │
                    │                  Authenticator
                    │                          │
                    │                          ▼
                    │                    /mobile/jwt
                    │                          │
                    │                    nieuwe JWT
                    │                          │
                    │                     jwt.json
                    │                          │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                       rooster succesvol
                                 │
                    ┌────────────┴─────────────┐
                    │                          │
                    ▼                          ▼
            last_events.json              wallpaper
                    │
                    │
             bij API/netwerkfout
                    │
                    ▼
             laatst bekende data
                    │
                    ▼
          wallpaper + waarschuwing
```

---

## 18. Repository

De broncode is beschikbaar op GitHub:

https://github.com/SanderHenderyckx/VIVES-Dynamic-Wallpaper

Bestanden die normaal in de repository thuishoren:

```text
.gitignore
README.md
config.json
vives_login.py
wallpaper.py
```

Lokale authenticatie-, sessie- en runtimebestanden horen niet in de repository.

---

## 19. Referenties

* [VIVES Plus](https://plus.vives.be/mobile/login)
* [Python `subprocess`](https://docs.python.org/3/library/subprocess.html)
* [Python `sys.executable`](https://docs.python.org/3/library/sys.html)
* [Pillow `ImageDraw`](https://pillow.readthedocs.io/en/latest/reference/ImageDraw.html)
* [Playwright Python](https://playwright.dev/python/docs/api/class-browsertype)
* [GitHub README-documentatie](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)
* [GitHub — Reviewing AI-generated code](https://docs.github.com/en/copilot/tutorials/review-ai-generated-code)
