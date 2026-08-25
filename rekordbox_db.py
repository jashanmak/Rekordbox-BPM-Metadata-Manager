"""
Rekordbox database interface module using pyrekordbox.
Handles connecting to master.db (local or USB), fetching playlist structures,
querying rich metadata, creating backups, and updating track locations.
"""

import os
import shutil
import datetime
import string
from typing import List, Dict, Any, Optional

import psutil
from pyrekordbox import Rekordbox6Database
from key_converter import to_camelot, to_openkey


def is_rekordbox_running() -> bool:
    """
    Checks if main Rekordbox DJ application process is currently running.
    Explicitly checks for main Rekordbox GUI executables and excludes RekordboxManager.
    """
    target_names = {"rekordbox.exe", "rekordbox6.exe", "rekordbox7.exe"}
    
    for proc in psutil.process_iter(['name']):
        try:
            name = proc.info['name']
            if name and name.lower() in target_names:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def get_rekordbox_db(db_path: Optional[str] = None) -> Rekordbox6Database:
    """Initializes and returns Rekordbox database connection."""
    if db_path and os.path.exists(db_path):
        return Rekordbox6Database(db_path)
    return Rekordbox6Database()


def detect_usb_databases() -> List[Dict[str, str]]:
    """
    Scans all Windows drive letters for Pioneer USB master.db collections.
    :return: List of dicts with drive letter, path, and display name.
    """
    usb_sources = []
    # Drive letters D: to Z:
    for letter in string.ascii_uppercase[3:]:
        drive_path = f"{letter}:\\"
        if os.path.exists(drive_path):
            possible_dbs = [
                os.path.join(drive_path, "PIONEER", "master.db"),
                os.path.join(drive_path, "PIONEER", "rekordbox", "master.db"),
                os.path.join(drive_path, "Pioneer", "rekordbox", "master.db"),
            ]
            for pdb in possible_dbs:
                if os.path.exists(pdb):
                    usb_sources.append({
                        "name": f"USB Drive ({letter}:) - {os.path.basename(pdb)}",
                        "path": pdb
                    })
    return usb_sources


def backup_database(db_path: Optional[str] = None, backup_dir: Optional[str] = None) -> Optional[str]:
    """Creates a timestamped backup of Rekordbox master.db file."""
    if not db_path:
        appdata = os.environ.get("APPDATA", "")
        possible_paths = [
            os.path.join(appdata, "Pioneer", "rekordbox6", "master.db"),
            os.path.join(appdata, "Pioneer", "rekordbox", "master.db"),
            os.path.join(appdata, "Pioneer", "rekordbox7", "master.db"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                db_path = path
                break
                
    if not db_path or not os.path.exists(db_path):
        print("[DB] Warning: Could not locate master.db for file backup.")
        return None

    if backup_dir is None:
        backup_dir = os.path.join(os.path.dirname(__file__), "backups")

    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"master_backup_{timestamp}.db")
    
    try:
        shutil.copy2(db_path, backup_file)
        print(f"[DB] Backup created at: {backup_file}")
        return backup_file
    except Exception as e:
        print(f"[DB] Failed to create backup: {e}")
        return None


def get_analyzed_tracks(db: Rekordbox6Database) -> List[Any]:
    """Queries all tracks from Rekordbox database that have BPM > 0."""
    all_content = db.get_content().all()
    analyzed = []
    
    for track in all_content:
        if track.BPM and track.BPM > 0 and track.FolderPath:
            analyzed.append(track)
            
    return analyzed


def get_playlists(db: Rekordbox6Database) -> List[Dict[str, Any]]:
    """Fetches all playlists from Rekordbox database."""
    playlists_raw = db.get_playlist().all()
    result = []
    
    for p in playlists_raw:
        if p.Name and p.Songs:
            song_count = len(p.Songs)
            if song_count > 0:
                result.append({
                    "id": p.ID,
                    "name": p.Name,
                    "song_count": song_count,
                    "raw_playlist": p
                })
                
    result.sort(key=lambda x: x["name"].lower())
    return result


def get_tracks_by_playlist(db: Rekordbox6Database, playlist_id: str) -> List[Any]:
    """Fetches analyzed tracks belonging to a specific playlist ID."""
    playlists = db.get_playlist().all()
    target = None
    
    for p in playlists:
        if str(p.ID) == str(playlist_id):
            target = p
            break
            
    if not target or not target.Songs:
        return []
        
    tracks = []
    for song_entry in target.Songs:
        content = song_entry.Content
        if content and content.BPM and content.BPM > 0 and content.FolderPath:
            tracks.append(content)
            
    return tracks


def extract_track_dict(track: Any) -> Dict[str, Any]:
    """Extracts a standardized dictionary of all Rekordbox metadata fields."""
    raw_bpm = track.BPM / 100.0 if track.BPM else 0.0
    key_std = track.KeyName or ""
    key_camelot = to_camelot(key_std)
    key_alpha = to_openkey(key_std)
    
    rating = track.Rating or 0
    stars_str = "★" * rating if rating > 0 else ""
    energy_str = f"E{rating}" if rating > 0 else ""

    return {
        "id": track.ID,
        "title": track.Title or "",
        "artist": track.ArtistName or "",
        "album": track.AlbumName or "",
        "genre": track.GenreName or "",
        "comment": track.Commnt or track.DeliveryComment or "",
        "rating": rating,
        "stars": stars_str,
        "energy": energy_str,
        "year": track.ReleaseYear or "",
        "bpm": raw_bpm,
        "key_std": key_std,
        "key_camelot": key_camelot,
        "key_alpha": key_alpha,
        "color": track.ColorName or "",
        "play_count": track.DJPlayCount or 0,
        "bitrate": track.BitRate or 0,
        "track_number": track.TrackNo or 0,
        "folder_path": track.FolderPath or "",
        "raw_track": track,
    }


def update_track_location(db: Rekordbox6Database, track: Any, new_file_path: str) -> None:
    """Updates the file path location of a track in Rekordbox database."""
    normalized_path = new_file_path.replace("\\", "/")
    filename = os.path.basename(normalized_path)
    
    track.FolderPath = normalized_path
    track.FileNameL = filename
    track.FileNameS = filename[:255] if filename else filename
