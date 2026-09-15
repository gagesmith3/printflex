import random
import re
from datetime import date

import pytest

from printflex.idgen import clean_name, generate_card

TODAY = date(1994, 6, 15)


def card(seed=42, **overrides):
    return generate_card("ADA", "LOVELACE", "EAST DAKOTA", "ED", overrides=overrides, today=TODAY, rng=random.Random(seed))


def parse(text: str) -> date:
    month, day, year = map(int, text.split("/"))
    return date(year, month, day)


def test_random_cards_are_well_formed():
    for seed in range(200):
        c = card(seed)
        dob, issued, expires = parse(c["dob"]), parse(c["iss"]), parse(c["exp"])
        age = TODAY.year - dob.year - ((TODAY.month, TODAY.day) < (dob.month, dob.day))
        assert 21 <= age <= 40
        assert issued <= TODAY < expires
        assert re.fullmatch(r"[A-Z]\d{3}-\d{3}-\d{3}", c["dl_number"])
        assert re.fullmatch(r"[56]-(0\d|1[01])", c["height"])
        assert ", ED " in c["address2"]
        assert c["signature"] == "Ada Lovelace"


def test_new_jersey_zip_codes():
    for seed in range(50):
        c = generate_card("ADA", "LOVELACE", "NEW JERSEY", "NJ", today=TODAY, rng=random.Random(seed))
        assert re.search(r", NJ 0[78]\d{3}$", c["address2"])


def test_same_seed_gives_same_card():
    assert card(7) == card(7)


def test_overrides_are_used():
    c = card(dob="1970-02-03", sex="x", height="5'9", eyes="grn", hair="red")
    assert (c["dob"], c["sex"], c["height"], c["eyes"], c["hair"]) == ("02/03/1970", "X", "5-09", "GRN", "RED")


def test_blank_overrides_are_filled_randomly():
    c = card(dob="", sex="   ")
    assert c["sex"] in ("M", "F")


@pytest.mark.parametrize(
    "field,value",
    [("dob", "not-a-date"), ("dob", "2000-01-01"), ("height", "tall"), ("height", "5-14"), ("eyes", "PURPLE"), ("sex", "Q")],
)
def test_bad_overrides_raise(field, value):
    with pytest.raises(ValueError):
        card(**{field: value})


def test_clean_name_normalizes():
    assert clean_name("  o'brien   smith-jones ", "LAST") == "O'BRIEN SMITH-JONES"


@pytest.mark.parametrize("raw", ["", "   ", None, "R2D2", "X" * 25, "<script>"])
def test_clean_name_rejects_bad_input(raw):
    with pytest.raises(ValueError):
        clean_name(raw, "FIRST")
