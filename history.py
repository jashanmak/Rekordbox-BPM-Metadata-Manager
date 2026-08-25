"""
Rename session history logger and full physical + database revert engine.
"""

import os
import json
import datetime
from typing import List, Dict, Any, Optional, Tuple

from pyrekordbox import Rekordbox6Database


HISTORY_DIR = os.path.join(os.path.dirname(__file__), "history")


def save_session_history(
    session_id: str,
    renamed_items: List[Dict[str, Any]]
) -> str:
    """
    Saves renamed file mappings for a session to JSON history file.
    
    :param session_id: Session identifier string
    :param renamed_items: List of dicts containing track_id, original_filepath, renamed_filepath
    :return: Path to history file saved
    """
    os.makedirs(HISTORY_DIR, exist_ok=True)
    filepath = os.path.join(HISTORY_DIR, f"session_{session_id}.json")
    
    data = {
        "session_id": session_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "total_items": len(renamed_items),
        "items": renamed_items
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    return filepath


def list_history_sessions() -> List[Dict[str, Any]]:
    """
    Lists all past rename history sessions sorted by newest first.
    """
    if not os.path.exists(HISTORY_DIR):
        return []
        
    sessions = []
    for file in os.listdir(HISTORY_DIR):
        if file.startswith("session_") and file.endswith(".json"):
            filepath = os.path.join(HISTORY_DIR, file)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sessions.append({
                        "session_id": data.get("session_id"),
                        "timestamp": data.get("timestamp"),
                        "total_items": data.get("total_items", 0),
                        "filepath": filepath
                    })
            except Exception:
                pass
                
    sessions.sort(key=lambda s: s.get("timestamp", ""), reverse=True)
    return sessions


def revert_session(
    session_id: str,
    db: Optional[Rekordbox6Database] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Reverts a past rename session:
    1. Renames physical files back to their original file paths.
    2. Updates track locations in Rekordbox master.db back to original paths.
    
    :param session_id: History session ID
    :param db: Active Rekordbox6Database connection (will connect if None)
    :param dry_run: If True, previews revert without modifying disk or DB
    :return: Summary dictionary with counts
    """
    filepath = os.path.join(HISTORY_DIR, f"session_{session_id}.json")
    if not os.path.exists(filepath):
        return {"error": f"Session history file not found: {filepath}"}
        
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    items = data.get("items", [])
    
    if not dry_run and db is None:
        db = Rekordbox6Database()
        
    stats = {
        "total": len(items),
        "reverted": 0,
        "missing": 0,
        "failed": 0,
        "dry_run": dry_run
    }
    
    # Map tracks by ID for fast lookup if DB provided
    db_tracks_by_id = {}
    if db is not None:
        all_content = db.get_content().all()
        for t in all_content:
            db_tracks_by_id[str(t.ID)] = t
            
    for item in items:
        track_id = str(item.get("track_id"))
        orig_path = item.get("original_filepath")
        renamed_path = item.get("renamed_filepath")
        
        if not orig_path or not renamed_path:
            stats["failed"] += 1
            continue
            
        renamed_path = renamed_path.replace("/", "\\")
        orig_path = orig_path.replace("/", "\\")
        
        if not os.path.exists(renamed_path):
            print(f"[Revert] File not found at renamed path: {renamed_path}")
            stats["missing"] += 1
            continue
            
        if dry_run:
            stats["reverted"] += 1
            continue
            
        # 1. Rename physical file back
        try:
            target_dir = os.path.dirname(orig_path)
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)
            os.rename(renamed_path, orig_path)
        except Exception as e:
            print(f"[Revert] Failed to revert file {renamed_path} -> {orig_path}: {e}")
            stats["failed"] += 1
            continue
            
        # 2. Update DB location
        if db is not None and track_id in db_tracks_by_id:
            track = db_tracks_by_id[track_id]
            norm_orig = orig_path.replace("\\", "/")
            orig_filename = os.path.basename(norm_orig)
            track.FolderPath = norm_orig
            track.FileNameL = orig_filename
            track.FileNameS = orig_filename[:255]
            
        stats["reverted"] += 1
        
    if not dry_run and db is not None and stats["reverted"] > 0:
        db.commit()
        print(f"[Revert] Successfully committed location reverts to Rekordbox database.")
        
    return stats
