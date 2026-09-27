# VIVES Dynamic Wallpaper

Automatische Windows-bureaubladachtergrond voor het VIVES-lessenrooster.

Het project haalt het persoonlijke rooster op via de VIVES Plus API, genereert een donkere wallpaper met de lessen van vandaag, morgen en overmorgen, en stelt die afbeelding automatisch in als Windows-bureaubladachtergrond.

De huidige versie is gericht op VIVES-studenten. De kalenderbron en de wallpaperlogica kunnen later verder van elkaar worden losgekoppeld.

---

## 1. Wat doet het systeem?

`wallpaper.py` wordt automatisch uitgevoerd via Windows Taakplanner.

De normale flow is:

```text
Windows Task Scheduler
        ↓
wallpaper.py
        ↓
JWT uit jwt.json lezen
        ↓
JWT controleren op exp
        ↓
VIVES API /api/events
        ↓
Rooster voor vandaag + 2 dagen
        ↓
Wallpaper genereren
        ↓
Windows wallpaper aanpassen
```

Als de JWT verlopen is of minder dan 10 minuten geldig blijft, wordt eerst een nieuwe token opgehaald:

```text
wallpaper.py
        ↓
vives_login.py
        ↓
Aparte Chromium-browser
        ↓
VIVES-account login
        ↓
KU Leuven Authenticator indien nodig
        ↓
VIVES Plus /mobile/jwt
        ↓
Nieuwe id_token
        ↓
jwt.json vernieuwen
        ↓
wallpaper.py gaat verder
```

Het VIVES-wachtwoord wordt nergens in dit project opgeslagen.

---

## 2. Projectbestanden

De projectmap is normaal:

```text
%USERPROFILE%\VivesWallpaper
```

### `wallpaper.py`

Hoofdprogramma.

Taken:

- JWT uit `jwt.json` lezen
- vervaldatum (`exp`) controleren
- indien nodig `vives_login.py` starten
- rooster ophalen via de VIVES API
- lessen filteren op `type == "course"`
- locaties verkorten voor de wallpaper
- lange vaknamen afkappen wanneer nodig
- wallpaper tekenen met Pillow
- wallpaper opslaan als PNG
- Windows opdracht geven om de PNG als bureaubladachtergrond te gebruiken

### `vives_login.py`

Verzorgt de interactieve VIVES-authenticatie en haalt een nieuwe JWT op.

Playwright gebruikt hiervoor een apart persistent Chromium-profiel:

```text
%USERPROFILE%\VivesWallpaper\vives_browser
```

Na het inloggen wordt binnen dezelfde browsercontext:

```text
https://plus.vives.be/mobile/jwt
```

geopend. De response bevat een `id_token`, die lokaal wordt opgeslagen in `jwt.json`.

### `config.json`

Bevat de beperkte gebruikersinstellingen:

```json
{
    "accent": [165, 35, 35],
    "show_location": true,
    "show_update_time": true
}
```

- `accent` — kleur van de dagkoppen
- `show_location` — lokaal wel of niet tonen
- `show_update_time` — tijdstip van de laatste wallpaper-update wel of niet tonen

Ontwerpkeuzes zoals fonts, afmetingen en positionering blijven in de Python-code.

### `README.md`

Deze documentatie.

### `.gitignore`

Sluit lokale en gevoelige bestanden uit van Git.

### `jwt.json` — lokaal

Bevat de huidige VIVES `id_token`.

Niet delen en nooit committen naar Git.

### `vives_browser\` — lokaal

Persistent Chromium-profiel voor Playwright.

Kan sessie- en authenticatiegegevens bevatten en moet privé blijven.

### `vives_wallpaper.png` — lokaal

De door `wallpaper.py` gegenereerde afbeelding.

---

## 3. VIVES API

Het rooster wordt opgehaald met:

```text
https://plus.vives.be/api/events
```

De aanvraag gebruikt:

```text
from = vandaag
to   = vandaag + 3 dagen
```

De JWT wordt als Bearer-token meegestuurd:

```python
headers={"Authorization": f"Bearer {token}"}
```

Daarna worden alleen events met:

```python
e.get("type") == "course"
```

weergegeven.

De vaknaam komt uit `description` en gebruikt `title` als fallback.

De API levert per event ook `groupInfo`. Dat wordt bewust niet als algemene klasgroep gebruikt. Een student kan een persoonlijk traject hebben en lessen volgen die aan verschillende groepen gekoppeld zijn.

---

## 4. Weergave

De wallpaper gebruikt een donkere achtergrond en een sobere typografische hiërarchie.

Per les wordt informatie zo weergegeven:

```text
08:30–10:30   H - 4.17
BI - Data Engineering
```

De tijd is het meest prominent, het lokaal is kleiner en grijzer, en de vaknaam staat op de regel eronder.

Locaties worden verkort zodat extra informatie zoals lokaaltype en capaciteit niet onnodig wordt weergegeven. Bijvoorbeeld:

```text
H - 4.17 leslokaal met stopc. (28p)
→ H - 4.17

H - 3.05 aula (90p)
→ H - 3.05
```

Lange vaknamen worden automatisch afgekapt als ze niet binnen de beschikbare breedte passen.

De drie dagen worden compact onder elkaar weergegeven zodat er voldoende verticale ruimte overblijft.

---

## 5. Schermresolutie en schaal

Het ontwerp werd oorspronkelijk gemaakt voor 1920×1080, maar de huidige versie leest het schermformaat automatisch uit.

Voor de schermmetingen wordt DPI-awareness ingeschakeld zodat Windows niet onbedoeld geschaalde afmetingen teruggeeft.

De layout, fonts en afstanden worden proportioneel geschaald vanaf het referentieformaat:

```text
1920×1080 → schaal 1.000
2560×1440 → schaal ≈ 1.333
3840×2160 → schaal 2.000
```

De kleinste schaal van breedte en hoogte wordt gebruikt zodat de verhoudingen behouden blijven.

---

## 6. Authenticatie

De authenticatieflow is:

```text
VIVES Plus login
      ↓
KU Leuven authenticatie
      ↓
VIVES-account
      ↓
KU Leuven Authenticator indien vereist
      ↓
VIVES Plus
      ↓
/mobile/jwt
      ↓
{"id_token":"eyJ..."}
```

Een gewone Python-request kan de interactieve loginflow niet vervangen. Daarom gebruikt `vives_login.py` Playwright.

De normale Chrome-sessie van de gebruiker wordt niet gebruikt. Het project gebruikt een apart persistent browserprofiel.

---

## 7. JWT-vervaldatum

`wallpaper.py` leest de standaard JWT-claim:

```text
exp
```

De claim bepaalt wanneer de token verloopt.

De wallpaper gebruikt een veiligheidsmarge van 10 minuten:

```python
if TEST_FORCE_RELOGIN or datetime.now() >= expires_at - timedelta(minutes=10):
```

Normaal staat:

```python
TEST_FORCE_RELOGIN = False
```

---

## 8. Herlogin-flow

Wanneer de JWT bijna verlopen is:

```text
1. wallpaper.py detecteert de exp-vervaldatum
2. vives_login.py wordt gestart
3. Chromium opent
4. VIVES login verschijnt
5. gebruiker logt in
6. KU Leuven Authenticator wordt bevestigd indien nodig
7. gebruiker drukt Enter in CMD
8. /mobile/jwt wordt opnieuw opgehaald
9. jwt.json wordt overschreven
10. wallpaper.py leest de nieuwe token
11. rooster wordt opgehaald
12. wallpaper wordt opnieuw gemaakt
```

`wallpaper.py` wacht op `vives_login.py` met `subprocess.run(..., check=True)`.

De Python-interpreter voor het subprocess wordt niet als een specifiek gebruikerspad hardcoded. De code gebruikt:

```python
PYTHON_EXE = Path(sys.executable).with_name("python.exe")
```

---

## 9. Handmatig testen

### Wallpaper vernieuwen

```cmd
cd %USERPROFILE%\VivesWallpaper && python wallpaper.py
```

### VIVES-login / JWT vernieuwen

```cmd
cd %USERPROFILE%\VivesWallpaper && python vives_login.py
```

Verwachte succesvolle uitvoer:

```text
VIVES-login openen...

Log in met je VIVES-account.
Bevestig de KU Leuven Authenticator.
Druk daarna op Enter in dit CMD-venster...
Nieuwe JWT ophalen...
Status: 200

Nieuwe VIVES-token opgeslagen.
```

### Token-vervaldatum bekijken

```cmd
python -c "import json,base64,datetime; t=json.load(open(r'%USERPROFILE%\VivesWallpaper\jwt.json',encoding='utf-8'))['id_token']; p=t.split('.')[1]+'='*(-len(t.split('.')[1])%4); e=json.loads(base64.urlsafe_b64decode(p))['exp']; print('Verloopt:',datetime.datetime.fromtimestamp(e).strftime('%d/%m/%Y %H:%M:%S'))"
```

Dit toont alleen de vervaldatum en niet de token zelf.

---

## 10. Testen van de herlogin zonder te wachten

Zet tijdelijk in `wallpaper.py`:

```python
TEST_FORCE_RELOGIN = True
```

Run daarna:

```cmd
cd %USERPROFILE%\VivesWallpaper && python wallpaper.py
```

De loginflow wordt dan bij elke run geforceerd.

Na het testen altijd terugzetten naar:

```python
TEST_FORCE_RELOGIN = False
```

---

## 11. Windows Taakplanner

De wallpaper wordt automatisch gestart via Windows Task Scheduler.

### Taak

```text
VIVES Wallpaper
```

### Planning

- dagelijks
- herhalen: elke 1 uur
- duur: 1 dag

### Actie

De taak gebruikt `pythonw.exe` zodat een normale wallpaper-update geen zichtbaar terminalvenster opent.

De precieze Python-locatie kan per computer verschillen. De repositorycode zelf gebruikt geen hardcoded gebruikersnaam voor de Python-interpreter.

Bij een herauthenticatie kan wel een zichtbaar Chromium/loginvenster verschijnen. Dat is bewust: de gebruiker moet dan interactief authenticeren.

---

## 12. Installatie

Vereisten:

- Windows
- Python 3
- `requests`
- `Pillow`
- `playwright`
- Playwright Chromium

Packages installeren:

```cmd
python -m pip install requests Pillow playwright
```

Chromium installeren:

```cmd
python -m playwright install chromium
```

Daarna is een eerste interactieve login nodig:

```cmd
cd %USERPROFILE%\VivesWallpaper && python vives_login.py
```

---

## 13. Beveiliging

De volgende bestanden blijven lokaal:

```text
jwt.json
vives_browser/
vives_wallpaper.png
```

`jwt.json` bevat een authenticatoken. De inhoud mag nooit publiek worden gedeeld.

`vives_browser\` kan sessiegegevens bevatten en hoort eveneens niet in een publieke repository.

De `.gitignore` in de projectmap sluit deze bestanden uit.

Belangrijk: `.gitignore` voorkomt dat niet-getrackte bestanden worden toegevoegd. Een bestand dat al eerder door Git werd getrackt, moet apart uit tracking worden verwijderd.

---

## 14. GitHub

Deze repository wordt gebruikt als leer- en portfolio-project en staat op GitHub:

```text
https://github.com/SanderHenderyckx/VIVES-Dynamic-Wallpaper
```

Bestanden die normaal in de repository thuishoren:

```text
.gitignore
README.md
config.json
vives_login.py
wallpaper.py
```

Lokale authenticatie- en runtimebestanden horen niet in de repository.

---

## 15. AI-assisted development

This project was developed with substantial assistance from ChatGPT.

The implementation, architecture and code were reviewed, tested and adapted during development, including the VIVES authentication flow, JWT renewal, API access, wallpaper generation and Windows Task Scheduler integration.

AI-generated code was reviewed and tested during development rather than treated as automatically correct.

---

## 16. Bekende beperkingen

### VIVES-authenticatie

Het project is afhankelijk van de huidige VIVES Plus / KU Leuven loginflow. Wijzigingen aan die flow kunnen `vives_login.py` breken.

### VIVES API

Het project gebruikt de huidige structuur van `/api/events`. Wijzigingen aan de API kunnen codewijzigingen vereisen.

### Interactieve herlogin

De eerste login en herauthenticatie zijn bewust interactief. Het VIVES-wachtwoord wordt niet opgeslagen.

### Windows

De huidige wallpaperinstelling gebruikt de Windows API via `ctypes` en is daardoor specifiek gericht op Windows.

### Kalenderbron

De huidige versie is specifiek gekoppeld aan VIVES Plus. Een toekomstige uitbreiding kan de kalenderbron abstraheren, bijvoorbeeld richting iCalendar of andere agenda's.

---

## 17. Mogelijke toekomstige uitbreidingen

- generieke kalenderprovider naast VIVES
- ondersteuning voor iCalendar (`.ics`)
- tweede agenda of takenlijst
- deadlines of examens
- verdere optimalisatie voor ultrawide schermen
- eenvoudigere installatie voor andere VIVES-studenten
- gebruikersconfiguratie zonder Python-code te wijzigen

Deze uitbreidingen zijn bewust nog geen onderdeel van de huidige stabiele versie.

---

## 18. Architectuuroverzicht

```text
                    ┌──────────────────────────┐
                    │ Windows Task Scheduler   │
                    │ elke 1 uur               │
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
                    │                   Playwright
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
                                 ▼
                    ┌──────────────────────────┐
                    │ PNG genereren            │
                    │ + wallpaper instellen    │
                    └──────────────────────────┘
```

---

## 19. Referenties

- VIVES Plus: https://plus.vives.be/mobile/login
- Python `subprocess`: https://docs.python.org/3/library/subprocess.html
- Python `sys.executable`: https://docs.python.org/3/library/sys.html
- Pillow `ImageDraw`: https://pillow.readthedocs.io/en/latest/reference/ImageDraw.html
- Playwright browser automation: https://playwright.dev/python/docs/api/class-browsertype
- GitHub repository documentation: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes
- GitHub guidance on reviewing AI-generated code: https://docs.github.com/en/copilot/tutorials/review-ai-generated-code
