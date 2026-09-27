# VIVES Dynamic Wallpaper

Automatische Windows-bureaubladachtergrond voor het VIVES-lessenrooster.

Het project haalt het persoonlijke rooster op via de VIVES Plus API, genereert een donkere wallpaper met de lessen van vandaag, morgen en overmorgen, en stelt die afbeelding automatisch in als Windows-bureaubladachtergrond.

De huidige versie is in de eerste plaats bedoeld voor VIVES-studenten. Later kan de kalenderbron eventueel verder worden losgekoppeld van de wallpaperlogica.

---

## 1. Wat doet het systeem?

Elke uur draait `wallpaper.py` automatisch via Windows Taakplanner.

De normale flow is:

```text
Windows Task Scheduler
        ↓
wallpaper.py
        ↓
JWT uit jwt.json lezen
        ↓
JWT controleren op exp (vervaldatum)
        ↓
VIVES API /api/events
        ↓
rooster voor vandaag + 2 dagen
        ↓
wallpaper genereren
        ↓
Windows wallpaper automatisch aanpassen
```

Als de JWT verlopen is of minder dan 10 minuten geldig blijft:

```text
wallpaper.py
     ↓
vives_login.py
     ↓
aparte Chromium-browser
     ↓
VIVES-account login
     ↓
KU Leuven Authenticator indien nodig
     ↓
VIVES Plus /mobile/jwt
     ↓
nieuwe id_token
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
- Windows opdracht geven om de nieuwe PNG als bureaubladachtergrond te gebruiken

### `vives_login.py`

Verzorgt de interactieve VIVES-authenticatie en haalt een nieuwe JWT op.

Het programma gebruikt Playwright met een apart persistent Chromium-profiel:

```text
%USERPROFILE%\VivesWallpaper\vives_browser
```

Na het inloggen wordt binnen dezelfde browsercontext:

```text
https://plus.vives.be/mobile/jwt
```

geopend. De JSON-response bevat een `id_token`, die lokaal wordt opgeslagen in `jwt.json`.

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

Ontwerpkeuzes zoals lettertypes, afmetingen en positionering blijven in de Python-code staan.

### `README.md`

Deze documentatie.

### `.gitignore`

Zorgt ervoor dat lokale en gevoelige bestanden niet per ongeluk door Git worden meegenomen.

### `jwt.json` — lokaal

Bevat de huidige VIVES `id_token`.

**Niet delen en nooit committen naar Git.**

### `vives_browser\` — lokaal

Persistent Chromium-profiel voor Playwright.

Dit kan sessie- en authenticatiegegevens bevatten en moet privé blijven.

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

De API levert per event ook `groupInfo`. Dat wordt bewust niet gebruikt als algemene klasgroep: een student kan vakken volgen met verschillende groepen of een persoonlijk traject hebben, en een event kan bijvoorbeeld voor `2BIT + STVBIT` gelden zonder dat dit de vaste groep van de student is.

---

## 4. Weergave

De wallpaper gebruikt een donkere achtergrond en een sobere typografische hiërarchie.

Per les wordt informatie als volgt weergegeven:

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

Het ontwerp gebruikt de kleinste schaal van breedte en hoogte zodat de verhoudingen behouden blijven.

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

Een gewone Python-request zonder een geldige ingelogde browsercontext kan de interactieve loginflow niet vervangen. Daarom gebruikt `vives_login.py` Playwright.

Playwright gebruikt een apart persistent profiel zodat de normale Chrome-profielgegevens van de gebruiker niet nodig zijn.

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

Er wordt niet gewacht tot de echte token verloopt om de flow te kunnen testen. Met `TEST_FORCE_RELOGIN = True` kan de volledige herloginflow geforceerd worden.

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

`wallpaper.py` wacht op `vives_login.py` met:

```python
subprocess.run(..., check=True)
```

De Python-interpreter voor dat subprocess wordt niet meer hardcoded als een specifiek gebruikerspad. De code gebruikt de actieve Python-installatie als uitgangspunt:

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

Run vervolgens:

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

De precieze locatie van Python kan per computer verschillen. De repositorycode zelf probeert geen gebruikersnaam of absoluut Python-pad te veronderstellen.

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

`jwt.json` bevat een authenticatietoken. De inhoud mag nooit publiek worden gedeeld.

`vives_browser\` kan sessiegegevens bevatten en hoort eveneens niet in een publieke repository.

De `.gitignore` in de projectmap sluit deze bestanden uit.

Belangrijk: `.gitignore` voorkomt dat niet-getrackte bestanden worden toegevoegd. Een bestand dat al eerder door Git werd getrackt, moet apart uit tracking worden verwijderd.

---

## 14. GitHub

Het project is geschikt om later op GitHub te plaatsen als leer- en portfolio-project.

Bestanden die normaal in de repository thuishoren:

```text
.gitignore
README.md
config.json
vives_login.py
wallpaper.py
```

Lokale authenticatie- en runtimebestanden horen niet in de repository.

Een goede README moet vooral duidelijk maken wat het project doet, hoe het gebruikt wordt en wat iemand nodig heeft om ermee te starten. GitHub raadt dit expliciet aan voor repositories. citeturn942922search1turn942922search2

---

## 15. AI-assisted development

This project was developed with substantial assistance from ChatGPT.

The implementation, architecture and code were reviewed, tested and adapted during development, including testing the VIVES authentication flow, JWT renewal, API access, wallpaper generation and Windows Task Scheduler integration.

AI-generated code was not treated as automatically correct; functionality and changes were tested during development. GitHub similarly recommends reviewing and validating AI-generated code before relying on it. citeturn942922search0

---

## 16. Bekende beperkingen

### VIVES-authenticatie

Het project is afhankelijk van de huidige VIVES Plus / KU Leuven loginflow. Wijzigingen aan die flow kunnen `vives_login.py` breken.

### VIVES API

Het project gebruikt de huidige structuur van `/api/events`. Wijzigingen aan de API kunnen codewijzigingen vereisen.

### Interactieve herlogin

De eerste login en herauthenticatie zijn bewust interactief. Het VIVES-wachtwoord wordt niet geautomatiseerd opgeslagen.

### Windows

De huidige wallpaperinstelling gebruikt de Windows API via `ctypes` en is daardoor specifiek gericht op Windows.

### Kalenderbron

De huidige versie is specifiek gekoppeld aan VIVES Plus. Een toekomstige uitbreiding kan de kalenderbron abstraheren, bijvoorbeeld richting iCalendar of andere agenda's.

---

## 17. Mogelijke toekomstige uitbreidingen

Mogelijke vervolgstappen:

- generieke kalenderprovider naast VIVES
- ondersteuning voor iCalendar (`.ics`)
- tweede agenda of takenlijst
- deadlines of examens
- verdere optimalisatie voor ultrawide schermen
- betere installatie voor andere VIVES-studenten
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
- GitHub repository best practices: https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories
- GitHub README documentation: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes
- GitHub guidance on reviewing AI-generated code: https://docs.github.com/en/copilot/tutorials/review-ai-generated-code
