"""
castalia_hub/local_server.py — Local SQLite Campaign Hub REST API server.
Implements the exact REST contract in docs/systems/LAUNCHER_SPEC.md so you can
develop, test, and run LAN/self-hosted campaigns immediately with zero external deps.
"""
import datetime
import hashlib
import json
import os
import re
import secrets
import sqlite3
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS campaigns (
  id                TEXT PRIMARY KEY,
  host_name         TEXT NOT NULL,
  host_token_hash   TEXT NOT NULL,
  title             TEXT NOT NULL,
  description       TEXT NOT NULL,
  ruleset           TEXT NOT NULL DEFAULT 'standard',
  castalia_version  TEXT NOT NULL,
  current_level     INTEGER NOT NULL DEFAULT 1,
  current_wp        TEXT NOT NULL DEFAULT 'a1n',
  has_cube          INTEGER NOT NULL DEFAULT 0,
  host_progress_b64 TEXT,
  shared_stash      INTEGER NOT NULL DEFAULT 0,
  campaign_mode     TEXT NOT NULL DEFAULT 'pilgrimage',
  pilgrimage_scope  TEXT NOT NULL DEFAULT 'full',
  total_play_seconds INTEGER NOT NULL DEFAULT 0,
  host_char_name    TEXT,
  host_char_hash    TEXT,
  pilgrimage_invalidated_reason TEXT,
  max_seats         INTEGER NOT NULL DEFAULT 5,
  schedule_text     TEXT NOT NULL,
  recurrence_days   INTEGER DEFAULT 7,
  next_session_utc  TEXT,
  status            TEXT NOT NULL DEFAULT 'recruiting',
  live_join_info    TEXT,
  discord_msg_id    TEXT,
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rsvps (
  id                TEXT PRIMARY KEY,
  campaign_id       TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  session_utc       TEXT NOT NULL,
  player_name       TEXT NOT NULL,
  rsvp_token_hash   TEXT NOT NULL,
  join_mode         TEXT NOT NULL DEFAULT 'returning',
  char_name         TEXT NOT NULL,
  char_class        TEXT NOT NULL,
  char_level        INTEGER NOT NULL DEFAULT 1,
  char_wp           TEXT NOT NULL DEFAULT 'a1n',
  build_summary     TEXT NOT NULL DEFAULT '',
  char_hash         TEXT,
  status            TEXT NOT NULL DEFAULT 'confirmed',
  created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chronicles (
  id                TEXT PRIMARY KEY,
  campaign_id       TEXT NOT NULL REFERENCES campaigns(id),
  completed_at      TEXT NOT NULL,
  sessions_played   INTEGER NOT NULL DEFAULT 1,
  death_count       INTEGER NOT NULL DEFAULT 0,
  total_play_seconds INTEGER NOT NULL DEFAULT 0,
  pilgrimage_scope  TEXT NOT NULL DEFAULT 'full',
  party_roster_json TEXT NOT NULL,
  summary           TEXT NOT NULL,
  screenshot_url    TEXT
);
"""


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def _hash_token(tok: str) -> str:
    return hashlib.sha256(tok.encode("utf-8")).hexdigest()


def _slugify(title: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:24] or "campaign"
    return f"{base}-{secrets.token_hex(2)}"


def _advance_iso_days(iso_str: Optional[str], days: Optional[int]) -> Optional[str]:
    if not iso_str or not days:
        return iso_str
    try:
        dt = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return (dt + datetime.timedelta(days=int(days))).replace(microsecond=0).isoformat()
    except Exception:
        return iso_str


class CampaignDB:
    def __init__(self, db_path: str, discord_webhook: Optional[str] = None, hoh_webhook: Optional[str] = None):
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.db_path = db_path
        self.discord_webhook = discord_webhook or os.environ.get("DISCORD_CAMPAIGN_WEBHOOK_URL", "")
        self.hoh_webhook = hoh_webhook or os.environ.get("DISCORD_HOH_WEBHOOK_URL", "") or self.discord_webhook
        self._lock = threading.Lock()
        with self._conn() as conn:
            conn.executescript(SCHEMA_SQL)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _public_campaign(row: sqlite3.Row, include_live: bool = False, rsvps=None) -> Dict[str, Any]:
        d = dict(row)
        d.pop("host_token_hash", None)
        if not include_live or d.get("status") != "live":
            d["live_join_info"] = None
        if rsvps is not None:
            d["rsvps"] = rsvps
            d["confirmed_seats"] = sum(1 for r in rsvps if r["status"] == "confirmed")
        return d

    @staticmethod
    def _public_rsvp(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d.pop("rsvp_token_hash", None)
        return d

    def _post_discord(self, webhook: str, embed: Dict[str, Any], message_id: Optional[str] = None) -> Optional[str]:
        if not webhook:
            return message_id
        try:
            url = f"{webhook}/messages/{message_id}" if message_id else f"{webhook}?wait=true"
            method = "PATCH" if message_id else "POST"
            req = urllib.request.Request(
                url,
                data=json.dumps({"embeds": [embed]}).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "CastaliaHub/1.0"},
                method=method,
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8") or "{}")
                return data.get("id") or message_id
        except Exception:
            return message_id

    def _sync_campaign_discord(self, camp: Dict[str, Any], confirmed_count: int) -> Optional[str]:
        if not self.discord_webhook:
            return camp.get("discord_msg_id")
        status_emoji = {"live": "🟢 LIVE", "recruiting": "🟡 Recruiting", "active": "🔵 Active", "completed": "🏆 Completed"}.get(
            camp["status"], camp["status"]
        )
        embed = {
            "title": f"{status_emoji} — {camp['title']} (v{camp['castalia_version']})",
            "description": camp["description"][:1500],
            "color": 0x43B581 if camp["status"] == "live" else 0xC89B3C,
            "fields": [
                {"name": "Host", "value": camp["host_name"], "inline": True},
                {"name": "Ruleset", "value": camp["ruleset"], "inline": True},
                {"name": "Seats", "value": f"{confirmed_count}/{camp['max_seats']}", "inline": True},
                {"name": "Progress", "value": f"Lvl {camp['current_level']} · `{camp['current_wp']}`", "inline": True},
                {"name": "Schedule", "value": camp["schedule_text"], "inline": True},
            ],
        }
        return self._post_discord(self.discord_webhook, embed, camp.get("discord_msg_id"))

    # ── Operations ───────────────────────────────────────────────────────────

    def list_campaigns(self, ruleset: Optional[str] = None, open_only: bool = False):
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM campaigns WHERE status IN ('recruiting', 'active', 'live') ORDER BY updated_at DESC"
            ).fetchall()
            out = []
            for r in rows:
                if ruleset and r["ruleset"] != ruleset:
                    continue
                rsvps = [
                    self._public_rsvp(x)
                    for x in conn.execute(
                        "SELECT * FROM rsvps WHERE campaign_id = ? AND status != 'cancelled' ORDER BY created_at ASC",
                        (r["id"],),
                    ).fetchall()
                ]
                item = self._public_campaign(r, include_live=False, rsvps=rsvps)
                if open_only and item["confirmed_seats"] >= item["max_seats"]:
                    continue
                out.append(item)
            return out

    def get_campaign(self, cid: str, bearer: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (cid,)).fetchone()
            if not row:
                return None
            rsvp_rows = conn.execute(
                "SELECT * FROM rsvps WHERE campaign_id = ? AND status != 'cancelled' ORDER BY created_at ASC",
                (cid,),
            ).fetchall()
            include_live = False
            if bearer:
                h = _hash_token(bearer)
                if h == row["host_token_hash"] or any(x["rsvp_token_hash"] == h and x["status"] == "confirmed" for x in rsvp_rows):
                    include_live = True
            return self._public_campaign(row, include_live=include_live, rsvps=[self._public_rsvp(x) for x in rsvp_rows])

    def create_campaign(self, body: Dict[str, Any]) -> Dict[str, Any]:
        cid = _slugify(body.get("title", "campaign"))
        host_token = secrets.token_urlsafe(24)
        now = _now_iso()
        raw_mode = str(body.get("campaign_mode") or "").strip().lower()
        req_lvl = max(1, min(99, int(body.get("current_level", 1))))
        req_wp = str(body.get("current_wp") or "a1n").strip()
        if raw_mode in ("pilgrimage", "open"):
            mode = raw_mode
        else:
            mode = "open" if (req_lvl > 1 or req_wp.lower() != "a1n") else "pilgrimage"
        raw_scope = str(body.get("pilgrimage_scope") or "full").strip().lower()
        scope = raw_scope if raw_scope in ("full", "normal", "nightmare", "hell") else "full"
        scope_starts = {"full": (1, "a1n"), "normal": (1, "a1n"), "nightmare": (38, "a1nm"), "hell": (65, "a1h")}
        if mode == "pilgrimage":
            start_lvl, start_wp = scope_starts[scope]
        else:
            start_lvl, start_wp = req_lvl, req_wp
        with self._lock, self._conn() as conn:
            conn.execute(
                """INSERT INTO campaigns (
                    id, host_name, host_token_hash, title, description, ruleset,
                    castalia_version, current_level, current_wp, shared_stash, campaign_mode, pilgrimage_scope, max_seats,
                    schedule_text, recurrence_days, next_session_utc, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'recruiting', ?, ?)""",
                (
                    cid,
                    str(body.get("host_name") or "Host").strip(),
                    _hash_token(host_token),
                    str(body.get("title") or "Untitled Campaign").strip(),
                    str(body.get("description") or "").strip(),
                    str(body.get("ruleset") or "standard").strip(),
                    str(body.get("castalia_version") or "0.3.0").strip().lstrip("v"),
                    start_lvl,
                    start_wp,
                    1 if body.get("shared_stash") else 0,
                    mode,
                    scope,
                    max(2, min(8, int(body.get("max_seats", 5)))),
                    str(body.get("schedule_text") or "Weekly").strip(),
                    body.get("recurrence_days", 7),
                    body.get("next_session_utc"),
                    now,
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (cid,)).fetchone()
            camp = self._public_campaign(row, include_live=False, rsvps=[])
            msg_id = self._sync_campaign_discord(camp, 0)
            if msg_id:
                conn.execute("UPDATE campaigns SET discord_msg_id = ? WHERE id = ?", (msg_id, cid))
                camp["discord_msg_id"] = msg_id
            return {"campaign": camp, "host_token": host_token}

    def _require_host(self, conn: sqlite3.Connection, cid: str, bearer: Optional[str]) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (cid,)).fetchone()
        if not row:
            raise KeyError(f"Campaign '{cid}' not found")
        if not bearer or _hash_token(bearer) != row["host_token_hash"]:
            raise PermissionError("Invalid or missing host_token")
        return row

    def update_campaign(self, cid: str, body: Dict[str, Any], bearer: Optional[str]) -> Dict[str, Any]:
        allowed = (
            "title", "description", "ruleset", "castalia_version",
            "current_level", "current_wp", "max_seats", "schedule_text",
            "recurrence_days", "next_session_utc", "status",
            "host_char_name", "host_char_hash", "pilgrimage_invalidated_reason",
        )
        with self._lock, self._conn() as conn:
            existing = self._require_host(conn, cid, bearer)
            sets, vals = [], []
            for k in allowed:
                if k in body and body[k] is not None:
                    # host_char_name is locked once set on a campaign
                    if k == "host_char_name" and existing["host_char_name"]:
                        continue
                    v = body[k]
                    if k == "castalia_version":
                        v = str(v).strip().lstrip("v")
                    sets.append(f"{k} = ?")
                    vals.append(v)
            sets.append("updated_at = ?")
            vals.append(_now_iso())
            vals.append(cid)
            conn.execute(f"UPDATE campaigns SET {', '.join(sets)} WHERE id = ?", vals)
            row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (cid,)).fetchone()
            rsvps = [
                self._public_rsvp(x)
                for x in conn.execute("SELECT * FROM rsvps WHERE campaign_id = ? AND status != 'cancelled'", (cid,)).fetchall()
            ]
            camp = self._public_campaign(row, include_live=True, rsvps=rsvps)
            self._sync_campaign_discord(camp, camp["confirmed_seats"])
            return camp

    def delete_campaign(self, cid: str, bearer: Optional[str]) -> Dict[str, Any]:
        with self._lock, self._conn() as conn:
            self._require_host(conn, cid, bearer)
            conn.execute("DELETE FROM chronicles WHERE campaign_id = ?", (cid,))
            conn.execute("DELETE FROM campaigns WHERE id = ?", (cid,))
            return {"deleted": cid}

    def go_live(self, cid: str, join_info: str, bearer: Optional[str]) -> Dict[str, Any]:
        with self._lock, self._conn() as conn:
            self._require_host(conn, cid, bearer)
            conn.execute(
                "UPDATE campaigns SET status = 'live', live_join_info = ?, updated_at = ? WHERE id = ?",
                (join_info.strip(), _now_iso(), cid),
            )
            row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (cid,)).fetchone()
            rsvps = [
                self._public_rsvp(x)
                for x in conn.execute("SELECT * FROM rsvps WHERE campaign_id = ? AND status != 'cancelled'", (cid,)).fetchall()
            ]
            camp = self._public_campaign(row, include_live=True, rsvps=rsvps)
            self._sync_campaign_discord(camp, camp["confirmed_seats"])
            return camp

    def end_session(self, cid: str, body: Dict[str, Any], bearer: Optional[str]) -> Dict[str, Any]:
        with self._lock, self._conn() as conn:
            row = self._require_host(conn, cid, bearer)
            new_lvl = int(body.get("current_level", row["current_level"]))
            new_wp = str(body.get("current_wp") or row["current_wp"])
            if "has_cube" in body and body["has_cube"] is not None:
                has_cube = 1 if body["has_cube"] else 0
            else:
                has_cube = int(row["has_cube"]) if new_wp.lower() in ("start", "a1n", "a2n") else 1
            host_prog = body.get("host_progress_b64")
            if host_prog is None:
                host_prog = row["host_progress_b64"]
            else:
                host_prog = str(host_prog)[:600]
            next_utc = body.get("next_session_utc") or None
            is_pilgrimage = str(row["campaign_mode"] or "pilgrimage") == "pilgrimage"
            add_sec = max(0, int(body.get("session_seconds") or 0)) if is_pilgrimage else 0
            total_sec = int(row["total_play_seconds"] or 0) + add_sec
            host_char_name = row["host_char_name"] or (str(body.get("host_char_name")).strip()[:15] if body.get("host_char_name") else None)
            host_char_hash = str(body.get("host_char_hash")).strip()[:64] if body.get("host_char_hash") else row["host_char_hash"]
            inval_reason = row["pilgrimage_invalidated_reason"] or (
                str(body.get("pilgrimage_invalidated_reason")).strip()[:200] if body.get("pilgrimage_invalidated_reason") else None
            )
            conn.execute(
                """UPDATE campaigns
                   SET status = 'active', live_join_info = NULL,
                       current_level = ?, current_wp = ?, has_cube = ?, host_progress_b64 = ?,
                       total_play_seconds = ?, host_char_name = ?, host_char_hash = ?,
                       pilgrimage_invalidated_reason = ?, next_session_utc = ?, updated_at = ?
                   WHERE id = ?""",
                (new_lvl, new_wp, has_cube, host_prog, total_sec, host_char_name, host_char_hash, inval_reason, next_utc, _now_iso(), cid),
            )
            updated = conn.execute("SELECT * FROM campaigns WHERE id = ?", (cid,)).fetchone()
            rsvps = [
                self._public_rsvp(x)
                for x in conn.execute("SELECT * FROM rsvps WHERE campaign_id = ? AND status != 'cancelled'", (cid,)).fetchall()
            ]
            camp = self._public_campaign(updated, include_live=False, rsvps=rsvps)
            self._sync_campaign_discord(camp, camp["confirmed_seats"])
            return camp

    def rsvp(self, cid: str, body: Dict[str, Any]) -> Dict[str, Any]:
        rid = f"rsvp-{secrets.token_hex(4)}"
        tok = secrets.token_urlsafe(24)
        now = _now_iso()
        with self._lock, self._conn() as conn:
            row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (cid,)).fetchone()
            if not row:
                raise KeyError(f"Campaign '{cid}' not found")
            char_name = str(body.get("char_name") or "Hero").strip()[:15]
            dup = conn.execute(
                "SELECT id FROM rsvps WHERE campaign_id = ? AND status != 'cancelled' AND LOWER(char_name) = LOWER(?)",
                (cid, char_name),
            ).fetchone()
            if dup:
                raise FileExistsError(
                    f"Character name '{char_name}' is already taken in this campaign (D2RLoader rejects duplicate names in TCP/IP games). Pick a different name."
                )
            confirmed = conn.execute(
                "SELECT COUNT(*) FROM rsvps WHERE campaign_id = ? AND status = 'confirmed'", (cid,)
            ).fetchone()[0]
            status = "confirmed" if confirmed < row["max_seats"] else "waitlist"
            conn.execute(
                """INSERT INTO rsvps (
                    id, campaign_id, session_utc, player_name, rsvp_token_hash,
                    join_mode, char_name, char_class, char_level, char_wp,
                    build_summary, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    rid,
                    cid,
                    str(row["next_session_utc"] or now),
                    str(body.get("player_name") or "Player").strip(),
                    _hash_token(tok),
                    str(body.get("join_mode") or "returning"),
                    char_name,
                    str(body.get("char_class") or "pal").strip().lower(),
                    int(body.get("char_level", row["current_level"])),
                    str(body.get("char_wp") or row["current_wp"]),
                    str(body.get("build_summary") or ""),
                    status,
                    now,
                ),
            )
            rrow = conn.execute("SELECT * FROM rsvps WHERE id = ?", (rid,)).fetchone()
            return {"rsvp": self._public_rsvp(rrow), "rsvp_token": tok}

    def update_telemetry(self, cid: str, rid: str, body: Dict[str, Any], bearer: Optional[str]) -> Dict[str, Any]:
        with self._lock, self._conn() as conn:
            crow = conn.execute("SELECT * FROM campaigns WHERE id = ?", (cid,)).fetchone()
            rrow = conn.execute("SELECT * FROM rsvps WHERE id = ? AND campaign_id = ?", (rid, cid)).fetchone()
            if not crow or not rrow:
                raise KeyError("Campaign or RSVP not found")
            if not bearer or _hash_token(bearer) not in (rrow["rsvp_token_hash"], crow["host_token_hash"]):
                raise PermissionError("Invalid rsvp_token or host_token")
            new_name = str(body.get("char_name") or rrow["char_name"]).strip()[:15]
            dup = conn.execute(
                "SELECT id FROM rsvps WHERE campaign_id = ? AND status != 'cancelled' AND id != ? AND LOWER(char_name) = LOWER(?)",
                (cid, rid, new_name),
            ).fetchone()
            if dup:
                raise FileExistsError(
                    f"Character name '{new_name}' is already taken in this campaign (D2RLoader rejects duplicate names in TCP/IP games)."
                )
            new_hash = str(body.get("char_hash")).strip()[:64] if body.get("char_hash") else rrow["char_hash"]
            conn.execute(
                """UPDATE rsvps
                   SET char_name = ?, char_class = ?, char_level = ?, char_wp = ?, build_summary = ?, char_hash = ?
                   WHERE id = ?""",
                (
                    new_name,
                    str(body.get("char_class") or rrow["char_class"]).lower(),
                    int(body.get("char_level", rrow["char_level"])),
                    str(body.get("char_wp") or rrow["char_wp"]),
                    str(body.get("build_summary") or rrow["build_summary"]),
                    new_hash,
                    rid,
                ),
            )
            updated = conn.execute("SELECT * FROM rsvps WHERE id = ?", (rid,)).fetchone()
            return self._public_rsvp(updated)

    def cancel_rsvp(self, cid: str, rid: str, bearer: Optional[str]) -> Dict[str, Any]:
        with self._lock, self._conn() as conn:
            crow = conn.execute("SELECT * FROM campaigns WHERE id = ?", (cid,)).fetchone()
            rrow = conn.execute("SELECT * FROM rsvps WHERE id = ? AND campaign_id = ?", (rid, cid)).fetchone()
            if not crow or not rrow:
                raise KeyError("Campaign or RSVP not found")
            if not bearer or _hash_token(bearer) not in (rrow["rsvp_token_hash"], crow["host_token_hash"]):
                raise PermissionError("Invalid rsvp_token or host_token")
            was_confirmed = rrow["status"] == "confirmed"
            conn.execute("UPDATE rsvps SET status = 'cancelled' WHERE id = ?", (rid,))
            promoted = None
            if was_confirmed:
                nxt = conn.execute(
                    "SELECT id FROM rsvps WHERE campaign_id = ? AND status = 'waitlist' ORDER BY created_at ASC LIMIT 1",
                    (cid,),
                ).fetchone()
                if nxt:
                    conn.execute("UPDATE rsvps SET status = 'confirmed' WHERE id = ?", (nxt["id"],))
                    promoted = nxt["id"]
            return {"cancelled": rid, "promoted": promoted}

    def complete_campaign(self, cid: str, body: Dict[str, Any], bearer: Optional[str]) -> Dict[str, Any]:
        with self._lock, self._conn() as conn:
            crow = self._require_host(conn, cid, bearer)
            if str(crow["campaign_mode"] or "pilgrimage") != "pilgrimage":
                raise ValueError("Only Pilgrimage campaigns are eligible for Hall of Heroes.")
            if crow["pilgrimage_invalidated_reason"]:
                raise ValueError(f"Pilgrimage integrity was voided: {crow['pilgrimage_invalidated_reason']}")
            rsvps = [
                self._public_rsvp(x)
                for x in conn.execute("SELECT * FROM rsvps WHERE campaign_id = ? AND status = 'confirmed'", (cid,)).fetchall()
            ]
            now = _now_iso()
            chid = f"chron-{secrets.token_hex(4)}"
            roster_json = json.dumps(rsvps)
            conn.execute(
                "UPDATE campaigns SET status = 'completed', live_join_info = NULL, updated_at = ? WHERE id = ?",
                (now, cid),
            )
            conn.execute(
                """INSERT INTO chronicles (
                    id, campaign_id, completed_at, sessions_played, death_count,
                    total_play_seconds, pilgrimage_scope, party_roster_json, summary, screenshot_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    chid,
                    cid,
                    now,
                    int(body.get("sessions_played", 1)),
                    int(body.get("death_count", 0)),
                    int(crow["total_play_seconds"] or 0),
                    str(crow["pilgrimage_scope"] or "full"),
                    roster_json,
                    str(body.get("summary") or f"{crow['title']} cleared Baal!"),
                    body.get("screenshot_url"),
                ),
            )
            ch_row = conn.execute("SELECT * FROM chronicles WHERE id = ?", (chid,)).fetchone()
            out = dict(ch_row)
            out["party_roster"] = rsvps
            out["title"] = crow["title"]
            out["castalia_version"] = crow["castalia_version"]
            out["ruleset"] = crow["ruleset"]
            out["shared_stash"] = bool(crow["shared_stash"])
            if self.hoh_webhook:
                self._post_discord(
                    self.hoh_webhook,
                    {
                        "title": f"🏆 Hall of Heroes — {crow['title']} (v{crow['castalia_version']})",
                        "description": out["summary"],
                        "color": 0xF0D890,
                    },
                )
            return out

    def list_chronicles(self):
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                """SELECT ch.*, c.title, c.host_name, c.ruleset, c.castalia_version, c.shared_stash
                   FROM chronicles ch JOIN campaigns c ON c.id = ch.campaign_id
                   ORDER BY ch.completed_at DESC"""
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                try:
                    d["party_roster"] = json.loads(d.pop("party_roster_json", "[]"))
                except Exception:
                    d["party_roster"] = []
                out.append(d)
            return out


def make_handler(db: CampaignDB):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            if os.environ.get("CASTALIA_API_QUIET") != "1":
                super().log_message(fmt, *args)

        def _send(self, code: int, payload: Any):
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
            self.end_headers()
            self.wfile.write(raw)

        def _bearer(self) -> Optional[str]:
            auth = self.headers.get("Authorization", "")
            return auth[7:].strip() if auth.startswith("Bearer ") else None

        def _read_json(self) -> Dict[str, Any]:
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0:
                return {}
            return json.loads(self.rfile.read(n).decode("utf-8"))

        def do_OPTIONS(self):
            self._send(200, {"ok": True})

        def _dispatch(self, method: str):
            parsed = urllib.parse.urlparse(self.path)
            parts = [p for p in parsed.path.strip("/").split("/") if p]
            qs = urllib.parse.parse_qs(parsed.query)
            bearer = self._bearer()
            try:
                if parts == ["api", "campaigns"] and method == "GET":
                    ruleset = qs.get("ruleset", [None])[0]
                    open_only = qs.get("open_seats", ["false"])[0].lower() == "true"
                    return self._send(200, db.list_campaigns(ruleset=ruleset, open_only=open_only))
                if parts == ["api", "campaigns"] and method == "POST":
                    return self._send(201, db.create_campaign(self._read_json()))
                if parts == ["api", "chronicles"] and method == "GET":
                    return self._send(200, db.list_chronicles())
                if len(parts) >= 3 and parts[0] == "api" and parts[1] == "campaigns":
                    cid = parts[2]
                    if len(parts) == 3 and method == "GET":
                        res = db.get_campaign(cid, bearer=bearer)
                        return self._send(200, res) if res else self._send(404, {"error": "not_found"})
                    if len(parts) == 3 and method == "PATCH":
                        return self._send(200, db.update_campaign(cid, self._read_json(), bearer))
                    if len(parts) == 3 and method == "DELETE":
                        return self._send(200, db.delete_campaign(cid, bearer))
                    if len(parts) == 4 and parts[3] == "go-live" and method == "POST":
                        body = self._read_json()
                        return self._send(200, db.go_live(cid, str(body.get("live_join_info", "")), bearer))
                    if len(parts) == 4 and parts[3] == "end-session" and method == "POST":
                        return self._send(200, db.end_session(cid, self._read_json(), bearer))
                    if len(parts) == 4 and parts[3] == "rsvp" and method == "POST":
                        return self._send(201, db.rsvp(cid, self._read_json()))
                    if len(parts) == 4 and parts[3] == "complete" and method == "POST":
                        return self._send(200, db.complete_campaign(cid, self._read_json(), bearer))
                    if len(parts) == 5 and parts[3] == "rsvp" and method == "DELETE":
                        return self._send(200, db.cancel_rsvp(cid, parts[4], bearer))
                    if len(parts) == 6 and parts[3] == "rsvp" and parts[5] == "telemetry" and method == "PATCH":
                        return self._send(200, db.update_telemetry(cid, parts[4], self._read_json(), bearer))
                self._send(404, {"error": "unknown_route"})
            except PermissionError as e:
                self._send(403, {"error": str(e)})
            except KeyError as e:
                self._send(404, {"error": str(e)})
            except FileExistsError as e:
                self._send(409, {"error": str(e)})
            except Exception as e:
                self._send(400, {"error": str(e)})

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        def do_PATCH(self):
            self._dispatch("PATCH")

        def do_DELETE(self):
            self._dispatch("DELETE")

    return Handler


def start_local_api_server(
    db_path: str,
    host: str = "127.0.0.1",
    port: int = 8787,
) -> Tuple[ThreadingHTTPServer, CampaignDB]:
    db = CampaignDB(db_path)
    srv = ThreadingHTTPServer((host, port), make_handler(db))
    return srv, db
