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

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GITHUB_REPO = "grant0711/d2r-castalia"
DEFAULT_DATA_DIR = os.path.expanduser("~/.local/share/castalia-hub")
DEFAULT_API_URL = os.environ.get("CASTALIA_API_URL", "http://127.0.0.1:8787")

# Save extensions swapped per campaign profile (Settings.json stays global & untouched!)
SAVE_EXTS = (".d2s", ".d2i", ".key", ".ctl", ".map", ".ma0", ".ma1", ".ma2", ".ma3", ".ma4")
GAME_ID_LOG_RE = re.compile(r"(?:Game\s*ID|game_id|advertised_id)\s*[:=]\s*([A-Za-z0-9_-]{4,24})", re.I)


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
        self.config_path = os.path.join(self.data_dir, "config.json")
        self.tokens_path = os.path.join(self.data_dir, "tokens.json")
        self.active_profile_path = os.path.join(self.data_dir, "active_profile.json")

        os.makedirs(self.versions_dir, exist_ok=True)
        os.makedirs(self.profiles_dir, exist_ok=True)
        os.makedirs(os.path.join(self.profiles_dir, "solo"), exist_ok=True)

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
        os.replace(tmp, path)

    def get_config(self) -> Dict[str, Any]:
        return dict(self.config)

    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        for k in ("api_url", "display_name", "d2r_game_dir", "d2r_save_dir"):
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
        candidates = [
            os.path.join(
                REPO_ROOT,
                "prefixes",
                "acct1",
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
        return "solo" if target == "solo" else (target if target.startswith("campaign-") else f"campaign-{target}")

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
            if _is_save_file(fn):
                shutil.copy2(os.path.join(live_dir, fn), os.path.join(solo_dir, fn))
                copied += 1
        return copied

    def recover_if_dirty(self) -> Optional[str]:
        """If active_profile.json exists (previous crash), sync live saves back to that profile."""
        if not os.path.isfile(self.active_profile_path):
            return None
        state = self._load_json(self.active_profile_path, {})
        pid = state.get("profile_id")
        if pid:
            self._sync_live_to_profile(pid)
        os.remove(self.active_profile_path)
        return pid

    def _sync_live_to_profile(self, profile_id: str) -> int:
        live_dir = self.config["d2r_save_dir"]
        pdir = self.profile_dir_for(profile_id)
        if not os.path.isdir(live_dir):
            return 0
        # Remove old save files in profile dir that were deleted in-game, then copy live saves
        for fn in os.listdir(pdir):
            if _is_save_file(fn):
                os.remove(os.path.join(pdir, fn))
        count = 0
        for fn in os.listdir(live_dir):
            if _is_save_file(fn):
                shutil.copy2(os.path.join(live_dir, fn), os.path.join(pdir, fn))
                count += 1
        return count

    def swap_to_profile(self, target: str) -> str:
        """
        Crash-safe swap: recover any dirty profile, clear live save files (preserving Settings.json),
        copy target profile into live save dir, and write active_profile.json lockfile.
        """
        self.migrate_initial_solo_saves()
        self.recover_if_dirty()

        pid = self.profile_id_for(target)
        pdir = self.profile_dir_for(pid)
        live_dir = self.config["d2r_save_dir"]
        os.makedirs(live_dir, exist_ok=True)

        for fn in os.listdir(live_dir):
            if _is_save_file(fn):
                os.remove(os.path.join(live_dir, fn))

        for fn in os.listdir(pdir):
            if _is_save_file(fn):
                shutil.copy2(os.path.join(pdir, fn), os.path.join(live_dir, fn))

        self._save_json(
            self.active_profile_path,
            {
                "profile_id": pid,
                "switched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "pid": os.getpid(),
            },
        )
        return pid

    def sync_back_active_profile(self) -> Optional[str]:
        """Sync live saves back to the active profile and clear active_profile.json."""
        if not os.path.isfile(self.active_profile_path):
            return None
        state = self._load_json(self.active_profile_path, {})
        pid = state.get("profile_id")
        if pid:
            self._sync_live_to_profile(pid)
        os.remove(self.active_profile_path)
        return pid

    def list_profile_chars(self, target: str) -> List[Dict[str, Any]]:
        """List all .d2s characters (with telemetry & build summary) in a profile."""
        if target == "solo":
            self.migrate_initial_solo_saves()
        pdir = self.profile_dir_for(target)
        chars = []
        for fn in sorted(os.listdir(pdir)):
            if fn.lower().endswith(".d2s"):
                full = os.path.join(pdir, fn)
                try:
                    chars.append(parse_d2s_telemetry(full))
                except Exception as e:
                    chars.append({"char_name": os.path.splitext(fn)[0], "error": str(e), "path": full})
        chars.sort(key=lambda c: -float(c.get("mtime", 0)))
        return chars

    def create_dropin_char(
        self,
        target: str,
        char_name: str,
        class_code: str,
        level: int,
        wp_code: str,
    ) -> Dict[str, Any]:
        pdir = self.profile_dir_for(target)
        return generate_dropin_character(pdir, char_name, class_code, level, wp_code)

    # ── Multi-Version Mod Cache (GitHub Releases + SHA-256) ──────────────────

    def list_cached_versions(self) -> List[str]:
        if not os.path.isdir(self.versions_dir):
            return []
        vers = [d.lstrip("v") for d in sorted(os.listdir(self.versions_dir)) if os.path.isdir(os.path.join(self.versions_dir, d))]
        return vers

    def list_github_releases(self) -> List[Dict[str, Any]]:
        """Fetch published Castalia releases from GitHub Releases API (with local fallback)."""
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
            with zipfile.ZipFile(tmp_zip, "r") as zf:
                zf.extractall(cache_dir)
            os.remove(tmp_zip)

        # Swap into game mod directory
        if os.path.isdir(mod_mpq):
            shutil.rmtree(mod_mpq)
        os.makedirs(os.path.dirname(mod_mpq), exist_ok=True)
        shutil.copytree(cache_mpq, mod_mpq)
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

    def go_live(self, campaign_id: str, game_id: str) -> Dict[str, Any]:
        tok = self.get_token(campaign_id, "host_token")
        if not tok:
            raise RuntimeError(f"No local host_token found for campaign '{campaign_id}'")
        return self._api("POST", f"/api/campaigns/{campaign_id}/go-live", body={"live_join_info": game_id}, token=tok)

    def end_session(
        self,
        campaign_id: str,
        current_level: Optional[int] = None,
        current_wp: Optional[str] = None,
        next_session_utc: Optional[str] = None,
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
        return self._api("POST", f"/api/campaigns/{campaign_id}/end-session", body=body, token=tok)

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
        for cmd in (["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"], ["wl-copy"], ["clip"]):
            if shutil.which(cmd[0]):
                try:
                    subprocess.run(cmd, input=text, text=True, check=True)
                    return True
                except Exception:
                    continue
        return False

    def _tail_d2rloader_log_for_game_id(self, campaign_id: str, stop_event: threading.Event) -> None:
        log_path = os.path.join(self.config["d2r_game_dir"], "d2rloader", "logs", "d2rloader.log")
        offset = os.path.getsize(log_path) if os.path.isfile(log_path) else 0
        published = False
        while not stop_event.is_set() and not published:
            if os.path.isfile(log_path):
                try:
                    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(offset)
                        chunk = f.read()
                        offset = f.tell()
                    m = GAME_ID_LOG_RE.search(chunk)
                    if m:
                        gid = m.group(1)
                        try:
                            self.go_live(campaign_id, gid)
                            published = True
                        except Exception:
                            pass
                except Exception:
                    pass
            stop_event.wait(1.5)

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
        clean_title = re.sub(r"[^A-Za-z0-9]", "", str(campaign.get("title", "Castalia")))
        game_name = f"Cas-{clean_title}"[:15]
        payload = {
            "mode": "host" if is_host else "join",
            "campaign_id": str(campaign.get("id", "")),
            "game_name": game_name,
            "description": str(campaign.get("description", ""))[:120],
            "password": "",
            "difficulty": diff_idx,
            "unlisted": True,
            "lan_only": False,
            "max_players": int(campaign.get("max_seats", 5)),
            "level_diff_enabled": False,
            "game_id": str(campaign.get("live_join_info") or ""),
        }
        os.makedirs(intent_dir, exist_ok=True)
        self._save_json(intent_path, payload)
        return intent_path

    def launch_session(self, target: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Full launch lifecycle:
          1. If campaign: fetch snapshot, sync pinned mod version, write castalia_launch_intent.json, copy Game ID
          2. Swap isolated save profile into live mods/castalia/
          3. Launch D2RLoader (via bin/d2r-mod --coop on Linux or D2RLoader.exe on Windows)
          4. On exit: clear intent, sync saves back, parse .d2s telemetry, update RSVP & auto-roll Host progress
        """
        campaign = None
        is_host = False
        copied_game_id = None

        if target != "solo":
            campaign = self.get_campaign(target)
            is_host = bool(campaign.get("is_host"))
            ver_status = self.ensure_version_installed(campaign["castalia_version"])
            if campaign.get("live_join_info"):
                copied_game_id = campaign["live_join_info"]
                self.copy_to_clipboard(copied_game_id)
        else:
            ver_status = "solo_current"

        intent_path = self.write_launch_intent(campaign, is_host)
        if campaign and is_host and intent_path:
            intent_data = self._load_json(intent_path, {})
            if intent_data.get("game_name"):
                self.copy_to_clipboard(intent_data["game_name"])
        pid = self.swap_to_profile(target)
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

        try:
            d2r_mod_bin = os.path.join(REPO_ROOT, "bin", "d2r-mod")
            if sys.platform != "win32" and os.path.isfile(d2r_mod_bin):
                cmd = [d2r_mod_bin, "--coop"] if campaign else [d2r_mod_bin]
                subprocess.run(cmd, check=False)
            else:
                loader_exe = os.path.join(self.config["d2r_game_dir"], "D2RLoader.exe")
                subprocess.run([loader_exe], cwd=self.config["d2r_game_dir"], check=False)
        finally:
            stop_evt.set()
            if tail_thread:
                tail_thread.join(timeout=2)
            self.write_launch_intent(None, False)
            self.sync_back_active_profile()

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
                    )
                    result["host_rollover"] = rolled
                except Exception as e:
                    result["rollover_error"] = str(e)
                if latest_char.get("hell_baal_cleared"):
                    result["hell_baal_victory_prompt"] = True
        return result
