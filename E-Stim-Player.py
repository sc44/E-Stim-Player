#! /usr/bin/env python3

import datetime
import json
import os
import re
import threading
import time
import tkinter as tk
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from tkinter import filedialog
from typing import Any, List, Optional

import customtkinter as ctk
import numpy as np
import sounddevice as sd

try:
    import soundfile as sf
except ImportError:
    sf = None

APP_VERSION = "1.1"
APP_CREATOR = "sc44"
VALID_LOOP_KEYS = ("off", "track", "session")
VALID_LANGUAGES = ("en", "de")
LANGUAGE_LABELS = {"en": "English", "de": "Deutsch"}
LABEL_TO_LANGUAGE = {v: k for k, v in LANGUAGE_LABELS.items()}

DEFAULT_SAMPLE_RATE = 44100
BLOCKSIZE = 4048
FLAC_METER_SCALE = 0.55
AUDIO_FILE_EXTENSIONS = (".flac", ".wav", ".ogg")

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "E-Stim Player",
        "menu_file": "File",
        "menu_open_session": "Open Session...",
        "menu_create_session": "Create / Edit Session...",
        "menu_export_track": "Save Current Track as .flac...",
        "menu_export_all_tracks": "Save All Tracks as Individual .flac...",
        "menu_export_session": "Save Entire Session as .flac...",
        "menu_settings": "Settings",
        "menu_about": "Info...",
        "menu_exit": "Exit",
        "about_title": "Info – E-Stim Player",
        "about_heading": "E-Stim Player",
        "about_version": "Version {version}",
        "about_creator": "Creator: {creator}",
        "about_desc": "Desktop audio and session player for FLAC, M3U, XML, and ALASS2 S-Expression sessions.",
        "about_btn_close": "Close",
        "btn_open_session": "Open Session",
        "btn_create_session": "New / Edit Session",
        "no_session_loaded": "No session loaded",
        "btn_start": "▶ Start",
        "btn_pause": "⏸ Pause",
        "btn_stop": "⏹ Stop",
        "loop_off": "Off",
        "loop_track": "Track",
        "loop_session": "Session",
        "tracks_label": "Tracks",
        "status_ready": "Ready",
        "status_paused": "Paused",
        "status_stopped": "Stopped",
        "status_playback_started": "Playback started",
        "status_session_finished": "Session finished",
        "status_loop_mode": "Loop mode: {mode}",
        "status_loaded": "Loaded: {filename}",
        "status_load_error": "Error loading file: {error}",
        "status_settings_saved": "Settings saved to {path}",
        "status_seeking_track": "Seeking in Track",
        "status_position_set": "Position set",
        "status_track_pos": "{prefix} {idx:02d}: {name}  ({cur:.1f}s / {dur:.1f}s){loop}",
        "status_playing_track": "Playing Track {idx:02d}: {name}  ({cur:.1f}s / {dur:.1f}s){loop}",
        "status_loop_suffix": " [Loop: {mode}]",
        "status_export_running": "FLAC export is already running...",
        "status_no_session_track": "No session loaded – track export not possible.",
        "status_no_session_batch": "No session loaded – batch export not possible.",
        "status_no_session_session": "No session loaded – session export not possible.",
        "status_exporting_single": "Exporting {label} as FLAC ({pct}%)...",
        "status_export_failed": "FLAC export failed: {error}",
        "status_export_saved": "FLAC saved: {filename} ({path})",
        "status_batch_start": "Exporting 0/{total} tracks ({pct}%) to {dir}...",
        "status_batch_progress": "Exporting {idx}/{total} ({pct}%): {filename}",
        "status_batch_failed": "Batch export failed: {error}",
        "status_batch_done": "{total} tracks saved as .flac in: {dir}",
        "status_audio_error": "Audio error on Track {idx}: {error} (sr={sr}, bs={bs}, vol={vol})",
        "export_vol_title": "FLAC Export Volume",
        "export_vol_prompt": "Export volume in % (0–200%, default: {cur_pct}%):",
        "dialog_open_title": "Open Session or FLAC",
        "filter_all_supported": "Sessions, FLAC & M3U",
        "filter_flac": "FLAC Audio",
        "filter_alass2": "ALASS2 Session",
        "filter_smartstim": "SmartStim Session",
        "filter_m3u": "M3U Playlist",
        "filter_all_files": "All Files",
        "dialog_save_track_title": "Save Track as FLAC",
        "dialog_select_base_dir": "Select Base Folder for Session Directory",
        "dialog_save_session_title": "Save Entire Session as FLAC",
        "dialog_save_alass2_title": "Save Session (.alass2)",
        "kind_playlist": "Playlist",
        "kind_tracks": "Tracks",
        "session_header": "{name}  |  {count} {kind}  |  Total: {total}",
        "detail_track_header": "Track #{index}: {name}",
        "detail_duration": "Duration: {dur:.2f} s",
        "detail_source": "Source:    {path}",
        "detail_exists": "Exists:    {ans}",
        "yes": "Yes",
        "no": "No",
        "detail_subtrack": "Subtrack {index}:",
        "settings_title": "Settings – E-Stim Player",
        "settings_width": "Window Width (px):",
        "settings_height": "Window Height (px):",
        "settings_last_dir": "Last Directory:",
        "settings_master_vol": "Master Volume (%):",
        "settings_export_vol": "Export Volume (%):",
        "settings_language": "Language:",
        "settings_file_info": "File: {path}",
        "settings_btn_current_size": "Current Size",
        "settings_btn_save": "Save",
        "settings_err_min_size": "Minimum size: 400 x 300 px",
        "settings_err_vol_range": "Master volume must be between 0 and 100%.",
        "settings_err_export_vol_range": "Export volume must be between 0 and 200% (or empty).",
        "settings_err_invalid_int": "Please enter valid integer numbers.",
        "err_soundfile_missing": "The 'soundfile' package is not installed ('pip install soundfile').",
        "err_audio_not_found": "Audio file not found: {path}",
        "creator_title": "Session Creator / Editor",
        "creator_session_name": "Session Name:",
        "creator_creator": "Creator:",
        "creator_tracks": "Tracks",
        "creator_add_track": "+ Add Track",
        "creator_dup_track": "Duplicate",
        "creator_del_track": "Delete",
        "creator_track_name": "Track Name:",
        "creator_track_time": "Duration (s):",
        "creator_track_num": "Track #:",
        "creator_ch0": "Channel 0 (Left)",
        "creator_ch1": "Channel 1 (Right)",
        "creator_bf": "Base Freq (bf, Hz):",
        "creator_vol": "Volume (vol):",
        "creator_volc": "Vol Slope (volc):",
        "creator_ton": "Gate On (t_on, s):",
        "creator_toff": "Gate Off (t_off, s):",
        "creator_bfm_act": "BFM Active",
        "creator_bfm_mf": "BFM Mod Freq (mf):",
        "creator_bfm_md": "BFM Mod Depth (md):",
        "creator_pam_act": "PAM Active",
        "creator_pam_mf": "PAM Mod Freq (mf):",
        "creator_pam_md": "PAM Mod Depth (md):",
        "creator_save_load": "Save .alass2 & Load",
        "creator_apply_only": "Load into Player",
        "creator_err_name": "Please enter a session name.",
    },
    "de": {
        "app_title": "E-Stim Player",
        "menu_file": "Datei",
        "menu_open_session": "Session öffnen...",
        "menu_create_session": "Session erstellen / bearbeiten...",
        "menu_export_track": "Aktuellen Track als .flac speichern...",
        "menu_export_all_tracks": "Alle Tracks als einzelne .flac speichern...",
        "menu_export_session": "Ganze Session als .flac speichern...",
        "menu_settings": "Einstellungen",
        "menu_about": "Info...",
        "menu_exit": "Beenden",
        "about_title": "Info – E-Stim Player",
        "about_heading": "E-Stim Player",
        "about_version": "Version {version}",
        "about_creator": "Creator: {creator}",
        "about_desc": "Desktop-Audio- und Session-Player für FLAC-, M3U-, XML- und ALASS2-S-Expression-Sessions.",
        "about_btn_close": "Schließen",
        "btn_open_session": "Session öffnen",
        "btn_create_session": "Session erstellen",
        "no_session_loaded": "Keine Session geladen",
        "btn_start": "▶ Start",
        "btn_pause": "⏸ Pause",
        "btn_stop": "⏹ Stop",
        "loop_off": "Aus",
        "loop_track": "Track",
        "loop_session": "Session",
        "tracks_label": "Tracks",
        "status_ready": "Bereit",
        "status_paused": "Pausiert",
        "status_stopped": "Gestoppt",
        "status_playback_started": "Wiedergabe gestartet",
        "status_session_finished": "Session beendet",
        "status_loop_mode": "Loop-Modus: {mode}",
        "status_loaded": "Geladen: {filename}",
        "status_load_error": "Fehler beim Laden: {error}",
        "status_settings_saved": "Einstellungen gespeichert in {path}",
        "status_seeking_track": "Spule in Track",
        "status_position_set": "Position gesetzt",
        "status_track_pos": "{prefix} {idx:02d}: {name}  ({cur:.1f}s / {dur:.1f}s){loop}",
        "status_playing_track": "Spiele Track {idx:02d}: {name}  ({cur:.1f}s / {dur:.1f}s){loop}",
        "status_loop_suffix": " [Loop: {mode}]",
        "status_export_running": "FLAC-Export läuft bereits...",
        "status_no_session_track": "Keine Session geladen – Track-Export nicht möglich.",
        "status_no_session_batch": "Keine Session geladen – Batch-Export nicht möglich.",
        "status_no_session_session": "Keine Session geladen – Session-Export nicht möglich.",
        "status_exporting_single": "Exportiere {label} als FLAC ({pct}%)...",
        "status_export_failed": "FLAC-Export fehlgeschlagen: {error}",
        "status_export_saved": "FLAC gespeichert: {filename} ({path})",
        "status_batch_start": "Exportiere 0/{total} Tracks ({pct}%) nach {dir}...",
        "status_batch_progress": "Exportiere {idx}/{total} ({pct}%): {filename}",
        "status_batch_failed": "Batch-Export fehlgeschlagen: {error}",
        "status_batch_done": "{total} Tracks als .flac gespeichert in: {dir}",
        "status_audio_error": "Audio-Fehler bei Track {idx}: {error} (sr={sr}, bs={bs}, vol={vol})",
        "export_vol_title": "FLAC-Export Lautstärke",
        "export_vol_prompt": "Export-Lautstärke in % (0–200%, Standard: {cur_pct}%):",
        "dialog_open_title": "Session oder FLAC öffnen",
        "filter_all_supported": "Sessions, FLAC & M3U",
        "filter_flac": "FLAC Audio",
        "filter_alass2": "ALASS2 Session",
        "filter_smartstim": "SmartStim Session",
        "filter_m3u": "M3U Playlist",
        "filter_all_files": "Alle Dateien",
        "dialog_save_track_title": "Track als FLAC speichern",
        "dialog_select_base_dir": "Basisordner für Session-Ordner auswählen",
        "dialog_save_session_title": "Ganze Session als FLAC speichern",
        "dialog_save_alass2_title": "Session speichern (.alass2)",
        "kind_playlist": "Playlist",
        "kind_tracks": "Tracks",
        "session_header": "{name}  |  {count} {kind}  |  Gesamt: {total}",
        "detail_track_header": "Track #{index}: {name}",
        "detail_duration": "Dauer: {dur:.2f} s",
        "detail_source": "Quelle:    {path}",
        "detail_exists": "Existiert: {ans}",
        "yes": "Ja",
        "no": "Nein",
        "detail_subtrack": "Subtrack {index}:",
        "settings_title": "Einstellungen – E-Stim Player",
        "settings_width": "Fensterbreite (px):",
        "settings_height": "Fensterhöhe (px):",
        "settings_last_dir": "Letzter Ordner:",
        "settings_master_vol": "Master-Volumen (%):",
        "settings_export_vol": "Export-Lautstärke (%):",
        "settings_language": "Sprache:",
        "settings_file_info": "Datei: {path}",
        "settings_btn_current_size": "Aktuelle Größe",
        "settings_btn_save": "Speichern",
        "settings_err_min_size": "Mindestgröße: 400 x 300 px",
        "settings_err_vol_range": "Master-Volumen muss zwischen 0 und 100 % liegen.",
        "settings_err_export_vol_range": "Export-Lautstärke muss zwischen 0 und 200 % liegen (oder leer sein).",
        "settings_err_invalid_int": "Bitte gültige Ganzzahlen eingeben.",
        "err_soundfile_missing": "Das Paket 'soundfile' ist nicht installiert ('pip install soundfile').",
        "err_audio_not_found": "Audio-Datei nicht gefunden: {path}",
        "creator_title": "Session-Ersteller / Editor",
        "creator_session_name": "Session-Name:",
        "creator_creator": "Ersteller:",
        "creator_tracks": "Tracks",
        "creator_add_track": "+ Track hinzufügen",
        "creator_dup_track": "Duplizieren",
        "creator_del_track": "Löschen",
        "creator_track_name": "Track-Name:",
        "creator_track_time": "Dauer (s):",
        "creator_track_num": "Track-Nr.:",
        "creator_ch0": "Kanal 0 (Links)",
        "creator_ch1": "Kanal 1 (Rechts)",
        "creator_bf": "Grundfrequenz (bf, Hz):",
        "creator_vol": "Lautstärke (vol):",
        "creator_volc": "Vol-Anstieg (volc):",
        "creator_ton": "Gate An (t_on, s):",
        "creator_toff": "Gate Aus (t_off, s):",
        "creator_bfm_act": "BFM aktiv",
        "creator_bfm_mf": "BFM Mod-Freq (mf):",
        "creator_bfm_md": "BFM Mod-Hub (md):",
        "creator_pam_act": "PAM aktiv",
        "creator_pam_mf": "PAM Mod-Freq (mf):",
        "creator_pam_md": "PAM Mod-Hub (md):",
        "creator_save_load": ".alass2 speichern & laden",
        "creator_apply_only": "In Player laden",
        "creator_err_name": "Bitte einen Session-Namen eingeben.",
    },
}


def tr_text(lang: str, key: str, **kwargs) -> str:
    table = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    template = table.get(key, TRANSLATIONS["en"].get(key, key))
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template


def _normalize_loop_key(raw: Any, default: str = "off") -> str:
    if not isinstance(raw, str):
        return default
    val = raw.strip().lower()
    if val in ("off", "aus"):
        return "off"
    if val == "track":
        return "track"
    if val == "session":
        return "session"
    return default


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None or isinstance(value, bool):
        return float(default)
    if isinstance(value, (int, float, np.number)):
        val = float(value)
        return val if np.isfinite(val) else float(default)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", ".")
        if not cleaned:
            return float(default)
        try:
            val = float(cleaned)
            return val if np.isfinite(val) else float(default)
        except ValueError:
            return float(default)
    return float(default)


def _to_int(value: Any, default: int = 0) -> int:
    return int(round(_to_float(value, float(default))))


def _to_float32_stereo(arr: Any, frames: int) -> np.ndarray:
    safe_frames = max(1, _to_int(frames, 1))
    try:
        a = np.array(arr, dtype=np.float32, copy=True)
    except Exception:
        return np.zeros((safe_frames, 2), dtype=np.float32)

    if a.size == 0:
        return np.zeros((safe_frames, 2), dtype=np.float32)
    if a.ndim == 1:
        a = np.repeat(a[:, None], 2, axis=1)
    elif a.shape[1] == 1:
        a = np.repeat(a, 2, axis=1)
    else:
        a = a[:, :2]

    if len(a) < safe_frames:
        pad = np.zeros((safe_frames - len(a), 2), dtype=np.float32)
        a = np.vstack((a, pad))
    elif len(a) > safe_frames:
        a = a[:safe_frames]

    a = np.nan_to_num(a, nan=0.0, posinf=1.0, neginf=-1.0)
    a = np.clip(a, -1.0, 1.0)
    return np.ascontiguousarray(a, dtype=np.float32)


def _apply_pan_stereo(stereo_arr: np.ndarray, pan: float) -> np.ndarray:
    """Applies stereo balance (-1.0 = left, 0.0 = center, +1.0 = right)."""
    p = max(-1.0, min(1.0, _to_float(pan, 0.0)))
    if len(stereo_arr) == 0 or abs(p) < 1e-6:
        return stereo_arr
    gain_l = 1.0 if p <= 0.0 else (1.0 - p)
    gain_r = 1.0 if p >= 0.0 else (1.0 + p)
    out = np.array(stereo_arr, dtype=np.float32, copy=True)
    out[:, 0] = np.clip(out[:, 0] * float(gain_l), -1.0, 1.0)
    out[:, 1] = np.clip(out[:, 1] * float(gain_r), -1.0, 1.0)
    return np.ascontiguousarray(out, dtype=np.float32)


def _apply_export_gain(stereo_arr: np.ndarray, gain: float) -> np.ndarray:
    """Applies an export gain factor to a stereo array with safe clipping."""
    g = max(0.0, _to_float(gain, 1.0))
    safe_len = max(1, len(stereo_arr))
    if len(stereo_arr) == 0 or abs(g - 1.0) < 1e-6:
        return _to_float32_stereo(stereo_arr, safe_len)
    out = np.array(stereo_arr, dtype=np.float32, copy=True) * np.float32(g)
    out = np.nan_to_num(out, nan=0.0, posinf=1.0, neginf=-1.0)
    out = np.clip(out, -1.0, 1.0)
    return np.ascontiguousarray(out, dtype=np.float32)


def _format_pan_label(pan: float) -> str:
    p = max(-1.0, min(1.0, _to_float(pan, 0.0)))
    pct = int(round(abs(p) * 100))
    if pct == 0:
        return "L/R: 0"
    if p < 0:
        return f"L: {pct}%"
    return f"R: {pct}%"


def _format_mm_ss(seconds: float) -> str:
    total_sec = max(0, int(round(_to_float(seconds, 0.0))))
    mins, secs = divmod(total_sec, 60)
    return f"{mins}:{secs:02d}"


def parse_german_float(value: Optional[str], default: float = 0.0) -> float:
    if value is None or str(value).strip() == "":
        return float(default)
    return _to_float(value, default)


def parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in ("true", "1", "yes", "t")


def sanitize_filename(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in (" ", "-", "_") else "_" for ch in name).strip()
    return cleaned or "export"


def get_session_export_dir(base_dir: str, session_name: str) -> str:
    root_dir = base_dir if os.path.isdir(base_dir) else os.path.expanduser("~")
    folder_name = sanitize_filename(session_name)
    session_dir = os.path.join(root_dir, folder_name)
    os.makedirs(session_dir, exist_ok=True)
    return session_dir


def get_settings_path() -> str:
    config_dir = os.path.join(os.path.expanduser("~"), ".config", "E-Stim")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "settings.json")


def load_settings(
    default_width: int = 900,
    default_height: int = 620,
    default_vol: float = 0.7,
    default_loop_mode: str = "off",
    default_last_session: Optional[str] = None,
    default_last_track_idx: int = 0,
    default_pan: float = 0.0,
    default_language: str = "en",
    default_export_vol_pct: Optional[int] = None,
    default_creator_width: int = 860,
    default_creator_height: int = 620,
) -> dict:
    norm_default_loop = _normalize_loop_key(default_loop_mode, "off")
    norm_default_lang = default_language if default_language in VALID_LANGUAGES else "en"
    c_w_def = max(740, _to_int(default_creator_width, 860))
    c_h_def = max(520, _to_int(default_creator_height, 620))
    fallback = {
        "window_width": default_width,
        "window_height": default_height,
        "last_dir": os.path.expanduser("~"),
        "master_vol": default_vol,
        "pan": max(-1.0, min(1.0, _to_float(default_pan, 0.0))),
        "loop_mode": norm_default_loop,
        "last_session": default_last_session,
        "last_track_idx": max(0, int(default_last_track_idx)),
        "language": norm_default_lang,
        "export_vol_pct": default_export_vol_pct,
        "creator_width": c_w_def,
        "creator_height": c_h_def,
    }
    path = get_settings_path()
    if not os.path.exists(path):
        return fallback
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        w = _to_int(data.get("window_width", default_width), default_width)
        h = _to_int(data.get("window_height", default_height), default_height)
        if w < 400 or h < 300:
            w, h = default_width, default_height
        c_w = _to_int(data.get("creator_width", c_w_def), c_w_def)
        c_h = _to_int(data.get("creator_height", c_h_def), c_h_def)
        if c_w < 740 or c_h < 520:
            c_w, c_h = c_w_def, c_h_def
        last_dir = data.get("last_dir") or os.path.expanduser("~")
        if not os.path.isdir(last_dir):
            last_dir = os.path.expanduser("~")
        vol = _to_float(data.get("master_vol", default_vol), default_vol)
        vol = max(0.0, min(1.0, vol))
        pan = max(-1.0, min(1.0, _to_float(data.get("pan", default_pan), default_pan)))
        loop_mode = _normalize_loop_key(data.get("loop_mode", norm_default_loop), norm_default_loop)
        raw_lang = str(data.get("language", norm_default_lang)).strip().lower()
        language = raw_lang if raw_lang in VALID_LANGUAGES else norm_default_lang
        raw_session = data.get("last_session", default_last_session)
        last_session: Optional[str] = None
        if isinstance(raw_session, str) and raw_session.strip():
            abs_sess = os.path.abspath(raw_session.strip())
            if os.path.isfile(abs_sess):
                last_session = abs_sess
        track_idx = max(0, _to_int(data.get("last_track_idx", default_last_track_idx), default_last_track_idx))
        raw_exp_pct = data.get("export_vol_pct", default_export_vol_pct)
        export_vol_pct: Optional[int] = None
        if raw_exp_pct is not None and not isinstance(raw_exp_pct, bool):
            export_vol_pct = max(0, min(200, _to_int(raw_exp_pct, 70)))
        return {
            "window_width": w,
            "window_height": h,
            "last_dir": last_dir,
            "master_vol": vol,
            "pan": pan,
            "loop_mode": loop_mode,
            "last_session": last_session,
            "last_track_idx": track_idx,
            "language": language,
            "export_vol_pct": export_vol_pct,
            "creator_width": c_w,
            "creator_height": c_h,
        }
    except Exception:
        return fallback


def save_settings(
    width: int,
    height: int,
    last_dir: str,
    master_vol: float,
    loop_mode: str = "off",
    last_session: Optional[str] = None,
    last_track_idx: int = 0,
    pan: float = 0.0,
    language: str = "en",
    export_vol_pct: Optional[int] = None,
    creator_width: int = 860,
    creator_height: int = 620,
) -> str:
    path = get_settings_path()
    valid_mode = _normalize_loop_key(loop_mode, "off")
    valid_lang = language if language in VALID_LANGUAGES else "en"
    session_val = os.path.abspath(last_session) if last_session else None
    safe_vol = max(0.0, min(1.0, _to_float(master_vol, 0.7)))
    safe_pan = max(-1.0, min(1.0, _to_float(pan, 0.0)))
    safe_cw = max(740, _to_int(creator_width, 860))
    safe_ch = max(520, _to_int(creator_height, 620))
    exp_pct_val: Optional[int] = (
        max(0, min(200, _to_int(export_vol_pct, 70)))
        if (export_vol_pct is not None and not isinstance(export_vol_pct, bool))
        else None
    )
    payload = {
        "window_width": _to_int(width, 900),
        "window_height": _to_int(height, 620),
        "last_dir": str(last_dir),
        "master_vol": round(safe_vol, 4),
        "pan": round(safe_pan, 4),
        "loop_mode": valid_mode,
        "last_session": session_val,
        "last_track_idx": max(0, _to_int(last_track_idx, 0)),
        "language": valid_lang,
        "export_vol_pct": exp_pct_val,
        "creator_width": safe_cw,
        "creator_height": safe_ch,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path


@dataclass
class SubtrackConfig:
    index: int
    bf: Optional[float] = None
    vol: float = 0.0
    vol_c: float = 0.0
    t_on: Optional[float] = None
    t_off: Optional[float] = None
    t_att: float = 0.0
    bfm_act: bool = False
    bfm_mf: float = 0.0
    bfm_md: float = 0.0
    pam_act: bool = False
    pam_mf: float = 0.0
    pam_md: float = 0.0


@dataclass
class TrackConfig:
    index: int
    name: str
    duration: float
    subtracks: List[SubtrackConfig] = field(default_factory=list)
    audio_path: Optional[str] = None


@dataclass
class SessionConfig:
    name: str
    channels: int
    tracks: List[TrackConfig]
    is_playlist: bool = False
    creator: str = "SmartStim"
    creation: str = ""
    modification: str = ""


def _fmt_num(val: float) -> str:
    if abs(val - round(val)) < 1e-9:
        return str(int(round(val)))
    return f"{val:.6f}".rstrip("0").rstrip(".")


def _escape_sexp_str(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def format_sexp_session(session: SessionConfig) -> str:
    """Serializes a SessionConfig into S-Expression format (:Session_name, :Track_name, :CHANNELS ...)."""
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")
    creator_str = session.creator.strip() or "SmartStim"
    creation_str = session.creation.strip() or now_str
    mod_str = now_str

    header = (
        f'(:Session_name "{_escape_sexp_str(session.name)}" '
        f':Creator "{_escape_sexp_str(creator_str)}" '
        f':Creation "{_escape_sexp_str(creation_str)}" '
        f':Modification "{_escape_sexp_str(mod_str)}" )'
    )
    parts: List[str] = [header]

    for pos, tr in enumerate(session.tracks):
        t_num = _to_int(tr.index, pos + 1)
        t_dur = max(0.05, _to_float(tr.duration, 1.0))
        ch_blocks: List[str] = []
        sub_list = tr.subtracks if tr.subtracks else [
            SubtrackConfig(index=0, bf=280.0, vol=0.8),
            SubtrackConfig(index=1, bf=280.0, vol=0.8),
        ]
        for s_pos, st in enumerate(sub_list):
            ch_idx = _to_int(st.index, s_pos)
            lines = [f"(:CHANNEL {ch_idx}"]
            if st.bf is not None:
                lines.append(f"  :bf {_fmt_num(_to_float(st.bf, 0.0))}")
            raw_vol = _to_float(st.vol, 0.0)
            vol_sexp = raw_vol * 100.0 if 0.0 < raw_vol <= 1.0 else raw_vol
            lines.append(f"  :vol {_fmt_num(vol_sexp)}")
            if abs(_to_float(st.vol_c, 0.0)) > 1e-9:
                lines.append(f"  :volc {_fmt_num(_to_float(st.vol_c, 0.0))}")
            if st.t_on is not None and _to_float(st.t_on, 0.0) > 0.0:
                lines.append(f"  :t_on {_fmt_num(_to_float(st.t_on, 0.0))}")
            if st.t_off is not None and _to_float(st.t_off, 0.0) > 0.0:
                lines.append(f"  :t_off {_fmt_num(_to_float(st.t_off, 0.0))}")
            if abs(_to_float(st.t_att, 0.0)) > 1e-9:
                lines.append(f"  :t_att {_fmt_num(_to_float(st.t_att, 0.0))}")
            if st.bfm_act:
                lines.append(
                    f"  :bfm_act T  :bfm_mf {_fmt_num(_to_float(st.bfm_mf, 0.0))} "
                    f":bfm_md {_fmt_num(_to_float(st.bfm_md, 0.0))}"
                )
            if st.pam_act:
                lines.append(
                    f"  :pam_act T  :pam_mf {_fmt_num(_to_float(st.pam_mf, 0.0))} "
                    f":pam_md {_fmt_num(_to_float(st.pam_md, 0.0))}"
                )
            lines.append(")")
            ch_blocks.append("\n".join(lines))

        track_block = (
            f'(:Track_name "{_escape_sexp_str(tr.name)}"  '
            f':Track_time {_fmt_num(t_dur)}  '
            f':Track_number {t_num}  :CHANNELS\n'
            f'(({chr(10).join(ch_blocks)}\n)))'
        )
        parts.append(track_block)

    return "\n".join(parts) + "\n"


def save_sexp_session(filepath: str, session: SessionConfig) -> str:
    abs_fp = os.path.abspath(filepath)
    if not os.path.splitext(abs_fp)[1]:
        abs_fp += ".alass2"
    os.makedirs(os.path.dirname(abs_fp), exist_ok=True)
    content = format_sexp_session(session)
    with open(abs_fp, "w", encoding="utf-8") as f:
        f.write(content)
    return abs_fp


def probe_audio_duration(filepath: str) -> float:
    if not os.path.isfile(filepath):
        return 0.05
    if sf is not None:
        try:
            info = sf.info(filepath)
            if info.samplerate and info.samplerate > 0:
                return max(0.05, float(info.frames) / float(info.samplerate))
        except Exception:
            pass
    return 0.05


def load_single_audio_file(filepath: str) -> SessionConfig:
    """Loads a single audio file (e.g. .flac) as a one-track session."""
    abs_fp = os.path.abspath(filepath)
    title = os.path.splitext(os.path.basename(abs_fp))[0] or "Audio"
    duration = probe_audio_duration(abs_fp)
    channels = 2
    if sf is not None:
        try:
            info = sf.info(abs_fp)
            if info.channels and info.channels > 0:
                channels = min(2, int(info.channels))
        except Exception:
            pass

    track = TrackConfig(
        index=0,
        name=title,
        duration=max(0.05, _to_float(duration, 0.05)),
        subtracks=[],
        audio_path=abs_fp,
    )
    return SessionConfig(
        name=title,
        channels=max(1, channels),
        tracks=[track],
        is_playlist=False,
    )


def load_session_xml(filepath: str) -> SessionConfig:
    tree = ET.parse(filepath)
    root = tree.getroot()

    session_name = root.attrib.get("Name", os.path.basename(filepath))
    channels = _to_int(root.attrib.get("Channels", "2"), 2)
    tracks: List[TrackConfig] = []

    tracks_elem = root.find("Tracks")
    if tracks_elem is not None:
        for t_elem in tracks_elem.findall("Track"):
            t_name = t_elem.attrib.get("Name", "Untitled")
            t_time = parse_german_float(t_elem.attrib.get("Time"), 1.0)
            t_index = _to_int(t_elem.attrib.get("Index", len(tracks)), len(tracks))

            subtracks: List[SubtrackConfig] = []
            subtracks_elem = t_elem.find("Subtracks")
            if subtracks_elem is not None:
                for s_elem in subtracks_elem.findall("Subtrack"):
                    s_idx = _to_int(s_elem.attrib.get("Index", len(subtracks)), len(subtracks))

                    def get_tag(tag_name: str) -> Optional[str]:
                        el = s_elem.find(tag_name)
                        return el.attrib.get("V") if el is not None else None

                    bf_raw = get_tag("BF")
                    bf_val = parse_german_float(bf_raw) if bf_raw is not None else None

                    ton_raw = get_tag("TOn")
                    ton_val = parse_german_float(ton_raw) if ton_raw is not None else None

                    toff_raw = get_tag("TOff")
                    toff_val = parse_german_float(toff_raw) if toff_raw is not None else None

                    subtracks.append(
                        SubtrackConfig(
                            index=s_idx,
                            bf=bf_val,
                            vol=parse_german_float(get_tag("Vol"), 0.0),
                            vol_c=parse_german_float(get_tag("VolC"), 0.0),
                            t_on=ton_val,
                            t_off=toff_val,
                            t_att=parse_german_float(get_tag("TAtt"), 0.0),
                            bfm_act=parse_bool(get_tag("BFM_Act"), False),
                            bfm_mf=parse_german_float(get_tag("BFM_MF"), 0.0),
                            bfm_md=parse_german_float(get_tag("BFM_MD"), 0.0),
                            pam_act=parse_bool(get_tag("PAM_Act"), False),
                            pam_mf=parse_german_float(get_tag("PAM_MF"), 0.0),
                            pam_md=parse_german_float(get_tag("PAM_MD"), 0.0),
                        )
                    )

            tracks.append(
                TrackConfig(
                    index=t_index,
                    name=t_name,
                    duration=max(0.05, t_time),
                    subtracks=subtracks,
                )
            )

    return SessionConfig(
        name=session_name,
        channels=max(1, channels),
        tracks=tracks,
        is_playlist=False,
    )


_SEXP_TOKEN_RE = re.compile(r'\s*(;[^\n]*|[\(\)]|:[A-Za-z0-9_]+|"(?:\\.|[^"\\])*"|[^\s\(\)]+)\s*')


def _tokenize_sexp(text: str) -> List[str]:
    tokens: List[str] = []
    pos = 0
    n = len(text)
    while pos < n:
        m = _SEXP_TOKEN_RE.match(text, pos)
        if not m:
            pos += 1
            continue
        tok = m.group(1)
        pos = m.end()
        if tok.startswith(";"):
            continue
        tokens.append(tok)
    return tokens


def _parse_sexp_forms(tokens: List[str]) -> List[Any]:
    idx = 0
    n = len(tokens)

    def _parse_one() -> Any:
        nonlocal idx
        if idx >= n:
            return None
        tok = tokens[idx]
        if tok == "(":
            idx += 1
            items: List[Any] = []
            while idx < n and tokens[idx] != ")":
                items.append(_parse_one())
            if idx < n and tokens[idx] == ")":
                idx += 1
            return items
        if tok == ")":
            idx += 1
            return None
        idx += 1
        if tok.startswith('"') and tok.endswith('"') and len(tok) >= 2:
            return tok[1:-1]
        if tok.startswith(":"):
            return tok.lower()
        return tok

    forms: List[Any] = []
    while idx < n:
        val = _parse_one()
        if val is not None:
            forms.append(val)
    return forms


def _plist_to_dict(items: List[Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    i = 0
    while i < len(items):
        key = items[i]
        if isinstance(key, str) and key.startswith(":"):
            if i + 1 < len(items) and not (isinstance(items[i + 1], str) and items[i + 1].startswith(":")):
                out[key] = items[i + 1]
                i += 2
            else:
                out[key] = True
                i += 1
        else:
            i += 1
    return out


def load_sexp_session(filepath: str) -> SessionConfig:
    """Loads an S-Expression session (.alass2 / :Session_name, :Track_name, :CHANNELS, :CHANNEL ...)."""
    with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
        raw_text = f.read()

    forms = _parse_sexp_forms(_tokenize_sexp(raw_text))
    session_name = os.path.basename(filepath)
    creator = "SmartStim"
    creation = ""
    modification = ""
    tracks: List[TrackConfig] = []
    max_channels = 2

    for form in forms:
        if not isinstance(form, list) or not form:
            continue
        plist = _plist_to_dict(form)

        if ":session_name" in plist:
            session_name = str(plist[":session_name"])
            if ":creator" in plist:
                creator = str(plist[":creator"])
            if ":creation" in plist:
                creation = str(plist[":creation"])
            if ":modification" in plist:
                modification = str(plist[":modification"])
            continue

        if ":track_name" in plist or ":channels" in plist or ":track_time" in plist:
            t_name = str(plist.get(":track_name", f"Track {len(tracks)}"))
            t_time = _to_float(plist.get(":track_time", 1.0), 1.0)
            t_index = _to_int(plist.get(":track_number", len(tracks)), len(tracks))

            subtracks: List[SubtrackConfig] = []
            ch_list = plist.get(":channels")
            if isinstance(ch_list, list):
                if len(ch_list) == 1 and isinstance(ch_list[0], list) and ch_list[0] and isinstance(ch_list[0][0], list):
                    channel_forms = ch_list[0]
                else:
                    channel_forms = ch_list

                for s_pos, ch_form in enumerate(channel_forms):
                    if not isinstance(ch_form, list):
                        continue
                    ch_plist = _plist_to_dict(ch_form)
                    s_idx = _to_int(ch_plist.get(":channel", s_pos), s_pos)

                    bf_raw = ch_plist.get(":bf")
                    bf_val = _to_float(bf_raw, 0.0) if bf_raw is not None else None

                    ton_raw = ch_plist.get(":t_on")
                    ton_val = _to_float(ton_raw, 0.0) if ton_raw is not None else None

                    toff_raw = ch_plist.get(":t_off")
                    toff_val = _to_float(toff_raw, 0.0) if toff_raw is not None else None

                    vol_c_val = _to_float(ch_plist.get(":volc", 0.0), 0.0)
                    if ":vol" in ch_plist:
                        vol_val = _to_float(ch_plist.get(":vol"), 0.0)
                    elif vol_c_val != 0.0:
                        vol_val = 0.5
                    else:
                        vol_val = 0.0

                    subtracks.append(
                        SubtrackConfig(
                            index=s_idx,
                            bf=bf_val,
                            vol=vol_val,
                            vol_c=vol_c_val,
                            t_on=ton_val,
                            t_off=toff_val,
                            t_att=_to_float(ch_plist.get(":t_att", 0.0), 0.0),
                            bfm_act=parse_bool(ch_plist.get(":bfm_act", False), False),
                            bfm_mf=_to_float(ch_plist.get(":bfm_mf", 0.0), 0.0),
                            bfm_md=_to_float(ch_plist.get(":bfm_md", 0.0), 0.0),
                            pam_act=parse_bool(ch_plist.get(":pam_act", False), False),
                            pam_mf=_to_float(ch_plist.get(":pam_mf", 0.0), 0.0),
                            pam_md=_to_float(ch_plist.get(":pam_md", 0.0), 0.0),
                        )
                    )

            if subtracks:
                max_channels = max(max_channels, len(subtracks))

            tracks.append(
                TrackConfig(
                    index=t_index,
                    name=t_name,
                    duration=max(0.05, t_time),
                    subtracks=subtracks,
                )
            )

    return SessionConfig(
        name=session_name,
        channels=max_channels,
        tracks=tracks,
        is_playlist=False,
        creator=creator,
        creation=creation,
        modification=modification,
    )


def load_session_or_playlist(filepath: str) -> SessionConfig:
    ext = os.path.splitext(filepath)[1].lower()
    if ext in AUDIO_FILE_EXTENSIONS:
        return load_single_audio_file(filepath)
    if ext in (".m3u", ".m3u8"):
        return load_m3u_playlist(filepath)
    if ext in (".alass2", ".seq", ".sexp", ".lisp", ".lsp"):
        return load_sexp_session(filepath)
    try:
        with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
            head = f.read(256).lstrip()
        if head.startswith("(") and ":session_name" in head.lower():
            return load_sexp_session(filepath)
    except Exception:
        pass
    return load_session_xml(filepath)


def load_m3u_playlist(filepath: str) -> SessionConfig:
    """Loads an .m3u / .m3u8 playlist as a SessionConfig with external audio files."""
    abs_m3u = os.path.abspath(filepath)
    base_dir = os.path.dirname(abs_m3u)
    playlist_name = os.path.splitext(os.path.basename(abs_m3u))[0] or "Playlist"

    with open(abs_m3u, "r", encoding="utf-8-sig", errors="replace") as f:
        lines = [line.strip() for line in f]

    tracks: List[TrackConfig] = []
    pending_title: Optional[str] = None
    pending_duration: Optional[float] = None

    for raw_line in lines:
        if not raw_line:
            continue
        if raw_line.startswith("#EXTINF:"):
            meta = raw_line[len("#EXTINF:") :]
            parts = meta.split(",", 1)
            try:
                sec = _to_float(parts[0].strip().split()[0], 0.0)
                if sec > 0:
                    pending_duration = sec
            except (ValueError, IndexError):
                pending_duration = None
            if len(parts) == 2 and parts[1].strip():
                pending_title = parts[1].strip()
            continue
        if raw_line.startswith("#"):
            continue

        entry_path = raw_line
        if not os.path.isabs(entry_path):
            entry_path = os.path.normpath(os.path.join(base_dir, entry_path))

        probed_dur = probe_audio_duration(entry_path)
        duration = pending_duration if (pending_duration and pending_duration > 0) else probed_dur
        title = pending_title or os.path.splitext(os.path.basename(entry_path))[0] or f"Track {len(tracks)}"

        tracks.append(
            TrackConfig(
                index=len(tracks),
                name=title,
                duration=max(0.05, _to_float(duration, 0.05)),
                subtracks=[],
                audio_path=entry_path,
            )
        )
        pending_title = None
        pending_duration = None

    return SessionConfig(
        name=playlist_name,
        channels=2,
        tracks=tracks,
        is_playlist=True,
    )


class AudioFileClip:
    """Streams audio files (FLAC/WAV/OGG via soundfile) in blocks for fast startup."""

    def __init__(self, filepath: str, target_sample_rate: int = DEFAULT_SAMPLE_RATE, lang: str = "en"):
        if sf is None:
            raise RuntimeError(tr_text(lang, "err_soundfile_missing"))
        if not os.path.isfile(filepath):
            raise FileNotFoundError(tr_text(lang, "err_audio_not_found", path=filepath))

        self.is_flac = filepath.lower().endswith(".flac")
        self.target_sample_rate = max(8000, _to_int(target_sample_rate, DEFAULT_SAMPLE_RATE))
        self._file = sf.SoundFile(filepath, mode="r")
        self.source_sample_rate = (
            max(1, _to_int(self._file.samplerate, self.target_sample_rate))
            if self._file.samplerate
            else self.target_sample_rate
        )
        self.channels = int(self._file.channels) if self._file.channels else 1
        self.total_source_frames = int(len(self._file))
        self.duration = max(0.05, self.total_source_frames / float(max(1, self.source_sample_rate)))
        self.total_frames = max(1, int(round(self.duration * self.target_sample_rate)))
        self._source_cursor = 0

    @property
    def cursor(self) -> int:
        if self.source_sample_rate == self.target_sample_rate:
            return self._source_cursor
        return min(
            self.total_frames,
            int(round(self._source_cursor * self.target_sample_rate / max(1, self.source_sample_rate))),
        )

    def seek_to(self, time_sec: float):
        clamped_t = max(0.0, min(_to_float(time_sec, 0.0), self.duration))
        src_frame = min(self.total_source_frames, int(round(clamped_t * self.source_sample_rate)))
        self._source_cursor = src_frame
        self._file.seek(src_frame)

    @property
    def elapsed_sec(self) -> float:
        return self._source_cursor / float(max(1, self.source_sample_rate))

    def _to_stereo(self, chunk: np.ndarray) -> np.ndarray:
        if chunk.size == 0:
            return np.zeros((0, 2), dtype=np.float32)
        if chunk.ndim == 1:
            chunk = chunk[:, None]
        if chunk.shape[1] == 1:
            return np.repeat(chunk, 2, axis=1).astype(np.float32)
        return chunk[:, :2].astype(np.float32)

    def _resample_block(self, stereo_chunk: np.ndarray, expected_frames: int) -> np.ndarray:
        if len(stereo_chunk) == 0:
            return np.zeros((0, 2), dtype=np.float32)
        if self.source_sample_rate == self.target_sample_rate:
            return stereo_chunk

        src_len = len(stereo_chunk)
        dst_len = max(1, int(round(src_len * self.target_sample_rate / max(1, self.source_sample_rate))))
        dst_len = min(dst_len, expected_frames)
        old_idx = np.linspace(0.0, src_len - 1, num=src_len, dtype=np.float64)
        new_idx = np.linspace(0.0, src_len - 1, num=dst_len, dtype=np.float64)
        left = np.interp(new_idx, old_idx, stereo_chunk[:, 0]).astype(np.float32)
        right = np.interp(new_idx, old_idx, stereo_chunk[:, 1]).astype(np.float32)
        return np.column_stack((left, right))

    def read_block(self, frames: int, master_vol: float) -> tuple[np.ndarray, np.ndarray]:
        safe_frames = max(1, _to_int(frames, 1))
        safe_vol = _to_float(master_vol, 0.7)
        if self.source_sample_rate == self.target_sample_rate:
            src_to_read = safe_frames
        else:
            src_to_read = max(1, int(np.ceil(safe_frames * self.source_sample_rate / max(1, self.source_sample_rate))))

        raw_chunk = self._file.read(src_to_read, dtype="float32", always_2d=True)
        self._source_cursor = min(self.total_source_frames, int(self._file.tell()))

        stereo_chunk = self._to_stereo(raw_chunk)
        resampled = self._resample_block(stereo_chunk, safe_frames)

        if len(resampled) < safe_frames:
            pad = np.zeros((safe_frames - len(resampled), 2), dtype=np.float32)
            raw_out = np.vstack((resampled, pad))
        else:
            raw_out = resampled[:safe_frames]

        raw_out = _to_float32_stereo(raw_out, safe_frames)
        scaled_out = _to_float32_stereo(raw_out * safe_vol, safe_frames)
        return scaled_out, raw_out

    def close(self):
        try:
            self._file.close()
        except Exception:
            pass

    def __del__(self):
        self.close()


class SmartStimSynthesizer:
    """Synthesizes a track chunk in real time for stereo/multichannel output."""

    def __init__(self, sample_rate: int = DEFAULT_SAMPLE_RATE):
        self.sample_rate = max(8000, _to_int(sample_rate, DEFAULT_SAMPLE_RATE))
        self.phases: List[float] = []
        self.bfm_phases: List[float] = []
        self.pam_phases: List[float] = []
        self.elapsed_in_track: float = 0.0

    def reset_for_track(self, num_channels: int):
        ch_count = max(1, _to_int(num_channels, 2))
        self.phases = [0.0] * ch_count
        self.bfm_phases = [0.0] * ch_count
        self.pam_phases = [0.0] * ch_count
        self.elapsed_in_track = 0.0

    def continue_for_track(self, num_channels: int, carry_sec: float = 0.0):
        """Carries phases and timeline across a gapless track transition."""
        ch_count = max(1, _to_int(num_channels, 2))
        if len(self.phases) != ch_count:
            self.phases = (self.phases + [0.0] * ch_count)[:ch_count]
            self.bfm_phases = (self.bfm_phases + [0.0] * ch_count)[:ch_count]
            self.pam_phases = (self.pam_phases + [0.0] * ch_count)[:ch_count]
        self.elapsed_in_track = max(0.0, _to_float(carry_sec, 0.0))

    def seek_to(self, time_sec: float, track: TrackConfig):
        """Sets track time and modulator/carrier phases consistently to time_sec."""
        dur = max(0.05, _to_float(track.duration, 0.05))
        clamped_t = max(0.0, min(_to_float(time_sec, 0.0), dur))
        num_channels = max(2, len(track.subtracks))
        self.phases = [0.0] * num_channels
        self.bfm_phases = [0.0] * num_channels
        self.pam_phases = [0.0] * num_channels
        self.elapsed_in_track = clamped_t

        for ch in range(num_channels):
            if ch >= len(track.subtracks):
                continue
            st = track.subtracks[ch]
            base_freq = _to_float(st.bf, 0.0) if st.bf is not None else 0.0
            bfm_mf = _to_float(st.bfm_mf, 0.0)
            bfm_md = _to_float(st.bfm_md, 0.0)
            pam_mf = _to_float(st.pam_mf, 0.0)

            if st.bfm_act and bfm_mf > 0.0:
                self.bfm_phases[ch] = float(np.mod(2.0 * np.pi * bfm_mf * clamped_t, 2.0 * np.pi))
                mod_integral = base_freq * clamped_t
                if bfm_md != 0.0:
                    mod_integral += (bfm_md / (2.0 * np.pi * bfm_mf)) * (
                        1.0 - np.cos(2.0 * np.pi * bfm_mf * clamped_t)
                    )
                self.phases[ch] = float(np.mod(2.0 * np.pi * mod_integral, 2.0 * np.pi))
            else:
                self.phases[ch] = float(np.mod(2.0 * np.pi * max(0.0, base_freq) * clamped_t, 2.0 * np.pi))

            if st.pam_act and pam_mf > 0.0:
                self.pam_phases[ch] = float(np.mod(2.0 * np.pi * pam_mf * clamped_t, 2.0 * np.pi))

    def render_block(
        self, track: TrackConfig, frames: int, master_vol: float
    ) -> tuple[np.ndarray, np.ndarray]:
        """Returns (output_audio_with_master_vol, unscaled_signal_for_meter)."""
        safe_frames = max(1, _to_int(frames, 1))
        safe_vol = _to_float(master_vol, 0.7)
        out_channels = max(2, len(track.subtracks))
        raw_output = np.zeros((safe_frames, out_channels), dtype=np.float32)

        t_arr = self.elapsed_in_track + np.arange(safe_frames, dtype=np.float64) / self.sample_rate

        for ch in range(out_channels):
            if ch >= len(track.subtracks):
                continue
            st = track.subtracks[ch]
            st_vol = _to_float(st.vol, 0.0)
            st_vol_c = _to_float(st.vol_c, 0.0)
            vol_arr = np.clip(st_vol + st_vol_c * t_arr, 0.0, 1.0)

            gate = np.ones(safe_frames, dtype=np.float64)
            t_on_val = _to_float(st.t_on, 0.0) if st.t_on is not None else 0.0
            if t_on_val > 0.0:
                t_off_val = _to_float(st.t_off, 0.0) if st.t_off is not None else 0.0
                period = t_on_val + t_off_val
                if period > 0.0:
                    cycle_pos = np.mod(t_arr, period)
                    gate = np.where(cycle_pos <= t_on_val, 1.0, 0.0)

            base_freq = _to_float(st.bf, 0.0) if st.bf is not None else 0.0
            bfm_mf = _to_float(st.bfm_mf, 0.0)
            bfm_md = _to_float(st.bfm_md, 0.0)
            if st.bfm_act and bfm_mf > 0.0:
                bfm_inc = 2.0 * np.pi * bfm_mf / self.sample_rate
                bfm_phase_arr = self.bfm_phases[ch] + np.arange(safe_frames, dtype=np.float64) * bfm_inc
                self.bfm_phases[ch] = float(np.mod(bfm_phase_arr[-1] + bfm_inc, 2.0 * np.pi))
                mod_freq = np.maximum(0.0, base_freq + bfm_md * np.sin(bfm_phase_arr))
            else:
                mod_freq = np.full(safe_frames, max(0.0, base_freq), dtype=np.float64)

            has_carrier = bool(np.any(mod_freq > 0.0))
            if has_carrier:
                phase_incs = 2.0 * np.pi * mod_freq / self.sample_rate
                phase_arr = self.phases[ch] + np.cumsum(phase_incs)
                self.phases[ch] = float(np.mod(phase_arr[-1], 2.0 * np.pi))
                carrier = np.sin(phase_arr)
            else:
                carrier = np.zeros(safe_frames, dtype=np.float64)

            pam_mf = _to_float(st.pam_mf, 0.0)
            pam_md = _to_float(st.pam_md, 0.0)
            if st.pam_act and pam_mf > 0.0:
                pam_inc = 2.0 * np.pi * pam_mf / self.sample_rate
                pam_phase_arr = self.pam_phases[ch] + np.arange(safe_frames, dtype=np.float64) * pam_inc
                self.pam_phases[ch] = float(np.mod(pam_phase_arr[-1] + pam_inc, 2.0 * np.pi))
                pam_lfo = 0.5 * (1.0 + np.sin(pam_phase_arr))
                depth = abs(pam_md) / 100.0
                if pam_md < 0.0:
                    pam_gain = 1.0 - depth * pam_lfo
                else:
                    pam_gain = 1.0 - depth * (1.0 - pam_lfo)

                if not np.any(carrier != 0.0):
                    carrier = (pam_lfo - 0.5) * 0.4
                else:
                    carrier = carrier * pam_gain

            raw_signal = carrier * gate * vol_arr * 0.25
            raw_output[:, ch] = _to_float32_stereo(np.column_stack((raw_signal, raw_signal)), safe_frames)[:, 0]

        clean_raw = _to_float32_stereo(raw_output, safe_frames)
        clean_scaled = _to_float32_stereo(clean_raw * safe_vol, safe_frames)
        self.elapsed_in_track += safe_frames / self.sample_rate
        return clean_scaled, clean_raw


def render_tracks_stereo(
    tracks: List[TrackConfig],
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    master_vol: float = 0.7,
    pan: float = 0.0,
    lang: str = "en",
    export_gain: float = 1.0,
) -> np.ndarray:
    """Renders a list of tracks in stereo (float32, N x 2) with optional export gain."""
    safe_sr = max(8000, _to_int(sample_rate, DEFAULT_SAMPLE_RATE))
    safe_vol = max(0.0, min(1.0, _to_float(master_vol, 0.7)))
    safe_pan = max(-1.0, min(1.0, _to_float(pan, 0.0)))
    safe_gain = max(0.0, _to_float(export_gain, 1.0))
    synth = SmartStimSynthesizer(sample_rate=safe_sr)
    chunks: List[np.ndarray] = []

    for track in tracks:
        if track.audio_path:
            clip = AudioFileClip(track.audio_path, target_sample_rate=safe_sr, lang=lang)
            try:
                rendered = 0
                while rendered < clip.total_frames:
                    n = min(BLOCKSIZE, clip.total_frames - rendered)
                    scaled_audio, _ = clip.read_block(n, safe_vol)
                    stereo_blk = _apply_pan_stereo(_to_float32_stereo(scaled_audio, n), safe_pan)
                    chunks.append(_apply_export_gain(stereo_blk, safe_gain))
                    rendered += n
            finally:
                clip.close()
            continue

        dur = max(0.05, _to_float(track.duration, 0.05))
        total_frames = max(1, int(round(dur * safe_sr)))
        synth.reset_for_track(max(2, len(track.subtracks)))
        rendered = 0
        while rendered < total_frames:
            n = min(BLOCKSIZE, total_frames - rendered)
            scaled_audio, _ = synth.render_block(track, n, safe_vol)
            stereo_blk = _apply_pan_stereo(_to_float32_stereo(scaled_audio, n), safe_pan)
            chunks.append(_apply_export_gain(stereo_blk, safe_gain))
            rendered += n

    if not chunks:
        return np.zeros((1, 2), dtype=np.float32)
    return np.ascontiguousarray(np.vstack(chunks), dtype=np.float32)


def write_flac_file(filepath: str, audio: np.ndarray, sample_rate: int = DEFAULT_SAMPLE_RATE, lang: str = "en"):
    """Writes stereo audio as a .flac file (via soundfile)."""
    if sf is None:
        raise RuntimeError(tr_text(lang, "err_soundfile_missing"))
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    sf.write(filepath, audio, max(8000, _to_int(sample_rate, DEFAULT_SAMPLE_RATE)), format="FLAC", subtype="PCM_24")


class CenterBalanceSlider(ctk.CTkCanvas):
    """Balance slider (-1.0 to +1.0) whose active highlight expands from center (0.0) to L or R."""

    def __init__(
        self,
        master,
        from_: float = -1.0,
        to: float = 1.0,
        width: int = 120,
        height: int = 20,
        command=None,
        track_color: str = "#3a3f47",
        active_color: str = "#3b8ed0",
        thumb_color: str = "#dce4ee",
        thumb_hover_color: str = "#ffffff",
        **kwargs,
    ):
        bg_color = kwargs.pop("bg", None) or kwargs.pop("fg_color", None)
        if bg_color is None:
            parent_bg = master.cget("fg_color")
            if isinstance(parent_bg, (list, tuple)):
                bg_color = parent_bg[1] if len(parent_bg) > 1 else parent_bg[0]
            else:
                bg_color = parent_bg or "#2b2b2b"

        super().__init__(
            master,
            width=width,
            height=height,
            bg=bg_color,
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.from_val = float(from_)
        self.to_val = float(to)
        self.command = command
        self.track_color = track_color
        self.active_color = active_color
        self.thumb_color = thumb_color
        self.thumb_hover_color = thumb_hover_color
        self._hover = False
        self._dragging = False
        self._value = 0.0

        self.bind("<Configure>", lambda _e: self._redraw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, _event):
        self._hover = True
        self._redraw()

    def _on_leave(self, _event):
        self._hover = False
        self._redraw()

    def _x_to_val(self, x: float) -> float:
        w = max(1, self.winfo_width())
        pad = 8.0
        usable = max(1.0, w - 2.0 * pad)
        ratio = max(0.0, min(1.0, (float(x) - pad) / usable))
        return self.from_val + ratio * (self.to_val - self.from_val)

    def _val_to_x(self, val: float) -> float:
        w = max(1, self.winfo_width())
        pad = 8.0
        usable = max(1.0, w - 2.0 * pad)
        span = self.to_val - self.from_val
        ratio = 0.5 if abs(span) < 1e-9 else (float(val) - self.from_val) / span
        ratio = max(0.0, min(1.0, ratio))
        return pad + ratio * usable

    def set(self, value: float):
        clamped = max(self.from_val, min(self.to_val, _to_float(value, 0.0)))
        self._value = clamped
        self._redraw()

    def get(self) -> float:
        return self._value

    def _on_press(self, event):
        self._dragging = True
        new_val = self._x_to_val(event.x)
        self.set(new_val)
        if callable(self.command):
            self.command(self._value)

    def _on_drag(self, event):
        if not self._dragging:
            return
        new_val = self._x_to_val(event.x)
        self.set(new_val)
        if callable(self.command):
            self.command(self._value)

    def _on_release(self, event):
        self._dragging = False
        self.event_generate("<ButtonRelease-1>", x=event.x, y=event.y)

    @staticmethod
    def _round_rect_coords(x1: float, y1: float, x2: float, y2: float, r: float):
        r = max(0.0, min(r, abs(x2 - x1) / 2.0, abs(y2 - y1) / 2.0))
        if r <= 0.5:
            return [x1, y1, x2, y1, x2, y2, x1, y2]
        return [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]

    def _redraw(self):
        self.delete("all")
        w = max(20, self.winfo_width())
        h = max(12, self.winfo_height())
        cy = h / 2.0
        pad = 8.0
        track_h = 6.0
        x_start = pad
        x_end = max(pad + 1.0, w - pad)
        x_center = self._val_to_x(0.0)
        x_thumb = self._val_to_x(self._value)

        self.create_polygon(
            self._round_rect_coords(x_start, cy - track_h / 2.0, x_end, cy + track_h / 2.0, track_h / 2.0),
            smooth=True,
            fill=self.track_color,
            outline="",
        )

        if abs(x_thumb - x_center) >= 0.5:
            left_x = min(x_center, x_thumb)
            right_x = max(x_center, x_thumb)
            self.create_polygon(
                self._round_rect_coords(left_x, cy - track_h / 2.0, right_x, cy + track_h / 2.0, track_h / 2.0),
                smooth=True,
                fill=self.active_color,
                outline="",
            )

        self.create_line(x_center, cy - 5.0, x_center, cy + 5.0, fill="#8b949e", width=1)

        r = 7.0
        fill_thumb = self.thumb_hover_color if (self._hover or self._dragging) else self.thumb_color
        self.create_oval(
            x_thumb - r,
            cy - r,
            x_thumb + r,
            cy + r,
            fill=fill_thumb,
            outline="#1f6aa5",
            width=1,
        )


class StereoVuMeter(ctk.CTkFrame):
    """Fast stereo VU meter with two CustomTkinter progress bars (L / R)."""

    def __init__(self, master, width: int = 230, height: int = 56, gain: float = 2.0, **kwargs):
        super().__init__(
            master,
            width=width,
            height=height,
            fg_color="#1a1d24",
            border_width=1,
            border_color="#2d333b",
            **kwargs,
        )
        self.gain = _to_float(gain, 2.0)
        self._left_level = 0.0
        self._right_level = 0.0
        self._left_color = "#2ecc71"
        self._right_color = "#2ecc71"

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure((0, 1), weight=1)

        ctk.CTkLabel(self, text="L", width=18, font=ctk.CTkFont(family="Consolas", size=11, weight="bold")).grid(
            row=0, column=0, padx=(8, 4), pady=(6, 2)
        )
        self.bar_left = ctk.CTkProgressBar(self, height=12, progress_color=self._left_color)
        self.bar_left.set(0.0)
        self.bar_left.grid(row=0, column=1, padx=(0, 8), pady=(6, 2), sticky="ew")

        ctk.CTkLabel(self, text="R", width=18, font=ctk.CTkFont(family="Consolas", size=11, weight="bold")).grid(
            row=1, column=0, padx=(8, 4), pady=(2, 6)
        )
        self.bar_right = ctk.CTkProgressBar(self, height=12, progress_color=self._right_color)
        self.bar_right.set(0.0)
        self.bar_right.grid(row=1, column=1, padx=(0, 8), pady=(2, 6), sticky="ew")

    @staticmethod
    def _bar_color(ratio: float) -> str:
        if ratio >= 0.85:
            return "#e5484d"
        if ratio >= 0.60:
            return "#f5b041"
        return "#2ecc71"

    def set_levels(self, left: float, right: float):
        left_val = max(0.0, min(1.0, _to_float(left, 0.0) * self.gain))
        right_val = max(0.0, min(1.0, _to_float(right, 0.0) * self.gain))

        decay = 0.14
        next_left = max(left_val, self._left_level - decay)
        next_right = max(right_val, self._right_level - decay)

        if abs(next_left - self._left_level) >= 0.005:
            self._left_level = next_left
            self.bar_left.set(self._left_level)
        new_l_col = self._bar_color(self._left_level)
        if new_l_col != self._left_color:
            self._left_color = new_l_col
            self.bar_left.configure(progress_color=new_l_col)

        if abs(next_right - self._right_level) >= 0.005:
            self._right_level = next_right
            self.bar_right.set(self._right_level)
        new_r_col = self._bar_color(self._right_level)
        if new_r_col != self._right_color:
            self._right_color = new_r_col
            self.bar_right.configure(progress_color=new_r_col)

    def reset(self):
        self._left_level = 0.0
        self._right_level = 0.0
        self._left_color = "#2ecc71"
        self._right_color = "#2ecc71"
        self.bar_left.set(0.0)
        self.bar_right.set(0.0)
        self.bar_left.configure(progress_color="#2ecc71")
        self.bar_right.configure(progress_color="#2ecc71")


class _ChannelEditorCard(ctk.CTkFrame):
    """Form card for configuring a single S-Expression channel (:CHANNEL 0 / 1)."""

    def __init__(self, master, title: str, lang: str, **kwargs):
        super().__init__(master, **kwargs)
        self.lang = lang
        self.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, columnspan=4, padx=10, pady=(8, 4), sticky="w"
        )

        self.entry_bf = self._add_field(1, 0, "creator_bf", "280")
        self.entry_vol = self._add_field(1, 2, "creator_vol", "80")

        self.entry_volc = self._add_field(2, 0, "creator_volc", "0")
        self.entry_ton = self._add_field(2, 2, "creator_ton", "")

        self.entry_toff = self._add_field(3, 0, "creator_toff", "")
        self.chk_bfm = ctk.CTkCheckBox(self, text=tr_text(lang, "creator_bfm_act"), command=self._sync_states)
        self.chk_bfm.grid(row=3, column=2, columnspan=2, padx=10, pady=4, sticky="w")

        self.entry_bfm_mf = self._add_field(4, 0, "creator_bfm_mf", "0.4")
        self.entry_bfm_md = self._add_field(4, 2, "creator_bfm_md", "0.1")

        self.chk_pam = ctk.CTkCheckBox(self, text=tr_text(lang, "creator_pam_act"), command=self._sync_states)
        self.chk_pam.grid(row=5, column=0, columnspan=2, padx=10, pady=4, sticky="w")

        self.entry_pam_mf = self._add_field(6, 0, "creator_pam_mf", "0.5")
        self.entry_pam_md = self._add_field(6, 2, "creator_pam_md", "50")

    def _add_field(self, row: int, col: int, label_key: str, default_val: str) -> ctk.CTkEntry:
        ctk.CTkLabel(self, text=tr_text(self.lang, label_key), anchor="w").grid(
            row=row, column=col, padx=(10, 4), pady=3, sticky="w"
        )
        ent = ctk.CTkEntry(self, width=85)
        ent.insert(0, default_val)
        ent.grid(row=row, column=col + 1, padx=(4, 10), pady=3, sticky="ew")
        return ent

    def _sync_states(self):
        bfm_on = bool(self.chk_bfm.get())
        for w in (self.entry_bfm_mf, self.entry_bfm_md):
            w.configure(state="normal" if bfm_on else "disabled")
        pam_on = bool(self.chk_pam.get())
        for w in (self.entry_pam_mf, self.entry_pam_md):
            w.configure(state="normal" if pam_on else "disabled")

    @staticmethod
    def _set_entry(ent: ctk.CTkEntry, val: Any):
        ent.configure(state="normal")
        ent.delete(0, "end")
        if val is not None and str(val) != "":
            ent.insert(0, str(val))

    def load_subtrack(self, st: SubtrackConfig):
        self._set_entry(self.entry_bf, _fmt_num(_to_float(st.bf, 280.0)) if st.bf is not None else "")
        raw_vol = _to_float(st.vol, 0.8)
        vol_disp = raw_vol * 100.0 if 0.0 < raw_vol <= 1.0 else raw_vol
        self._set_entry(self.entry_vol, _fmt_num(vol_disp))
        self._set_entry(self.entry_volc, _fmt_num(_to_float(st.vol_c, 0.0)))
        self._set_entry(self.entry_ton, _fmt_num(_to_float(st.t_on, 0.0)) if st.t_on else "")
        self._set_entry(self.entry_toff, _fmt_num(_to_float(st.t_off, 0.0)) if st.t_off else "")

        if st.bfm_act:
            self.chk_bfm.select()
        else:
            self.chk_bfm.deselect()
        self._set_entry(self.entry_bfm_mf, _fmt_num(_to_float(st.bfm_mf, 0.4)))
        self._set_entry(self.entry_bfm_md, _fmt_num(_to_float(st.bfm_md, 0.1)))

        if st.pam_act:
            self.chk_pam.select()
        else:
            self.chk_pam.deselect()
        self._set_entry(self.entry_pam_mf, _fmt_num(_to_float(st.pam_mf, 0.5)))
        self._set_entry(self.entry_pam_md, _fmt_num(_to_float(st.pam_md, 50.0)))
        self._sync_states()

    def build_subtrack(self, ch_index: int) -> SubtrackConfig:
        bf_txt = self.entry_bf.get().strip()
        bf_val = _to_float(bf_txt, 280.0) if bf_txt else None
        vol_raw = _to_float(self.entry_vol.get().strip(), 80.0)
        vol_norm = max(0.0, min(1.0, vol_raw / 100.0 if vol_raw > 1.0 else vol_raw))
        ton_txt = self.entry_ton.get().strip()
        toff_txt = self.entry_toff.get().strip()
        return SubtrackConfig(
            index=ch_index,
            bf=bf_val,
            vol=vol_norm,
            vol_c=_to_float(self.entry_volc.get().strip(), 0.0),
            t_on=_to_float(ton_txt, 0.0) if ton_txt else None,
            t_off=_to_float(toff_txt, 0.0) if toff_txt else None,
            bfm_act=bool(self.chk_bfm.get()),
            bfm_mf=_to_float(self.entry_bfm_mf.get().strip(), 0.0),
            bfm_md=_to_float(self.entry_bfm_md.get().strip(), 0.0),
            pam_act=bool(self.chk_pam.get()),
            pam_mf=_to_float(self.entry_pam_mf.get().strip(), 0.0),
            pam_md=_to_float(self.entry_pam_md.get().strip(), 0.0),
        )


class SessionCreatorDialog(ctk.CTkToplevel):
    """Plugin dialog to create or edit sessions via form or raw S-Expression text (.alass2)."""

    def __init__(self, master: "EStimPlayerApp", base_session: Optional[SessionConfig] = None):
        super().__init__(master=master)
        self.player_app = master
        self.lang = master.language if master.language in VALID_LANGUAGES else "en"
        init_w = max(740, _to_int(getattr(master, "creator_width", 860), 860))
        init_h = max(520, _to_int(getattr(master, "creator_height", 620), 620))
        self.title(self._t("creator_title"))
        self.geometry(f"{init_w}x{init_h}")
        self.minsize(740, 520)
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._tracks: List[TrackConfig] = self._init_tracks(base_session)
        self._selected_idx: int = 0
        self._track_buttons: List[ctk.CTkButton] = []
        self._last_tab: str = ""

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        meta_frame = ctk.CTkFrame(self)
        meta_frame.grid(row=0, column=0, padx=14, pady=(12, 6), sticky="ew")
        meta_frame.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(meta_frame, text=self._t("creator_session_name")).grid(
            row=0, column=0, padx=(10, 4), pady=8, sticky="w"
        )
        self.entry_session_name = ctk.CTkEntry(meta_frame)
        self.entry_session_name.insert(0, base_session.name if base_session else "Custom Session")
        self.entry_session_name.grid(row=0, column=1, padx=(4, 12), pady=8, sticky="ew")

        ctk.CTkLabel(meta_frame, text=self._t("creator_creator")).grid(
            row=0, column=2, padx=(6, 4), pady=8, sticky="w"
        )
        self.entry_creator = ctk.CTkEntry(meta_frame, width=160)
        self.entry_creator.insert(0, base_session.creator if (base_session and base_session.creator) else "SmartStim")
        self.entry_creator.grid(row=0, column=3, padx=(4, 10), pady=8, sticky="ew")

        self.tab_form_label = "Formular" if self.lang == "de" else "Form"
        self.tab_raw_label = "Raw S-Expression"

        self.tabs = ctk.CTkTabview(self, command=self._on_tab_changed)
        self.tabs.grid(row=1, column=0, padx=14, pady=6, sticky="nsew")
        tab_form = self.tabs.add(self.tab_form_label)
        tab_raw = self.tabs.add(self.tab_raw_label)
        self._last_tab = self.tab_form_label

        tab_form.grid_columnconfigure(1, weight=1)
        tab_form.grid_rowconfigure(0, weight=1)

        left_pane = ctk.CTkFrame(tab_form, width=230)
        left_pane.grid(row=0, column=0, padx=(4, 6), pady=4, sticky="nsew")
        left_pane.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(left_pane, text=self._t("creator_tracks"), font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, padx=8, pady=(8, 4), sticky="w"
        )
        self.track_scroll = ctk.CTkScrollableFrame(left_pane, width=205)
        self.track_scroll.grid(row=1, column=0, padx=8, pady=4, sticky="nsew")

        t_btn_bar = ctk.CTkFrame(left_pane, fg_color="transparent")
        t_btn_bar.grid(row=2, column=0, padx=8, pady=(4, 8), sticky="ew")
        t_btn_bar.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(t_btn_bar, text=self._t("creator_add_track"), command=self._add_track).grid(
            row=0, column=0, padx=(0, 2), sticky="ew"
        )
        ctk.CTkButton(t_btn_bar, text=self._t("creator_dup_track"), command=self._duplicate_track).grid(
            row=0, column=1, padx=2, sticky="ew"
        )
        ctk.CTkButton(t_btn_bar, text=self._t("creator_del_track"), command=self._delete_track).grid(
            row=0, column=2, padx=(2, 0), sticky="ew"
        )

        right_pane = ctk.CTkScrollableFrame(tab_form)
        right_pane.grid(row=0, column=1, padx=(6, 4), pady=4, sticky="nsew")
        right_pane.grid_columnconfigure((1, 3, 5), weight=1)

        ctk.CTkLabel(right_pane, text=self._t("creator_track_name")).grid(
            row=0, column=0, padx=(8, 4), pady=6, sticky="w"
        )
        self.entry_track_name = ctk.CTkEntry(right_pane)
        self.entry_track_name.grid(row=0, column=1, padx=(4, 8), pady=6, sticky="ew")

        ctk.CTkLabel(right_pane, text=self._t("creator_track_time")).grid(
            row=0, column=2, padx=(6, 4), pady=6, sticky="w"
        )
        self.entry_track_time = ctk.CTkEntry(right_pane, width=80)
        self.entry_track_time.grid(row=0, column=3, padx=(4, 8), pady=6, sticky="ew")

        ctk.CTkLabel(right_pane, text=self._t("creator_track_num")).grid(
            row=0, column=4, padx=(6, 4), pady=6, sticky="w"
        )
        self.entry_track_num = ctk.CTkEntry(right_pane, width=65)
        self.entry_track_num.grid(row=0, column=5, padx=(4, 8), pady=6, sticky="ew")

        self.card_ch0 = _ChannelEditorCard(right_pane, self._t("creator_ch0"), self.lang)
        self.card_ch0.grid(row=1, column=0, columnspan=6, padx=6, pady=6, sticky="ew")

        self.card_ch1 = _ChannelEditorCard(right_pane, self._t("creator_ch1"), self.lang)
        self.card_ch1.grid(row=2, column=0, columnspan=6, padx=6, pady=6, sticky="ew")

        tab_raw.grid_columnconfigure(0, weight=1)
        tab_raw.grid_rowconfigure(1, weight=1)

        raw_toolbar = ctk.CTkFrame(tab_raw, fg_color="transparent")
        raw_toolbar.grid(row=0, column=0, padx=4, pady=(2, 6), sticky="ew")
        ctk.CTkButton(
            raw_toolbar,
            text="Aus Formular erzeugen" if self.lang == "de" else "Generate from Form",
            command=self._sync_form_to_raw,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            raw_toolbar,
            text="In Formular übernehmen" if self.lang == "de" else "Apply to Form",
            command=self._sync_raw_to_form,
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            raw_toolbar,
            text="Syntax prüfen" if self.lang == "de" else "Check Syntax",
            command=self._validate_raw_ui,
        ).pack(side="left", padx=6)

        self.raw_textbox = ctk.CTkTextbox(tab_raw, font=ctk.CTkFont(family="Consolas", size=12))
        self.raw_textbox.grid(row=1, column=0, padx=4, pady=(0, 4), sticky="nsew")

        footer = ctk.CTkFrame(self)
        footer.grid(row=2, column=0, padx=14, pady=(6, 12), sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        self.lbl_err = ctk.CTkLabel(footer, text="", text_color="#e5484d", anchor="w")
        self.lbl_err.grid(row=0, column=0, padx=10, pady=8, sticky="ew")

        ctk.CTkButton(footer, text=self._t("creator_apply_only"), command=self._apply_to_player).grid(
            row=0, column=1, padx=6, pady=8
        )
        ctk.CTkButton(footer, text=self._t("creator_save_load"), command=self._save_and_load).grid(
            row=0, column=2, padx=(6, 10), pady=8
        )

        self._rebuild_track_list()
        self._load_track_to_form(0)
        self._sync_form_to_raw()

    def _t(self, key: str, **kwargs) -> str:
        return tr_text(self.lang, key, **kwargs)

    def _save_dialog_size(self):
        self.update_idletasks()
        fallback_w = max(740, _to_int(getattr(self.player_app, "creator_width", 860), 860))
        fallback_h = max(520, _to_int(getattr(self.player_app, "creator_height", 620), 620))
        w = self.winfo_width() if self.winfo_width() >= 740 else fallback_w
        h = self.winfo_height() if self.winfo_height() >= 520 else fallback_h
        self.player_app.creator_width = w
        self.player_app.creator_height = h
        self.player_app._persist_current_settings()

    def _on_close(self):
        self._save_dialog_size()
        self.destroy()

    @staticmethod
    def _default_track(num: int) -> TrackConfig:
        return TrackConfig(
            index=num,
            name=f"Track-{num}",
            duration=60.0,
            subtracks=[
                SubtrackConfig(index=0, bf=280.0, vol=0.8, pam_act=True, pam_mf=0.5, pam_md=50.0),
                SubtrackConfig(
                    index=1,
                    bf=280.0,
                    vol=0.8,
                    bfm_act=True,
                    bfm_mf=0.4,
                    bfm_md=0.1,
                    pam_act=True,
                    pam_mf=0.5,
                    pam_md=50.0,
                ),
            ],
        )

    def _init_tracks(self, base_session: Optional[SessionConfig]) -> List[TrackConfig]:
        if base_session and base_session.tracks and not base_session.is_playlist:
            cloned: List[TrackConfig] = []
            for idx, tr in enumerate(base_session.tracks):
                subs = [SubtrackConfig(**vars(st)) for st in tr.subtracks]
                while len(subs) < 2:
                    subs.append(SubtrackConfig(index=len(subs), bf=280.0, vol=0.5))
                cloned.append(
                    TrackConfig(
                        index=tr.index if tr.index else idx + 1,
                        name=tr.name,
                        duration=max(0.05, _to_float(tr.duration, 60.0)),
                        subtracks=subs[:2],
                    )
                )
            return cloned
        return [self._default_track(1)]

    def _store_form_to_track(self, idx: int):
        if not (0 <= idx < len(self._tracks)):
            return
        tr = self._tracks[idx]
        tr.name = self.entry_track_name.get().strip() or f"Track-{idx + 1}"
        tr.duration = max(0.05, _to_float(self.entry_track_time.get().strip(), 60.0))
        tr.index = _to_int(self.entry_track_num.get().strip(), idx + 1)
        tr.subtracks = [self.card_ch0.build_subtrack(0), self.card_ch1.build_subtrack(1)]

    def _load_track_to_form(self, idx: int):
        if not (0 <= idx < len(self._tracks)):
            return
        self._selected_idx = idx
        tr = self._tracks[idx]
        self.entry_track_name.delete(0, "end")
        self.entry_track_name.insert(0, tr.name)
        self.entry_track_time.delete(0, "end")
        self.entry_track_time.insert(0, _fmt_num(tr.duration))
        self.entry_track_num.delete(0, "end")
        self.entry_track_num.insert(0, str(tr.index))
        subs = (
            tr.subtracks
            if len(tr.subtracks) >= 2
            else [
                SubtrackConfig(index=0, bf=280.0, vol=0.8),
                SubtrackConfig(index=1, bf=280.0, vol=0.8),
            ]
        )
        self.card_ch0.load_subtrack(subs[0])
        self.card_ch1.load_subtrack(subs[1])
        self._highlight_selected()

    def _highlight_selected(self):
        for i, btn in enumerate(self._track_buttons):
            btn.configure(fg_color=("#1f6aa5", "#1f6aa5") if i == self._selected_idx else ("gray75", "gray25"))

    def _rebuild_track_list(self):
        for b in self._track_buttons:
            b.destroy()
        self._track_buttons.clear()
        for i, tr in enumerate(self._tracks):
            btn = ctk.CTkButton(
                self.track_scroll,
                text=f"{i + 1:02d} | {tr.name} ({_fmt_num(tr.duration)}s)",
                anchor="w",
                fg_color=("gray75", "gray25"),
                command=lambda idx=i: self._select_track(idx),
            )
            btn.pack(fill="x", padx=3, pady=2)
            self._track_buttons.append(btn)
        self._highlight_selected()

    def _select_track(self, idx: int):
        self._store_form_to_track(self._selected_idx)
        self._rebuild_track_list()
        self._load_track_to_form(idx)

    def _add_track(self):
        self._store_form_to_track(self._selected_idx)
        next_num = len(self._tracks) + 1
        self._tracks.append(self._default_track(next_num))
        self._rebuild_track_list()
        self._load_track_to_form(len(self._tracks) - 1)

    def _duplicate_track(self):
        self._store_form_to_track(self._selected_idx)
        src = self._tracks[self._selected_idx]
        next_num = len(self._tracks) + 1
        copy_tr = TrackConfig(
            index=next_num,
            name=f"{src.name} Copy",
            duration=src.duration,
            subtracks=[SubtrackConfig(**vars(st)) for st in src.subtracks],
        )
        self._tracks.append(copy_tr)
        self._rebuild_track_list()
        self._load_track_to_form(len(self._tracks) - 1)

    def _delete_track(self):
        if len(self._tracks) <= 1:
            return
        self._tracks.pop(self._selected_idx)
        next_idx = min(self._selected_idx, len(self._tracks) - 1)
        self._rebuild_track_list()
        self._load_track_to_form(next_idx)

    def _collect_form_session(self) -> Optional[SessionConfig]:
        self._store_form_to_track(self._selected_idx)
        s_name = self.entry_session_name.get().strip()
        if not s_name:
            self.lbl_err.configure(text=self._t("creator_err_name"), text_color="#e5484d")
            return None
        self.lbl_err.configure(text="")
        now_str = datetime.datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")
        return SessionConfig(
            name=s_name,
            channels=2,
            tracks=[
                TrackConfig(
                    index=tr.index,
                    name=tr.name,
                    duration=max(0.05, _to_float(tr.duration, 1.0)),
                    subtracks=[SubtrackConfig(**vars(st)) for st in tr.subtracks],
                )
                for tr in self._tracks
            ],
            is_playlist=False,
            creator=self.entry_creator.get().strip() or "SmartStim",
            creation=now_str,
            modification=now_str,
        )

    def _sync_form_to_raw(self):
        sess = self._collect_form_session()
        if sess is None:
            return
        sexp_str = format_sexp_session(sess)
        self.raw_textbox.delete("1.0", "end")
        self.raw_textbox.insert("1.0", sexp_str)
        self.lbl_err.configure(text="")

    @staticmethod
    def _validate_sexp_brackets(raw_txt: str, is_de: bool) -> Optional[str]:
        in_str = False
        escape = False
        stack: List[tuple[int, int]] = []
        line = 1
        col = 0

        for ch in raw_txt:
            if ch == "\n":
                line += 1
                col = 0
                escape = False
                continue
            col += 1
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "(":
                stack.append((line, col))
            elif ch == ")":
                if not stack:
                    return (
                        f"Überzählige schließende Klammer ')' in Zeile {line}, Spalte {col}."
                        if is_de
                        else f"Unmatched closing parenthesis ')' at line {line}, col {col}."
                    )
                stack.pop()

        if in_str:
            return (
                "Nicht geschlossener Textstring '\"' im S-Expression-Code."
                if is_de
                else "Unterminated string literal '\"' in S-expression."
            )
        if stack:
            l_open, c_open = stack[-1]
            return (
                f"Offene Klammer '(' in Zeile {l_open}, Spalte {c_open} wird nicht geschlossen."
                if is_de
                else f"Unclosed opening parenthesis '(' at line {l_open}, col {c_open}."
            )
        return None

    @staticmethod
    def _parse_strict_number(val: Any, key_name: str, is_de: bool) -> float:
        if isinstance(val, bool) or val is None:
            raise ValueError(f"Ungültiger Wert für {key_name}." if is_de else f"Invalid value for {key_name}.")
        s = str(val).strip().replace(",", ".")
        if not s:
            raise ValueError(f"Leerer Wert für {key_name}." if is_de else f"Empty value for {key_name}.")
        fval = float(s)
        if not np.isfinite(fval):
            raise ValueError(f"Nicht endlicher Wert für {key_name}." if is_de else f"Non-finite value for {key_name}.")
        return fval

    def _validate_sexp_parameters(self, forms: List[Any]) -> Optional[str]:
        is_de = self.lang == "de"
        has_session_name = False
        track_count = 0
        numeric_keys = (":bf", ":vol", ":volc", ":t_on", ":t_off", ":t_att", ":bfm_mf", ":bfm_md", ":pam_mf", ":pam_md")

        for form in forms:
            if not isinstance(form, list) or not form:
                continue
            plist = _plist_to_dict(form)
            if ":session_name" in plist:
                sname = str(plist[":session_name"]).strip()
                if not sname:
                    return ":Session_name darf nicht leer sein." if is_de else ":Session_name cannot be empty."
                has_session_name = True
            elif ":track_name" in plist or ":channels" in plist or ":track_time" in plist:
                track_count += 1
                tname = str(plist.get(":track_name", "")).strip()
                if not tname:
                    return (
                        f"Track {track_count}: :Track_name fehlt oder ist leer."
                        if is_de
                        else f"Track {track_count}: :Track_name is missing or empty."
                    )
                if ":track_time" not in plist:
                    return (
                        f"Track '{tname}': :Track_time fehlt."
                        if is_de
                        else f"Track '{tname}': :Track_time is missing."
                    )
                try:
                    dur = self._parse_strict_number(plist[":track_time"], ":track_time", is_de)
                except ValueError as exc:
                    return f"Track '{tname}': {exc}"
                if dur <= 0.0:
                    return (
                        f"Track '{tname}': :Track_time muss größer als 0 sein."
                        if is_de
                        else f"Track '{tname}': :Track_time must be greater than 0."
                    )

                ch_list = plist.get(":channels")
                if not isinstance(ch_list, list) or not ch_list:
                    return (
                        f"Track '{tname}': :CHANNELS fehlt oder ist leer."
                        if is_de
                        else f"Track '{tname}': :CHANNELS is missing or empty."
                    )
                channel_forms = (
                    ch_list[0]
                    if (len(ch_list) == 1 and isinstance(ch_list[0], list) and ch_list[0] and isinstance(ch_list[0][0], list))
                    else ch_list
                )
                for s_pos, ch_form in enumerate(channel_forms):
                    if not isinstance(ch_form, list):
                        return (
                            f"Track '{tname}', Kanal {s_pos}: Ungültiger Kanalblock."
                            if is_de
                            else f"Track '{tname}', channel {s_pos}: Invalid channel form."
                        )
                    ch_plist = _plist_to_dict(ch_form)
                    for nkey in numeric_keys:
                        if nkey in ch_plist:
                            try:
                                self._parse_strict_number(ch_plist[nkey], nkey, is_de)
                            except ValueError as exc:
                                return f"Track '{tname}', Kanal {s_pos}: {exc}"

        if not has_session_name:
            return (
                "Hinweis: :Session_name nicht gefunden (Fallback-Name wird verwendet)."
                if is_de
                else "Notice: :Session_name not found (fallback name will be used)."
            )
        if track_count == 0:
            return (
                "Mindestens ein Track (:Track_name / :CHANNELS) ist erforderlich."
                if is_de
                else "At least one track (:Track_name / :CHANNELS) is required."
            )
        return None

    def _validate_raw_ui(self) -> bool:
        is_de = self.lang == "de"
        raw_txt = self.raw_textbox.get("1.0", "end").strip()
        if not raw_txt:
            self.lbl_err.configure(
                text="S-Expression-Text ist leer." if is_de else "S-expression text is empty.",
                text_color="#e5484d",
            )
            return False

        bracket_err = self._validate_sexp_brackets(raw_txt, is_de)
        if bracket_err:
            self.lbl_err.configure(text=bracket_err, text_color="#e5484d")
            return False

        forms = _parse_sexp_forms(_tokenize_sexp(raw_txt))
        if not forms:
            self.lbl_err.configure(
                text="Keine gültigen S-Expression-Blöcke gefunden." if is_de else "No valid S-expression forms found.",
                text_color="#e5484d",
            )
            return False

        param_err = self._validate_sexp_parameters(forms)
        if param_err:
            is_notice = param_err.startswith("Hinweis:") or param_err.startswith("Notice:")
            self.lbl_err.configure(text=param_err, text_color="#f5b041" if is_notice else "#e5484d")
            return is_notice

        self.lbl_err.configure(
            text="Klammern und Parameter sind gültig." if is_de else "Parentheses and parameters are valid.",
            text_color="#2ecc71",
        )
        return True

    def _parse_raw_text_to_session(self) -> Optional[SessionConfig]:
        is_de = self.lang == "de"
        raw_txt = self.raw_textbox.get("1.0", "end").strip()
        if not raw_txt:
            self.lbl_err.configure(text=self._t("creator_err_name"), text_color="#e5484d")
            return None

        bracket_err = self._validate_sexp_brackets(raw_txt, is_de)
        if bracket_err:
            self.lbl_err.configure(text=bracket_err, text_color="#e5484d")
            return None

        try:
            forms = _parse_sexp_forms(_tokenize_sexp(raw_txt))
            if not forms:
                self.lbl_err.configure(
                    text="Ungültiger S-Expression-Code." if is_de else "Invalid S-expression.",
                    text_color="#e5484d",
                )
                return None

            param_err = self._validate_sexp_parameters(forms)
            if param_err and not (param_err.startswith("Hinweis:") or param_err.startswith("Notice:")):
                self.lbl_err.configure(text=param_err, text_color="#e5484d")
                return None

            s_name = self.entry_session_name.get().strip() or "Custom Session"
            creator = self.entry_creator.get().strip() or "SmartStim"
            tracks: List[TrackConfig] = []

            for form in forms:
                if not isinstance(form, list) or not form:
                    continue
                plist = _plist_to_dict(form)
                if ":session_name" in plist:
                    s_name = str(plist[":session_name"])
                    if ":creator" in plist:
                        creator = str(plist[":creator"])
                elif ":track_name" in plist or ":channels" in plist or ":track_time" in plist:
                    t_name = str(plist.get(":track_name", f"Track-{len(tracks) + 1}"))
                    t_time = max(0.05, _to_float(plist.get(":track_time", 60.0), 60.0))
                    t_num = _to_int(plist.get(":track_number", len(tracks) + 1), len(tracks) + 1)
                    subs: List[SubtrackConfig] = []
                    ch_list = plist.get(":channels")
                    if isinstance(ch_list, list):
                        channel_forms = (
                            ch_list[0]
                            if (len(ch_list) == 1 and isinstance(ch_list[0], list) and ch_list[0] and isinstance(ch_list[0][0], list))
                            else ch_list
                        )
                        for s_pos, ch_form in enumerate(channel_forms):
                            if not isinstance(ch_form, list):
                                continue
                            ch_plist = _plist_to_dict(ch_form)
                            bf_raw = ch_plist.get(":bf")
                            ton_raw = ch_plist.get(":t_on")
                            toff_raw = ch_plist.get(":t_off")
                            subs.append(
                                SubtrackConfig(
                                    index=_to_int(ch_plist.get(":channel", s_pos), s_pos),
                                    bf=_to_float(bf_raw, 280.0) if bf_raw is not None else None,
                                    vol=_to_float(ch_plist.get(":vol", 80.0), 80.0),
                                    vol_c=_to_float(ch_plist.get(":volc", 0.0), 0.0),
                                    t_on=_to_float(ton_raw, 0.0) if ton_raw is not None else None,
                                    t_off=_to_float(toff_raw, 0.0) if toff_raw is not None else None,
                                    t_att=_to_float(ch_plist.get(":t_att", 0.0), 0.0),
                                    bfm_act=parse_bool(ch_plist.get(":bfm_act", False), False),
                                    bfm_mf=_to_float(ch_plist.get(":bfm_mf", 0.0), 0.0),
                                    bfm_md=_to_float(ch_plist.get(":bfm_md", 0.0), 0.0),
                                    pam_act=parse_bool(ch_plist.get(":pam_act", False), False),
                                    pam_mf=_to_float(ch_plist.get(":pam_mf", 0.0), 0.0),
                                    pam_md=_to_float(ch_plist.get(":pam_md", 0.0), 0.0),
                                )
                            )
                    while len(subs) < 2:
                        subs.append(SubtrackConfig(index=len(subs), bf=280.0, vol=0.8))
                    tracks.append(TrackConfig(index=t_num, name=t_name, duration=t_time, subtracks=subs))

            if not tracks:
                tracks = [self._default_track(1)]

            self.lbl_err.configure(text="")
            now_str = datetime.datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")
            return SessionConfig(
                name=s_name,
                channels=max(2, max(len(t.subtracks) for t in tracks)),
                tracks=tracks,
                is_playlist=False,
                creator=creator,
                creation=now_str,
                modification=now_str,
            )
        except Exception as exc:
            self.lbl_err.configure(text=str(exc), text_color="#e5484d")
            return None

    def _sync_raw_to_form(self):
        sess = self._parse_raw_text_to_session()
        if sess is None:
            return
        self.entry_session_name.delete(0, "end")
        self.entry_session_name.insert(0, sess.name)
        self.entry_creator.delete(0, "end")
        self.entry_creator.insert(0, sess.creator)
        self._tracks = sess.tracks
        self._selected_idx = 0
        self._rebuild_track_list()
        self._load_track_to_form(0)

    def _on_tab_changed(self):
        current_tab = self.tabs.get()
        if current_tab == self._last_tab:
            return
        if current_tab == self.tab_raw_label:
            self._sync_form_to_raw()
        elif current_tab == self.tab_form_label and self._last_tab == self.tab_raw_label:
            self._sync_raw_to_form()
        self._last_tab = current_tab

    def _collect_session(self) -> Optional[SessionConfig]:
        if self.tabs.get() == self.tab_raw_label:
            return self._parse_raw_text_to_session()
        return self._collect_form_session()

    def _apply_to_player(self):
        sess = self._collect_session()
        if sess is None:
            return
        self._save_dialog_size()
        self.player_app.load_session_direct(sess)
        self.destroy()

    def _save_and_load(self):
        sess = self._collect_session()
        if sess is None:
            return
        start_dir = self.player_app.last_dir if os.path.isdir(self.player_app.last_dir) else os.path.expanduser("~")
        default_file = f"{sanitize_filename(sess.name)}.alass2"
        target = filedialog.asksaveasfilename(
            parent=self,
            title=self._t("dialog_save_alass2_title"),
            initialdir=start_dir,
            initialfile=default_file,
            defaultextension=".alass2",
            filetypes=[(self._t("filter_alass2"), "*.alass2"), (self._t("filter_all_files"), "*.*")],
        )
        if not target:
            return
        saved_fp = save_sexp_session(target, sess)
        self.player_app.last_dir = os.path.dirname(saved_fp)
        self.player_app.last_session = saved_fp
        self._save_dialog_size()
        self.player_app.load_file(saved_fp, preferred_track_idx=0)
        self.destroy()


class AboutDialog(ctk.CTkToplevel):
    """Info dialog showing application name, version, and creator."""

    def __init__(self, master: "EStimPlayerApp", language: str = "en"):
        super().__init__(master=master)
        self.lang = language if language in VALID_LANGUAGES else "en"
        self.title(tr_text(self.lang, "about_title"))
        self.geometry("390x235")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            master=self,
            text=tr_text(self.lang, "about_heading"),
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(18, 2))

        ctk.CTkLabel(
            master=self,
            text=tr_text(self.lang, "about_version", version=APP_VERSION),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#3b8ed0",
        ).grid(row=1, column=0, padx=20, pady=(0, 2))

        ctk.CTkLabel(
            master=self,
            text=tr_text(self.lang, "about_creator", creator=APP_CREATOR),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray80",
        ).grid(row=2, column=0, padx=20, pady=(0, 8))

        ctk.CTkLabel(
            master=self,
            text=tr_text(self.lang, "about_desc"),
            wraplength=340,
            justify="center",
            font=ctk.CTkFont(size=12),
        ).grid(row=3, column=0, padx=20, pady=(0, 14))

        ctk.CTkButton(
            master=self,
            text=tr_text(self.lang, "about_btn_close"),
            width=110,
            command=self.destroy,
        ).grid(row=4, column=0, padx=20, pady=(0, 16))


class SettingsDialog(ctk.CTkToplevel):
    """Settings dialog for window size, master volume, export volume, directory, and language."""

    def __init__(
        self,
        master: "EStimPlayerApp",
        current_width: int,
        current_height: int,
        last_dir: str,
        master_vol: float,
        language: str = "en",
        export_vol_pct: Optional[int] = None,
    ):
        super().__init__(master=master)
        self.player_app = master
        self.lang = language if language in VALID_LANGUAGES else "en"
        self.title(tr_text(self.lang, "settings_title"))
        self.geometry("460x380")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(master=self, text=tr_text(self.lang, "settings_width")).grid(
            row=0, column=0, padx=(16, 8), pady=(18, 6), sticky="w"
        )
        self.entry_width = ctk.CTkEntry(master=self)
        self.entry_width.insert(0, str(current_width))
        self.entry_width.grid(row=0, column=1, padx=(8, 16), pady=(18, 6), sticky="ew")

        ctk.CTkLabel(master=self, text=tr_text(self.lang, "settings_height")).grid(
            row=1, column=0, padx=(16, 8), pady=6, sticky="w"
        )
        self.entry_height = ctk.CTkEntry(master=self)
        self.entry_height.insert(0, str(current_height))
        self.entry_height.grid(row=1, column=1, padx=(8, 16), pady=6, sticky="ew")

        ctk.CTkLabel(master=self, text=tr_text(self.lang, "settings_last_dir")).grid(
            row=2, column=0, padx=(16, 8), pady=6, sticky="w"
        )
        self.entry_last_dir = ctk.CTkEntry(master=self)
        self.entry_last_dir.insert(0, last_dir)
        self.entry_last_dir.grid(row=2, column=1, padx=(8, 16), pady=6, sticky="ew")

        ctk.CTkLabel(master=self, text=tr_text(self.lang, "settings_master_vol")).grid(
            row=3, column=0, padx=(16, 8), pady=6, sticky="w"
        )
        self.entry_vol = ctk.CTkEntry(master=self)
        self.entry_vol.insert(0, str(int(round(master_vol * 100))))
        self.entry_vol.grid(row=3, column=1, padx=(8, 16), pady=6, sticky="ew")

        ctk.CTkLabel(master=self, text=tr_text(self.lang, "settings_export_vol")).grid(
            row=4, column=0, padx=(16, 8), pady=6, sticky="w"
        )
        self.entry_export_vol = ctk.CTkEntry(master=self)
        if export_vol_pct is not None and not isinstance(export_vol_pct, bool):
            self.entry_export_vol.insert(0, str(max(0, min(200, _to_int(export_vol_pct, 70)))))
        self.entry_export_vol.grid(row=4, column=1, padx=(8, 16), pady=6, sticky="ew")

        ctk.CTkLabel(master=self, text=tr_text(self.lang, "settings_language")).grid(
            row=5, column=0, padx=(16, 8), pady=6, sticky="w"
        )
        self.option_lang = ctk.CTkOptionMenu(
            master=self,
            values=[LANGUAGE_LABELS[code] for code in VALID_LANGUAGES],
        )
        self.option_lang.set(LANGUAGE_LABELS.get(self.lang, "English"))
        self.option_lang.grid(row=5, column=1, padx=(8, 16), pady=6, sticky="ew")

        self.lbl_info = ctk.CTkLabel(
            master=self,
            text=tr_text(self.lang, "settings_file_info", path=get_settings_path()),
            font=ctk.CTkFont(size=11),
            text_color="gray70",
        )
        self.lbl_info.grid(row=6, column=0, columnspan=2, padx=16, pady=(6, 4), sticky="w")

        btn_frame = ctk.CTkFrame(master=self, fg_color="transparent")
        btn_frame.grid(row=7, column=0, columnspan=2, padx=16, pady=(10, 14), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            master=btn_frame,
            text=tr_text(self.lang, "settings_btn_current_size"),
            command=self._fill_current_size,
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")
        ctk.CTkButton(
            master=btn_frame,
            text=tr_text(self.lang, "settings_btn_save"),
            command=self._save_and_apply,
        ).grid(row=0, column=1, padx=(6, 0), sticky="ew")

    def _fill_current_size(self):
        self.entry_width.delete(0, "end")
        self.entry_width.insert(0, str(self.player_app.winfo_width()))
        self.entry_height.delete(0, "end")
        self.entry_height.insert(0, str(self.player_app.winfo_height()))

    def _save_and_apply(self):
        try:
            w = int(self.entry_width.get().strip())
            h = int(self.entry_height.get().strip())
            vol_pct = int(self.entry_vol.get().strip())
            if w < 400 or h < 300:
                self.lbl_info.configure(text=tr_text(self.lang, "settings_err_min_size"), text_color="#e5484d")
                return
            if not (0 <= vol_pct <= 100):
                self.lbl_info.configure(text=tr_text(self.lang, "settings_err_vol_range"), text_color="#e5484d")
                return

            raw_exp = self.entry_export_vol.get().strip()
            if raw_exp == "":
                parsed_exp_vol: Optional[int] = None
            else:
                exp_val = int(raw_exp)
                if not (0 <= exp_val <= 200):
                    self.lbl_info.configure(
                        text=tr_text(self.lang, "settings_err_export_vol_range"), text_color="#e5484d"
                    )
                    return
                parsed_exp_vol = exp_val
        except ValueError:
            self.lbl_info.configure(text=tr_text(self.lang, "settings_err_invalid_int"), text_color="#e5484d")
            return

        selected_label = self.option_lang.get().strip()
        selected_lang = LABEL_TO_LANGUAGE.get(selected_label, self.lang)
        last_dir = self.entry_last_dir.get().strip() or self.player_app.last_dir
        self.player_app.apply_and_save_settings(
            w,
            h,
            last_dir,
            vol_pct / 100.0,
            language=selected_lang,
            export_vol_pct=parsed_exp_vol,
        )
        self.destroy()


class EStimPlayerApp(ctk.CTk):
    def __init__(self, initial_file: Optional[str] = None, sample_rate: int = DEFAULT_SAMPLE_RATE):
        super().__init__(className="E-StimPlayer")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        loaded = load_settings(900, 620, 0.7, "off", None, 0, default_pan=0.0, default_language="en")
        win_w = loaded["window_width"]
        win_h = loaded["window_height"]
        self.creator_width = max(740, _to_int(loaded.get("creator_width", 860), 860))
        self.creator_height = max(520, _to_int(loaded.get("creator_height", 620), 620))
        self.last_dir = loaded["last_dir"]
        self.master_vol = _to_float(loaded["master_vol"], 0.7)
        self.pan = max(-1.0, min(1.0, _to_float(loaded.get("pan", 0.0), 0.0)))
        self.language = loaded.get("language", "en") if loaded.get("language") in VALID_LANGUAGES else "en"
        self.last_session: Optional[str] = loaded["last_session"]
        self.last_track_idx: int = _to_int(loaded["last_track_idx"], 0)
        self.export_vol_pct: Optional[int] = loaded.get("export_vol_pct")

        self.title(self._t("app_title"))
        self.geometry(f"{win_w}x{win_h}")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.session: Optional[SessionConfig] = None
        self.sample_rate = max(8000, _to_int(sample_rate, DEFAULT_SAMPLE_RATE))
        self.synth = SmartStimSynthesizer(sample_rate=self.sample_rate)

        self.is_playing = False
        self.is_exporting = False
        self._seek_requested = False
        self._gapless_transition = False
        self._syncing_seek_slider = False
        self._last_settings_save = 0.0
        self.loop_mode = _normalize_loop_key(loaded["loop_mode"], "off")
        self.current_track_idx = self.last_track_idx
        self.track_elapsed = 0.0
        self._latest_meter_levels = (0.0, 0.0)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._play_thread: Optional[threading.Thread] = None

        self._build_menu()
        self._build_ui()
        self.after(50, self._meter_tick)

        startup_file = initial_file if (initial_file and os.path.isfile(initial_file)) else self.last_session
        if startup_file:
            self.load_file(startup_file, preferred_track_idx=self.last_track_idx)

    def _t(self, key: str, **kwargs) -> str:
        return tr_text(self.language, key, **kwargs)

    def _loop_display_values(self) -> List[str]:
        return [self._t("loop_off"), self._t("loop_track"), self._t("loop_session")]

    def _loop_key_to_display(self, key: str) -> str:
        norm = _normalize_loop_key(key, "off")
        return self._t(f"loop_{norm}")

    def _loop_display_to_key(self, label: str) -> str:
        mapping = {
            self._t("loop_off"): "off",
            self._t("loop_track"): "track",
            self._t("loop_session"): "session",
        }
        return mapping.get(label, _normalize_loop_key(label, "off"))

    def _meter_tick(self):
        """Periodic UI timer on main thread without blocking audio."""
        with self._lock:
            playing = self.is_playing
            left_lvl, right_lvl = self._latest_meter_levels
        if playing:
            self.vu_meter.set_levels(left_lvl, right_lvl)
        self.after(50, self._meter_tick)

    def _build_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label=self._t("menu_open_session"), command=self.on_open_file)
        file_menu.add_command(label=self._t("menu_create_session"), command=self.open_session_creator)
        file_menu.add_separator()
        file_menu.add_command(label=self._t("menu_export_track"), command=self.on_export_track_flac)
        file_menu.add_command(label=self._t("menu_export_all_tracks"), command=self.on_export_all_tracks_flac)
        file_menu.add_command(label=self._t("menu_export_session"), command=self.on_export_session_flac)
        file_menu.add_separator()
        file_menu.add_command(label=self._t("menu_settings"), command=self.open_settings)
        file_menu.add_command(label=self._t("menu_about"), command=self.open_about)
        file_menu.add_separator()
        file_menu.add_command(label=self._t("menu_exit"), command=self.on_close)
        menubar.add_cascade(label=self._t("menu_file"), menu=file_menu)
        self.configure(menu=menubar)

    def open_about(self):
        with self._lock:
            lang = self.language
        AboutDialog(self, language=lang)

    def open_session_creator(self):
        with self._lock:
            cur_session = self.session
        SessionCreatorDialog(self, base_session=cur_session)

    def _reset_track_scroll(self):
        """Scrolls the track list back to the top when loading a session."""
        def _do_reset():
            if not hasattr(self, "track_list_frame"):
                return
            try:
                self.track_list_frame.update_idletasks()
                canvas = getattr(self.track_list_frame, "_parent_canvas", None)
                if canvas is not None:
                    canvas.yview_moveto(0.0)
            except Exception:
                pass

        self.after(0, _do_reset)

    def _scroll_track_into_view(self, idx: int):
        """Scrolls the track list so track `idx` is visible."""
        if not (0 <= idx < len(self.track_buttons)):
            return

        def _do_scroll():
            if not (0 <= idx < len(self.track_buttons)):
                return
            btn = self.track_buttons[idx]
            try:
                if not btn.winfo_exists():
                    return
                self.track_list_frame.update_idletasks()
                canvas = getattr(self.track_list_frame, "_parent_canvas", None)
                if canvas is None:
                    return
                bbox = canvas.bbox("all")
                if not bbox:
                    return
                total_h = float(bbox[3] - bbox[1])
                view_h = float(canvas.winfo_height())
                if total_h <= view_h or total_h <= 0.0:
                    canvas.yview_moveto(0.0)
                    return

                btn_y = float(btn.winfo_y())
                btn_h = float(btn.winfo_height())
                cur_top = float(canvas.canvasy(0))
                cur_bottom = cur_top + view_h

                margin = max(8.0, btn_h * 0.5)
                if btn_y < cur_top + margin:
                    target_top = max(0.0, btn_y - margin)
                    canvas.yview_moveto(target_top / total_h)
                elif (btn_y + btn_h) > (cur_bottom - margin):
                    target_top = max(0.0, min(total_h - view_h, (btn_y + btn_h + margin) - view_h))
                    canvas.yview_moveto(target_top / total_h)
            except Exception:
                pass

        self.after(0, _do_scroll)

    def load_session_direct(self, session: SessionConfig, preferred_track_idx: int = 0):
        self.on_stop_click(reset_track=False)
        target_idx = preferred_track_idx if (0 <= preferred_track_idx < len(session.tracks)) else 0
        with self._lock:
            self.session = session
            self.current_track_idx = target_idx
            self.track_elapsed = 0.0
            self._seek_requested = False
            self._gapless_transition = False
            self._latest_meter_levels = (0.0, 0.0)

        total_sec = sum(_to_float(t.duration, 0.0) for t in session.tracks)
        kind_label = self._t("kind_playlist") if session.is_playlist else self._t("kind_tracks")
        self.lbl_session.configure(
            text=self._t(
                "session_header",
                name=session.name,
                count=len(session.tracks),
                kind=kind_label,
                total=_format_mm_ss(total_sec),
            )
        )

        for btn in self.track_buttons:
            btn.destroy()
        self.track_buttons.clear()

        for idx, tr in enumerate(session.tracks):
            dur = max(0.05, _to_float(tr.duration, 0.05))
            btn = ctk.CTkButton(
                master=self.track_list_frame,
                text=f"{idx:02d} | {tr.name} ({dur:.1f}s)",
                anchor="w",
                fg_color=("gray75", "gray25"),
                command=lambda i=idx: self.select_and_play_track(i),
            )
            btn.pack(fill="x", padx=4, pady=2)
            self.track_buttons.append(btn)

        self._highlight_track(target_idx, scroll_into_view=False)
        self._reset_track_scroll()
        self._update_details(target_idx)
        self._set_seek_ui(0.0)
        self.lbl_status.configure(text=self._t("status_loaded", filename=session.name))

    def _apply_language_to_ui(self):
        self.title(self._t("app_title"))
        self._build_menu()
        self.btn_open.configure(text=self._t("btn_open_session"))
        self.btn_create.configure(text=self._t("btn_create_session"))
        self.btn_play.configure(text=self._t("btn_start"))
        self.btn_pause.configure(text=self._t("btn_pause"))
        self.btn_stop.configure(text=self._t("btn_stop"))

        with self._lock:
            mode_key = self.loop_mode
            t_idx = _to_int(self.current_track_idx, 0)
            session = self.session

        self.loop_switch.configure(values=self._loop_display_values())
        self.loop_switch.set(self._loop_key_to_display(mode_key))
        self.track_list_frame.configure(label_text=self._t("tracks_label"))

        if session:
            total_sec = sum(_to_float(t.duration, 0.0) for t in session.tracks)
            kind_label = self._t("kind_playlist") if session.is_playlist else self._t("kind_tracks")
            self.lbl_session.configure(
                text=self._t(
                    "session_header",
                    name=session.name,
                    count=len(session.tracks),
                    kind=kind_label,
                    total=_format_mm_ss(total_sec),
                )
            )
            self._update_details(t_idx)
        else:
            self.lbl_session.configure(text=self._t("no_session_loaded"))

    def _current_window_size(self) -> tuple[int, int]:
        w = self.winfo_width() if self.winfo_width() > 1 else 900
        h = self.winfo_height() if self.winfo_height() > 1 else 620
        return w, h

    def _persist_current_settings(self, min_interval_sec: float = 0.0) -> str:
        now = time.monotonic()
        if min_interval_sec > 0.0 and (now - self._last_settings_save) < min_interval_sec:
            return get_settings_path()
        self._last_settings_save = now
        w, h = self._current_window_size()
        with self._lock:
            vol = _to_float(self.master_vol, 0.7)
            pan = max(-1.0, min(1.0, _to_float(self.pan, 0.0)))
            mode = self.loop_mode
            t_idx = _to_int(self.current_track_idx, 0)
            lang = self.language
            exp_pct = self.export_vol_pct
            c_w = max(740, _to_int(self.creator_width, 860))
            c_h = max(520, _to_int(self.creator_height, 620))
        self.last_track_idx = max(0, t_idx)
        return save_settings(
            w,
            h,
            self.last_dir,
            vol,
            mode,
            self.last_session,
            self.last_track_idx,
            pan=pan,
            language=lang,
            export_vol_pct=exp_pct,
            creator_width=c_w,
            creator_height=c_h,
        )

    def on_close(self):
        self._persist_current_settings()
        self.on_stop_click(reset_track=False)
        self.destroy()

    def open_settings(self):
        w, h = self._current_window_size()
        with self._lock:
            vol = _to_float(self.master_vol, 0.7)
            lang = self.language
            exp_pct = self.export_vol_pct
        SettingsDialog(self, w, h, self.last_dir, vol, language=lang, export_vol_pct=exp_pct)

    def apply_and_save_settings(
        self,
        width: int,
        height: int,
        last_dir: str,
        master_vol: float,
        language: Optional[str] = None,
        export_vol_pct: Optional[int] = None,
    ) -> str:
        self.last_dir = last_dir
        new_lang = language if (language in VALID_LANGUAGES) else self.language
        with self._lock:
            self.master_vol = float(max(0.0, min(1.0, _to_float(master_vol, 0.7))))
            pan = max(-1.0, min(1.0, _to_float(self.pan, 0.0)))
            mode = self.loop_mode
            t_idx = _to_int(self.current_track_idx, 0)
            self.language = new_lang
            self.export_vol_pct = (
                max(0, min(200, _to_int(export_vol_pct, 70)))
                if (export_vol_pct is not None and not isinstance(export_vol_pct, bool))
                else None
            )
            exp_pct = self.export_vol_pct
            c_w = max(740, _to_int(self.creator_width, 860))
            c_h = max(520, _to_int(self.creator_height, 620))
        self.last_track_idx = max(0, t_idx)
        self.slider_vol.set(self.master_vol)
        self.lbl_vol.configure(text=f"Vol: {int(round(self.master_vol * 100))}%")
        self.geometry(f"{_to_int(width, 900)}x{_to_int(height, 620)}")
        self._apply_language_to_ui()
        saved_path = save_settings(
            width,
            height,
            self.last_dir,
            self.master_vol,
            mode,
            self.last_session,
            self.last_track_idx,
            pan=pan,
            language=self.language,
            export_vol_pct=exp_pct,
            creator_width=c_w,
            creator_height=c_h,
        )
        if hasattr(self, "lbl_status"):
            self.lbl_status.configure(text=self._t("status_settings_saved", path=saved_path))
        return saved_path

    def _ask_export_volume(self, current_vol: float) -> Optional[tuple[float, int]]:
        """Uses configured export_vol_pct directly if set; otherwise asks via dialog."""
        with self._lock:
            saved_exp = self.export_vol_pct

        base_vol = max(1e-6, _to_float(current_vol, 0.7))

        if saved_exp is not None and not isinstance(saved_exp, bool):
            pct_int = max(0, min(200, _to_int(saved_exp, 70)))
            gain = (pct_int / 100.0) / base_vol
            return gain, pct_int

        cur_pct = int(round(max(0.0, min(1.0, base_vol)) * 100))
        dlg = ctk.CTkInputDialog(
            title=self._t("export_vol_title"),
            text=self._t("export_vol_prompt", cur_pct=cur_pct),
        )
        raw = dlg.get_input()
        if raw is None:
            return None
        pct_val = max(0.0, min(200.0, _to_float(raw, float(cur_pct))))
        pct_int = int(round(pct_val))
        with self._lock:
            self.export_vol_pct = pct_int
        self._persist_current_settings()
        target_vol = pct_val / 100.0
        gain = target_vol / base_vol
        return gain, pct_int

    def _set_seek_ui(self, ratio: float):
        clamped = max(0.0, min(1.0, _to_float(ratio, 0.0)))
        self.progress.set(clamped)
        self._syncing_seek_slider = True
        try:
            self.slider_seek.set(clamped)
        finally:
            self._syncing_seek_slider = False

    def on_seek_change(self, val: float):
        if self._syncing_seek_slider:
            return
        clamped = max(0.0, min(1.0, _to_float(val, 0.0)))
        self.progress.set(clamped)

        with self._lock:
            session = self.session
            t_idx = _to_int(self.current_track_idx, 0)
            playing = self.is_playing
            mode = self.loop_mode

        if not session or not (0 <= t_idx < len(session.tracks)):
            return

        track = session.tracks[t_idx]
        dur = max(0.05, _to_float(track.duration, 0.05))
        target_sec = clamped * dur

        with self._lock:
            self.track_elapsed = target_sec
            self._seek_requested = True
            self._gapless_transition = False

        loop_suffix = self._t("status_loop_suffix", mode=self._loop_key_to_display(mode)) if mode != "off" else ""
        state_prefix = self._t("status_seeking_track") if playing else self._t("status_position_set")
        self.lbl_status.configure(
            text=self._t(
                "status_track_pos",
                prefix=state_prefix,
                idx=t_idx,
                name=track.name,
                cur=target_sec,
                dur=dur,
                loop=loop_suffix,
            )
        )

    def on_export_track_flac(self):
        if self.is_exporting:
            self.lbl_status.configure(text=self._t("status_export_running"))
            return
        if not self.session or not self.session.tracks:
            self.lbl_status.configure(text=self._t("status_no_session_track"))
            return

        with self._lock:
            t_idx = _to_int(self.current_track_idx, 0)
            vol = _to_float(self.master_vol, 0.7)
            pan = max(-1.0, min(1.0, _to_float(self.pan, 0.0)))

        vol_choice = self._ask_export_volume(vol)
        if vol_choice is None:
            return
        export_gain, export_pct = vol_choice

        if not (0 <= t_idx < len(self.session.tracks)):
            t_idx = 0
        track = self.session.tracks[t_idx]

        session_dir = get_session_export_dir(self.last_dir, self.session.name)
        default_name = f"{t_idx:02d}_{sanitize_filename(track.name)}.flac"
        target_path = filedialog.asksaveasfilename(
            parent=self,
            title=self._t("dialog_save_track_title"),
            initialdir=session_dir,
            initialfile=default_name,
            defaultextension=".flac",
            filetypes=[(self._t("filter_flac"), "*.flac"), (self._t("filter_all_files"), "*.*")],
        )
        if not target_path:
            return

        abs_target = os.path.abspath(target_path)
        if not abs_target.lower().endswith(".flac"):
            abs_target += ".flac"
        if os.path.dirname(abs_target) == os.path.abspath(self.last_dir):
            abs_target = os.path.join(session_dir, os.path.basename(abs_target))

        self.last_dir = os.path.dirname(os.path.dirname(abs_target)) or os.path.dirname(abs_target)
        self._persist_current_settings()
        self._start_flac_export_thread(
            [track],
            abs_target,
            vol,
            pan,
            label=f"Track {t_idx:02d}: {track.name}",
            export_gain=export_gain,
            export_pct=export_pct,
        )

    def on_export_all_tracks_flac(self):
        if self.is_exporting:
            self.lbl_status.configure(text=self._t("status_export_running"))
            return
        if not self.session or not self.session.tracks:
            self.lbl_status.configure(text=self._t("status_no_session_batch"))
            return

        with self._lock:
            vol = _to_float(self.master_vol, 0.7)
            pan = max(-1.0, min(1.0, _to_float(self.pan, 0.0)))

        vol_choice = self._ask_export_volume(vol)
        if vol_choice is None:
            return
        export_gain, export_pct = vol_choice

        base_start_dir = self.last_dir if os.path.isdir(self.last_dir) else os.path.expanduser("~")
        chosen_base_dir = filedialog.askdirectory(
            parent=self,
            title=self._t("dialog_select_base_dir"),
            initialdir=base_start_dir,
            mustexist=True,
        )
        if not chosen_base_dir:
            return

        abs_base_dir = os.path.abspath(chosen_base_dir)
        session_folder_name = sanitize_filename(self.session.name)
        if os.path.basename(abs_base_dir) == session_folder_name:
            session_dir = abs_base_dir
            self.last_dir = os.path.dirname(abs_base_dir) or abs_base_dir
        else:
            session_dir = get_session_export_dir(abs_base_dir, self.session.name)
            self.last_dir = abs_base_dir

        os.makedirs(session_dir, exist_ok=True)
        self._persist_current_settings()
        self._start_batch_flac_export_thread(
            list(self.session.tracks), session_dir, vol, pan, export_gain=export_gain, export_pct=export_pct
        )

    def on_export_session_flac(self):
        if self.is_exporting:
            self.lbl_status.configure(text=self._t("status_export_running"))
            return
        if not self.session or not self.session.tracks:
            self.lbl_status.configure(text=self._t("status_no_session_session"))
            return

        with self._lock:
            vol = _to_float(self.master_vol, 0.7)
            pan = max(-1.0, min(1.0, _to_float(self.pan, 0.0)))

        vol_choice = self._ask_export_volume(vol)
        if vol_choice is None:
            return
        export_gain, export_pct = vol_choice

        session_dir = get_session_export_dir(self.last_dir, self.session.name)
        default_name = f"{sanitize_filename(self.session.name)}_session.flac"
        target_path = filedialog.asksaveasfilename(
            parent=self,
            title=self._t("dialog_save_session_title"),
            initialdir=session_dir,
            initialfile=default_name,
            defaultextension=".flac",
            filetypes=[(self._t("filter_flac"), "*.flac"), (self._t("filter_all_files"), "*.*")],
        )
        if not target_path:
            return

        abs_target = os.path.abspath(target_path)
        if not abs_target.lower().endswith(".flac"):
            abs_target += ".flac"
        if os.path.dirname(abs_target) == os.path.abspath(self.last_dir):
            abs_target = os.path.join(session_dir, os.path.basename(abs_target))

        self.last_dir = os.path.dirname(os.path.dirname(abs_target)) or os.path.dirname(abs_target)
        self._persist_current_settings()
        self._start_flac_export_thread(
            list(self.session.tracks),
            abs_target,
            vol,
            pan,
            label=f"Session: {self.session.name}",
            export_gain=export_gain,
            export_pct=export_pct,
        )

    def _start_batch_flac_export_thread(
        self,
        tracks: List[TrackConfig],
        session_dir: str,
        master_vol: float,
        pan: float = 0.0,
        export_gain: float = 1.0,
        export_pct: int = 70,
    ):
        self.is_exporting = True
        total = len(tracks)
        lang_snap = self.language
        self._set_seek_ui(0.0)
        self.lbl_status.configure(text=self._t("status_batch_start", total=total, pct=export_pct, dir=session_dir))

        def _worker():
            try:
                for idx, track in enumerate(tracks, start=1):
                    out_name = f"{idx - 1:02d}_{sanitize_filename(track.name)}.flac"
                    out_path = os.path.join(session_dir, out_name)
                    audio = render_tracks_stereo(
                        [track], self.sample_rate, master_vol, pan=pan, lang=lang_snap, export_gain=export_gain
                    )
                    write_flac_file(out_path, audio, self.sample_rate, lang=lang_snap)
                    ratio = idx / max(1, total)
                    self.after(
                        0,
                        lambda r=ratio, i=idx, n=total, fn=out_name, p=export_pct: (
                            self._set_seek_ui(r),
                            self.lbl_status.configure(
                                text=self._t("status_batch_progress", idx=i, total=n, pct=p, filename=fn)
                            ),
                        ),
                    )
            except Exception as exc:
                self.after(
                    0,
                    lambda e=exc: self.lbl_status.configure(text=self._t("status_batch_failed", error=e)),
                )
            else:
                self.after(
                    0,
                    lambda d=session_dir, n=total: self.lbl_status.configure(
                        text=self._t("status_batch_done", total=n, dir=d)
                    ),
                )
            finally:
                self.after(0, lambda: setattr(self, "is_exporting", False))

        threading.Thread(target=_worker, daemon=True).start()

    def _start_flac_export_thread(
        self,
        tracks: List[TrackConfig],
        target_path: str,
        master_vol: float,
        pan: float,
        label: str,
        export_gain: float = 1.0,
        export_pct: int = 70,
    ):
        self.is_exporting = True
        lang_snap = self.language
        self.lbl_status.configure(text=self._t("status_exporting_single", label=label, pct=export_pct))

        def _worker():
            try:
                audio = render_tracks_stereo(
                    tracks, self.sample_rate, master_vol, pan=pan, lang=lang_snap, export_gain=export_gain
                )
                write_flac_file(target_path, audio, self.sample_rate, lang=lang_snap)
            except Exception as exc:
                self.after(
                    0,
                    lambda e=exc: self.lbl_status.configure(text=self._t("status_export_failed", error=e)),
                )
            else:
                self.after(
                    0,
                    lambda p=target_path: self.lbl_status.configure(
                        text=self._t("status_export_saved", filename=os.path.basename(p), path=p)
                    ),
                )
            finally:
                self.after(0, lambda: setattr(self, "is_exporting", False))

        threading.Thread(target=_worker, daemon=True).start()

    @staticmethod
    def _patch_scrollable_wheel_safety(scrollable: ctk.CTkScrollableFrame):
        """Prevents AttributeError ('str' object has no attribute 'master') on invalid event.widget."""
        orig_wheel_all = scrollable._mouse_wheel_all
        orig_check_valid = scrollable._check_if_valid_scroll

        def _is_real_widget(candidate) -> bool:
            if candidate is None or isinstance(candidate, str):
                return False
            if not hasattr(candidate, "master") or not hasattr(candidate, "winfo_exists"):
                return False
            try:
                return bool(candidate.winfo_exists())
            except Exception:
                return False

        def _safe_check_if_valid_scroll(widget):
            if not _is_real_widget(widget):
                return False
            return orig_check_valid(widget)

        def _safe_mouse_wheel_all(event):
            w = getattr(event, "widget", None)
            if not _is_real_widget(w):
                return
            return orig_wheel_all(event)

        scrollable._check_if_valid_scroll = _safe_check_if_valid_scroll
        scrollable._mouse_wheel_all = _safe_mouse_wheel_all

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        top_frame = ctk.CTkFrame(master=self)
        top_frame.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        top_frame.grid_columnconfigure(2, weight=1)

        self.btn_open = ctk.CTkButton(
            master=top_frame, text=self._t("btn_open_session"), command=self.on_open_file
        )
        self.btn_open.grid(row=0, column=0, padx=(10, 5), pady=10)

        self.btn_create = ctk.CTkButton(
            master=top_frame, text=self._t("btn_create_session"), command=self.open_session_creator
        )
        self.btn_create.grid(row=0, column=1, padx=5, pady=10)

        self.lbl_session = ctk.CTkLabel(
            master=top_frame,
            text=self._t("no_session_loaded"),
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.lbl_session.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        ctrl_frame = ctk.CTkFrame(master=self)
        ctrl_frame.grid(row=1, column=0, padx=16, pady=8, sticky="ew")
        ctrl_frame.grid_columnconfigure(4, weight=1)

        self.btn_play = ctk.CTkButton(
            master=ctrl_frame, text=self._t("btn_start"), width=86, command=self.on_start_click
        )
        self.btn_play.grid(row=0, column=0, rowspan=2, padx=(10, 5), pady=10)

        self.btn_pause = ctk.CTkButton(
            master=ctrl_frame, text=self._t("btn_pause"), width=86, command=self.on_pause_click
        )
        self.btn_pause.grid(row=0, column=1, rowspan=2, padx=5, pady=10)

        self.btn_stop = ctk.CTkButton(
            master=ctrl_frame, text=self._t("btn_stop"), width=86, command=self.on_stop_click
        )
        self.btn_stop.grid(row=0, column=2, rowspan=2, padx=5, pady=10)

        self.loop_switch = ctk.CTkSegmentedButton(
            master=ctrl_frame,
            values=self._loop_display_values(),
            command=self.on_loop_change,
        )
        self.loop_switch.set(self._loop_key_to_display(self.loop_mode))
        self.loop_switch.grid(row=0, column=3, rowspan=2, padx=(10, 8), pady=10)

        initial_vol_pct = int(round(self.master_vol * 100))
        self.lbl_vol = ctk.CTkLabel(master=ctrl_frame, text=f"Vol: {initial_vol_pct}%", width=72, anchor="e")
        self.lbl_vol.grid(row=0, column=4, padx=(4, 4), pady=(8, 2), sticky="e")

        self.slider_vol = ctk.CTkSlider(master=ctrl_frame, from_=0.0, to=1.0, width=120, command=self.on_vol_change)
        self.slider_vol.set(self.master_vol)
        self.slider_vol.bind("<ButtonRelease-1>", self.on_vol_release)
        self.slider_vol.grid(row=0, column=5, padx=(0, 8), pady=(8, 2))

        self.lbl_pan = ctk.CTkLabel(master=ctrl_frame, text=_format_pan_label(self.pan), width=72, anchor="e")
        self.lbl_pan.grid(row=1, column=4, padx=(4, 4), pady=(2, 8), sticky="e")

        self.slider_pan = CenterBalanceSlider(
            ctrl_frame,
            from_=-1.0,
            to=1.0,
            width=120,
            height=20,
            command=self.on_pan_change,
        )
        self.slider_pan.set(self.pan)
        self.slider_pan.bind("<ButtonRelease-1>", self.on_pan_release)
        self.slider_pan.bind("<Double-Button-1>", self.on_pan_reset)
        self.slider_pan.grid(row=1, column=5, padx=(0, 8), pady=(2, 8))

        self.vu_meter = StereoVuMeter(ctrl_frame, width=230, height=56, gain=2.0)
        self.vu_meter.grid(row=0, column=6, rowspan=2, padx=(4, 10), pady=6)

        main_frame = ctk.CTkFrame(master=self)
        main_frame.grid(row=2, column=0, padx=16, pady=8, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        self.track_list_frame = ctk.CTkScrollableFrame(master=main_frame, label_text=self._t("tracks_label"))
        self.track_list_frame.grid(row=0, column=0, padx=(10, 6), pady=10, sticky="nsew")
        self._patch_scrollable_wheel_safety(self.track_list_frame)

        self.detail_box = ctk.CTkTextbox(master=main_frame, font=ctk.CTkFont(family="Consolas", size=12))
        self.detail_box.grid(row=0, column=1, padx=(6, 10), pady=10, sticky="nsew")
        self.detail_box.configure(state="disabled")

        prog_frame = ctk.CTkFrame(master=self)
        prog_frame.grid(row=3, column=0, padx=16, pady=(8, 16), sticky="ew")
        prog_frame.grid_columnconfigure(0, weight=1)

        self.progress = ctk.CTkProgressBar(master=prog_frame)
        self.progress.set(0.0)
        self.progress.grid(row=0, column=0, padx=12, pady=(10, 2), sticky="ew")

        self.slider_seek = ctk.CTkSlider(
            master=prog_frame, from_=0.0, to=1.0, number_of_steps=1000, command=self.on_seek_change
        )
        self.slider_seek.set(0.0)
        self.slider_seek.grid(row=1, column=0, padx=10, pady=(2, 4), sticky="ew")

        self.lbl_status = ctk.CTkLabel(master=prog_frame, text=self._t("status_ready"), anchor="w")
        self.lbl_status.grid(row=2, column=0, padx=12, pady=(0, 10), sticky="ew")

        self.track_buttons: List[ctk.CTkButton] = []

    def on_loop_change(self, mode_label: str):
        valid_key = self._loop_display_to_key(mode_label)
        with self._lock:
            self.loop_mode = valid_key
        self._persist_current_settings()
        self.lbl_status.configure(text=self._t("status_loop_mode", mode=self._loop_key_to_display(valid_key)))

    def on_open_file(self):
        start_dir = self.last_dir if os.path.isdir(self.last_dir) else os.path.expanduser("~")
        filepath = filedialog.askopenfilename(
            parent=self,
            title=self._t("dialog_open_title"),
            initialdir=start_dir,
            filetypes=[
                (self._t("filter_all_supported"), "*.SmrtStm4 *.alass2 *.flac *.m3u *.m3u8 *.xml *.seq *.sexp *.lisp"),
                (self._t("filter_flac"), "*.flac"),
                (self._t("filter_alass2"), "*.alass2"),
                (self._t("filter_smartstim"), "*.SmrtStm4 *.xml"),
                (self._t("filter_m3u"), "*.m3u *.m3u8"),
                (self._t("filter_all_files"), "*.*"),
            ],
        )
        if filepath:
            abs_fp = os.path.abspath(filepath)
            self.last_dir = os.path.dirname(abs_fp)
            self.last_session = abs_fp
            self._persist_current_settings()
            self.load_file(abs_fp, preferred_track_idx=0)

    def load_file(self, filepath: str, preferred_track_idx: Optional[int] = None):
        self.on_stop_click(reset_track=False)
        abs_fp = os.path.abspath(filepath)
        try:
            session = load_session_or_playlist(abs_fp)
        except Exception as exc:
            self.lbl_status.configure(text=self._t("status_load_error", error=exc))
            return

        target_idx = self.last_track_idx if preferred_track_idx is None else _to_int(preferred_track_idx, 0)
        if len(session.tracks) > 0:
            if not (0 <= target_idx < len(session.tracks)):
                target_idx = 0
        else:
            target_idx = 0

        self.last_session = abs_fp
        self.last_dir = os.path.dirname(abs_fp)
        self.last_track_idx = target_idx

        with self._lock:
            self.session = session
            self.current_track_idx = target_idx
            self.track_elapsed = 0.0
            self._seek_requested = False
            self._gapless_transition = False
            self._latest_meter_levels = (0.0, 0.0)

        self._persist_current_settings()

        total_sec = sum(_to_float(t.duration, 0.0) for t in session.tracks)
        kind_label = self._t("kind_playlist") if session.is_playlist else self._t("kind_tracks")
        self.lbl_session.configure(
            text=self._t(
                "session_header",
                name=session.name,
                count=len(session.tracks),
                kind=kind_label,
                total=_format_mm_ss(total_sec),
            )
        )

        for btn in self.track_buttons:
            btn.destroy()
        self.track_buttons.clear()

        for idx, tr in enumerate(session.tracks):
            dur = max(0.05, _to_float(tr.duration, 0.05))
            label = f"{idx:02d} | {tr.name} ({dur:.1f}s)"
            btn = ctk.CTkButton(
                master=self.track_list_frame,
                text=label,
                anchor="w",
                fg_color=("gray75", "gray25"),
                command=lambda i=idx: self.select_and_play_track(i),
            )
            btn.pack(fill="x", padx=4, pady=2)
            self.track_buttons.append(btn)

        self._highlight_track(target_idx, scroll_into_view=False)
        self._reset_track_scroll()
        self._update_details(target_idx)
        self._set_seek_ui(0.0)
        self.lbl_status.configure(text=self._t("status_loaded", filename=os.path.basename(abs_fp)))

    def _highlight_track(self, idx: int, scroll_into_view: bool = True):
        for i, btn in enumerate(self.track_buttons):
            if i == idx:
                btn.configure(fg_color=("#1f6aa5", "#1f6aa5"))
            else:
                btn.configure(fg_color=("gray75", "gray25"))
        if scroll_into_view:
            self._scroll_track_into_view(idx)

    def _update_details(self, idx: int):
        if not self.session or not (0 <= idx < len(self.session.tracks)):
            return
        tr = self.session.tracks[idx]
        dur = max(0.05, _to_float(tr.duration, 0.05))
        lines = [
            self._t("detail_track_header", index=tr.index, name=tr.name),
            self._t("detail_duration", dur=dur),
            "-" * 38,
        ]
        if tr.audio_path:
            exists_str = self._t("yes") if os.path.isfile(tr.audio_path) else self._t("no")
            lines.append(self._t("detail_source", path=tr.audio_path))
            lines.append(self._t("detail_exists", ans=exists_str))
        else:
            for st in tr.subtracks:
                lines.append(self._t("detail_subtrack", index=st.index))
                lines.append(f"  BF (Hz):   {st.bf if st.bf is not None else '-'}")
                lines.append(f"  Vol / C:   {st.vol} / {st.vol_c}")
                if st.t_on is not None or st.t_off is not None:
                    lines.append(f"  Gate:      TOn={st.t_on}s, TOff={st.t_off}s")
                if st.bfm_act:
                    lines.append(f"  BFM:       MF={st.bfm_mf} Hz, MD={st.bfm_md}")
                if st.pam_act:
                    lines.append(f"  PAM:       MF={st.pam_mf} Hz, MD={st.pam_md}")
                lines.append("")

        self.detail_box.configure(state="normal")
        self.detail_box.delete("1.0", "end")
        self.detail_box.insert("1.0", "\n".join(lines))
        self.detail_box.configure(state="disabled")

    def on_vol_change(self, val: float):
        safe_val = max(0.0, min(1.0, _to_float(val, 0.7)))
        with self._lock:
            self.master_vol = safe_val
        self.lbl_vol.configure(text=f"Vol: {int(round(safe_val * 100))}%")

    def on_vol_release(self, _event=None):
        self._persist_current_settings()

    def on_pan_change(self, val: float):
        safe_pan = max(-1.0, min(1.0, _to_float(val, 0.0)))
        if abs(safe_pan) < 0.02:
            safe_pan = 0.0
            self.slider_pan.set(0.0)
        with self._lock:
            self.pan = safe_pan
        self.lbl_pan.configure(text=_format_pan_label(safe_pan))

    def on_pan_release(self, _event=None):
        self._persist_current_settings()

    def on_pan_reset(self, _event=None):
        self.slider_pan.set(0.0)
        self.on_pan_change(0.0)
        self._persist_current_settings()

    def select_and_play_track(self, idx: int):
        if not self.session or not (0 <= idx < len(self.session.tracks)):
            return
        with self._lock:
            self.current_track_idx = idx
            self.track_elapsed = 0.0
            self._seek_requested = True
            self._gapless_transition = False
        self.last_track_idx = idx
        self._persist_current_settings()
        self._highlight_track(idx, scroll_into_view=True)
        self._update_details(idx)
        self._set_seek_ui(0.0)
        self.on_start_click()

    def on_start_click(self):
        if not self.session or not self.session.tracks:
            return
        with self._lock:
            if not (0 <= self.current_track_idx < len(self.session.tracks)):
                self.current_track_idx = 0
            start_idx = self.current_track_idx
            self.is_playing = True
            self._seek_requested = True
            self._gapless_transition = False
            self._stop_event.clear()
            need_thread = self._play_thread is None or not self._play_thread.is_alive()

        self.last_track_idx = start_idx
        self._persist_current_settings(min_interval_sec=1.0)
        self._highlight_track(start_idx, scroll_into_view=True)
        self._update_details(start_idx)
        self.lbl_status.configure(text=self._t("status_playback_started"))
        if need_thread:
            self._play_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._play_thread.start()

    def on_pause_click(self):
        with self._lock:
            self.is_playing = False
            self._latest_meter_levels = (0.0, 0.0)
        self._persist_current_settings()
        self.vu_meter.reset()
        self.lbl_status.configure(text=self._t("status_paused"))

    def on_stop_click(self, reset_track: bool = False):
        with self._lock:
            self.is_playing = False
            self.track_elapsed = 0.0
            self._seek_requested = True
            self._gapless_transition = False
            if reset_track:
                self.current_track_idx = 0
            target_idx = (
                self.current_track_idx
                if (self.session and 0 <= self.current_track_idx < len(self.session.tracks))
                else 0
            )
            self._latest_meter_levels = (0.0, 0.0)
        self._stop_event.set()
        if self._play_thread and self._play_thread.is_alive() and threading.current_thread() is not self._play_thread:
            self._play_thread.join(timeout=0.5)
        self._set_seek_ui(0.0)
        self.vu_meter.reset()
        if self.track_buttons:
            self._highlight_track(target_idx, scroll_into_view=bool(reset_track))
            self._update_details(target_idx)
        if reset_track:
            self._persist_current_settings()
        self.lbl_status.configure(text=self._t("status_stopped"))

    def _playback_loop(self):
        sr = int(max(8000, _to_int(self.sample_rate, DEFAULT_SAMPLE_RATE)))
        bs = int(max(64, _to_int(BLOCKSIZE, 8192)))
        last_ui_track = -1
        active_clip: Optional[AudioFileClip] = None
        last_ui_update = 0.0
        dbg_t_idx = -1
        dbg_vol = 0.0

        def _close_clip():
            nonlocal active_clip
            if active_clip is not None:
                active_clip.close()
                active_clip = None

        try:
            with sd.OutputStream(
                samplerate=sr,
                channels=2,
                dtype="float32",
                blocksize=bs,
            ) as stream:
                self.synth.reset_for_track(2)

                while not self._stop_event.is_set():
                    with self._lock:
                        playing = bool(self.is_playing)
                        session = self.session
                        t_idx = _to_int(self.current_track_idx, 0)
                        vol = float(max(0.0, min(1.0, _to_float(self.master_vol, 0.7))))
                        pan = float(max(-1.0, min(1.0, _to_float(self.pan, 0.0))))
                        loop_mode = self.loop_mode
                        seek_now = bool(self._seek_requested)
                        gapless_now = bool(self._gapless_transition)
                        cur_elapsed = float(max(0.0, _to_float(self.track_elapsed, 0.0)))
                        lang_now = self.language

                    dbg_t_idx = t_idx
                    dbg_vol = vol

                    if not playing or not session:
                        time.sleep(0.04)
                        continue

                    if t_idx >= len(session.tracks):
                        _close_clip()
                        if loop_mode == "session" and len(session.tracks) > 0:
                            with self._lock:
                                self.current_track_idx = 0
                                self.track_elapsed = 0.0
                                self._seek_requested = True
                                self._gapless_transition = True
                            last_ui_track = -1
                            continue
                        with self._lock:
                            self.is_playing = False
                            self.current_track_idx = 0
                            self.track_elapsed = 0.0
                            self._seek_requested = False
                            self._gapless_transition = False
                            self._latest_meter_levels = (0.0, 0.0)
                        self.after(
                            0,
                            lambda: (
                                self._set_seek_ui(0.0),
                                self.vu_meter.reset(),
                                self.lbl_status.configure(text=self._t("status_session_finished")),
                            ),
                        )
                        break

                    track = session.tracks[t_idx]
                    track_dur = float(max(0.05, _to_float(track.duration, 0.05)))
                    track.duration = track_dur
                    track_changed = t_idx != last_ui_track
                    if track_changed:
                        _close_clip()
                        last_ui_track = t_idx
                        if track.audio_path:
                            active_clip = AudioFileClip(track.audio_path, target_sample_rate=sr, lang=lang_now)
                            track_dur = float(max(0.05, _to_float(active_clip.duration, 0.05)))
                            track.duration = track_dur
                            active_clip.seek_to(cur_elapsed)
                        elif gapless_now:
                            self.synth.continue_for_track(max(2, len(track.subtracks)), carry_sec=cur_elapsed)
                        else:
                            self.synth.seek_to(cur_elapsed, track)
                        with self._lock:
                            self._seek_requested = False
                            self._gapless_transition = False
                    elif seek_now:
                        if active_clip is not None:
                            active_clip.seek_to(cur_elapsed)
                        else:
                            self.synth.seek_to(cur_elapsed, track)
                        with self._lock:
                            self._seek_requested = False
                            self._gapless_transition = False

                    if active_clip is not None:
                        rem_frames = max(0, int(round((track_dur - cur_elapsed) * sr)))
                        read_frames = min(bs, max(1, rem_frames))
                        scaled_audio, raw_audio = active_clip.read_block(read_frames, vol)
                        stereo_scaled = _apply_pan_stereo(_to_float32_stereo(scaled_audio, read_frames), pan)
                        stereo_raw = _apply_pan_stereo(_to_float32_stereo(raw_audio, read_frames), pan)
                        stream.write(stereo_scaled)

                        meter_scale = FLAC_METER_SCALE if active_clip.is_flac else 0.5
                        left_lvl = float(np.max(np.abs(stereo_raw[:, 0]))) * meter_scale
                        right_lvl = float(np.max(np.abs(stereo_raw[:, 1]))) * meter_scale
                        finished_now = active_clip.cursor >= active_clip.total_frames

                        track_finished = False
                        next_elapsed = cur_elapsed + (len(stereo_scaled) / sr)
                        overflow_sec = max(0.0, next_elapsed - track_dur)
                        with self._lock:
                            if self._seek_requested:
                                continue
                            self._latest_meter_levels = (left_lvl, right_lvl)
                            if finished_now or next_elapsed >= track_dur:
                                track_finished = True
                                if loop_mode == "track":
                                    self.track_elapsed = 0.0
                                    self._gapless_transition = True
                                else:
                                    self.current_track_idx += 1
                                    self.track_elapsed = overflow_sec
                                    self._gapless_transition = True
                                elapsed = track_dur
                            else:
                                self.track_elapsed = next_elapsed
                                elapsed = next_elapsed

                        if track_finished:
                            if loop_mode == "track":
                                active_clip.seek_to(0.0)
                                elapsed = 0.0
                            else:
                                _close_clip()
                    else:
                        rem_sec = max(0.0, track_dur - cur_elapsed)
                        rem_frames = max(1, int(np.ceil(rem_sec * sr)))
                        render_frames = min(bs, rem_frames)
                        scaled_audio, raw_audio = self.synth.render_block(track, render_frames, vol)
                        stereo_scaled = _apply_pan_stereo(_to_float32_stereo(scaled_audio, render_frames), pan)
                        stereo_raw = _apply_pan_stereo(_to_float32_stereo(raw_audio, render_frames), pan)
                        stream.write(stereo_scaled)

                        left_lvl = float(np.max(np.abs(stereo_raw[:, 0])))
                        right_lvl = float(np.max(np.abs(stereo_raw[:, 1])))

                        track_finished = False
                        next_elapsed = cur_elapsed + (render_frames / sr)
                        overflow_sec = max(0.0, next_elapsed - track_dur)
                        with self._lock:
                            if self._seek_requested:
                                continue
                            self._latest_meter_levels = (left_lvl, right_lvl)
                            if next_elapsed >= track_dur:
                                track_finished = True
                                if loop_mode == "track":
                                    self.track_elapsed = 0.0
                                    self._gapless_transition = True
                                else:
                                    self.current_track_idx += 1
                                    self.track_elapsed = overflow_sec
                                    self._gapless_transition = True
                                elapsed = track_dur
                            else:
                                self.track_elapsed = next_elapsed
                                elapsed = next_elapsed

                        if track_finished and loop_mode == "track":
                            self.synth.continue_for_track(max(2, len(track.subtracks)), carry_sec=0.0)
                            elapsed = 0.0

                    if track_changed:
                        self.after(
                            0,
                            lambda i=t_idx: (
                                self._highlight_track(i, scroll_into_view=True),
                                self._update_details(i),
                            ),
                        )

                    now = time.monotonic()
                    if now - last_ui_update >= 0.15 or track_finished:
                        last_ui_update = now
                        ratio = min(1.0, elapsed / max(0.05, track_dur))
                        loop_suffix = (
                            self._t("status_loop_suffix", mode=self._loop_key_to_display(loop_mode))
                            if loop_mode != "off"
                            else ""
                        )
                        status_txt = self._t(
                            "status_playing_track",
                            idx=t_idx,
                            name=track.name,
                            cur=min(elapsed, track_dur),
                            dur=track_dur,
                            loop=loop_suffix,
                        )
                        self.after(
                            0,
                            lambda pr=ratio, s=status_txt: (
                                self._set_seek_ui(pr),
                                self.lbl_status.configure(text=s),
                            ),
                        )

        except Exception as exc:
            with self._lock:
                self.is_playing = False
                self._latest_meter_levels = (0.0, 0.0)
            diag = self._t(
                "status_audio_error",
                idx=dbg_t_idx,
                error=exc,
                sr=type(sr).__name__,
                bs=type(bs).__name__,
                vol=type(dbg_vol).__name__,
            )
            self.after(
                0,
                lambda msg=diag: (self.vu_meter.reset(), self.lbl_status.configure(text=msg)),
            )
        finally:
            _close_clip()


if __name__ == "__main__":
    default_path = ""
    app = EStimPlayerApp(
        initial_file=default_path if os.path.exists(default_path) else None,
        sample_rate=DEFAULT_SAMPLE_RATE,
    )

#Icon-Pfad ermitteln und laden (getrennt vom Start)

script_dir = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(script_dir, "/usr/share/pixmaps/e-stim-player.png")

if os.path.exists(icon_path):
    try:
        app.icon_image = tk.PhotoImage(file=icon_path)
        app.iconphoto(True, app.icon_image)
        print("Icon erfolgreich geladen.")
    except Exception as e:
        print(f"Fehler beim Laden des Icons (wird ignoriert): {e}")
else:
    print("Kein Icon gefunden, Programm startet normal.")

app.mainloop()
