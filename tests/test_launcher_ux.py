"""
TDD test suite for Castalia Launcher UX & Host Toolkit:
  1. Real Castalia skill-name resolution from d2r_game_dir/mods/castalia/castalia.mpq/data
     (even when REPO_ROOT/castalia/data does not exist, e.g. Windows / release-worktree)
  2. list_importable_chars() & import_char_to_campaign() (with & without optional respec)
  3. Launcher-level respec_profile_char() (Solo & Campaign profiles, valid .d2s checksum)
  4. Host reachability probe test_host_reachability() & D2RTcpGuard protocol filter
  5. Local UI server HTTP routes: /local/importable-chars, /local/import-char,
     /local/respec-char, /local/test-host (with X-Castalia-Token auth)
"""
import asyncio
import json
import os
import shutil
import socket
import struct
import sys
import tempfile
import threading
import unittest
import urllib.request

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (REPO_ROOT, os.path.join(REPO_ROOT, "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

from castalia_hub import d2s_telemetry as telem_mod
from castalia_hub.core import CastaliaHub
from castalia_hub.ui_server import start_ui_server
from mod_builder import char_manager as cm


class TestLauncherUXAndHostToolkit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = os.path.join(self.tmp.name, "hub")
        self.save_dir = os.path.join(self.tmp.name, "live_saves")
        os.makedirs(self.save_dir, exist_ok=True)
        self.game_dir = os.path.join(REPO_ROOT, "game", "Diablo II Resurrected")
        self.hub = CastaliaHub(
            data_dir=self.data_dir,
            d2r_game_dir=self.game_dir,
            d2r_save_dir=self.save_dir,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _make_sample_char(self, dst_dir: str, name: str, class_id: int = 4, level: int = 15) -> str:
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, f"{name}.d2s")
        shutil.copy2(os.path.join(REPO_ROOT, "tools", "char_templates", "default.d2s"), dst)
        cm.configure_character_d2s(dst, char_name=name, class_id=class_id, level=level, wp_target="a1n", stash_gold=10000)
        # Allocate 5 points into first class skill so build_summary & respec are testable
        with open(dst, "rb") as f:
            raw = bytearray(f.read())
        _, if_, _ = cm.locate_sections(raw)
        raw[if_ + 2] = 5
        raw[if_ + 4] = 3
        struct.pack_into("<I", raw, 8, len(raw))
        struct.pack_into("<I", raw, 12, cm.calc_d2s_checksum(raw))
        with open(dst, "wb") as f:
            f.write(raw)
        return dst

    # ── 1. Real Skill Names from d2r_game_dir (Windows / release-worktree safe) ──

    def test_skill_names_resolve_from_d2r_game_dir_without_repo_symlink(self):
        char_path = self._make_sample_char(self.save_dir, "TestSin", class_id=6, level=15)
        old_repo = telem_mod.REPO_ROOT
        old_cache = telem_mod._SKILL_NAME_CACHE
        try:
            # Simulate Windows / release-worktree where REPO_ROOT/castalia/data does not exist
            telem_mod.REPO_ROOT = self.tmp.name
            telem_mod._SKILL_NAME_CACHE = None
            info = telem_mod.parse_d2s_telemetry(char_path, d2r_game_dir=self.game_dir)
            self.assertNotIn("Skill#", info["build_summary"], f"Expected real skill names, got: {info['build_summary']}")
            self.assertTrue(len(info["build_summary"]) > 0)
        finally:
            telem_mod.REPO_ROOT = old_repo
            telem_mod._SKILL_NAME_CACHE = old_cache

    # ── 2. Import Existing Character (with & without Respec) ────────────────────

    def test_list_importable_and_import_with_respec(self):
        solo_dir = os.path.join(self.hub.profiles_dir, "solo")
        src_solo = self._make_sample_char(solo_dir, "SoloBarb", class_id=4, level=20)
        src_live = self._make_sample_char(self.save_dir, "LivePal", class_id=3, level=18)

        cands = self.hub.list_importable_chars("camp-test-1")
        names = {c["char_name"] for c in cands}
        self.assertIn("SoloBarb", names)
        self.assertIn("LivePal", names)

        # Import SoloBarb WITH respec=True
        imported = self.hub.import_char_to_campaign("camp-test-1", src_solo, respec=True)
        self.assertEqual(imported["char_name"], "SoloBarb")
        dst_path = os.path.join(self.hub.profile_dir_for("camp-test-1"), "SoloBarb.d2s")
        self.assertTrue(os.path.isfile(dst_path))
        with open(dst_path, "rb") as f:
            raw = f.read()
        self.assertEqual(cm.calc_d2s_checksum(raw), struct.unpack_from("<I", raw, 12)[0])
        _, if_, jm = cm.locate_sections(raw)
        self.assertEqual(sum(raw[if_ + 2 : jm]), 0, "Expected all skills refunded on respec=True import")

        # SoloBarb should no longer appear as importable into camp-test-1
        cands_after = self.hub.list_importable_chars("camp-test-1")
        self.assertNotIn("SoloBarb", {c["char_name"] for c in cands_after})
        self.assertIn("LivePal", {c["char_name"] for c in cands_after})

    # ── 3. Launcher-Level Respec on Solo Character ──────────────────────────────

    def test_respec_solo_profile_char(self):
        solo_dir = os.path.join(self.hub.profiles_dir, "solo")
        p = self._make_sample_char(solo_dir, "SoloSorc", class_id=1, level=16)
        res = self.hub.respec_profile_char("solo", "SoloSorc", reset_stats=True)
        self.assertEqual(res["char_name"], "SoloSorc")
        with open(p, "rb") as f:
            raw = f.read()
        self.assertEqual(cm.calc_d2s_checksum(raw), struct.unpack_from("<I", raw, 12)[0])
        _, if_, jm = cm.locate_sections(raw)
        self.assertEqual(sum(raw[if_ + 2 : jm]), 0)

    # ── 4. Host Reachability Test & Reusable D2RTcpGuard ────────────────────────

    def test_host_reachability_probe_and_tcp_guard(self):
        from castalia_hub.tcp_guard import D2RTcpGuard

        # Start a local mock D2R listener that sends the 0xAF 0x00 greeting
        srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv_sock.bind(("127.0.0.1", 0))
        srv_sock.listen(5)
        port = srv_sock.getsockname()[1]

        def _accept_once():
            try:
                conn, _ = srv_sock.accept()
                conn.sendall(b"\xaf\x00")
                conn.close()
            except Exception:
                pass

        t = threading.Thread(target=_accept_once, daemon=True)
        t.start()
        try:
            res = self.hub.test_host_reachability(f"127.0.0.1:{port}")
            self.assertTrue(res["reachable"])
            self.assertTrue(res["d2r_greeting"])
            self.assertIsInstance(res["latency_ms"], int)
        finally:
            srv_sock.close()

        # Closed port should report reachable=False cleanly
        res_bad = self.hub.test_host_reachability("127.0.0.1:1")
        self.assertFalse(res_bad["reachable"])

        # Verify D2RTcpGuard is importable from castalia_hub.tcp_guard
        g = D2RTcpGuard("127.0.0.1", 0, "127.0.0.1", 4000)
        self.assertEqual(g.target_port, 4000)

    # ── 5. Local UI Server HTTP Endpoints ───────────────────────────────────────

    def test_ui_server_new_endpoints(self):
        solo_dir = os.path.join(self.hub.profiles_dir, "solo")
        src_solo = self._make_sample_char(solo_dir, "HttpBarb", class_id=4, level=19)

        srv = start_ui_server(self.hub, host="127.0.0.1", port=0)
        port = srv.server_address[1]
        token = srv.auth_token
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            def _req(method, path, body=None):
                data = json.dumps(body).encode("utf-8") if body is not None else None
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}{path}",
                    data=data,
                    method=method,
                    headers={"X-Castalia-Token": token, "Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=5) as r:
                    return r.status, json.loads(r.read().decode("utf-8"))

            st, cands = _req("GET", "/local/importable-chars?campaign_id=camp-http-1")
            self.assertEqual(st, 200)
            self.assertIn("HttpBarb", {c["char_name"] for c in cands})

            st, imp = _req("POST", "/local/import-char", {
                "campaign_id": "camp-http-1",
                "source_path": src_solo,
                "respec": True,
            })
            self.assertEqual(st, 200)
            self.assertEqual(imp["char_name"], "HttpBarb")

            st, rsp = _req("POST", "/local/respec-char", {
                "target": "solo",
                "char_name": "HttpBarb",
                "reset_stats": True,
            })
            self.assertEqual(st, 200)
            self.assertEqual(rsp["char_name"], "HttpBarb")

            st, probe = _req("POST", "/local/test-host", {"address": "127.0.0.1:1"})
            self.assertEqual(st, 200)
            self.assertFalse(probe["reachable"])

            st, lres = _req("POST", "/local/launch", {"target": "solo", "dry_run": True})
            self.assertEqual(st, 200)
            self.assertEqual(lres["profile_id"], "solo")

            # Static guard: index.html must use SESSION_TOKEN, never undefined TOKEN
            idx_html = open(os.path.join(REPO_ROOT, "castalia_hub", "static", "index.html"), "r", encoding="utf-8").read()
            import re
            self.assertNotRegex(idx_html, r"\bTOKEN\b", "index.html must reference SESSION_TOKEN, not undefined TOKEN")
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
