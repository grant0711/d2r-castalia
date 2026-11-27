"""
castalia_hub/core.py — Shared engine for both `bin/d2r-campaign` CLI and `bin/d2r-launcher` GUI.
Implements:
  - Config & local capability token storage (tokens.json)
  - Crash-safe per-campaign save profile swapper (solo / campaign-<id>)
  - Multi-version GitHub Releases mod cache with SHA-256 verification
  - Campaign Hub REST API client
  - D2R / D2RLoader detection, clipboard Game ID copy, log-tail auto-go-live & post-exit telemetry
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from typing import Any, Dict, List, Optional, Tuple

from castalia_hub.d2s_telemetry import generate_dropin_character, parse_d2s_telemetry

REPO_ROOT = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
GITHUB_REPO = "grant0711/d2r-castalia"
DEFAULT_DATA_DIR = (
    os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "CastaliaHub")
    if sys.platform == "win32"
    else os.path.expanduser("~/.local/share/castalia-hub")
)
DEFAULT_API_URL = os.environ.get("CASTALIA_API_URL", "https://castalia-campaign-hub.d2rcastalia.workers.dev")

# Save extensions swapped per campaign profile (Settings.json stays global & untouched!)
CHAR_EXTS = (".d2s", ".key", ".ctl", ".map", ".ma0", ".ma1", ".ma2", ".ma3", ".ma4")
STASH_EXTS = (".d2i",)
SAVE_EXTS = CHAR_EXTS + STASH_EXTS
GAME_ID_LOG_RE = re.compile(r"(?:Game\s*ID|game_id|advertised_id)\s*[:=]\s*([A-Za-z0-9_-]{4,24})", re.I)
LISTENER_READY_RE = re.compile(r"Listener ready:\s*bound_port=(\d+)", re.I)


def _is_char_file(filename: str) -> bool:
    low = filename.lower()
    if low == "settings.json":
        return False
    return low.endswith(CHAR_EXTS)


def _is_stash_file(filename: str) -> bool:
    return filename.lower().endswith(STASH_EXTS)


def _is_save_file(filename: str) -> bool:
    low = filename.lower()
    if low == "settings.json":
        return False
    return low.endswith(SAVE_EXTS)


class CastaliaHub:
    """Unified core engine shared by CLI and Desktop GUI."""

    def __init__(
        self,
        data_dir: Optional[str] = None,
        api_url: Optional[str] = None,
        d2r_game_dir: Optional[str] = None,
        d2r_save_dir: Optional[str] = None,
    ):
        self.data_dir = os.path.abspath(data_dir or os.environ.get("CASTALIA_HUB_DIR") or DEFAULT_DATA_DIR)
        self.versions_dir = os.path.join(self.data_dir, "versions")
        self.profiles_dir = os.path.join(self.data_dir, "profiles")
        self.global_stash_dir = os.path.join(self.profiles_dir, "_global_stash")
        self.config_path = os.path.join(self.data_dir, "config.json")
        self.tokens_path = os.path.join(self.data_dir, "tokens.json")
        self.active_profile_path = os.path.join(self.data_dir, "active_profile.json")

        os.makedirs(self.versions_dir, exist_ok=True)
        os.makedirs(self.profiles_dir, exist_ok=True)
        os.makedirs(os.path.join(self.profiles_dir, "solo"), exist_ok=True)
        os.makedirs(self.global_stash_dir, exist_ok=True)

        self.config = self._load_json(self.config_path, default={})
        if api_url:
            self.config["api_url"] = api_url
        if d2r_game_dir:
            self.config["d2r_game_dir"] = d2r_game_dir
        if d2r_save_dir:
            self.config["d2r_save_dir"] = d2r_save_dir

        self.config.setdefault("api_url", DEFAULT_API_URL)
        self.config.setdefault("display_name", os.environ.get("USER") or "Wanderer")
        self.config.setdefault("d2r_game_dir", self._auto_detect_d2r_game_dir())
        self.config.setdefault("d2r_save_dir", self._auto_detect_d2r_save_dir())
        self._save_json(self.config_path, self.config)

    # ── JSON & Token Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _load_json(path: str, default: Any) -> Any:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return default
        return default

    @staticmethod
    def _save_json(path: str, data: Any) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        if os.name != "nt" and os.path.basename(path) == "tokens.json":
            os.chmod(tmp, 0o600)
        os.replace(tmp, path)

    def get_config(self) -> Dict[str, Any]:
        return dict(self.config)

    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        for k in ("api_url", "display_name", "d2r_game_dir", "d2r_save_dir", "host_connect_address"):
            if k in updates and updates[k] is not None:
                self.config[k] = str(updates[k]).strip()
        self._save_json(self.config_path, self.config)
        return self.get_config()

    def load_tokens(self) -> Dict[str, Dict[str, str]]:
        return self._load_json(self.tokens_path, default={})

    def save_token(self, campaign_id: str, key: str, value: str) -> None:
        tokens = self.load_tokens()
        tokens.setdefault(campaign_id, {})[key] = value
        self._save_json(self.tokens_path, tokens)

    def get_token(self, campaign_id: str, key: str) -> Optional[str]:
        return self.load_tokens().get(campaign_id, {}).get(key)

    def export_tokens_json(self) -> str:
        return json.dumps(self.load_tokens(), indent=2)

    def import_tokens_json(self, raw_json: str) -> int:
        incoming = json.loads(raw_json)
        if not isinstance(incoming, dict):
            raise ValueError("tokens.json must be a JSON object")
        tokens = self.load_tokens()
        count = 0
        for cid, entry in incoming.items():
            if isinstance(entry, dict):
                tokens.setdefault(cid, {}).update(entry)
                count += 1
        self._save_json(self.tokens_path, tokens)
        return count

    # ── D2R & D2RLoader Environment Detection ────────────────────────────────

    @staticmethod
    def _auto_detect_d2r_game_dir() -> str:
        if sys.platform == "win32":
            candidates = [
                r"C:\Program Files (x86)\Diablo II Resurrected",
                r"C:\Program Files\Diablo II Resurrected",
                r"C:\Games\Diablo II Resurrected",
                r"C:\Program Files (x86)\Steam\steamapps\common\Diablo II Resurrected",
                r"D:\Diablo II Resurrected",
                r"D:\Games\Diablo II Resurrected",
                r"D:\Battle.net\Diablo II Resurrected",
                r"D:\Program Files (x86)\Diablo II Resurrected",
                r"D:\Program Files\Diablo II Resurrected",
                r"D:\SteamLibrary\steamapps\common\Diablo II Resurrected",
                r"E:\Diablo II Resurrected",
                r"E:\Games\Diablo II Resurrected",
                r"E:\SteamLibrary\steamapps\common\Diablo II Resurrected",
                r"F:\SteamLibrary\steamapps\common\Diablo II Resurrected",
            ]
            for c in candidates:
                if os.path.isfile(os.path.join(c, "D2RLoader.exe")):
                    return c
        else:
            candidates = [
                os.path.join(REPO_ROOT, "game", "Diablo II Resurrected"),
                os.path.expanduser("~/games/d2r/game/Diablo II Resurrected"),
                r"C:\Program Files (x86)\Diablo II Resurrected",
            ]
        for c in candidates:
            if os.path.isdir(c):
                return c
        return candidates[0]

    @staticmethod
    def _auto_detect_d2r_save_dir() -> str:
        if sys.platform == "win32":
            win_save = os.path.join(
                os.path.expanduser("~"),
                "Saved Games",
                "Diablo II Resurrected",
                "mods",
                "castalia",
            )
            return win_save
        prefix = os.environ.get("D2R_PREFIX", "acct1")
        candidates = [
            os.path.join(
                REPO_ROOT,
                "prefixes",
                prefix,
                "pfx",
                "drive_c",
                "users",
                "steamuser",
                "Saved Games",
                "Diablo II Resurrected",
                "mods",
                "castalia",
            ),
            os.path.expanduser("~/Saved Games/Diablo II Resurrected/mods/castalia"),
        ]
        for c in candidates:
            if os.path.isdir(c):
                return c
        return candidates[0]

    def detect_d2r_env(self) -> Dict[str, Any]:
        game_dir = self.config.get("d2r_game_dir", "")
        save_dir = self.config.get("d2r_save_dir", "")
        loader_exe = os.path.join(game_dir, "D2RLoader.exe")
        loader_toml = os.path.join(game_dir, "d2rloader", "config", "d2rloader.toml")
        mod_dir = os.path.join(game_dir, "mods", "castalia", "castalia.mpq")
        ver_file = os.path.join(mod_dir, "castalia_version.json")
        installed_version = None
        if os.path.isfile(ver_file):
            installed_version = self._load_json(ver_file, {}).get("version")
        return {
            "d2r_game_dir": game_dir,
            "d2r_save_dir": save_dir,
            "game_dir_exists": os.path.isdir(game_dir),
            "d2rloader_found": os.path.isfile(loader_exe),
            "d2rloader_toml_found": os.path.isfile(loader_toml),
            "installed_mod_version": installed_version,
            "cached_versions": self.list_cached_versions(),
        }

    # ── Crash-Safe Per-Campaign Save Profile Swapper ─────────────────────────

    def profile_id_for(self, target: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_-]", "", str(target or "").strip())
        if not safe or safe == "solo":
            return "solo"
        return safe if safe.startswith("campaign-") else f"campaign-{safe}"

    def profile_dir_for(self, target: str) -> str:
        pid = self.profile_id_for(target)
        pdir = os.path.join(self.profiles_dir, pid)
        os.makedirs(pdir, exist_ok=True)
        return pdir

    def migrate_initial_solo_saves(self) -> int:
        """One-time safe import of pre-existing live saves into profiles/solo/."""
        if os.path.isfile(self.active_profile_path):
            return 0
        solo_dir = self.profile_dir_for("solo")
        if any(_is_save_file(f) for f in os.listdir(solo_dir)):
            return 0
        live_dir = self.config["d2r_save_dir"]
        if not os.path.isdir(live_dir):
            return 0
        copied = 0
        for fn in os.listdir(live_dir):
            if _is_char_file(fn):
                shutil.copy2(os.path.join(live_dir, fn), os.path.join(solo_dir, fn))
                copied += 1
            elif _is_stash_file(fn):
                dst_stash = os.path.join(self.global_stash_dir, fn)
                if not os.path.isfile(dst_stash):
                    shutil.copy2(os.path.join(live_dir, fn), dst_stash)
                    copied += 1
        return copied

    def _migrate_global_stash(self) -> None:
        """Ensure any legacy .d2i in profiles/solo/ or live saves is seeded into profiles/_global_stash/."""
        os.makedirs(self.global_stash_dir, exist_ok=True)
        if any(_is_stash_file(f) for f in os.listdir(self.global_stash_dir)):
            return
        solo_dir = self.profile_dir_for("solo")
        for sdir in (solo_dir, self.config.get("d2r_save_dir") or ""):
            if not sdir or not os.path.isdir(sdir):
                continue
            found = False
            for fn in os.listdir(sdir):
                if _is_stash_file(fn):
                    shutil.copy2(os.path.join(sdir, fn), os.path.join(self.global_stash_dir, fn))
                    found = True
            if found:
                # Remove legacy .d2i from solo_dir so _global_stash is the single source of truth
                if sdir == solo_dir:
                    for fn in os.listdir(solo_dir):
                        if _is_stash_file(fn):
                            os.remove(os.path.join(solo_dir, fn))
                return

    def recover_if_dirty(self) -> Optional[str]:
        """If active_profile.json exists (previous crash), sync live saves back and restore game_port."""
        if not os.path.isfile(self.active_profile_path):
            return None
        state = self._load_json(self.active_profile_path, {})
        pid = state.get("profile_id")
        stash_source = state.get("stash_source")
        if pid:
            self._sync_live_to_profile(pid, stash_source=stash_source)
        prev_port = state.get("prev_game_port")
        if isinstance(prev_port, int) and prev_port > 0:
            self.set_d2rloader_game_port(prev_port)
        os.remove(self.active_profile_path)
        return pid

    # Alias for clarity in callers & tests
    recover_dirty_profile = recover_if_dirty

    def _stash_dir_for(self, stash_source: Optional[str], profile_id: str) -> str:
        if stash_source == "_global_stash" or (stash_source is None and profile_id == "solo"):
            os.makedirs(self.global_stash_dir, exist_ok=True)
            return self.global_stash_dir
        return self.profile_dir_for(stash_source or profile_id)

    def _sync_live_to_profile(self, profile_id: str, stash_source: Optional[str] = None) -> int:
        live_dir = self.config["d2r_save_dir"]
        pdir = self.profile_dir_for(profile_id)
        sdir = self._stash_dir_for(stash_source, profile_id)
        if not os.path.isdir(live_dir):
            return 0
        # Sync character files (.d2s/.key/.ma*/.ctl) -> profile dir
        for fn in os.listdir(pdir):
            if _is_char_file(fn):
                os.remove(os.path.join(pdir, fn))
        # Sync shared stash files (.d2i) -> stash_source dir (_global_stash or campaign-<id>)
        for fn in os.listdir(sdir):
            if _is_stash_file(fn):
                os.remove(os.path.join(sdir, fn))
        count = 0
        for fn in os.listdir(live_dir):
            if _is_char_file(fn):
                shutil.copy2(os.path.join(live_dir, fn), os.path.join(pdir, fn))
                count += 1
            elif _is_stash_file(fn):
                shutil.copy2(os.path.join(live_dir, fn), os.path.join(sdir, fn))
                count += 1
        return count

    def swap_to_profile(self, target: str, shared_stash: bool = False) -> str:
        """
        Crash-safe swap: recover any dirty profile, clear live save files (preserving Settings.json),
        copy target character files + routed Shared Stash (.d2i from _global_stash when solo or
        shared_stash=True, else campaign-local isolated stash), and write active_profile.json lockfile.
        """
        self.migrate_initial_solo_saves()
        self._migrate_global_stash()
        self.recover_if_dirty()

        pid = self.profile_id_for(target)
        pdir = self.profile_dir_for(pid)
        use_global_stash = (pid == "solo") or bool(shared_stash)
        stash_source = "_global_stash" if use_global_stash else pid
        sdir = self._stash_dir_for(stash_source, pid)

        live_dir = self.config["d2r_save_dir"]
        os.makedirs(live_dir, exist_ok=True)

        for fn in os.listdir(live_dir):
            if _is_save_file(fn):
                os.remove(os.path.join(live_dir, fn))

        for fn in os.listdir(pdir):
            if _is_char_file(fn):
                shutil.copy2(os.path.join(pdir, fn), os.path.join(live_dir, fn))

        for fn in os.listdir(sdir):
            if _is_stash_file(fn):
                shutil.copy2(os.path.join(sdir, fn), os.path.join(live_dir, fn))

        self._save_json(
            self.active_profile_path,
            {
                "profile_id": pid,
                "stash_source": stash_source,
                "switched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "pid": os.getpid(),
            },
        )
        return pid

    def _restore_solo_to_live(self) -> int:
        """Restore profiles/solo/ characters + _global_stash .d2i into the live D2R save dir."""
        self._migrate_global_stash()
        live_dir = self.config["d2r_save_dir"]
        solo_dir = self.profile_dir_for("solo")
        os.makedirs(live_dir, exist_ok=True)
        for fn in os.listdir(live_dir):
            if _is_save_file(fn):
                os.remove(os.path.join(live_dir, fn))
        copied = 0
        for fn in os.listdir(solo_dir):
            if _is_char_file(fn):
                shutil.copy2(os.path.join(solo_dir, fn), os.path.join(live_dir, fn))
                copied += 1
        for fn in os.listdir(self.global_stash_dir):
            if _is_stash_file(fn):
                shutil.copy2(os.path.join(self.global_stash_dir, fn), os.path.join(live_dir, fn))
                copied += 1
        return copied

    def sync_back_active_profile(self) -> Optional[str]:
        """Sync live saves back to the active profile (+ stash_source) and clear active_profile.json."""
        if not os.path.isfile(self.active_profile_path):
            return None
        state = self._load_json(self.active_profile_path, {})
        pid = state.get("profile_id")
        stash_source = state.get("stash_source")
        if pid:
            self._sync_live_to_profile(pid, stash_source=stash_source)
        os.remove(self.active_profile_path)
        return pid

    def list_profile_chars(self, target: str) -> List[Dict[str, Any]]:
        """List all .d2s characters (with telemetry & build summary) in a profile."""
        if target == "solo":
            self.migrate_initial_solo_saves()
        pdir = self.profile_dir_for(target)
        gdir = self.config.get("d2r_game_dir")
        chars = []
        for fn in sorted(os.listdir(pdir)):
            if fn.lower().endswith(".d2s"):
                full = os.path.join(pdir, fn)
                try:
                    chars.append(parse_d2s_telemetry(full, d2r_game_dir=gdir))
                except Exception as e:
                    chars.append({"char_name": os.path.splitext(fn)[0], "error": str(e), "path": full})
        chars.sort(key=lambda c: -float(c.get("mtime", 0)))
        return chars

    def list_importable_chars(self, campaign_id: str) -> List[Dict[str, Any]]:
        """
        Scan Solo, Live D2R saves, and other Campaign profiles for existing .d2s characters
        that are not yet present in `campaign_id`, so a player can 1-click import them.
        """
        target_dir = self.profile_dir_for(campaign_id)
        existing_names = {
            os.path.splitext(f)[0].lower()
            for f in os.listdir(target_dir)
            if f.lower().endswith(".d2s")
        }
        gdir = self.config.get("d2r_game_dir")

        sources: List[Tuple[str, str]] = []
        live_dir = self.config.get("d2r_save_dir") or ""
        if live_dir and os.path.isdir(live_dir):
            sources.append(("Live Saves", live_dir))
        solo_dir = os.path.join(self.profiles_dir, "solo")
        if os.path.isdir(solo_dir):
            sources.append(("Solo", solo_dir))
        if os.path.isdir(self.profiles_dir):
            target_pid = self.profile_id_for(campaign_id)
            for entry in sorted(os.listdir(self.profiles_dir)):
                if entry in ("solo", target_pid):
                    continue
                cdir = os.path.join(self.profiles_dir, entry)
                if os.path.isdir(cdir):
                    label = entry.replace("campaign-", "Campaign: ")
                    sources.append((label, cdir))

        seen_paths: set = set()
        seen_names: set = set()
        out: List[Dict[str, Any]] = []
        for label, sdir in sources:
            for fn in sorted(os.listdir(sdir)):
                if not fn.lower().endswith(".d2s"):
                    continue
                stem = os.path.splitext(fn)[0].lower()
                if stem in existing_names or stem in seen_names:
                    continue
                full = os.path.abspath(os.path.join(sdir, fn))
                if full in seen_paths or not os.path.isfile(full):
                    continue
                seen_paths.add(full)
                seen_names.add(stem)
                try:
                    info = parse_d2s_telemetry(full, d2r_game_dir=gdir)
                    info["source_label"] = label
                    info["source_path"] = full
                    out.append(info)
                except Exception:
                    continue
        out.sort(key=lambda c: -float(c.get("mtime", 0)))
        return out

    def import_char_to_campaign(self, campaign_id: str, source_path: str, respec: bool = False) -> Dict[str, Any]:
        """
        Copy an existing .d2s (and its sidecar .key/.ma*/.ctl files) from Solo, Live saves,
        or another campaign profile into `campaign_id`, optionally refunding all stats & skills.
        """
        abs_src = os.path.abspath(source_path or "")
        if not abs_src.lower().endswith(".d2s") or not os.path.isfile(abs_src):
            raise FileNotFoundError(f"Character save not found: {source_path}")

        allowed_roots = [os.path.abspath(self.profiles_dir)]
        live_dir = self.config.get("d2r_save_dir") or ""
        if live_dir:
            allowed_roots.append(os.path.abspath(live_dir))
        if not any(abs_src.startswith(r + os.sep) or os.path.dirname(abs_src) == r for r in allowed_roots):
            raise ValueError("Source character must reside inside D2R saves or CastaliaHub profiles.")

        target_dir = self.profile_dir_for(campaign_id)
        src_dir = os.path.dirname(abs_src)
        base_name = os.path.basename(abs_src)
        stem = os.path.splitext(base_name)[0].lower()
        for fname in os.listdir(src_dir):
            if os.path.splitext(fname)[0].lower() == stem:
                fpath = os.path.join(src_dir, fname)
                if os.path.isfile(fpath):
                    shutil.copy2(fpath, os.path.join(target_dir, fname))

        dst_d2s = os.path.join(target_dir, base_name)
        if respec:
            from mod_builder.char_manager import configure_character_d2s
            configure_character_d2s(dst_d2s, reset_skills=True, reset_stats=True, reroll_seed=False)
        return parse_d2s_telemetry(dst_d2s, d2r_game_dir=self.config.get("d2r_game_dir"))

    def respec_profile_char(self, target: str, char_name: str, reset_stats: bool = True) -> Dict[str, Any]:
        """Launcher-level respec: refund all skill points (and optionally stat points) on a profile .d2s."""
        from mod_builder.char_manager import configure_character_d2s
        pdir = self.profile_dir_for(target)
        low_target = f"{char_name.strip().lower()}.d2s"
        match = next((f for f in os.listdir(pdir) if f.lower() == low_target), None)
        if not match:
            raise FileNotFoundError(f"Character '{char_name}' not found in profile '{target}'.")
        dst_d2s = os.path.join(pdir, match)
        configure_character_d2s(dst_d2s, reset_skills=True, reset_stats=bool(reset_stats), reroll_seed=False)
        # Keep live save folder in sync if this profile is currently active
        if target == "solo":
            live_dir = self.config.get("d2r_save_dir") or ""
            live_copy = os.path.join(live_dir, match)
            if live_dir and os.path.isfile(live_copy):
                shutil.copy2(dst_d2s, live_copy)
        return parse_d2s_telemetry(dst_d2s, d2r_game_dir=self.config.get("d2r_game_dir"))

    @staticmethod
    def browse_directory(title: str = "Select Folder", initial_dir: Optional[str] = None) -> Optional[str]:
        """Open a native OS folder picker dialog and return the chosen path (or None if cancelled)."""
        if sys.platform == "win32":
            safe_title = title.replace("'", "''")
            init_part = ""
            if initial_dir and os.path.isdir(initial_dir):
                safe_init = initial_dir.replace("'", "''")
                init_part = f"$f.SelectedPath = '{safe_init}'; "
            ps = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
                f"$f.Description = '{safe_title}'; "
                f"{init_part}"
                "if ($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $f.SelectedPath }"
            )
            try:
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-STA", "-Command", ps],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                chosen = (res.stdout or "").strip()
                return chosen or None
            except Exception:
                return None

        # Linux: try zenity or kdialog
        for cmd in (
            ["zenity", "--file-selection", "--directory", f"--title={title}"],
            ["kdialog", "--getexistingdirectory", initial_dir or os.path.expanduser("~"), "--title", title],
        ):
            if shutil.which(cmd[0]):
                try:
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    chosen = (res.stdout or "").strip()
                    return chosen or None
                except Exception:
                    return None
        return None

    def test_host_reachability(self, address: Optional[str] = None, timeout: float = 4.0) -> Dict[str, Any]:
        """
        Test whether the configured host address (`host:port`, e.g. playit.gg tunnel)
        accepts TCP connections and optionally returns D2R's 0xAF server greeting.
        """
        raw_addr = (address if address is not None else self.config.get("host_connect_address") or "").strip()
        if not raw_addr:
            return {
                "reachable": False,
                "d2r_greeting": False,
                "address": "",
                "message": "No Host Connect Address configured yet (set your playit.gg IP:port in Settings).",
            }
        host, port = self.parse_host_port(raw_addr)
        t0 = time.monotonic()
        try:
            sock = socket.create_connection((host, port), timeout=timeout)
            latency_ms = int(round((time.monotonic() - t0) * 1000))
            d2r_greeting = False
            try:
                sock.settimeout(0.8)
                data = sock.recv(8)
                if data and data[0] == 0xAF:
                    d2r_greeting = True
            except socket.timeout:
                pass
            finally:
                sock.close()
            if d2r_greeting:
                msg = f"Reachable ({latency_ms} ms) — D2R host server is live and responding!"
            else:
                msg = f"TCP port reachable ({latency_ms} ms) — tunnel is open (start a D2R game to verify full handshake)."
            return {
                "reachable": True,
                "d2r_greeting": d2r_greeting,
                "latency_ms": latency_ms,
                "address": f"{host}:{port}",
                "message": msg,
            }
        except Exception as exc:
            return {
                "reachable": False,
                "d2r_greeting": False,
                "latency_ms": None,
                "address": f"{host}:{port}",
                "message": f"Could not reach {host}:{port} ({exc}). Check that playit.gg / port forwarding is running.",
            }

    def create_dropin_char(
        self,
        target: str,
        char_name: str,
        class_code: str,
        level: int,
        wp_code: str,
        has_cube: Optional[bool] = None,
        host_progress_b64: Optional[str] = None,
    ) -> Dict[str, Any]:
        pdir = self.profile_dir_for(target)
        return generate_dropin_character(
            pdir,
            char_name,
            class_code,
            level,
            wp_code,
            has_cube=has_cube,
            host_progress_b64=host_progress_b64,
        )

    # ── Multi-Version Mod Cache (GitHub Releases + SHA-256) ──────────────────

    def list_cached_versions(self) -> List[str]:
        if not os.path.isdir(self.versions_dir):
            return []
        vers = [d.lstrip("v") for d in sorted(os.listdir(self.versions_dir)) if os.path.isdir(os.path.join(self.versions_dir, d))]
        return vers

    def list_github_releases(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch published Castalia releases from GitHub Releases API (5-min in-memory cache + local fallback)."""
        now = time.time()
        cached = getattr(self, "_releases_cache", None)
        if not force_refresh and cached and (now - cached[0]) < 300:
            return cached[1]
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
        req = urllib.request.Request(url, headers={"User-Agent": "CastaliaHub/1.0", "Accept": "application/vnd.github+json"})
        releases: List[Dict[str, Any]] = []
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                for rel in json.loads(resp.read().decode()):
                    if rel.get("draft"):
                        continue
                    tag = rel.get("tag_name", "")
                    ver = tag.lstrip("v")
                    zip_url = None
                    sha_url = None
                    for a in rel.get("assets", []):
                        if a["name"].endswith(".zip"):
                            zip_url = a["browser_download_url"]
                        elif a["name"].endswith(".sha256"):
                            sha_url = a["browser_download_url"]
                    releases.append({
                        "version": ver,
                        "tag": tag,
                        "published_at": rel.get("published_at", ""),
                        "zip_url": zip_url,
                        "sha_url": sha_url,
                        "cached": os.path.isdir(os.path.join(self.versions_dir, tag)),
                    })
        except Exception:
            pass

        # Include local dev/installed version if not yet in GitHub Releases
        local_cfg = self._load_json(os.path.join(REPO_ROOT, "tools", "mod_builder", "mod_config.json"), {})
        local_ver = local_cfg.get("version")
        if local_ver and not any(r["version"] == local_ver for r in releases):
            releases.insert(0, {
                "version": local_ver,
                "tag": f"v{local_ver}",
                "published_at": "local-dev",
                "zip_url": None,
                "sha_url": None,
                "cached": True,
            })
        if releases:
            self._releases_cache = (now, releases)
        return releases

    def delete_cached_version(self, version: str) -> bool:
        tag = f"v{version.lstrip('v')}"
        vdir = os.path.join(self.versions_dir, tag)
        if os.path.isdir(vdir):
            shutil.rmtree(vdir)
            return True
        return False

    def ensure_version_installed(self, version: str) -> str:
        """
        Ensure <D2R>/mods/castalia/castalia.mpq matches `version`.
        Uses local versions/vX.Y.Z cache or downloads from GitHub Releases with SHA-256 check.
        """
        ver = version.lstrip("v")
        tag = f"v{ver}"
        game_dir = self.config["d2r_game_dir"]
        mod_mpq = os.path.join(game_dir, "mods", "castalia", "castalia.mpq")
        ver_json = os.path.join(mod_mpq, "castalia_version.json")
        if os.path.isfile(ver_json) and self._load_json(ver_json, {}).get("version") == ver:
            return f"already_installed:{ver}"

        cache_dir = os.path.join(self.versions_dir, tag)
        cache_mpq = os.path.join(cache_dir, "mods", "castalia", "castalia.mpq")
        if not os.path.isdir(cache_mpq):
            rels = self.list_github_releases()
            match = next((r for r in rels if r["version"] == ver and r.get("zip_url")), None)
            if not match:
                raise RuntimeError(f"Castalia {tag} is not installed locally and no GitHub Release zip was found.")
            tmp_zip = os.path.join(self.versions_dir, f"castalia-{tag}.zip.tmp")
            urllib.request.urlretrieve(match["zip_url"], tmp_zip)
            if match.get("sha_url"):
                with urllib.request.urlopen(match["sha_url"], timeout=10) as sr:
                    expected_sha = sr.read().decode().strip().split()[0]
                h = hashlib.sha256()
                with open(tmp_zip, "rb") as zf:
                    for chunk in iter(lambda: zf.read(1024 * 1024), b""):
                        h.update(chunk)
                if h.hexdigest() != expected_sha:
                    os.remove(tmp_zip)
                    raise RuntimeError(f"SHA-256 mismatch for castalia-{tag}.zip!")
            os.makedirs(cache_dir, exist_ok=True)
            real_cache = os.path.realpath(cache_dir)
            with zipfile.ZipFile(tmp_zip, "r") as zf:
                for member in zf.infolist():
                    dest = os.path.realpath(os.path.join(real_cache, member.filename))
                    if not (dest == real_cache or dest.startswith(real_cache + os.sep)):
                        raise RuntimeError(f"Unsafe zip entry detected in castalia-{tag}.zip: {member.filename}")
                zf.extractall(real_cache)
            os.remove(tmp_zip)

        # Swap into game mod directory
        if os.path.isdir(mod_mpq):
            shutil.rmtree(mod_mpq)
        os.makedirs(os.path.dirname(mod_mpq), exist_ok=True)
        shutil.copytree(cache_mpq, mod_mpq)
        # Also sync bundled D2RLoader plugins (e.g. castalia-autohost.dll) if included in the release zip
        cache_plugins = os.path.join(cache_dir, "mods", "castalia", "d2rloader", "plugins")
        if os.path.isdir(cache_plugins):
            dst_plugins = os.path.join(game_dir, "mods", "castalia", "d2rloader", "plugins")
            os.makedirs(dst_plugins, exist_ok=True)
            for fn in os.listdir(cache_plugins):
                src_p = os.path.join(cache_plugins, fn)
                if os.path.isfile(src_p):
                    shutil.copy2(src_p, os.path.join(dst_plugins, fn))
        return f"swapped:{ver}"

    # ── Campaign Hub REST API Client ─────────────────────────────────────────

    def _api(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None,
    ) -> Any:
        base = self.config["api_url"].rstrip("/")
        url = f"{base}{path}"
        headers = {"Accept": "application/json", "User-Agent": "CastaliaHub/1.0"}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", "ignore")
            raise RuntimeError(f"API {method} {path} failed ({e.code}): {err_body}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Cannot reach Campaign API at {base}: {e.reason}") from e

    def list_campaigns(self, ruleset: Optional[str] = None, open_only: bool = False) -> List[Dict[str, Any]]:
        qs = {}
        if ruleset:
            qs["ruleset"] = ruleset
        if open_only:
            qs["open_seats"] = "true"
        suffix = ("?" + urllib.parse.urlencode(qs)) if qs else ""
        return self._api("GET", f"/api/campaigns{suffix}")

    def get_campaign(self, campaign_id: str) -> Dict[str, Any]:
        tok = self.get_token(campaign_id, "host_token") or self.get_token(campaign_id, "rsvp_token")
        data = self._api("GET", f"/api/campaigns/{campaign_id}", token=tok)
        data["is_host"] = bool(self.get_token(campaign_id, "host_token"))
        data["my_rsvp_id"] = self.get_token(campaign_id, "rsvp_id")
        if data["is_host"] and data.get("status") != "completed":
            self._auto_bump_campaign_version(data)
        return data

    def create_campaign(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload.setdefault("host_name", self.config["display_name"])
        res = self._api("POST", "/api/campaigns", body=payload)
        cid = res["campaign"]["id"]
        self.save_token(cid, "host_token", res["host_token"])
        self.profile_dir_for(cid)
        return res

    def update_campaign(self, campaign_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        tok = self.get_token(campaign_id, "host_token")
        if not tok:
            raise RuntimeError(f"No local host_token found for campaign '{campaign_id}'")
        return self._api("PATCH", f"/api/campaigns/{campaign_id}", body=updates, token=tok)

    def delete_campaign(self, campaign_id: str) -> Dict[str, Any]:
        tok = self.get_token(campaign_id, "host_token")
        if not tok:
            raise RuntimeError(f"No local host_token found for campaign '{campaign_id}'")
        res = self._api("DELETE", f"/api/campaigns/{campaign_id}", token=tok)
        tokens = self.load_tokens()
        if campaign_id in tokens:
            tokens.pop(campaign_id, None)
            self._save_json(self.tokens_path, tokens)
        return res

    @staticmethod
    def _refresh_playit_tunnel_if_stale(max_age_seconds: int = 1800) -> None:
        """
        On Linux hosts running castalia-playit.service, restart the tunnel daemon before
        publishing Go Live if it has been running longer than `max_age_seconds`.
        Prevents overnight/sleep-stale playit control sessions from silently accepting
        client TCP handshakes without forwarding them to 127.0.0.1:4000.
        """
        if os.name == "nt":
            return
        try:
            active = subprocess.run(
                ["systemctl", "--user", "is-active", "--quiet", "castalia-playit.service"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
            if active.returncode != 0:
                return
            prop = subprocess.run(
                ["systemctl", "--user", "show", "-p", "ActiveEnterTimestamp", "--value", "castalia-playit.service"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            ts_str = (prop.stdout or "").strip()
            stale = True
            if ts_str:
                try:
                    # Format: "Thu 2026-11-26 18:16:02 UTC"
                    parts = ts_str.split()
                    if len(parts) >= 3:
                        dt = datetime.strptime(f"{parts[1]} {parts[2]}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                        age = (datetime.now(timezone.utc) - dt).total_seconds()
                        stale = age > max_age_seconds
                except Exception:
                    stale = True
            if stale:
                subprocess.run(
                    ["systemctl", "--user", "restart", "castalia-playit.service"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=8,
                )
        except Exception:
            pass

    def go_live(self, campaign_id: str, game_id: str) -> Dict[str, Any]:
        tok = self.get_token(campaign_id, "host_token")
        if not tok:
            raise RuntimeError(f"No local host_token found for campaign '{campaign_id}'")
        self._refresh_playit_tunnel_if_stale()
        return self._api("POST", f"/api/campaigns/{campaign_id}/go-live", body={"live_join_info": game_id}, token=tok)

    def end_session(
        self,
        campaign_id: str,
        current_level: Optional[int] = None,
        current_wp: Optional[str] = None,
        next_session_utc: Optional[str] = None,
        has_cube: Optional[bool] = None,
        host_progress_b64: Optional[str] = None,
        session_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        tok = self.get_token(campaign_id, "host_token")
        if not tok:
            raise RuntimeError(f"No local host_token found for campaign '{campaign_id}'")
        body: Dict[str, Any] = {}
        if current_level is not None:
            body["current_level"] = current_level
        if current_wp is not None:
            body["current_wp"] = current_wp
        if next_session_utc is not None:
            body["next_session_utc"] = next_session_utc
        if has_cube is not None:
            body["has_cube"] = bool(has_cube)
        if host_progress_b64:
            body["host_progress_b64"] = str(host_progress_b64)
        if session_seconds is not None and int(session_seconds) > 0:
            body["session_seconds"] = int(session_seconds)
        return self._api("POST", f"/api/campaigns/{campaign_id}/end-session", body=body, token=tok)

    def _import_existing_char_to_campaign(self, campaign_id: str, char_name: str) -> Optional[str]:
        """
        If a player RSVPs as 'returning' with a character that already exists in their live
        D2R save folder or solo profile (e.g. played manually before installing the launcher),
        copy that .d2s and its sidecar files into the campaign's isolated profile folder.
        """
        if not char_name:
            return None
        target_dir = self.profile_dir_for(campaign_id)
        low_target = f"{char_name.lower()}.d2s"
        if any(f.lower() == low_target for f in os.listdir(target_dir)):
            return next(os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.lower() == low_target)

        search_dirs = [
            self.config.get("d2r_save_dir") or "",
            os.path.join(self.profiles_dir, "solo"),
        ]
        for sdir in search_dirs:
            if not sdir or not os.path.isdir(sdir):
                continue
            match_d2s = next((f for f in os.listdir(sdir) if f.lower() == low_target), None)
            if not match_d2s:
                continue
            stem = os.path.splitext(match_d2s)[0].lower()
            for fname in os.listdir(sdir):
                if os.path.splitext(fname)[0].lower() == stem:
                    src = os.path.join(sdir, fname)
                    if os.path.isfile(src):
                        shutil.copy2(src, os.path.join(target_dir, fname))
            return os.path.join(target_dir, match_d2s)
        return None

    def rsvp_campaign(
        self,
        campaign_id: str,
        char_name: str,
        char_class: str,
        join_mode: str = "returning",
        char_level: int = 1,
        char_wp: str = "a1n",
        build_summary: str = "",
        player_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        if join_mode == "returning":
            imported = self._import_existing_char_to_campaign(campaign_id, char_name)
            if imported:
                try:
                    t = parse_d2s_telemetry(imported, d2r_game_dir=self.config.get("d2r_game_dir"))
                    char_level = int(t.get("char_level") or char_level)
                    char_wp = str(t.get("char_wp") or char_wp)
                    char_class = str(t.get("char_class") or char_class)
                    if not build_summary and t.get("build_summary"):
                        build_summary = str(t["build_summary"])
                except Exception:
                    pass
        body = {
            "player_name": player_name or self.config["display_name"],
            "join_mode": join_mode,
            "char_name": char_name,
            "char_class": char_class,
            "char_level": char_level,
            "char_wp": char_wp,
            "build_summary": build_summary,
        }
        res = self._api("POST", f"/api/campaigns/{campaign_id}/rsvp", body=body)
        self.save_token(campaign_id, "rsvp_token", res["rsvp_token"])
        self.save_token(campaign_id, "rsvp_id", res["rsvp"]["id"])
        self.save_token(campaign_id, "char_name", char_name)
        return res

    def cancel_rsvp(self, campaign_id: str, rsvp_id: Optional[str] = None) -> Dict[str, Any]:
        rid = rsvp_id or self.get_token(campaign_id, "rsvp_id")
        tok = self.get_token(campaign_id, "rsvp_token") or self.get_token(campaign_id, "host_token")
        if not rid or not tok:
            raise RuntimeError("No RSVP id or token found for this campaign.")
        return self._api("DELETE", f"/api/campaigns/{campaign_id}/rsvp/{rid}", token=tok)

    def send_telemetry(self, campaign_id: str, telem: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        rid = self.get_token(campaign_id, "rsvp_id")
        tok = self.get_token(campaign_id, "rsvp_token") or self.get_token(campaign_id, "host_token")
        if not rid or not tok:
            return None
        body = {
            "char_name": telem["char_name"],
            "char_class": telem["char_class"],
            "char_level": telem["char_level"],
            "char_wp": telem["char_wp"],
            "build_summary": telem["build_summary"],
        }
        return self._api("PATCH", f"/api/campaigns/{campaign_id}/rsvp/{rid}/telemetry", body=body, token=tok)

    def complete_campaign(self, campaign_id: str, summary: str, death_count: int = 0, sessions_played: int = 1) -> Dict[str, Any]:
        tok = self.get_token(campaign_id, "host_token")
        if not tok:
            raise RuntimeError(f"No local host_token found for campaign '{campaign_id}'")
        return self._api(
            "POST",
            f"/api/campaigns/{campaign_id}/complete",
            body={"summary": summary, "death_count": death_count, "sessions_played": sessions_played},
            token=tok,
        )

    def list_chronicles(self) -> List[Dict[str, Any]]:
        return self._api("GET", "/api/chronicles")

    # ── Clipboard & Launch Handoff ───────────────────────────────────────────

    @staticmethod
    def copy_to_clipboard(text: str) -> bool:
        if not text:
            return False
        cmds = (
            [["clip"]]
            if sys.platform == "win32"
            else [["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"], ["wl-copy"], ["clip"]]
        )
        kwargs: Dict[str, Any] = {"input": text, "text": True, "check": True}
        if sys.platform == "win32":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        for cmd in cmds:
            if shutil.which(cmd[0]):
                try:
                    subprocess.run(cmd, **kwargs)
                    return True
                except Exception:
                    continue
        return False

    @staticmethod
    def _detect_public_ipv4() -> Optional[str]:
        try:
            with urllib.request.urlopen("https://api.ipify.org", timeout=4) as r:
                ip = r.read().decode("utf-8").strip()
                if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
                    return ip
        except Exception:
            pass
        return None

    def _tail_d2rloader_log_for_game_id(self, campaign_id: str, stop_event: threading.Event) -> None:
        log_path = os.path.join(self.config["d2r_game_dir"], "d2rloader", "logs", "d2rloader.log")
        offset = os.path.getsize(log_path) if os.path.isfile(log_path) else 0
        published_id = False
        published_fallback = False
        while not stop_event.is_set() and not published_id:
            if os.path.isfile(log_path):
                try:
                    cur_size = os.path.getsize(log_path)
                    if cur_size < offset:
                        offset = 0  # D2RLoader truncated/rotated d2rloader.log on startup
                    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(offset)
                        chunk = f.read()
                        offset = f.tell()
                    m = GAME_ID_LOG_RE.search(chunk)
                    if m:
                        gid = m.group(1)
                        try:
                            self.go_live(campaign_id, gid)
                            published_id = True
                        except Exception:
                            pass
                    elif not published_fallback and LISTENER_READY_RE.search(chunk):
                        addr = (self.config.get("host_connect_address") or "").strip()
                        if addr:
                            try:
                                self.go_live(campaign_id, addr)
                                published_fallback = True
                            except Exception:
                                pass
                except Exception:
                    pass
            stop_event.wait(1.5)

    @staticmethod
    def parse_host_port(addr: str) -> Tuple[str, int]:
        s = (addr or "").strip()
        if ":" in s and s.count(":") == 1:
            host, port_str = s.rsplit(":", 1)
            if port_str.isdigit():
                return host.strip(), int(port_str)
        return s, 4000

    def set_d2rloader_game_port(self, port: int) -> Optional[int]:
        """Update game_port in d2rloader.toml and return the previous port (for clean restore)."""
        toml_path = os.path.join(self.config["d2r_game_dir"], "d2rloader", "config", "d2rloader.toml")
        if not os.path.isfile(toml_path):
            return None
        with open(toml_path, "r", encoding="utf-8") as f:
            raw = f.read()
        m = re.search(r"^(\s*game_port\s*=\s*)(\d+)(\s*)$", raw, flags=re.M)
        if not m:
            return None
        prev_port = int(m.group(2))
        if prev_port == port:
            return prev_port
        updated = raw[: m.start(2)] + str(port) + raw[m.end(2) :]
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write(updated)
        return prev_port

    def write_launch_intent(self, campaign: Optional[Dict[str, Any]], is_host: bool) -> Optional[str]:
        """Write or clear mods/castalia/d2rloader/config/castalia_launch_intent.json for castalia-autohost.dll."""
        intent_dir = os.path.join(self.config["d2r_game_dir"], "mods", "castalia", "d2rloader", "config")
        intent_path = os.path.join(intent_dir, "castalia_launch_intent.json")
        if campaign is None:
            if os.path.isfile(intent_path):
                os.remove(intent_path)
            return None

        wp = str(campaign.get("current_wp", "a1n")).lower()
        diff_idx = 1 if wp.endswith("nm") else (2 if wp.endswith("h") else 0)
        cid = str(campaign.get("id", ""))
        suffix = cid.rsplit("-", 1)[-1][:4] if "-" in cid else "0000"
        game_name = f"Cas-{wp.upper()}-{suffix}"[:15]
        join_host, join_port = self.parse_host_port(str(campaign.get("live_join_info") or ""))
        payload = {
            "mode": "host" if is_host else "join",
            "campaign_id": str(campaign.get("id", "")),
            "game_name": game_name,
            "description": str(campaign.get("description", ""))[:120],
            "password": "",
            "difficulty": diff_idx,
            "unlisted": False,
            "lan_only": False,
            "max_players": int(campaign.get("max_seats", 5)),
            "level_diff_enabled": False,
            "game_id": join_host,
            "game_port": join_port,
        }
        os.makedirs(intent_dir, exist_ok=True)
        self._save_json(intent_path, payload)
        return intent_path

    @staticmethod
    def _parse_semver(ver: str) -> Optional[Tuple[int, int, int]]:
        m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)$", str(ver or "").strip())
        if not m:
            return None
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))

    def _auto_bump_campaign_version(self, campaign: Dict[str, Any]) -> Optional[str]:
        """
        If a newer published GitHub release exists within the same MAJOR.MINOR line
        (e.g. 0.4.1 -> 0.4.2, but NOT 0.4.x -> 0.5.0 or 1.0.0), automatically bump the
        campaign's pinned castalia_version so Host and joining guests stay in sync.
        """
        cur_ver = str(campaign.get("castalia_version") or "").lstrip("v")
        cur_tuple = self._parse_semver(cur_ver)
        if not cur_tuple:
            return None
        try:
            rels = self.list_github_releases()
        except Exception:
            return None
        best_tuple = cur_tuple
        best_ver: Optional[str] = None
        for rel in rels:
            # Only auto-bump to published releases that guests can actually download
            if not rel.get("zip_url"):
                continue
            rv = str(rel.get("version") or "").lstrip("v")
            rt = self._parse_semver(rv)
            if not rt:
                continue
            if rt[0] == cur_tuple[0] and rt[1] == cur_tuple[1] and rt > best_tuple:
                best_tuple = rt
                best_ver = rv
        if not best_ver:
            return None
        try:
            self.update_campaign(campaign["id"], {"castalia_version": best_ver})
            campaign["castalia_version"] = best_ver
            return best_ver
        except Exception:
            return None

    def launch_session(self, target: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Full launch lifecycle:
          1. If campaign: fetch snapshot, auto-bump patch version (same MAJOR.MINOR) for Host,
             sync pinned mod version, write castalia_launch_intent.json,
             auto-configure d2rloader.toml game_port for custom playit.gg ports, copy host/Game ID to clipboard
          2. Swap isolated save profile into live mods/castalia/
          3. Launch D2RLoader (via bin/d2r-mod --coop on Linux or D2RLoader.exe on Windows)
          4. On exit: restore game_port, clear intent, sync saves back, parse .d2s telemetry & auto-roll Host
        """
        campaign = None
        is_host = False
        copied_game_id = None
        prev_game_port = None

        if target != "solo":
            campaign = self.get_campaign(target)
            is_host = bool(campaign.get("is_host"))
            if is_host and not dry_run:
                self._auto_bump_campaign_version(campaign)
            ver_status = self.ensure_version_installed(campaign["castalia_version"])
            if campaign.get("live_join_info") and not is_host:
                join_host, join_port = self.parse_host_port(str(campaign["live_join_info"]))
                copied_game_id = join_host
                self.copy_to_clipboard(join_host)
                if join_port != 4000 and not dry_run:
                    prev_game_port = self.set_d2rloader_game_port(join_port)
        else:
            ver_status = "solo_current"

        intent_path = self.write_launch_intent(campaign, is_host)
        if campaign and is_host and intent_path:
            intent_data = self._load_json(intent_path, {})
            if intent_data.get("game_name"):
                self.copy_to_clipboard(intent_data["game_name"])
        use_shared_stash = bool(campaign.get("shared_stash")) if campaign else True
        pid = self.swap_to_profile(target, shared_stash=use_shared_stash)
        if prev_game_port is not None and os.path.isfile(self.active_profile_path):
            ap = self._load_json(self.active_profile_path, {})
            ap["prev_game_port"] = prev_game_port
            self._save_json(self.active_profile_path, ap)
        result: Dict[str, Any] = {
            "profile_id": pid,
            "version_status": ver_status,
            "copied_game_id": copied_game_id,
            "launch_intent_path": intent_path,
            "dry_run": dry_run,
        }
        if dry_run:
            return result

        stop_evt = threading.Event()
        tail_thread = None
        if campaign and is_host:
            tail_thread = threading.Thread(
                target=self._tail_d2rloader_log_for_game_id,
                args=(target, stop_evt),
                daemon=True,
            )
            tail_thread.start()

        session_t0 = time.monotonic()
        try:
            d2r_mod_bin = os.path.join(REPO_ROOT, "bin", "d2r-mod")
            if sys.platform != "win32" and os.path.isfile(d2r_mod_bin):
                cmd = ["bash", d2r_mod_bin, "--coop"] if campaign else ["bash", d2r_mod_bin]
                subprocess.run(cmd, check=False)
            else:
                loader_exe = os.path.join(self.config["d2r_game_dir"], "D2RLoader.exe")
                if not os.path.isfile(loader_exe):
                    raise RuntimeError(
                        f"D2RLoader.exe not found in '{self.config['d2r_game_dir']}'. "
                        "Install D2RLoader (https://d2rloader.net/) into your D2R folder "
                        "or update your D2R Game Directory in Settings."
                    )
                subprocess.run(
                    [loader_exe, "-mod", "castalia", "-txt"],
                    cwd=self.config["d2r_game_dir"],
                    check=False,
                )
        finally:
            session_seconds = max(0, int(round(time.monotonic() - session_t0)))
            stop_evt.set()
            if tail_thread:
                tail_thread.join(timeout=2)
            if prev_game_port is not None:
                self.set_d2rloader_game_port(prev_game_port)
            self.write_launch_intent(None, False)
            self.sync_back_active_profile()
            if target != "solo":
                self._restore_solo_to_live()

        # Post-exit .d2s telemetry & Host auto-rollover
        chars = self.list_profile_chars(target)
        if campaign and chars:
            latest_char = chars[0]
            result["post_session_char"] = latest_char
            try:
                self.send_telemetry(target, latest_char)
            except Exception as e:
                result["telemetry_error"] = str(e)
            if is_host and latest_char.get("char_level"):
                try:
                    rolled = self.end_session(
                        target,
                        current_level=int(latest_char["char_level"]),
                        current_wp=str(latest_char["char_wp"]),
                        has_cube=bool(latest_char.get("has_cube", False)),
                        host_progress_b64=latest_char.get("host_progress_b64"),
                        session_seconds=session_seconds,
                    )
                    result["host_rollover"] = rolled
                except Exception as e:
                    result["rollover_error"] = str(e)
                if latest_char.get("hell_baal_cleared"):
                    result["hell_baal_victory_prompt"] = True
        return result
