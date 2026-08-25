# Rekordbox BPM & Metadata Manager v1.0

A desktop GUI application and CLI utility that extracts analyzed metadata (BPM, Key, Genre, Rating, Comments, Year) directly from Rekordbox's database (`master.db`), writes metadata into audio file ID3/Vorbis/MP4 tags, renames physical files, and updates Rekordbox's internal track locations. Includes full **1-Click Revert** capability.

---

## Features

- **Modern Desktop GUI**: Built with CustomTkinter for a dark-themed, sleek UI.
- **Camelot & OpenKey Translation**: Converts Rekordbox key notation to Camelot (`8A`, `12B`) or OpenKey (`8m`, `12d`).
- **1-Click Revert System**: Every renaming operation records session logs. Revert physical filenames on disk AND restore Rekordbox database paths back to their original state anytime.
- **Rich Metadata Extraction & Tagging**:
  - Write any Rekordbox metadata (BPM, Key, Genre, Comment, Rating, Year) into audio tags (MP3, FLAC, M4A, AIFF, WAV).
  - Use dynamic filename placeholders: `{bpm}`, `{key_camelot}`, `{key_alpha}`, `{key_std}`, `{artist}`, `{title}`, `{genre}`, `{comment}`, `{year}`, `{rating}`, `{color}`.
- **Safety First**:
  - Automatic timestamped database backups (`master.db`).
  - Rekordbox process lock detection.
  - `--dry-run` preview mode.

---

## Installation

```bash
cd C:\Users\yuuts\.gemini\antigravity\scratch\rekordbox-bpm-renamer
pip install -r requirements.txt
```

---

## Launching the Desktop GUI

To open the interactive Desktop GUI:
```bash
python main.py
```

---

## CLI Usage (Terminal Commands)

### 1. Preview Changes (Dry Run)
```bash
python main.py --cli --dry-run
```

### 2. Live Renaming with Camelot Key
```bash
python main.py --cli --key-notation camelot
```

### 3. Revert Past Session
Revert the most recent rename session:
```bash
python main.py --cli --revert latest
```
Or revert a specific session ID:
```bash
python main.py --cli --revert 20260824_224733
```
