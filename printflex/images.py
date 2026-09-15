"""Turn an uploaded phone photo into a license portrait."""

from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

PHOTO_SIZE = (600, 800)


class InvalidImage(ValueError):
    pass


def process_photo(stream, dest: Path) -> None:
    """Upright, crop to 3:4 portrait, resize, and save as JPEG."""
    try:
        with Image.open(stream) as original:
            original.load()
            image = ImageOps.exif_transpose(original)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise InvalidImage(str(exc)) from None
    image = crop_portrait(image.convert("RGB"))
    image = image.resize(PHOTO_SIZE, Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest, "JPEG", quality=90)


def crop_portrait(image: Image.Image, ratio: float = 3 / 4, top_bias: float = 0.3) -> Image.Image:
    """Crop to `ratio` (width / height). Tall photos keep more of the top, where the face usually is."""
    width, height = image.size
    if width / height > ratio:
        new_width = round(height * ratio)
        left = (width - new_width) // 2
        return image.crop((left, 0, left + new_width, height))
    new_height = round(width / ratio)
    top = round((height - new_height) * top_bias)
    return image.crop((0, top, width, top + new_height))


def prune_photos(folder: Path, keep: int, protect: set[str] = frozenset()) -> list[Path]:
    """Delete all but the newest `keep` photos. Job ids start with a timestamp, so names sort by age."""
    photos = sorted(folder.glob("*.jpg"), key=lambda path: path.name, reverse=True)
    removed = []
    for path in photos[keep:]:
        if path.stem not in protect:
            path.unlink(missing_ok=True)
            removed.append(path)
    return removed
