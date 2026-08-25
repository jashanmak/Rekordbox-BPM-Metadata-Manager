"""
Rekordbox BPM & Metadata Manager - Main Launcher.

Supports both desktop GUI mode and CLI mode.
"""

import os
import sys
import argparse
from colorama import init, Fore, Style

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from rekordbox_db import (
    is_rekordbox_running,
    get_rekordbox_db,
    backup_database,
    get_analyzed_tracks,
    extract_track_dict,
    update_track_location,
)
from tagger import write_audio_tags
from renamer import (
    build_new_filename,
    is_already_renamed,
    rename_file_on_disk,
)
from history import (
    save_session_history,
    revert_session,
    list_history_sessions,
)

init(autoreset=True)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Rekordbox BPM & Metadata Tagger and Renamer Tool."
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in Command-Line interface mode instead of launching GUI."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview tag and filename changes without modifying files or database."
    )
    parser.add_argument(
        "--template",
        type=str,
        default="[{bpm} BPM] [{key_camelot}] {artist} - {title}.{ext}",
        help="Filename template. Placeholders: {bpm}, {key_camelot}, {key_alpha}, {key_std}, {artist}, {title}, {genre}, {comment}, {year}, {ext}."
    )
    parser.add_argument(
        "--decimals",
        type=int,
        default=0,
        help="BPM decimal precision (0 for '128', 1 for '128.5'). Default: 0."
    )
    parser.add_argument(
        "--key-notation",
        type=str,
        choices=["camelot", "openkey", "standard"],
        default="camelot",
        help="Key notation for file tagging (camelot, openkey, standard)."
    )
    parser.add_argument(
        "--revert",
        type=str,
        default=None,
        help="Revert a past session by session ID (or 'latest' for most recent session)."
    )
    parser.add_argument(
        "--no-tag",
        action="store_true",
        help="Skip writing ID3/Vorbis tags to file headers."
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating database backup before running."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of tracks to process."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force renaming even if file name already contains BPM pattern."
    )
    return parser.parse_args()


def run_cli(args):
    print(f"\n{Fore.CYAN}==================================================")
    print(f"{Fore.CYAN}   Rekordbox BPM & Metadata Manager CLI")
    print(f"{Fore.CYAN}==================================================\n")

    if args.revert:
        session_id = args.revert
        if session_id.lower() == "latest":
            sessions = list_history_sessions()
            if not sessions:
                print(f"{Fore.RED}[ERROR] No past rename sessions found to revert.")
                return
            session_id = sessions[0]["session_id"]
        print(f"{Fore.YELLOW}[REVERT] Reverting session: {session_id}...")
        res = revert_session(session_id=session_id, dry_run=args.dry_run)
        print(f"{Fore.GREEN}[REVERT] Result: {res}")
        return

    if args.dry_run:
        print(f"{Fore.YELLOW}[MODE] Running in DRY-RUN mode. No files or database will be modified.\n")

    if is_rekordbox_running():
        print(f"{Fore.RED}[WARNING] Rekordbox is currently running!")
        if not args.dry_run and not args.force:
            print(f"{Fore.YELLOW}Modifying database while Rekordbox is open can lock the database.")
            print(f"{Fore.YELLOW}Please close Rekordbox and run this tool again.\n")
            sys.exit(1)

    if not args.dry_run and not args.no_backup:
        backup_path = backup_database()
        if not backup_path:
            confirm = input("Database backup failed. Proceed anyway? (y/N): ")
            if confirm.lower() != "y":
                sys.exit(1)

    print(f"{Fore.GREEN}[DB] Connecting to Rekordbox database...")
    try:
        db = get_rekordbox_db()
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Failed to connect to Rekordbox database: {e}")
        sys.exit(1)

    print(f"{Fore.GREEN}[DB] Fetching analyzed tracks...")
    tracks = get_analyzed_tracks(db)
    print(f"[DB] Found {len(tracks)} analyzed tracks with valid audio paths.\n")

    if args.limit and args.limit > 0:
        tracks = tracks[:args.limit]

    import datetime
    session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    renamed_items = []

    stats = {"processed": 0, "skipped_missing": 0, "skipped_already_renamed": 0, "renamed": 0, "failed": 0}

    for track in tracks:
        stats["processed"] += 1
        meta = extract_track_dict(track)
        filepath = meta["folder_path"].replace("/", "\\")
        old_filename = os.path.basename(filepath)

        if not os.path.exists(filepath):
            stats["skipped_missing"] += 1
            continue

        if not args.force and is_already_renamed(old_filename, meta["bpm"], decimals=args.decimals):
            stats["skipped_already_renamed"] += 1
            continue

        new_filename = build_new_filename(
            original_filepath=filepath,
            meta=meta,
            template=args.template,
            decimals=args.decimals,
        )

        if args.dry_run:
            print(f"{Fore.YELLOW}[DRY-RUN] {old_filename} -> {new_filename}")
            stats["renamed"] += 1
            continue

        # Tag key notation selection
        if args.key_notation == "camelot":
            tag_key = meta["key_camelot"]
        elif args.key_notation == "openkey":
            tag_key = meta["key_alpha"]
        else:
            tag_key = meta["key_std"]

        if not args.no_tag:
            write_audio_tags(
                file_path=filepath,
                bpm=meta["bpm"],
                key=tag_key,
                genre=meta["genre"],
                comment=meta["comment"],
                year=meta["year"],
                rating=meta["rating"]
            )

        success, new_filepath = rename_file_on_disk(
            old_filepath=filepath,
            new_filename=new_filename,
            dry_run=False
        )

        if success and new_filepath != filepath:
            update_track_location(db, track, new_filepath)
            renamed_items.append({
                "track_id": meta["id"],
                "original_filepath": filepath,
                "renamed_filepath": new_filepath,
                "bpm": meta["bpm"],
                "title": meta["title"],
                "artist": meta["artist"]
            })
            print(f"{Fore.GREEN}[SUCCESS] {old_filename} -> {new_filename}")
            stats["renamed"] += 1

    if not args.dry_run and stats["renamed"] > 0:
        print(f"\n{Fore.GREEN}[DB] Committing changes to Rekordbox database...")
        db.commit()
        save_session_history(session_id, renamed_items)
        print(f"{Fore.GREEN}[HISTORY] Saved rename history session: {session_id}")

    print(f"\n{Fore.CYAN}==================================================")
    print(f"{Fore.CYAN}                  Run Summary")
    print(f"{Fore.CYAN}==================================================")
    print(f"Total Processed:         {stats['processed']}")
    print(f"Renamed/Updated:         {stats['renamed']}")
    print(f"Skipped (Already Named): {stats['skipped_already_renamed']}")
    print(f"Skipped (Missing File):  {stats['skipped_missing']}")
    print(f"{Fore.CYAN}==================================================\n")


def main():
    args = parse_args()
    
    # Launch CLI if explicit flags provided or --cli specified
    if args.cli or args.dry_run or args.revert or args.limit:
        run_cli(args)
    else:
        # Default: Launch GUI
        try:
            from gui import launch_gui
            launch_gui()
        except Exception as e:
            print(f"Failed to launch GUI ({e}). Falling back to CLI mode...")
            run_cli(args)


if __name__ == "__main__":
    main()
