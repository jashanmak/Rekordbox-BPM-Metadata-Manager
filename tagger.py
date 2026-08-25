"""
Audio file metadata tagger using Mutagen.
Supports MP3, FLAC, M4A, AIFF, and WAV files with expanded metadata mapping
and cross-platform Serato / Traktor / Engine DJ key compatibility.
"""

import os
from typing import Optional, Dict, Any

import mutagen
from mutagen.id3 import ID3, TBPM, TKEY, TCON, COMM, TDRC, POPM, ID3NoHeaderError
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.aiff import AIFF
from mutagen.wave import WAVE


def write_audio_tags(
    file_path: str,
    bpm: Optional[float] = None,
    key: Optional[str] = None,
    genre: Optional[str] = None,
    comment: Optional[str] = None,
    year: Optional[Any] = None,
    rating: Optional[int] = None
) -> bool:
    """
    Writes BPM, Key (Serato/Traktor/Engine compatible), Genre, Comment, Year, and Rating tags.
    """
    if not os.path.exists(file_path):
        return False

    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == ".mp3":
            return _tag_mp3(file_path, bpm, key, genre, comment, year, rating)
        elif ext == ".flac":
            return _tag_flac(file_path, bpm, key, genre, comment, year, rating)
        elif ext in [".m4a", ".mp4", ".aac"]:
            return _tag_mp4(file_path, bpm, key, genre, comment, year, rating)
        elif ext in [".aif", ".aiff"]:
            return _tag_aiff(file_path, bpm, key, genre, comment, year, rating)
        elif ext == ".wav":
            return _tag_wav(file_path, bpm, key, genre, comment, year, rating)
        else:
            return False
    except Exception as e:
        print(f"[Tagger] Error writing tags to {file_path}: {e}")
        return False


def _tag_mp3(file_path: str, bpm, key, genre, comment, year, rating) -> bool:
    try:
        tags = ID3(file_path)
    except ID3NoHeaderError:
        tags = ID3()

    if bpm is not None:
        tags.add(TBPM(encoding=3, text=str(round(bpm, 2))))
    if key:
        # Standard ID3 key frame (read by Traktor, Serato, Rekordbox, Engine OS)
        tags.add(TKEY(encoding=3, text=str(key)))
    if genre:
        tags.add(TCON(encoding=3, text=str(genre)))
    if comment:
        tags.add(COMM(encoding=3, lang="eng", desc="", text=str(comment)))
    if year:
        tags.add(TDRC(encoding=3, text=str(year)))
    if rating is not None and rating > 0:
        popm_rating = int(rating * 51)
        tags.add(POPM(email="rekordbox@antigravity", rating=popm_rating, count=0))

    tags.save(file_path)
    return True


def _tag_flac(file_path: str, bpm, key, genre, comment, year, rating) -> bool:
    audio = FLAC(file_path)
    if bpm is not None:
        audio["BPM"] = str(round(bpm, 2))
    if key:
        audio["KEY"] = str(key)
        audio["INITIALKEY"] = str(key)
    if genre:
        audio["GENRE"] = str(genre)
    if comment:
        audio["COMMENT"] = str(comment)
    if year:
        audio["DATE"] = str(year)
    if rating is not None and rating > 0:
        audio["RATING"] = str(rating)
    audio.save()
    return True


def _tag_mp4(file_path: str, bpm, key, genre, comment, year, rating) -> bool:
    audio = MP4(file_path)
    if bpm is not None:
        audio["tmpo"] = [int(round(bpm))]
    if key:
        audio["\xa9key"] = [str(key)]
    if genre:
        audio["\xa9gen"] = [str(genre)]
    if comment:
        audio["\xa9cmt"] = [str(comment)]
    if year:
        audio["\xa9day"] = [str(year)]
    audio.save()
    return True


def _tag_aiff(file_path: str, bpm, key, genre, comment, year, rating) -> bool:
    try:
        audio = AIFF(file_path)
        if audio.tags is None:
            audio.add_tags()
        if bpm is not None:
            audio.tags.add(TBPM(encoding=3, text=str(round(bpm, 2))))
        if key:
            audio.tags.add(TKEY(encoding=3, text=str(key)))
        if genre:
            audio.tags.add(TCON(encoding=3, text=str(genre)))
        if comment:
            audio.tags.add(COMM(encoding=3, lang="eng", desc="", text=str(comment)))
        if year:
            audio.tags.add(TDRC(encoding=3, text=str(year)))
        audio.save()
        return True
    except Exception as e:
        return False


def _tag_wav(file_path: str, bpm, key, genre, comment, year, rating) -> bool:
    try:
        audio = WAVE(file_path)
        if audio.tags is None:
            audio.add_tags()
        if bpm is not None:
            audio.tags.add(TBPM(encoding=3, text=str(round(bpm, 2))))
        if key:
            audio.tags.add(TKEY(encoding=3, text=str(key)))
        if genre:
            audio.tags.add(TCON(encoding=3, text=str(genre)))
        audio.save()
        return True
    except Exception as e:
        return False
