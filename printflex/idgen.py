"""Random card details so every license looks complete. Everything here is fictional."""

import random
import re
from datetime import date, timedelta

SEXES = ("M", "F")
ALLOWED_SEXES = ("M", "F", "X")
EYES = ("BRO", "BLU", "GRN", "HAZ", "GRY")
HAIR = ("BRO", "BLK", "BLN", "RED", "GRY")
STREETS = (
    "MAPLE AVE", "OAK ST", "CEDAR LN", "ELM ST", "PARK AVE", "RIVERSIDE DR",
    "LAKEVIEW RD", "HIGHLAND DR", "MILL RD", "CHURCH ST", "WILLOW WAY", "SUNRISE BLVD",
)
CITIES = ("PINE RIDGE", "HOLLOWAY", "RED FORK", "SILVER CREEK", "GRANITE FALLS", "LONE OAK", "MARLOW")
# Leading ZIP digits per state so addresses look right. Other states get any five digits.
ZIP_PREFIXES = {"NJ": ("07", "08")}

OVERRIDE_FIELDS = ("dob", "sex", "height", "eyes", "hair")
MAX_NAME_LENGTH = 24
_HEIGHT = re.compile(r"^\s*(\d)\D*(\d{1,2})?\D*$")


def clean_name(raw: str | None, label: str) -> str:
    name = " ".join((raw or "").split()).upper()
    if not name:
        raise ValueError(f"ENTER {label} NAME")
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"{label} NAME TOO LONG")
    if not all(ch.isalpha() or ch in " '-." for ch in name):
        raise ValueError(f"{label} NAME HAS INVALID CHARACTERS")
    return name


def generate_card(
    first: str,
    last: str,
    state_name: str,
    state_abbr: str,
    overrides: dict | None = None,
    today: date | None = None,
    rng: random.Random | None = None,
) -> dict:
    """Build every field printed on the license. Blank overrides are filled randomly."""
    rng = rng or random.Random()
    today = today or date.today()
    given = {k: v.strip() for k, v in (overrides or {}).items() if k in OVERRIDE_FIELDS and v and v.strip()}

    dob = _parse_dob(given["dob"], today) if "dob" in given else _random_dob(rng, today)
    issued = today - timedelta(days=rng.randint(0, 3 * 365))
    expires = _safe_date(issued.year + 5, dob.month, dob.day)
    digits = f"{rng.randint(0, 999_999_999):09d}"

    return {
        "first": first,
        "last": last,
        "signature": f"{first.title()} {last.title()}",
        "state_name": state_name,
        "state_abbr": state_abbr,
        "dl_number": f"{rng.choice('ABCDEFGHJKLMNPRSTWXY')}{digits[:3]}-{digits[3:6]}-{digits[6:]}",
        "class": "D",
        "restrictions": "NONE",
        "endorsements": "NONE",
        "dob": _fmt(dob),
        "iss": _fmt(issued),
        "exp": _fmt(expires),
        "sex": _choice(given.get("sex"), ALLOWED_SEXES, "SEX") or rng.choice(SEXES),
        "height": _parse_height(given["height"]) if "height" in given else f"{rng.randint(5, 6)}-{rng.randint(0, 11):02d}",
        "weight": f"{rng.randint(120, 230)} LB",
        "eyes": _choice(given.get("eyes"), EYES, "EYES") or rng.choice(EYES),
        "hair": _choice(given.get("hair"), HAIR, "HAIR") or rng.choice(HAIR),
        "address1": f"{rng.randint(100, 9899)} {rng.choice(STREETS)}",
        "address2": f"{rng.choice(CITIES)}, {state_abbr} {_zip_code(rng, state_abbr)}",
    }


def _zip_code(rng: random.Random, state_abbr: str) -> str:
    prefixes = ZIP_PREFIXES.get(state_abbr)
    if not prefixes:
        return str(rng.randint(10000, 99999))
    return f"{rng.choice(prefixes)}{rng.randint(1, 999):03d}"


def _fmt(value: date) -> str:
    return value.strftime("%m/%d/%Y")


def _safe_date(year: int, month: int, day: int) -> date:
    try:
        return date(year, month, day)
    except ValueError:  # Feb 29 in a non-leap year
        return date(year, month, 28)


def _random_dob(rng: random.Random, today: date) -> date:
    """A birthday that makes the holder 21 to 40 years old."""
    latest = _safe_date(today.year - 21, today.month, today.day)
    earliest = _safe_date(today.year - 41, today.month, today.day) + timedelta(days=1)
    return earliest + timedelta(days=rng.randint(0, (latest - earliest).days))


def _parse_dob(value: str, today: date) -> date:
    try:
        dob = date.fromisoformat(value)
    except ValueError:
        raise ValueError("DOB MUST BE A DATE") from None
    if dob >= today or dob.year < today.year - 110:
        raise ValueError("DOB OUT OF RANGE")
    return dob


def _parse_height(value: str) -> str:
    match = _HEIGHT.match(value)
    inches = int(match.group(2) or 0) if match else 12
    if not match or inches > 11:
        raise ValueError("HEIGHT LIKE 5-10")
    return f"{match.group(1)}-{inches:02d}"


def _choice(value: str | None, allowed: tuple[str, ...], label: str) -> str | None:
    if value is None:
        return None
    if value.upper() not in allowed:
        raise ValueError(f"{label} MUST BE ONE OF {'/'.join(allowed)}")
    return value.upper()
