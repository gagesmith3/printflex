"""App configuration. Every value can be overridden with a PRINTFLEX_* environment variable."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(name: str, default: str) -> str:
    return os.environ.get(f"PRINTFLEX_{name}", default)


class Config:
    HOST = _env("HOST", "0.0.0.0")  # 127.0.0.1 = this machine only
    PORT = int(_env("PORT", "5000"))
    DATA_DIR = Path(_env("DATA_DIR", str(BASE_DIR / "data")))
    # Host shown in the startup banner and on-screen connection info.
    # Blank = auto-detect the LAN IP. Set to 10.42.0.1 on the UNO Q hotspot.
    PUBLIC_HOST = _env("PUBLIC_HOST", "")

    MAX_CONTENT_LENGTH = 15 * 1024 * 1024
    MAX_PHOTOS = 10
    SEND_FILE_MAX_AGE_DEFAULT = 0
    TEMPLATES_AUTO_RELOAD = True

    # In-world branding.
    SOFTWARE_NAME = _env("SOFTWARE_NAME", "PRINTFLEX")
    STATE_NAME = _env("STATE_NAME", "NEW JERSEY")
    STATE_ABBR = _env("STATE_ABBR", "NJ")
    # "Today" as far as the card is concerned (YYYY-MM-DD), for period pieces. Blank = real date.
    WORLD_DATE = _env("WORLD_DATE", "")
