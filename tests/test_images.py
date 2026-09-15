import io

import pytest
from PIL import Image

from printflex.images import PHOTO_SIZE, InvalidImage, crop_portrait, process_photo, prune_photos


def test_crop_portrait_ratios():
    assert crop_portrait(Image.new("RGB", (1000, 1000))).size == (750, 1000)
    assert crop_portrait(Image.new("RGB", (600, 1200))).size == (600, 800)


def test_tall_photo_crop_favors_the_top():
    image = Image.new("RGB", (600, 1200), "blue")
    image.paste(Image.new("RGB", (600, 150), "red"), (0, 0))
    # A centered crop would start at row 200 (blue); the biased crop starts at row 120 (red).
    assert crop_portrait(image).getpixel((300, 0)) == (255, 0, 0)


def test_process_photo_applies_exif_orientation(tmp_path):
    # Stored sideways with the left half red. Orientation 6 = rotate 90° clockwise to view,
    # which puts the stored left edge at the top.
    stored = Image.new("RGB", (1000, 600), "blue")
    stored.paste(Image.new("RGB", (500, 600), "red"), (0, 0))
    exif = Image.Exif()
    exif[0x0112] = 6
    buffer = io.BytesIO()
    stored.save(buffer, "JPEG", exif=exif)

    dest = tmp_path / "out.jpg"
    process_photo(io.BytesIO(buffer.getvalue()), dest)

    with Image.open(dest) as out:
        assert out.size == PHOTO_SIZE
        top_r, _, top_b = out.getpixel((300, 10))
        bottom_r, _, bottom_b = out.getpixel((300, 790))
    assert top_r > 200 and top_b < 60
    assert bottom_b > 200 and bottom_r < 60


def test_process_photo_rejects_non_images(tmp_path):
    with pytest.raises(InvalidImage):
        process_photo(io.BytesIO(b"not an image"), tmp_path / "out.jpg")


def test_prune_keeps_newest_and_protected(tmp_path):
    names = [f"20260101-0000{i:02d}-000000-abcd" for i in range(15)]
    for name in names:
        (tmp_path / f"{name}.jpg").write_bytes(b"x")

    removed = prune_photos(tmp_path, keep=10, protect={names[0]})

    assert sorted(p.stem for p in tmp_path.glob("*.jpg")) == sorted(names[5:] + [names[0]])
    assert len(removed) == 4
