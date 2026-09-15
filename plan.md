# The Goal
This app will be used within a prop for a movie. It will run a local flask server that will take photos sent to it by a user, display that picture and run an animation. The movie is about making fake ids so this will look like someone is printing out a drivers license. 


## The OS
It will be running on an arudunio uno q (on a linux distro) but is currently on my windows machine.

## The Style
Very 80s/90s retro vibes

# The How
Flask server with 2 main branches, server and user. The user endpoint will have a mobile based UI for taking photos, entering a name and sending it to the server. The server will take the picture sent to it, and start an animation to be created soon, once the animation is over it goes back to an idle screen. 

Should also run within its own venv

# Down the Road
Something to keep in mind is that this app will also eventually control GPIO pins/motors to move other props and also take inputs from physical buttons

# Decisions (v1)
- **Phases:** Phase A builds and tests everything on Windows. Phase B (UNO Q hotspot, systemd service, Chromium kiosk) starts only after Windows sign-off.
- **Network on set:** the UNO Q runs its own Wi-Fi hotspot and phones open `http://10.42.0.1/user`. During Windows development, the PC and phone share home Wi-Fi.
- **Photo:** taken with the phone's native camera through a file input, so plain HTTP works with no certificates. Choosing an existing photo also works.
- **Screen:** size not decided yet, so everything is laid out on a 1920x1080 stage that scales to any display.
- **Animation:** code-driven (HTML/CSS/JS) with a placeholder timeline: receive → compose → print → done.
- **Card:** the phone sends the photo and first/last name, and everything else is random. Optional overrides cover DOB, sex, height, eyes, and hair. The state is New Jersey (set in config), on a generic card layout rather than the real NJ design.
- **Look:** a one-off tool a genius South Jersey criminal wrote for their own use. It's set in the present day and still looks cool, just toned back slightly. Cool blue terminal with framed log and preview panels, and no branding or labels that say what it does. The card is the only polished thing. The prompt shows the operator alias (`PRINTFLEX_OPERATOR`), and a panic key covers the screen with a decoy spreadsheet.
- **Trigger:** switchable. Auto prints on arrival; Cue waits for START.
- **Crew tools:** reset/abort, replay last, timing settings.
- **Defaults:**
  - No sound.
  - Only the last 10 photos are kept.
  - A photo sent while printing gets PRINTER BUSY.
  - No login.
  - All fonts and assets are stored locally.
- **Hardware later:** the UNO Q header pins are driven by its STM32 microcontroller. The Arduino sketch will expose functions with `Bridge.provide()`, and Python will call them through `arduino-router`. `printflex/hardware/` is the hook for this; v1 ships only a mock.