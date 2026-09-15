# PrintFlex

On-screen prop for a movie about fake IDs. Someone on set takes a photo and enters a name on a phone. The display then "prints" a retro 80s/90s New Jersey driver's license and goes back to idle.

Development happens on Windows first. The Arduino UNO Q deployment (Phase B in [plan.md](plan.md)) comes after the Windows version is signed off.

## Run on Windows

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe run.py
```

Running the venv's `python.exe` directly means you never need `Activate.ps1`, so PowerShell's execution-policy error doesn't come up. On startup the server prints the addresses below.

| Page | Address | Used by |
|---|---|---|
| Display | `http://localhost:5000/server/display` | The screen. Press F11 for fullscreen, or run `chrome --kiosk <url>` |
| Phone | `http://<PC-IP>:5000/user` | Taking the photo and entering the name |
| Crew | `http://<PC-IP>:5000/server/operator` | Mode, START / REPLAY / RESET, timing |

- The first run brings up a Windows Firewall prompt. Allow Python on **Private** networks, and make sure your Wi-Fi is set to Private.
- The phone has to be on the same Wi-Fi as the PC.
- Run the tests with `.venv\Scripts\python.exe -m pytest`.

## Running takes

- **Auto mode:** a photo prints as soon as it arrives.
- **Cue mode:** the display shows DATA RECEIVED and waits for START.
- **REPLAY** runs the last card again without resending it. **RESET** returns to idle immediately, even mid-print.
- **PANIC** covers the display with a dull parts-inventory spreadsheet. Printing keeps going underneath, so uncovering it shows wherever the print has reached. Toggle it from the crew panel or with the backquote key.
- If a photo arrives while a card is printing or on screen, the phone shows "busy".
- Keys on the display: **Space/Enter** START, **R** REPLAY, **Esc** RESET, **Backquote** (left of 1) PANIC, **I** toggles the connection-info box.

Crew settings (mode, speed, phase durations, hold time, scanlines) are saved to `data/settings.json` and take effect on the next print.

## Configuration

Set these environment variables before starting (for example `$env:PRINTFLEX_PORT = "8080"`).

| Variable | Default | Purpose |
|---|---|---|
| `PRINTFLEX_PORT` | `5000` | Port to listen on |
| `PRINTFLEX_HOST` | `0.0.0.0` | Interface to bind; `127.0.0.1` keeps it local to this machine |
| `PRINTFLEX_PUBLIC_HOST` | auto-detected LAN IP | Address shown to phones; set to `10.42.0.1` on the UNO Q hotspot |
| `PRINTFLEX_DATA_DIR` | `./data` | Uploaded photos and `settings.json` |
| `PRINTFLEX_SOFTWARE_NAME` | `PRINTFLEX` | In-world software name |
| `PRINTFLEX_OPERATOR` | `user` | The character's handle, shown as `operator@printflex` on the display and phone |
| `PRINTFLEX_STATE_NAME` / `PRINTFLEX_STATE_ABBR` | `NEW JERSEY` / `NJ` | State printed on the card |
| `PRINTFLEX_WORLD_DATE` | today | `YYYY-MM-DD` date that card dates are based on, for period settings |

## The look

The display and phone page are the character's own tool, written for nobody else to see. They use a cool blue terminal look that never says what the program does, with small details like `log: off` and `tmp wiped`. The license card is the only polished thing on screen. The crew panel is off camera, so it keeps a louder, easier-to-read style.

## Where things live

| To change | Edit |
|---|---|
| Panic screen contents | [printflex/templates/_decoy.html](printflex/templates/_decoy.html) |
| Card layout and look | [printflex/templates/_card.html](printflex/templates/_card.html) and the "License card" section of [display.css](printflex/static/css/display.css) |
| Animation steps and terminal text | [printflex/static/js/animation.js](printflex/static/js/animation.js) |
| Random card data | [printflex/idgen.py](printflex/idgen.py) |
| State machine (auto/cue, busy, replay, reset) | [printflex/controller.py](printflex/controller.py) |
| Motors and buttons (later) | [printflex/hardware/](printflex/hardware/) |

The server owns the timeline. Every page follows it over Server-Sent Events (`/server/api/events`), so a display that reloads mid-print picks up at the right point.

## Fonts

VT323, Press Start 2P, Roboto Condensed and Caveat are stored in [printflex/static/fonts](printflex/static/fonts) so the app works without internet. All four are under the SIL Open Font License; the license files are in the same folder.
