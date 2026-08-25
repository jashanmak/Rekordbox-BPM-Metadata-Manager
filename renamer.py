"""
File renamer module with template formatting, filename sanitization,
artifact cleaning, expanded metadata placeholders ({energy}, {stars}),
and idempotency checks.
"""

import os
import re
from typing import Tuple, Optional, Dict, Any


def clean_filename_artifacts(text: str) -> str:
    """
    Cleans unwanted web domains, duplicate track numbers, and extra spaces.
    e.g. '01 - 01 - track (zyp.me).mp3' -> 'track'
    """
    cleaned = text
    # Remove web domain patterns like (zyp.me), [site.com], www.domain.com
    cleaned = re.sub(r'[\(\[\{]?(?:www\.)?[a-zA-Z0-9\-_]+\.(?:com|net|org|me|ru|club|xyz|site)[\)\]\}]?', '', cleaned, flags=re.IGNORECASE)
    # Remove duplicate leading track numbers like "01 - 01 - " or "1 - 01 - "
    cleaned = re.sub(r'^\s*(?:\d{1,3}\s*[\-\._]\s*){2,}', '', cleaned)
    # Remove double spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # Strip leading/trailing hyphens, underscores, dots, and spaces
    return cleaned.strip(" -_.")


def sanitize_filename(name: str) -> str:
    """Replaces characters invalid in Windows filenames."""
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', str(name))
    return sanitized.strip(" .")


def format_bpm_string(raw_bpm: float, decimals: int = 0) -> str:
    """Formats raw BPM based on decimal precision."""
    if decimals == 0:
        return str(int(round(raw_bpm)))
    else:
        return f"{raw_bpm:.{decimals}f}"


def build_new_filename(
    original_filepath: str,
    meta: Dict[str, Any],
    template: str = "[{bpm} BPM] [{key_camelot}] {artist} - {title}.{ext}",
    decimals: int = 0,
    clean_artifacts: bool = True
) -> str:
    """
    Constructs new filename using specified template and metadata dictionary.
    """
    folder, old_filename = os.path.split(original_filepath)
    name_without_ext, ext_with_dot = os.path.splitext(old_filename)
    ext = ext_with_dot.lstrip(".").lower()

    raw_bpm = meta.get("bpm", 0.0)
    formatted_bpm = format_bpm_string(raw_bpm, decimals=decimals)

    raw_artist = meta.get("artist", "")
    raw_title = meta.get("title", "") or name_without_ext

    if clean_artifacts:
        raw_artist = clean_filename_artifacts(raw_artist)
        raw_title = clean_filename_artifacts(raw_title)

    clean_artist = sanitize_filename(raw_artist)
    clean_title = sanitize_filename(raw_title)
    clean_orig = sanitize_filename(clean_filename_artifacts(name_without_ext) if clean_artifacts else name_without_ext)

    rating = meta.get("rating", 0)
    stars_str = "★" * rating if rating > 0 else ""
    energy_str = f"E{rating}" if rating > 0 else ""

    kwargs = {
        "bpm": formatted_bpm,
        "artist": clean_artist,
        "title": clean_title,
        "original_name": clean_orig,
        "ext": ext,
        "key": sanitize_filename(meta.get("key_std", "")),
        "key_std": sanitize_filename(meta.get("key_std", "")),
        "key_camelot": sanitize_filename(meta.get("key_camelot", "")),
        "key_alpha": sanitize_filename(meta.get("key_alpha", "")),
        "genre": sanitize_filename(meta.get("genre", "")),
        "comment": sanitize_filename(meta.get("comment", "")),
        "album": sanitize_filename(meta.get("album", "")),
        "year": sanitize_filename(meta.get("year", "")),
        "rating": str(rating),
        "stars": stars_str,
        "energy": energy_str,
        "color": sanitize_filename(meta.get("color", "")),
    }

    working_template = template
    if not clean_artist and "{artist}" in working_template:
        working_template = working_template.replace("{artist} - ", "").replace("{artist}", "")

    try:
        new_name = working_template.format(**kwargs)
    except KeyError:
        new_name = working_template
        for k, v in kwargs.items():
            new_name = new_name.replace(f"{{{k}}}", str(v))

    base, extension = os.path.splitext(new_name)
    sanitized_base = sanitize_filename(base)
    return f"{sanitized_base}{extension}"


def is_already_renamed(filename: str, bpm: float, decimals: int = 0) -> bool:
    """Checks if the filename already contains the BPM pattern."""
    formatted_bpm = format_bpm_string(bpm, decimals=decimals)
    patterns = [
        f"[{formatted_bpm} BPM]",
        f"({formatted_bpm} BPM)",
        f"{formatted_bpm}BPM",
        f"{formatted_bpm} BPM",
    ]
    for pattern in patterns:
        if pattern.lower() in filename.lower():
            return True
    return False


def rename_file_on_disk(
    old_filepath: str,
    new_filename: str,
    dry_run: bool = False
) -> Tuple[bool, str]:
    """Renames file on disk safely."""
    if not os.path.exists(old_filepath):
        return False, old_filepath

    folder = os.path.dirname(old_filepath)
    new_filepath = os.path.join(folder, new_filename)

    if old_filepath.replace("\\", "/").lower() == new_filepath.replace("\\", "/").lower():
        return True, new_filepath

    if os.path.exists(new_filepath) and not dry_run:
        print(f"[Renamer] Collision: Target file already exists: {new_filepath}")
        return False, old_filepath

    if dry_run:
        return True, new_filepath

    try:
        os.rename(old_filepath, new_filepath)
        return True, new_filepath
    except Exception as e:
        print(f"[Renamer] Failed to rename {old_filepath} -> {new_filepath}: {e}")
        return False, old_filepath
