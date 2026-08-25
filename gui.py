"""
Muted Windows 95 Aesthetic Desktop GUI for Rekordbox Manager v2.5.
Features: Playlist selector, Preset templates dropdown, USB drive detection,
Live search console filter, Energy/Stars tags, and Completion Audio Chime.
"""

import os
import sys
import datetime
import threading
from typing import List, Dict, Any, Optional

import customtkinter as ctk

try:
    import winsound
except ImportError:
    winsound = None

from rekordbox_db import (
    is_rekordbox_running,
    get_rekordbox_db,
    detect_usb_databases,
    backup_database,
    get_analyzed_tracks,
    get_playlists,
    get_tracks_by_playlist,
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
    list_history_sessions,
    revert_session,
)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

PRESET_TEMPLATES = [
    "[1] Standard DJ: [{bpm} BPM] [{key_camelot}] {artist} - {title}.{ext}",
    "[2] Key First: [{key_camelot}] [{bpm} BPM] {artist} - {title}.{ext}",
    "[3] Compact USB: {bpm}BPM - {key_camelot} - {title}.{ext}",
    "[4] Artist First: {artist} - {title} ({bpm} BPM - {key_camelot}).{ext}",
    "[5] Energy + Key + BPM: [{energy}] [{key_camelot}] [{bpm} BPM] {artist} - {title}.{ext}",
]

DEFAULT_TEMPLATE = "[{bpm} BPM] [{key_camelot}] {artist} - {title}.{ext}"

WIN95_GRAY = "#C0C0C0"
WIN95_NAVY = "#102A43"
WIN95_BLACK_ACCENT = "#1A1A1A"
WIN95_LCD_BLACK = "#141414"
WIN95_TEXT_MUTED = "#D0D0D0"
WIN95_GREEN_MUTED = "#8BBF9F"
WIN95_BUTTON_GRAY = "#D4D0C8"
WIN95_BUTTON_HOVER = "#E6E2DA"
WIN95_BUTTON_TEXT = "#000000"


class RekordboxAppWin95(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Rekordbox BPM & Metadata Manager v1.0")
        self.geometry("1020 x 820")
        self.minsize(900, 680)
        self.configure(fg_color=WIN95_BLACK_ACCENT)

        self.db = None
        self.playlists_data = []
        self.tracks = []
        self.track_dicts = []
        self.all_console_lines = []

        self._create_widgets()
        self._load_database_async()

    def _create_widgets(self):
        self.win_frame = ctk.CTkFrame(
            self,
            fg_color=WIN95_GRAY,
            border_color="#FFFFFF",
            border_width=2,
            corner_radius=0
        )
        self.win_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # Title Bar Banner
        self.title_bar = ctk.CTkFrame(
            self.win_frame,
            fg_color=WIN95_NAVY,
            height=36,
            corner_radius=0
        )
        self.title_bar.pack(fill="x", padx=4, pady=4)

        self.title_label = ctk.CTkLabel(
            self.title_bar,
            text="Rekordbox BPM & Metadata Manager v1.0",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color="#FFFFFF"
        )
        self.title_label.pack(side="left", padx=10, pady=5)

        self.status_lcd = ctk.CTkLabel(
            self.title_bar,
            text="[ CONNECTING... ]",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#E0E0E0",
            fg_color=WIN95_LCD_BLACK,
            corner_radius=2,
            padx=10,
            pady=3
        )
        self.status_lcd.pack(side="right", padx=6, pady=4)

        # Tabview
        self.tabview = ctk.CTkTabview(
            self.win_frame,
            fg_color=WIN95_GRAY,
            segmented_button_fg_color=WIN95_BLACK_ACCENT,
            segmented_button_selected_color=WIN95_NAVY,
            segmented_button_selected_hover_color="#183B5E",
            segmented_button_unselected_color="#262626",
            segmented_button_unselected_hover_color="#363636",
            corner_radius=0
        )
        self.tabview.pack(fill="both", expand=True, padx=6, pady=4)

        self.tab_rename = self.tabview.add("  Rename & Tag Utility  ")
        self.tab_revert = self.tabview.add("  Revert History  ")

        self._build_rename_tab()
        self._build_revert_tab()

        # Footer Status Bar
        self.footer_bar = ctk.CTkFrame(self.win_frame, fg_color=WIN95_BLACK_ACCENT, height=28, corner_radius=0)
        self.footer_bar.pack(fill="x", padx=4, pady=4)

        self.footer_text = ctk.CTkLabel(
            self.footer_bar,
            text="SYSTEM READY",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#A0A0A0"
        )
        self.footer_text.pack(side="left", padx=10, pady=2)

    def _build_rename_tab(self):
        # Source & Playlist Filter Section
        source_frame = ctk.CTkFrame(
            self.tab_rename,
            fg_color=WIN95_GRAY,
            border_color="#555555",
            border_width=2,
            corner_radius=0
        )
        source_frame.pack(fill="x", padx=6, pady=4)

        src_grid = ctk.CTkFrame(source_frame, fg_color="transparent")
        src_grid.pack(fill="x", padx=8, pady=4)

        lbl_lib = ctk.CTkLabel(src_grid, text="Library Source:", text_color="#000000", font=ctk.CTkFont(weight="bold"))
        lbl_lib.pack(side="left", padx=(0, 5))

        self.source_menu = ctk.CTkOptionMenu(
            src_grid,
            values=["Local Rekordbox (master.db)"],
            fg_color=WIN95_BLACK_ACCENT,
            button_color="#333333",
            button_hover_color="#555555",
            text_color="#FFFFFF",
            corner_radius=0,
            width=220
        )
        self.source_menu.pack(side="left", padx=5)

        lbl_playlist = ctk.CTkLabel(src_grid, text="Playlist Target:", text_color="#000000", font=ctk.CTkFont(weight="bold"))
        lbl_playlist.pack(side="left", padx=(15, 5))

        self.playlist_menu = ctk.CTkOptionMenu(
            src_grid,
            values=["All Analyzed Tracks"],
            fg_color=WIN95_BLACK_ACCENT,
            button_color="#333333",
            button_hover_color="#555555",
            text_color="#FFFFFF",
            corner_radius=0,
            width=260,
            command=self._on_playlist_selected
        )
        self.playlist_menu.pack(side="left", padx=5)

        # Template Box
        template_frame = ctk.CTkFrame(
            self.tab_rename,
            fg_color=WIN95_GRAY,
            border_color="#555555",
            border_width=2,
            corner_radius=0
        )
        template_frame.pack(fill="x", padx=6, pady=4)

        header_sub = ctk.CTkFrame(template_frame, fg_color="transparent")
        header_sub.pack(fill="x", padx=8, pady=(4, 2))

        tpl_label = ctk.CTkLabel(
            header_sub,
            text="Filename Format Template:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#000000"
        )
        tpl_label.pack(side="left")

        preset_lbl = ctk.CTkLabel(header_sub, text="Presets:", text_color="#000000", font=ctk.CTkFont(size=11, weight="bold"))
        preset_lbl.pack(side="left", padx=(20, 5))

        self.preset_menu = ctk.CTkOptionMenu(
            header_sub,
            values=PRESET_TEMPLATES,
            fg_color=WIN95_BLACK_ACCENT,
            button_color="#333333",
            button_hover_color="#555555",
            text_color="#FFFFFF",
            corner_radius=0,
            width=320,
            command=self._on_preset_selected
        )
        self.preset_menu.pack(side="left", padx=5)

        btn_reset_tpl = ctk.CTkButton(
            header_sub,
            text="↺ Reset",
            width=70,
            height=22,
            fg_color=WIN95_BUTTON_GRAY,
            hover_color=WIN95_BUTTON_HOVER,
            text_color=WIN95_BUTTON_TEXT,
            border_color="#000000",
            border_width=1,
            corner_radius=0,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._reset_template
        )
        btn_reset_tpl.pack(side="right")

        self.template_entry = ctk.CTkEntry(
            template_frame,
            fg_color=WIN95_LCD_BLACK,
            text_color=WIN95_TEXT_MUTED,
            border_color="#555555",
            border_width=2,
            corner_radius=0,
            font=ctk.CTkFont(family="Consolas", size=13)
        )
        self.template_entry.insert(0, DEFAULT_TEMPLATE)
        self.template_entry.pack(fill="x", padx=8, pady=4)

        # Quick Insert Buttons
        btn_frame = ctk.CTkFrame(template_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=8, pady=4)

        tags_to_add = [
            ("{bpm}", "+ BPM"),
            ("{key_camelot}", "+ Camelot"),
            ("{key_alpha}", "+ OpenKey"),
            ("{key_std}", "+ Std Key"),
            ("{artist}", "+ Artist"),
            ("{title}", "+ Title"),
            ("{genre}", "+ Genre"),
            ("{energy}", "+ Energy"),
            ("{stars}", "+ Stars"),
        ]

        for tag, label in tags_to_add:
            btn = ctk.CTkButton(
                btn_frame,
                text=label,
                width=80,
                height=24,
                fg_color=WIN95_BUTTON_GRAY,
                hover_color=WIN95_BUTTON_HOVER,
                text_color=WIN95_BUTTON_TEXT,
                border_color="#000000",
                border_width=1,
                corner_radius=0,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda t=tag: self._insert_tag(t)
            )
            btn.pack(side="left", padx=2, pady=2)

        # Options Section
        options_frame = ctk.CTkFrame(
            self.tab_rename,
            fg_color=WIN95_GRAY,
            border_color="#555555",
            border_width=2,
            corner_radius=0
        )
        options_frame.pack(fill="x", padx=6, pady=4)

        opt_grid = ctk.CTkFrame(options_frame, fg_color="transparent")
        opt_grid.pack(fill="x", padx=8, pady=4)

        self.var_write_tags = ctk.BooleanVar(value=True)
        self.chk_write_tags = ctk.CTkCheckBox(
            opt_grid,
            text="Write Tags",
            variable=self.var_write_tags,
            text_color="#000000",
            fg_color=WIN95_NAVY,
            hover_color="#183B5E",
            corner_radius=0
        )
        self.chk_write_tags.pack(side="left", padx=8)

        self.var_decimals = ctk.BooleanVar(value=False)
        self.chk_decimals = ctk.CTkCheckBox(
            opt_grid,
            text="Decimal BPM",
            variable=self.var_decimals,
            text_color="#000000",
            fg_color=WIN95_NAVY,
            hover_color="#183B5E",
            corner_radius=0
        )
        self.chk_decimals.pack(side="left", padx=8)

        self.var_force = ctk.BooleanVar(value=True)
        self.chk_force = ctk.CTkCheckBox(
            opt_grid,
            text="Re-apply Tracks",
            variable=self.var_force,
            text_color="#000000",
            fg_color=WIN95_NAVY,
            hover_color="#183B5E",
            corner_radius=0
        )
        self.chk_force.pack(side="left", padx=8)

        key_label = ctk.CTkLabel(opt_grid, text="Tag Key:", text_color="#000000", font=ctk.CTkFont(weight="bold"))
        key_label.pack(side="left", padx=(10, 5))

        self.key_notation_menu = ctk.CTkOptionMenu(
            opt_grid,
            values=["Camelot (8A, 12B)", "OpenKey (8m, 12d)", "Standard (Am, C#m)"],
            fg_color=WIN95_BLACK_ACCENT,
            button_color="#333333",
            button_hover_color="#555555",
            text_color="#FFFFFF",
            corner_radius=0,
            width=150
        )
        self.key_notation_menu.set("Camelot (8A, 12B)")
        self.key_notation_menu.pack(side="left", padx=5)

        # Control Buttons Frame
        ctrl_frame = ctk.CTkFrame(self.tab_rename, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=6, pady=6)

        self.btn_preview = ctk.CTkButton(
            ctrl_frame,
            text="🔍 PREVIEW CHANGES (DRY RUN)",
            fg_color="#1E3E5B",
            hover_color="#152B3F",
            text_color="#FFFFFF",
            border_color="#000000",
            border_width=2,
            height=36,
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            corner_radius=0,
            command=self._run_dry_run
        )
        self.btn_preview.pack(side="left", expand=True, fill="x", padx=4)

        self.btn_execute = ctk.CTkButton(
            ctrl_frame,
            text="⚡ EXECUTE RENAMING & TAGGING",
            fg_color="#236B43",
            hover_color="#184A2E",
            text_color="#FFFFFF",
            border_color="#000000",
            border_width=2,
            height=36,
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            corner_radius=0,
            command=self._run_execute
        )
        self.btn_execute.pack(side="left", expand=True, fill="x", padx=4)

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            self.tab_rename,
            fg_color=WIN95_LCD_BLACK,
            progress_color=WIN95_GREEN_MUTED,
            corner_radius=0
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=6, pady=(0, 4))

        # Live Search & Filter Bar
        search_frame = ctk.CTkFrame(self.tab_rename, fg_color="transparent")
        search_frame.pack(fill="x", padx=6, pady=(2, 2))

        search_lbl = ctk.CTkLabel(search_frame, text="🔎 Search Console:", text_color="#000000", font=ctk.CTkFont(size=11, weight="bold"))
        search_lbl.pack(side="left", padx=(4, 5))

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Type to filter log lines live (e.g. 128, 8A, House)...",
            fg_color=WIN95_LCD_BLACK,
            text_color=WIN95_TEXT_MUTED,
            border_color="#555555",
            border_width=1,
            corner_radius=0,
            height=24
        )
        self.search_entry.pack(fill="x", expand=True, side="left", padx=4)
        self.search_entry.bind("<KeyRelease>", self._filter_console_live)

        # Console Display
        self.console = ctk.CTkTextbox(
            self.tab_rename,
            fg_color=WIN95_LCD_BLACK,
            text_color=WIN95_TEXT_MUTED,
            border_color="#555555",
            border_width=2,
            corner_radius=0,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none"
        )
        self.console.pack(fill="both", expand=True, padx=6, pady=4)

    def _build_revert_tab(self):
        rev_frame = ctk.CTkFrame(
            self.tab_revert,
            fg_color=WIN95_GRAY,
            border_color="#555555",
            border_width=2,
            corner_radius=0
        )
        rev_frame.pack(fill="x", padx=6, pady=8)

        lbl = ctk.CTkLabel(
            rev_frame,
            text="Select Past Session to Revert:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#000000"
        )
        lbl.pack(anchor="w", padx=8, pady=4)

        sub_frame = ctk.CTkFrame(rev_frame, fg_color="transparent")
        sub_frame.pack(fill="x", padx=8, pady=4)

        self.history_menu = ctk.CTkOptionMenu(
            sub_frame,
            values=["No past sessions found"],
            fg_color=WIN95_BLACK_ACCENT,
            button_color="#333333",
            button_hover_color="#555555",
            text_color="#FFFFFF",
            corner_radius=0,
            width=420
        )
        self.history_menu.pack(side="left", padx=4)

        self.btn_refresh_hist = ctk.CTkButton(
            sub_frame,
            text="🔄 Refresh",
            width=110,
            fg_color=WIN95_BUTTON_GRAY,
            hover_color=WIN95_BUTTON_HOVER,
            text_color=WIN95_BUTTON_TEXT,
            border_color="#000000",
            border_width=1,
            corner_radius=0,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._refresh_history_list
        )
        self.btn_refresh_hist.pack(side="left", padx=4)

        self.btn_revert = ctk.CTkButton(
            sub_frame,
            text="↩️ REVERT SESSION",
            fg_color="#8B2626",
            hover_color="#601A1A",
            text_color="#FFFFFF",
            border_color="#000000",
            border_width=2,
            corner_radius=0,
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            command=self._run_revert
        )
        self.btn_revert.pack(side="left", padx=12)

        self.revert_console = ctk.CTkTextbox(
            self.tab_revert,
            fg_color=WIN95_LCD_BLACK,
            text_color=WIN95_TEXT_MUTED,
            border_color="#555555",
            border_width=2,
            corner_radius=0,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none"
        )
        self.revert_console.pack(fill="both", expand=True, padx=6, pady=8)

    def _reset_template(self):
        self.template_entry.delete(0, "end")
        self.template_entry.insert(0, DEFAULT_TEMPLATE)

    def _on_preset_selected(self, choice: str):
        if ":" in choice:
            raw_tpl = choice.split(":", 1)[1].strip()
            self.template_entry.delete(0, "end")
            self.template_entry.insert(0, raw_tpl)

    def _on_playlist_selected(self, choice: str):
        if "All Analyzed Tracks" in choice or not self.db:
            self.tracks = get_analyzed_tracks(self.db)
        else:
            playlist_name = choice.rsplit(" (", 1)[0].strip()
            for p in self.playlists_data:
                if p["name"] == playlist_name:
                    self.tracks = get_tracks_by_playlist(self.db, p["id"])
                    break
        self.track_dicts = [extract_track_dict(t) for t in self.tracks]
        self._log(f"Selected Playlist Target: '{choice}'. Loaded {len(self.track_dicts)} tracks.")

    def _insert_tag(self, tag: str):
        curr = self.template_entry.get().strip()
        if not curr:
            self.template_entry.insert(0, f"{tag}.{{ext}}")
            return

        if ".{ext}" in curr:
            parts = curr.split(".{ext}")
            prefix = parts[0].rstrip()
            suffix = ".{ext}".join(parts[1:])
            new_text = f"{prefix} {tag}.{{ext}}{suffix}"
            self.template_entry.delete(0, "end")
            self.template_entry.insert(0, new_text)
        else:
            self.template_entry.insert("insert", tag)

    def _log(self, msg: str, target_console=None):
        if target_console is None:
            target_console = self.console
            self.all_console_lines.append(msg)
        target_console.insert("end", msg + "\n")
        target_console.see("end")

    def _filter_console_live(self, event=None):
        query = self.search_entry.get().strip().lower()
        self.console.delete("1.0", "end")
        if not query:
            for line in self.all_console_lines:
                self.console.insert("end", line + "\n")
        else:
            for line in self.all_console_lines:
                if query in line.lower():
                    self.console.insert("end", line + "\n")
        self.console.see("end")

    def _play_completion_chime(self):
        if winsound:
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

    def _load_database_async(self):
        def worker():
            try:
                self.db = get_rekordbox_db()
                self.tracks = get_analyzed_tracks(self.db)
                self.track_dicts = [extract_track_dict(t) for t in self.tracks]
                self.playlists_data = get_playlists(self.db)

                # Populate sources (detect USBs)
                usb_sources = detect_usb_databases()
                source_options = ["Local Rekordbox (master.db)"] + [u["name"] for u in usb_sources]
                
                playlist_options = [f"All Analyzed Tracks ({len(self.tracks)})"] + [f"{p['name']} ({p['song_count']})" for p in self.playlists_data]

                self.after(0, lambda: self.source_menu.configure(values=source_options))
                self.after(0, lambda: self.playlist_menu.configure(values=playlist_options))
                self.after(0, lambda: self.playlist_menu.set(playlist_options[0]))

                self.after(0, lambda: self.status_lcd.configure(
                    text=f"[ ONLINE: {len(self.tracks)} TRACKS ]",
                    text_color=WIN95_GREEN_MUTED
                ))
                self.after(0, lambda: self._log(f"Connected to Rekordbox master.db. Found {len(self.tracks)} tracks across {len(self.playlists_data)} playlists."))
                self.after(0, self._refresh_history_list)
            except Exception as e:
                self.after(0, lambda: self.status_lcd.configure(
                    text="[ DB ERROR ]",
                    text_color="#D9534F"
                ))
                self.after(0, lambda: self._log(f"Error connecting to Rekordbox: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _refresh_history_list(self):
        sessions = list_history_sessions()
        if not sessions:
            self.history_menu.configure(values=["No past sessions found"])
            self.history_menu.set("No past sessions found")
        else:
            options = [f"{s['session_id']} | {s['timestamp'][:19]} ({s['total_items']} items)" for s in sessions]
            self.history_menu.configure(values=options)
            self.history_menu.set(options[0])

    def _run_dry_run(self):
        if not self.track_dicts:
            self._log("No tracks loaded.")
            return

        self.console.delete("1.0", "end")
        self.all_console_lines.clear()
        self._log("=== PREVIEWING CHANGES (DRY RUN) ===")
        
        template = self.template_entry.get().strip()
        decimals = 1 if self.var_decimals.get() else 0
        force_reapply = self.var_force.get()

        total = len(self.track_dicts)
        renamed_count = 0

        for i, meta in enumerate(self.track_dicts):
            self.progress_bar.set((i + 1) / total)
            orig_path = meta["folder_path"].replace("/", "\\")
            old_filename = os.path.basename(orig_path)

            if not os.path.exists(orig_path):
                continue

            new_filename = build_new_filename(
                original_filepath=orig_path,
                meta=meta,
                template=template,
                decimals=decimals
            )

            if old_filename == new_filename:
                continue

            if not force_reapply and is_already_renamed(old_filename, meta["bpm"], decimals=decimals):
                continue

            self._log(f"[DRY-RUN] {old_filename} -> {new_filename}")
            renamed_count += 1

        self._log(f"\nDry Run Complete: {renamed_count} tracks would be renamed.")
        self._play_completion_chime()

    def _run_execute(self):
        if not self.track_dicts:
            self._log("No tracks loaded.")
            return

        if is_rekordbox_running():
            self._log("[WARNING] Rekordbox is currently running! Please close Rekordbox to avoid DB locks.")
            return

        self.btn_execute.configure(state="disabled")
        self.btn_preview.configure(state="disabled")
        self.console.delete("1.0", "end")
        self.all_console_lines.clear()
        self._log("=== STARTING LIVE TAGGING & RENAMING ===")

        template = self.template_entry.get().strip()
        decimals = 1 if self.var_decimals.get() else 0
        write_tags_flag = self.var_write_tags.get()
        key_notation = self.key_notation_menu.get()
        force_reapply = self.var_force.get()

        def worker():
            backup_file = backup_database()
            if backup_file:
                self.after(0, lambda: self._log(f"[DB] Backup created at: {backup_file}"))

            session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            renamed_history_items = []

            total = len(self.track_dicts)
            success_count = 0

            for i, meta in enumerate(self.track_dicts):
                self.after(0, lambda val=(i+1)/total: self.progress_bar.set(val))
                orig_path = meta["folder_path"].replace("/", "\\")
                old_filename = os.path.basename(orig_path)

                if not os.path.exists(orig_path):
                    continue

                new_filename = build_new_filename(
                    original_filepath=orig_path,
                    meta=meta,
                    template=template,
                    decimals=decimals
                )

                if old_filename == new_filename:
                    continue

                if not force_reapply and is_already_renamed(old_filename, meta["bpm"], decimals=decimals):
                    continue

                if "Camelot" in key_notation:
                    tag_key = meta["key_camelot"]
                elif "OpenKey" in key_notation:
                    tag_key = meta["key_alpha"]
                else:
                    tag_key = meta["key_std"]

                # 1. Write Tags
                if write_tags_flag:
                    write_audio_tags(
                        file_path=orig_path,
                        bpm=meta["bpm"],
                        key=tag_key,
                        genre=meta["genre"],
                        comment=meta["comment"],
                        year=meta["year"],
                        rating=meta["rating"]
                    )

                # 2. Rename File
                success, new_filepath = rename_file_on_disk(
                    old_filepath=orig_path,
                    new_filename=new_filename,
                    dry_run=False
                )

                if success and new_filepath != orig_path:
                    # 3. Update DB
                    update_track_location(self.db, meta["raw_track"], new_filepath)
                    renamed_history_items.append({
                        "track_id": meta["id"],
                        "original_filepath": orig_path,
                        "renamed_filepath": new_filepath,
                        "bpm": meta["bpm"],
                        "title": meta["title"],
                        "artist": meta["artist"]
                    })
                    success_count += 1
                    self.after(0, lambda old=old_filename, new=new_filename: self._log(f"[SUCCESS] {old} -> {new}"))

            if success_count > 0:
                self.after(0, lambda: self._log("\n[DB] Committing changes to Rekordbox database..."))
                self.db.commit()
                save_session_history(session_id, renamed_history_items)
                self.after(0, lambda: self._log(f"[HISTORY] Saved rename history session: {session_id}"))

            self.after(0, lambda: self._log(f"\nCompleted! Renamed and tagged {success_count} tracks."))
            self.after(0, lambda: self.btn_execute.configure(state="normal"))
            self.after(0, lambda: self.btn_preview.configure(state="normal"))
            self.after(0, self._play_completion_chime)
            self.after(0, self._refresh_history_list)

        threading.Thread(target=worker, daemon=True).start()

    def _run_revert(self):
        selected = self.history_menu.get()
        if not selected or "No past" in selected:
            return

        session_id = selected.split(" | ")[0].strip()
        
        self.revert_console.delete("1.0", "end")
        self._log(f"=== REVERTING SESSION: {session_id} ===", target_console=self.revert_console)

        def worker():
            res = revert_session(session_id=session_id, db=self.db, dry_run=False)
            self.after(0, lambda: self._log(
                f"\nRevert Complete!\nTotal Items: {res.get('total')}\nReverted: {res.get('reverted')}\nMissing: {res.get('missing')}\nFailed: {res.get('failed')}",
                target_console=self.revert_console
            ))
            self.tracks = get_analyzed_tracks(self.db)
            self.track_dicts = [extract_track_dict(t) for t in self.tracks]
            self.after(0, self._play_completion_chime)

        threading.Thread(target=worker, daemon=True).start()


def launch_gui():
    app = RekordboxAppWin95()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
