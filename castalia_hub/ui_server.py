"""
castalia_hub/ui_server.py — Local HTTP bridge serving the Castalia Launcher desktop UI
and exposing castalia_hub.core methods as clean /local/* JSON endpoints.
"""
import hmac
import json
import os
import secrets
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict

from castalia_hub.core import CastaliaHub

STATIC_DIR = os.path.join(
    getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))),
    "castalia_hub",
    "static",
)


def make_ui_handler(hub: CastaliaHub):
    session_token = secrets.token_hex(24)

    class UIHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            if os.environ.get("CASTALIA_UI_QUIET") != "1":
                super().log_message(fmt, *args)

        def _send_security_headers(self):
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'",
            )

        def _check_local_auth(self) -> bool:
            host = (self.headers.get("Host") or "").split(":")[0].lower()
            if host not in ("127.0.0.1", "localhost"):
                self._send_json(403, {"error": "forbidden_host"})
                return False
            origin = self.headers.get("Origin") or ""
            if origin and not (origin.startswith("http://127.0.0.1") or origin.startswith("http://localhost")):
                self._send_json(403, {"error": "forbidden_origin"})
                return False
            tok = self.headers.get("X-Castalia-Token") or ""
            if not hmac.compare_digest(tok, session_token):
                self._send_json(403, {"error": "invalid_session_token"})
                return False
            return True

        def _send_json(self, code: int, payload: Any):
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self._send_security_headers()
            self.end_headers()
            self.wfile.write(raw)

        def _send_html(self, path: str):
            with open(path, "r", encoding="utf-8") as f:
                html = f.read().replace("__CASTALIA_TOKEN__", session_token)
            raw = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self._send_security_headers()
            self.end_headers()
            self.wfile.write(raw)

        def _read_json(self) -> Dict[str, Any]:
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n).decode("utf-8")) if n > 0 else {}

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            p = parsed.path
            qs = urllib.parse.parse_qs(parsed.query)
            try:
                if p in ("/", "/index.html"):
                    host = (self.headers.get("Host") or "").split(":")[0].lower()
                    if host not in ("127.0.0.1", "localhost"):
                        return self._send_json(403, {"error": "forbidden_host"})
                    return self._send_html(os.path.join(STATIC_DIR, "index.html"))
                if not self._check_local_auth():
                    return
                if p == "/local/state":
                    return self._send_json(200, {
                        "config": hub.get_config(),
                        "env": hub.detect_d2r_env(),
                        "tokens": list(hub.load_tokens().keys()),
                    })
                if p == "/local/versions":
                    return self._send_json(200, hub.list_github_releases())
                if p == "/local/campaigns":
                    ruleset = qs.get("ruleset", [None])[0]
                    open_only = qs.get("open_seats", ["false"])[0].lower() == "true"
                    return self._send_json(200, hub.list_campaigns(ruleset=ruleset, open_only=open_only))
                if p.startswith("/local/campaigns/"):
                    cid = p.split("/")[3]
                    return self._send_json(200, hub.get_campaign(cid))
                if p.startswith("/local/chars/"):
                    target = p.split("/")[3]
                    return self._send_json(200, hub.list_profile_chars(target))
                if p == "/local/chronicles":
                    return self._send_json(200, hub.list_chronicles())
                if p == "/local/tokens/export":
                    return self._send_json(200, {"tokens_json": hub.export_tokens_json()})
                self._send_json(404, {"error": "not_found"})
            except Exception as e:
                self._send_json(400, {"error": str(e)})

        def do_POST(self):
            if not self._check_local_auth():
                return
            parsed = urllib.parse.urlparse(self.path)
            p = parsed.path
            try:
                body = self._read_json()
                if p == "/local/config":
                    return self._send_json(200, hub.update_config(body))
                if p == "/local/tokens/import":
                    cnt = hub.import_tokens_json(body.get("tokens_json", "{}"))
                    return self._send_json(200, {"imported": cnt})
                if p == "/local/campaigns":
                    return self._send_json(201, hub.create_campaign(body))
                if p == "/local/dropin":
                    target = body["target"]
                    telem = hub.create_dropin_char(
                        target,
                        body["char_name"],
                        body["char_class"],
                        int(body["level"]),
                        body["wp_code"],
                        has_cube=body.get("has_cube"),
                        host_progress_b64=body.get("host_progress_b64"),
                    )
                    return self._send_json(201, telem)
                if p == "/local/rsvp":
                    return self._send_json(201, hub.rsvp_campaign(
                        body["campaign_id"],
                        char_name=body["char_name"],
                        char_class=body["char_class"],
                        join_mode=body.get("join_mode", "returning"),
                        char_level=int(body.get("char_level", 1)),
                        char_wp=body.get("char_wp", "a1n"),
                        build_summary=body.get("build_summary", ""),
                    ))
                if p == "/local/rsvp/cancel":
                    return self._send_json(200, hub.cancel_rsvp(body["campaign_id"], body.get("rsvp_id")))
                if p == "/local/live":
                    return self._send_json(200, hub.go_live(body["campaign_id"], body["game_id"]))
                if p == "/local/end-session":
                    return self._send_json(200, hub.end_session(
                        body["campaign_id"],
                        current_level=body.get("current_level"),
                        current_wp=body.get("current_wp"),
                        next_session_utc=body.get("next_session_utc"),
                    ))
                if p == "/local/upgrade":
                    return self._send_json(200, hub.update_campaign(body["campaign_id"], {"castalia_version": body["version"]}))
                if p == "/local/schedule":
                    updates: Dict[str, Any] = {}
                    if body.get("schedule_text") is not None:
                        updates["schedule_text"] = str(body["schedule_text"]).strip()[:60]
                    if body.get("next_session_utc") is not None:
                        updates["next_session_utc"] = str(body["next_session_utc"]).strip()[:40]
                    return self._send_json(200, hub.update_campaign(body["campaign_id"], updates))
                if p == "/local/delete":
                    return self._send_json(200, hub.delete_campaign(body["campaign_id"]))
                if p == "/local/complete":
                    return self._send_json(200, hub.complete_campaign(
                        body["campaign_id"],
                        summary=body.get("summary", ""),
                        death_count=int(body.get("death_count", 0)),
                        sessions_played=int(body.get("sessions_played", 1)),
                    ))
                if p == "/local/clipboard":
                    ok = hub.copy_to_clipboard(body.get("text", ""))
                    return self._send_json(200, {"copied": ok})
                if p == "/local/version/delete":
                    ok = hub.delete_cached_version(body["version"])
                    return self._send_json(200, {"deleted": ok})
                if p == "/local/launch":
                    target = body["target"]
                    dry = bool(body.get("dry_run", False))
                    if dry:
                        return self._send_json(200, hub.launch_session(target, dry_run=True))
                    # Run D2RLoader in background thread so UI stays responsive
                    t = threading.Thread(target=hub.launch_session, args=(target, False), daemon=True)
                    t.start()
                    return self._send_json(200, {"launched": True, "target": target})
                self._send_json(404, {"error": "not_found"})
            except Exception as e:
                self._send_json(400, {"error": str(e)})

    return UIHandler


def start_ui_server(hub: CastaliaHub, host: str = "127.0.0.1", port: int = 8788) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_ui_handler(hub))
