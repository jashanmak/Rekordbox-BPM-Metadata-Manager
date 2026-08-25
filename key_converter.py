"""
Key converter module for Musical, Camelot, and OpenKey/Alphanumeric key notations.
"""

from typing import Dict, Tuple, Optional

# Standard Key -> (Camelot, OpenKey)
KEY_MAP: Dict[str, Tuple[str, str]] = {
    # Minor Keys (A) / m
    "G#M": ("1A", "1m"), "ABM": ("1A", "1m"), "G#MIN": ("1A", "1m"), "ABMIN": ("1A", "1m"),
    "D#M": ("2A", "2m"), "EBM": ("2A", "2m"), "D#MIN": ("2A", "2m"), "EBMIN": ("2A", "2m"),
    "A#M": ("3A", "3m"), "BBM": ("3A", "3m"), "A#MIN": ("3A", "3m"), "BBMIN": ("3A", "3m"),
    "FM": ("4A", "4m"), "FMIN": ("4A", "4m"),
    "CM": ("5A", "5m"), "CMIN": ("5A", "5m"),
    "GM": ("6A", "6m"), "GMIN": ("6A", "6m"),
    "DM": ("7A", "7m"), "DMIN": ("7A", "7m"),
    "AM": ("8A", "8m"), "AMIN": ("8A", "8m"),
    "EM": ("9A", "9m"), "EMIN": ("9A", "9m"),
    "BM": ("10A", "10m"), "BMIN": ("10A", "10m"),
    "F#M": ("11A", "11m"), "GBM": ("11A", "11m"), "F#MIN": ("11A", "11m"), "GBMIN": ("11A", "11m"),
    "C#M": ("12A", "12m"), "DBM": ("12A", "12m"), "C#MIN": ("12A", "12m"), "DBMIN": ("12A", "12m"),

    # Major Keys (B) / d
    "B": ("1B", "1d"), "BMAJ": ("1B", "1d"),
    "F#": ("2B", "2d"), "GB": ("2B", "2d"), "F#MAJ": ("2B", "2d"), "GBMAJ": ("2B", "2d"),
    "C#": ("3B", "3d"), "DB": ("3B", "3d"), "C#MAJ": ("3B", "3d"), "DBMAJ": ("3B", "3d"),
    "G#": ("4B", "4d"), "AB": ("4B", "4d"), "G#MAJ": ("4B", "4d"), "ABMAJ": ("4B", "4d"),
    "D#": ("5B", "5d"), "EB": ("5B", "5d"), "D#MAJ": ("5B", "5d"), "EBMAJ": ("5B", "5d"),
    "A#": ("6B", "6d"), "BB": ("6B", "6d"), "A#MAJ": ("6B", "6d"), "BBMAJ": ("6B", "6d"),
    "F": ("7B", "7d"), "FMAJ": ("7B", "7d"),
    "C": ("8B", "8d"), "CMAJ": ("8B", "8d"),
    "G": ("9B", "9d"), "GMAJ": ("9B", "9d"),
    "D": ("10B", "10d"), "DMAJ": ("10B", "10d"),
    "A": ("11B", "11d"), "AMAJ": ("11B", "11d"),
    "E": ("12B", "12d"), "EMAJ": ("12B", "12d"),
}


def normalize_key_str(raw_key: Optional[str]) -> str:
    """Normalizes raw key string for mapping lookup."""
    if not raw_key:
        return ""
    clean = raw_key.strip().upper()
    clean = clean.replace(" ", "").replace("MAJOR", "MAJ").replace("MINOR", "MIN")
    return clean


def to_camelot(raw_key: Optional[str]) -> str:
    """
    Converts musical key string to Camelot key (e.g. 'Am' -> '8A', 'C#m' -> '12A').
    Returns original key string if mapping is not found.
    """
    if not raw_key:
        return ""
    
    clean = normalize_key_str(raw_key)
    
    # Check direct match
    if clean in KEY_MAP:
        return KEY_MAP[clean][0]
        
    # Check if raw_key is already in Camelot format (e.g. 8A, 12B)
    if len(raw_key) in [2, 3] and raw_key[:-1].isdigit() and raw_key[-1].upper() in ['A', 'B']:
        return raw_key.upper()
        
    return raw_key


def to_openkey(raw_key: Optional[str]) -> str:
    """
    Converts musical key string to OpenKey / Alphanumeric (e.g. 'Am' -> '8m', 'C' -> '8d').
    """
    if not raw_key:
        return ""
        
    clean = normalize_key_str(raw_key)
    
    if clean in KEY_MAP:
        return KEY_MAP[clean][1]
        
    return raw_key
